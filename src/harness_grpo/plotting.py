"""Plots from verified episode records only. All denominators are explicit."""

from collections import defaultdict
from pathlib import Path

from .records import DOMAINS, VARIANTS
from .reporting import summarize


def plot_results(records, output_dir, expected_samples, comparison=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    questions, batches = summarize(records, expected_samples, allow_incomplete=False)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=False)
    # Separate every run/variant/seed/split: never average unrelated checkpoints or runs.
    groups = defaultdict(list)
    for row in questions:
        groups[(row["run_id"], row["variant"], row["seed"], row["split"])].append(row)
    written = []
    for group_number, (key, rows) in enumerate(sorted(groups.items()), 1):
        rows.sort(key=lambda row: (row["batch_id"], row["task_id"]))
        flags = np.array([[int(v) for v in row["success_flags"]] for row in rows])
        fig, ax = plt.subplots(figsize=(max(8, min(24, len(rows) / 10)), 4))
        ax.imshow(flags.T, aspect="auto", interpolation="nearest", vmin=0, vmax=1, cmap="RdYlGn")
        ax.set(xlabel="Question index (batch then task ID; mapping in JSONL)", ylabel="Independent trajectory index",
               title=f"{key[1]} | {key[3]} | run={key[0]} seed={key[2]} (green=success, red=failure)")
        ax.set_yticks(range(expected_samples))
        for i in range(1, len(rows)):
            if rows[i]["batch_id"] != rows[i - 1]["batch_id"]:
                ax.axvline(i - 0.5, color="black", linewidth=0.8)
        fig.tight_layout()
        path = destination / f"trajectory_results_{group_number}.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        written.append(path)
        import json
        with (destination / f"trajectory_results_{group_number}_index.jsonl").open("x", encoding="utf-8") as stream:
            for index, row in enumerate(rows):
                stream.write(json.dumps({"column": index, **{k: row[k] for k in ("task_id", "domain", "batch_id", "run_id", "seed", "variant", "split")}}) + "\n")

    train = [row for row in batches if row["split"] == "train"]
    if train:
        fig, ax = plt.subplots(figsize=(9, 5))
        series = defaultdict(list)
        for row in train:
            series[(row["run_id"], row["variant"], row["seed"])].append(row)
        for key, values in sorted(series.items()):
            values.sort(key=lambda row: row["batch_id"])
            ax.plot([r["batch_id"] for r in values], [r["success_rate"] for r in values], marker="o", label=str(key))
        ax.set(xlabel="Training batch (different questions)", ylabel="Trajectory success rate", ylim=(0, 1),
               title="Training batch diagnostics; not a fixed-test learning curve")
        ax.legend(fontsize=8)
        fig.tight_layout()
        path = destination / "batch_success.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        written.append(path)

    if comparison:
        test = [row for row in questions if row["split"] == "test"]
        if {row["variant"] for row in test} != set(VARIANTS):
            raise ValueError("Comparison requires actual test results for all four approved variants")
        identities = {}
        for variant in VARIANTS:
            values = [row for row in test if row["variant"] == variant]
            if len({row["run_id"] for row in values}) != 1:
                raise ValueError("Select one experiment run per variant for a comparison")
            identities[variant] = {(row["seed"], row["task_id"], row["domain"]) for row in values}
            for seed in {r["seed"] for r in values}:
                versions = {r["policy_version"] for r in values if r["seed"] == seed}
                if len(versions) != 1:
                    raise ValueError("Test comparison requires one frozen policy version per variant/seed")
        if any(identity != identities[VARIANTS[0]] for identity in identities.values()):
            raise ValueError("Variants must use identical test tasks and evaluation seeds")
        categories = ["overall", *DOMAINS]
        if {row["domain"] for row in test} != set(DOMAINS):
            raise ValueError("Comparison requires all three test domains")
        fig, ax = plt.subplots(figsize=(11, 5))
        x = np.arange(len(categories))
        for index, variant in enumerate(VARIANTS):
            rates = []
            for domain in categories:
                values = [r for r in test if r["variant"] == variant and (domain == "overall" or r["domain"] == domain)]
                rates.append(sum(r["success_count"] for r in values) / (len(values) * expected_samples))
            ax.bar(x + (index - 1.5) * 0.2, rates, width=0.2, label=variant)
        ax.set_xticks(x, categories)
        ax.set(ylabel="Mean independent-trajectory success rate", ylim=(0, 1), title="Four-system test comparison (descriptive; no best-of-8 selection)")
        ax.legend(fontsize=8)
        run_labels = ", ".join(sorted({r["run_id"] for r in test}))
        fig.text(0.5, 0.012, "Source run IDs: " + run_labels, ha="center", fontsize=8)
        fig.tight_layout(rect=(0, .04, 1, 1))
        path = destination / "system_comparison.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        written.append(path)
    return written
