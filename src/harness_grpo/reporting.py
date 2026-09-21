"""Strict per-question, per-batch success accounting. No fabricated or imputed results."""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev

from .records import EpisodeRecord, read_jsonl

GROUP_FIELDS = ("run_id", "variant", "split", "batch_id", "task_id", "domain", "policy_version", "seed")


def summarize(records, expected_samples, allow_incomplete=False):
    if type(expected_samples) is not int or expected_samples < 1:
        raise ValueError("Expected samples must be an explicit positive integer")
    groups, seen, assignments = defaultdict(list), set(), {}
    for value in records:
        record = value if isinstance(value, EpisodeRecord) else EpisodeRecord.from_dict(value)
        record.validate()
        identity = (record.run_id, record.variant, record.split, record.seed, record.task_id, record.sample_index)
        if identity in seen:
            raise ValueError(f"Duplicate trajectory: {identity}")
        seen.add(identity)
        task_identity = identity[:-1]
        assignment = (record.batch_id, record.domain, record.policy_version)
        if task_identity in assignments and assignments[task_identity] != assignment:
            raise ValueError("One question's group crosses batch/domain/policy versions")
        assignments[task_identity] = assignment
        if record.sample_index >= expected_samples:
            raise ValueError("Sample index exceeds expected group size")
        key = tuple(getattr(record, name) for name in GROUP_FIELDS)
        groups[key].append(record)
    if not groups:
        raise ValueError("No trajectory results; refusing to invent an experimental chart")
    question_rows = []
    for key, group in sorted(groups.items()):
        group.sort(key=lambda r: r.sample_index)
        scored = [r for r in group if r.success is not None]
        complete = len(group) == expected_samples and len(scored) == expected_samples
        if not complete and not allow_incomplete:
            raise ValueError(f"Incomplete or unscored group: {key}; retain and resolve it, do not silently skip")
        success_count = sum(r.success is True for r in group)
        rewards = [r.reward for r in scored]
        question_rows.append({
            **dict(zip(GROUP_FIELDS, key)), "expected_samples": expected_samples,
            "observed_samples": len(group), "scored_samples": len(scored),
            "success_count": success_count, "failure_count": sum(r.success is False for r in group),
            "unscored_count": len(group) - len(scored), "complete": complete,
            "success_rate": success_count / expected_samples if complete else None,
            "mean_reward": mean(rewards) if rewards else None,
            "reward_std": pstdev(rewards) if rewards else None,
            "success_flags": [next((r.success for r in group if r.sample_index == i), None) for i in range(expected_samples)],
            "rewards": [next((r.reward for r in group if r.sample_index == i), None) for i in range(expected_samples)],
            "statuses": [next((r.status for r in group if r.sample_index == i), "missing") for i in range(expected_samples)],
        })
    batches = defaultdict(list)
    for row in question_rows:
        batches[(row["run_id"], row["variant"], row["split"], row["batch_id"], row["policy_version"], row["seed"])].append(row)
    batch_rows = []
    for key, rows in sorted(batches.items()):
        complete = all(row["complete"] for row in rows)
        histogram = Counter(row["success_count"] for row in rows if row["complete"])
        total = sum(row["success_count"] for row in rows)
        batch_rows.append({
            **dict(zip(("run_id", "variant", "split", "batch_id", "policy_version", "seed"), key)),
            "question_count": len(rows), "complete_question_count": sum(row["complete"] for row in rows),
            "expected_trajectories": len(rows) * expected_samples,
            "observed_trajectories": sum(row["observed_samples"] for row in rows),
            "success_count": total, "complete": complete,
            "success_rate": total / (len(rows) * expected_samples) if complete else None,
            "success_histogram": {str(i): histogram[i] for i in range(expected_samples + 1)},
            "zero_reward_std_groups": sum(row["complete"] and row["reward_std"] == 0 for row in rows),
            "mixed_success_groups": sum(row["complete"] and 0 < row["success_count"] < expected_samples for row in rows),
        })
    return question_rows, batch_rows


def _csv(path, rows):
    with Path(path).open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})


def write_reports(records, output_dir, expected_samples, allow_incomplete=False):
    questions, batches = summarize(records, expected_samples, allow_incomplete)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=False)
    _csv(destination / "question_success.csv", questions)
    _csv(destination / "batch_summary.csv", batches)
    for name, rows in (("question_success", questions), ("batch_summary", batches)):
        with (destination / f"{name}.jsonl").open("x", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    return questions, batches


def load_records(paths):
    return [EpisodeRecord.from_dict(value) for path in paths for value in read_jsonl(path)]
