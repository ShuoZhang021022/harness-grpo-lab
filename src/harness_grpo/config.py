"""Keep research decisions explicit. Missing decisions never become runnable defaults."""

import json
from pathlib import Path


def unresolved(config):
    missing = []
    def walk(value, prefix):
        if value is None:
            missing.append(prefix)
        elif isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{prefix}.{key}" if prefix else key)
    walk(config, "")
    return missing


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require_ready(config):
    pending = unresolved(config)
    if pending:
        raise ValueError("Formal experiment not configured; unresolved: " + ", ".join(pending))
    if config["training"]["questions_per_batch"] != 100 or config["training"]["samples_per_question"] != 8:
        raise ValueError("Batch settings disagree with the user's confirmed 100 questions x 8 samples")
    return config
