"""Build the authorized 3000/300 public tasks and separate reference verifiers.

Math references are source-provided labels, NOT falsely certified as independently
verified official keys. Code and life tasks are explicitly procedural synthetic data.
"""

import argparse
import hashlib
import itertools
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from harness_grpo.dataset import validate_experiment_dataset
from harness_grpo.records import write_jsonl

SEED = 20260920
OPS = {
    "add7": ("add 7", "v + 7", lambda v: v + 7),
    "sub11": ("subtract 11", "v - 11", lambda v: v - 11),
    "mul3": ("multiply by 3", "v * 3", lambda v: 3 * v),
    "floor2": ("divide by 2 and round down toward negative infinity", "v // 2", lambda v: v // 2),
    "mod37": ("take the nonnegative remainder after division by 37", "v % 37", lambda v: v % 37),
    "negate": ("negate the value", "-v", lambda v: -v),
    "absolute": ("take the absolute value", "abs(v)", lambda v: abs(v)),
    "square101": ("square the value, then take the nonnegative remainder after division by 101", "(v * v) % 101", lambda v: pow(v, 2, 101)),
    "doubleadd": ("multiply by 2, then add 1", "2 * v + 1", lambda v: v + v + 1),
    "shiftfloor3": ("add 5, then divide by 3 and round down toward negative infinity", "(v + 5) // 3", lambda v: (v + 5) // 3),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def public_task(identifier, domain, split, description, source, family, files=None):
    return {"id": identifier, "domain": domain, "split": split, "description": description,
            "files": files or [], "source": source, "family_id": family,
            "answer_format": {"math": "integer_0_999", "code": "hidden_tests", "life": "place_id"}[domain]}


def normalized_math(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


class MathDeduplicator:
    """Source filtering: exact normalized text, then 3-token shingle Jaccard >=0.85."""
    def __init__(self):
        self.exact, self.shingles, self.index = set(), [], {}

    def add(self, text):
        normalized = normalized_math(text)
        if normalized in self.exact:
            return False
        tokens = normalized.split()
        shingles = {tuple(tokens[i:i + 3]) for i in range(len(tokens) - 2)}
        candidates = set()
        for shingle in shingles:
            candidates.update(self.index.get(shingle, []))
        for index in candidates:
            other = self.shingles[index]
            if shingles and len(shingles & other) / len(shingles | other) >= .85:
                return False
        index = len(self.shingles)
        self.exact.add(normalized)
        self.shingles.append(shingles)
        for shingle in shingles:
            self.index.setdefault(shingle, []).append(index)
        return True


def math_tasks(source_root, audit):
    import pyarrow.parquet as pq
    seen, aime, supplement = MathDeduplicator(), [], []
    exclusions = Counter()
    source_files = sorted((source_root / "aime_1983_2025").rglob("*.parquet"))
    if not source_files:
        raise ValueError("Download the AIME source parquet before building")
    for path in source_files:
        for row in pq.read_table(path).to_pylist():
            if "[asy]" in row["problem"] or "\\includegraphics" in row["problem"] or "<img" in row["problem"]:
                exclusions["aime_requires_embedded_figure"] += 1
                continue
            answers = row["all_answers"] or []
            if len(set(answers)) != 1 or row["answer"] not in answers or not 0 <= row["answer"] <= 999:
                exclusions["aime_nonunique_or_invalid_reference"] += 1
                continue
            if not seen.add(row["problem"]):
                exclusions["aime_duplicate_text"] += 1
                continue
            identifier = f"aime_{row['year']}_{str(row['part']).replace(' ', '_')}_{row['index']:02d}"
            aime.append((identifier, row["problem"], row["answer"], {
                "kind": "aime_genuine_source_mirror", "reference": "https://huggingface.co/datasets/Pandores/aime-1983-2025",
                "item_id": identifier, "year": row["year"], "part": row["part"],
                "original_source": "AoPS Wiki AIME Problems and Solutions, as described by dataset publisher",
            }, row["solutions"]))
    rng = random.Random(SEED)
    rng.shuffle(aime)
    if len(aime) < 100:
        raise ValueError("Insufficient eligible AIME tasks for the 100-question test set")
    # All 100 math test tasks are AIME. Supplements use only MATH's original train split.
    math_test, math_train = aime[:100], aime[100:]
    needed = 1000 - len(math_train)
    candidates = []
    for path in sorted((source_root / "hendrycks_math").rglob("train-*.parquet")):
        for index, row in enumerate(pq.read_table(path).to_pylist()):
            if row["level"] not in ("Level 4", "Level 5"):
                continue
            if any(x in row["problem"] for x in ("[asy]", "\\includegraphics", "<img")):
                continue
            boxes = re.findall(r"\\boxed\{([0-9]{1,3})\}", row["solution"])
            # Require the final boxed expression itself to be a plain in-range integer.
            last_box = row["solution"].rfind("\\boxed{")
            if not boxes or not re.match(r"\\boxed\{[0-9]{1,3}\}", row["solution"][last_box:]):
                continue
            identifier = f"math_supplement_{path.parent.name}_{index:05d}"
            candidates.append((identifier, row["problem"], int(boxes[-1]), {
                "kind": "math_competition_supplement", "reference": "https://huggingface.co/datasets/EleutherAI/hendrycks_math",
                "item_id": f"{path.parent.name}/train/{index}", "level": row["level"], "topic": row["type"],
                "original_source": "https://github.com/hendrycks/math",
            }, [row["solution"]]))
    rng.shuffle(candidates)
    for candidate in candidates:
        if len(supplement) == needed:
            break
        if seen.add(candidate[1]):
            supplement.append(candidate)
        else:
            exclusions["supplement_duplicate_of_selected_math"] += 1
    if len(supplement) != needed:
        raise ValueError("Insufficient eligible supplemental competition questions")
    math_train += supplement
    audit["math"] = {"source_aime_rows": 1035, "eligible_aime": len(aime), "train_aime": len(aime) - 100,
                     "test_aime": 100, "train_supplement": len(supplement), "exclusions": dict(exclusions),
                     "supplement_levels": [4, 5], "deduplication": "normalized exact text and 3-token shingle Jaccard>=0.85",
                     "independent_reference_audit_complete": False}
    public, private = [], []
    for split, values in (("train", math_train), ("test", math_test)):
        for identifier, problem, answer, source, solutions in values:
            public.append(public_task(identifier, "math", split, problem, source, identifier))
            private.append({"id": identifier, "domain": "math", "answer": answer,
                            "verification_status": "source_reference_not_independently_audited",
                            "reference_solutions": solutions, "reference_source": source})
    return public, private


def interpret_ops(sequence, x):
    for name in sequence:
        x = OPS[name][2](x)
    return x


def emit_program(sequence):
    return "def solve(x):\n    v = x\n" + "".join(f"    v = {OPS[name][1]}\n" for name in sequence) + "    return v\n"


def code_tasks(public_root, audit):
    rng = random.Random(SEED + 1)
    sequences = list(itertools.permutations(OPS, 4))
    rng.shuffle(sequences)
    public, private, exclusions = [], [], Counter()
    for sequence in sequences:
        if len(public) == 1100:
            break
        inputs = sorted(set([-101, -50, -17, -1, 0, 1, 2, 5, 8, 13, 21, 34, 55, 89, 144] + [rng.randint(-500, 500) for _ in range(20)]))
        expected = [interpret_ops(sequence, x) for x in inputs]
        if len(set(expected)) < 6:
            exclusions["low_output_diversity"] += 1
            continue
        mutation_index = rng.randrange(4)
        alternatives = [name for name in OPS if name != sequence[mutation_index]]
        replacement = rng.choice(alternatives)
        mutated = list(sequence)
        mutated[mutation_index] = replacement
        wrong = [interpret_ops(mutated, x) for x in inputs]
        if wrong == expected:
            exclusions["mutation_not_detected_by_tests"] += 1
            continue
        # Execute ONLY the generator's own fixed-expression source, never downloaded or agent-generated code.
        reference_source, buggy_source = emit_program(sequence), emit_program(mutated)
        reference_ns, buggy_ns = {}, {}
        exec(compile(reference_source, "<owned-reference-generator>", "exec"), reference_ns)
        exec(compile(buggy_source, "<owned-bug-generator>", "exec"), buggy_ns)
        if [reference_ns["solve"](x) for x in inputs] != expected or [buggy_ns["solve"](x) for x in inputs] != wrong:
            raise AssertionError("Reference source disagrees with declarative oracle")
        family = "pipeline4_" + "_".join(sequence)
        identifier = "code_" + digest(family)[:16]
        split = "train" if len(public) < 1000 else "test"
        relative = f"{identifier}/buggy.py"
        target = public_root / relative
        target.parent.mkdir(parents=True)
        target.write_text(buggy_source, encoding="utf-8")
        visible_inputs = [-3, 0, 7]
        examples = [{"input": x, "output": interpret_ops(sequence, x)} for x in visible_inputs]
        description = (
            "Repair solve(x) in the provided buggy.py. The input x is an integer. For every integer input, the function must perform the following operations in order and return an integer result: "
            + "; ".join(f"Step {i+1}: {OPS[name][0]}" for i, name in enumerate(sequence))
            + ". Each step acts on the result of the preceding step. Keep the function interface unchanged, and return the result rather than printing it. Expected examples: "
            + json.dumps(examples, ensure_ascii=False) + ". Evaluation will call the repaired solve(x) and also check other inputs."
        )
        public.append(public_task(identifier, "code", split, description,
                      {"kind": "synthetic_code_repair", "reference": "scripts/build_datasets.py:OPS", "item_id": family}, family, [relative]))
        private.append({"id": identifier, "domain": "code", "entrypoint": "solve", "target_file": relative,
                        "tests": [{"id": f"case_{i:02d}", "arguments": [x], "expected": expected[i]} for i, x in enumerate(inputs)],
                        "reference_source": reference_source, "mutated_stage": mutation_index, "replacement_operation": replacement,
                        "verification_status": "generator_oracle_and_owned_reference_execution_agree",
                        "buggy_test_failure_count": sum(a != b for a, b in zip(expected, wrong))})
    if len(public) != 1100:
        raise ValueError("Insufficient distinct synthetic program families")
    audit["code"] = {"count": len(public), "source": "synthetic four-stage integer programs with one mutated operation",
                     "split_unit": "ordered operation sequence, not input values", "exclusions": dict(exclusions),
                     "reference_programs_checked": len(public), "all_buggy_programs_fail_at_least_one_hidden_test": True,
                     "scope_limit": "compositional integer-program repair; not repository-level real-world bug fixing"}
    return public, private


def life_tasks(audit):
    rng = random.Random(SEED + 2)
    public, private, seen = [], [], set()
    directions = {"north": (0, 1), "east": (1, 0), "south": (0, -1), "west": (-1, 0)}
    while len(public) < 1100:
        cells = {(0, 0)}
        for _ in range(80):
            base = rng.choice(sorted(cells))
            dx, dy = rng.choice(list(directions.values()))
            nxt = base[0] + dx, base[1] + dy
            if -4 <= nxt[0] <= 4 and -4 <= nxt[1] <= 4:
                cells.add(nxt)
            if len(cells) == 16:
                break
        if len(cells) != 16:
            continue
        family = digest(sorted(cells))
        if family in seen:
            continue
        seen.add(family)
        points = sorted(cells)
        ids = {point: f"place_{i:02d}" for i, point in enumerate(points)}
        start = rng.choice(points)
        current, route, moves = start, [start], []
        for _ in range(8):
            valid = [(label, (current[0] + dx, current[1] + dy)) for label, (dx, dy) in directions.items()
                     if (current[0] + dx, current[1] + dy) in cells]
            label, current = rng.choice(valid)
            moves.append(label)
            route.append(current)
        if current == start:
            continue
        # Independent replay verifies all road edges and exact final location.
        replay = start
        for label in moves:
            dx, dy = directions[label]
            replay = replay[0] + dx, replay[1] + dy
            assert replay in cells
        assert replay == current
        identifier = "life_" + family[:16]
        split = "train" if len(public) < 1000 else "test"
        places = [{"id": ids[p], "x": p[0], "y": p[1]} for p in points]
        description = (
            "The following is a fixed map of a fictional neighborhood. The positive x direction is east, and the positive y direction is north. Two listed places are connected by a two-way road if the Manhattan distance between their coordinates is 1; there are no direct roads between other pairs of places. "
            "Every move follows a road to an adjacent place. Place table: " + json.dumps(places, ensure_ascii=False)
            + f". Start at {ids[start]}. Move along one road in each of the following directions, in order: " + ", ".join(moves)
            + ". Return only the unique ID of your final location, such as place_00."
        )
        public.append(public_task(identifier, "life", split, description,
                      {"kind": "synthetic_frozen_map", "reference": "scripts/build_datasets.py:life_tasks", "item_id": family}, family))
        private.append({"id": identifier, "domain": "life", "answer": ids[current],
                        "valid_place_ids": list(ids.values()), "scene": places,
                        "route": [ids[p] for p in route], "verification_status": "deterministic_map_replay_verified"})
    audit["life"] = {"count": len(public), "split_unit": "distinct 16-place coordinate scene",
                     "oracle": "deterministic replay of eight road moves", "synthetic": True,
                     "scope_limit": "closed-world grid navigation; shared task grammar, unseen maps"}
    return public, private


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("data/private/sources"))
    parser.add_argument("--public-root", type=Path, default=Path("data/public"))
    parser.add_argument("--private-root", type=Path, default=Path("data/private/labels"))
    parser.add_argument("--audit-dir", type=Path, default=Path("artifacts/dataset_audit"))
    args = parser.parse_args()
    for path in (args.public_root, args.private_root, args.audit_dir):
        path.mkdir(parents=True, exist_ok=False)
    audit = {"build_seed": SEED, "status": "dataset_constructed_math_reference_audit_pending", "source_files": {}}
    for path in sorted(args.source_root.rglob("*.parquet")):
        audit["source_files"][str(path.relative_to(args.source_root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted(args.source_root.rglob("*.metadata")):
        lines = path.read_text(encoding="utf-8").splitlines()
        if lines:
            audit.setdefault("source_revisions", {})[str(path.relative_to(args.source_root))] = lines[0]
    public, private = [], []
    for group in (math_tasks(args.source_root, audit), code_tasks(args.public_root / "assets", audit), life_tasks(audit)):
        public.extend(group[0])
        private.extend(group[1])
    train, test = [t for t in public if t["split"] == "train"], [t for t in public if t["split"] == "test"]
    random.Random(SEED).shuffle(train)
    random.Random(SEED + 3).shuffle(test)
    write_jsonl(args.public_root / "train.jsonl", train)
    write_jsonl(args.public_root / "test.jsonl", test)
    write_jsonl(args.private_root / "verifiers.jsonl", private)
    for domain in ("math", "code", "life"):
        for split, values in (("train", train), ("test", test)):
            write_jsonl(args.public_root / f"{domain}_{split}.jsonl", (t for t in values if t["domain"] == domain))
    audit["validated_counts"] = validate_experiment_dataset(args.public_root / "train.jsonl", args.public_root / "test.jsonl", args.public_root / "assets")
    audit["manifest_hashes"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in args.public_root.glob("*.jsonl")}
    (args.audit_dir / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"counts": audit["validated_counts"], "math": audit["math"], "status": audit["status"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
