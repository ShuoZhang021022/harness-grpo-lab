"""Validate public task manifests without loading private answers into agent contexts."""

import hashlib
from collections import Counter
from pathlib import Path, PurePosixPath

from .records import DOMAINS, read_jsonl

PUBLIC_FIELDS = {"id", "domain", "split", "description", "files", "source", "family_id", "answer_format"}


def safe_asset(root, relative):
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise ValueError("Use relative POSIX paths in file manifests")
    p = PurePosixPath(relative)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise ValueError("Asset path must remain inside the public task directory")
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Asset escapes public data root")
    return target


def validate_tasks(tasks, public_root):
    identifiers, seen_content, families = set(), {}, {}
    counts = Counter()
    for task in tasks:
        if set(task) != PUBLIC_FIELDS:
            raise ValueError(f"Public task fields must be exactly {sorted(PUBLIC_FIELDS)}; private answers belong elsewhere")
        if not isinstance(task["id"], str) or not task["id"] or task["id"] in identifiers:
            raise ValueError("Task IDs must be nonempty unique strings")
        identifiers.add(task["id"])
        if task["domain"] not in DOMAINS or task["split"] not in ("train", "test"):
            raise ValueError("Invalid domain or split")
        if not isinstance(task["description"], str) or not task["description"].strip():
            raise ValueError("Task description must be nonempty text")
        if not isinstance(task["family_id"], str) or not task["family_id"]:
            raise ValueError("Source/template family is required for leakage checks")
        if not isinstance(task["source"], dict) or not all(task["source"].get(k) for k in ("kind", "reference", "item_id")):
            raise ValueError("Source kind, reference and item_id are required")
        if not isinstance(task["files"], list):
            raise ValueError("files must be a list of relative asset paths")
        if task["domain"] == "code" and not any(p.endswith(".py") for p in task["files"]):
            raise ValueError("Code-repair tasks need a public Python source file")
        expected_format = {"math": "integer_0_999", "code": "hidden_tests", "life": "place_id"}[task["domain"]]
        if task["answer_format"] != expected_format:
            raise ValueError("Wrong answer format for domain")
        digest = hashlib.sha256(" ".join(task["description"].split()).encode())
        for relative in task["files"]:
            asset = safe_asset(public_root, relative)
            if not asset.is_file():
                raise ValueError(f"Missing public asset: {relative}")
            digest.update(asset.read_bytes())
        content = digest.hexdigest()
        if content in seen_content:
            raise ValueError(f"Duplicate task content: {task['id']} / {seen_content[content]}")
        seen_content[content] = task["id"]
        family = (task["domain"], task["family_id"])
        if family in families and families[family] != task["split"]:
            raise ValueError("Source/template family crosses train/test boundary")
        families[family] = task["split"]
        counts[(task["split"], task["domain"])] += 1
    return {f"{split}/{domain}": counts[(split, domain)] for split in ("train", "test") for domain in DOMAINS}


def validate_experiment_dataset(train_path, test_path, public_root):
    train, test = list(read_jsonl(train_path)), list(read_jsonl(test_path))
    if any(t["split"] != "train" for t in train) or any(t["split"] != "test" for t in test):
        raise ValueError("Wrong split in manifest")
    counts = validate_tasks(train + test, public_root)
    for domain in DOMAINS:
        if counts[f"train/{domain}"] != 1000 or counts[f"test/{domain}"] != 100:
            raise ValueError("Require exactly 1000 train and 100 test tasks per domain")
    return counts


def main_agent_input(task, tool_catalog):
    """Intentionally excludes code contents, source identifiers, answers and private test data."""
    return {"problem_description": task["description"], "available_tools": tool_catalog}
