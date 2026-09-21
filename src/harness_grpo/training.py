"""Provider-independent batch barriers and sequential checkpoint transitions."""

import json
from pathlib import Path

from .records import write_jsonl
from .reporting import write_reports


def ordered_batches(tasks, task_ids):
    """Use a saved explicit order; do not invent a sampling schedule or resample failed tasks."""
    by_id = {task["id"]: task for task in tasks}
    if len(by_id) != len(tasks) or len(task_ids) != len(tasks) or set(task_ids) != set(by_id):
        raise ValueError("Saved order must contain every unique training task exactly once")
    if len(tasks) % 100:
        raise ValueError("Question count must be divisible by the confirmed 100-question batch size")
    ordered = [by_id[identifier] for identifier in task_ids]
    return [ordered[start:start + 100] for start in range(0, len(ordered), 100)]


def collect_and_update_batches(*, tasks, task_ids, initial_version, collect_episode,
                               update_policy, output_dir, resolved_config):
    """Low-level engine; formal callers must validate config/data first.

    collect_episode(task,batch_id,sample_index,policy_version) must finish one full
    episode. update_policy(records,old_version,batch_id) must persist its checkpoint
    and return the next immutable version ID. No next-batch sampling happens earlier.
    All 800 records survive, including similarity rejections and zero-variance groups.
    A service error persists partial records and stops without retrying or updating.
    """
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "resolved_config.json").write_text(json.dumps(resolved_config, ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "task_order.json").write_text(json.dumps(task_ids, ensure_ascii=False, indent=2), encoding="utf-8")
    version = initial_version
    for batch_id, batch in enumerate(ordered_batches(tasks, task_ids), 1):
        batch_dir = destination / f"batch_{batch_id:03d}"
        batch_dir.mkdir()
        records = []
        try:
            for task in batch:
                for sample_index in range(8):
                    record = collect_episode(task, batch_id, sample_index, version)
                    record.validate()
                    records.append(record)
                    if (record.task_id, record.batch_id, record.sample_index, record.policy_version, record.domain, record.split) != (
                            task["id"], batch_id, sample_index, version, task["domain"], "train"):
                        raise ValueError("Collector returned mismatched task/group/policy metadata")
                    if record.status == "infrastructure_error":
                        raise RuntimeError("Infrastructure error: batch stopped, no retry and no policy update")
        except Exception:
            write_jsonl(batch_dir / "partial_trajectories.jsonl", (r.to_dict() for r in records))
            raise
        write_jsonl(batch_dir / "trajectories.jsonl", (r.to_dict() for r in records))
        write_reports(records, batch_dir / "statistics", expected_samples=8)
        next_version = update_policy(records, version, batch_id)
        if not isinstance(next_version, str) or not next_version or next_version == version:
            raise ValueError("Updater must persist and return a new checkpoint version")
        (batch_dir / "transition.json").write_text(json.dumps({
            "batch_id": batch_id, "old_policy": version, "new_policy": next_version,
            "questions": 100, "trajectories": 800,
        }, indent=2), encoding="utf-8")
        version = next_version
    return version


def evaluate_frozen_policy(*, tasks, samples_per_question, policy_version, collect_episode, output_dir):
    """Log every test attempt from one frozen checkpoint. No hidden-answer candidate selection."""
    if type(samples_per_question) is not int or samples_per_question < 1:
        raise ValueError("Test samples per question must be explicitly confirmed")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=False)
    records = []
    try:
        for task_index, task in enumerate(tasks):
            if task["split"] != "test":
                raise ValueError("Evaluation requires test tasks")
            batch_id = task_index // 100 + 1
            for sample_index in range(samples_per_question):
                record = collect_episode(task, batch_id, sample_index, policy_version)
                record.validate()
                records.append(record)
                if (record.task_id, record.batch_id, record.sample_index, record.policy_version, record.split) != (
                        task["id"], batch_id, sample_index, policy_version, "test"):
                    raise ValueError("Test collector returned mismatched metadata")
                if record.status == "infrastructure_error":
                    raise RuntimeError("Unscored infrastructure error in test evaluation")
    except Exception:
        write_jsonl(destination / "partial_trajectories.jsonl", (r.to_dict() for r in records))
        raise
    write_jsonl(destination / "trajectories.jsonl", (r.to_dict() for r in records))
    write_reports(records, destination / "statistics", samples_per_question)
    return records
