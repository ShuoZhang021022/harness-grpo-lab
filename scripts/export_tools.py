"""Export the exact initial registry and freeze its source hash for an experiment."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from harness_grpo.tools import REGISTRY, catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(REGISTRY) != 50:
        raise ValueError(f"Expected exactly 50 initial tools, got {len(REGISTRY)}")
    args.output.mkdir(parents=True, exist_ok=False)
    descriptors = catalog()
    (args.output / "catalog.json").write_text(json.dumps(descriptors, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Initial Tool Library", "", "50 Python tools with no LLM calls, network access, or execution of supplied Python source code.", "",
             "The library contains 18 math tools, 17 code tools, and 15 life-scenario tools. See catalog.json for interface parameters and examples.", ""]
    for item in descriptors:
        lines.append(f"- `{item['name']}` [{item['domain']}]: {item['description']}")
    (args.output / "CATALOG.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    tool_root = Path(__file__).resolve().parents[1] / "src" / "harness_grpo" / "tools"
    source_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(tool_root.glob("*.py"))}
    source_hashes["catalog.json"] = hashlib.sha256((args.output / "catalog.json").read_bytes()).hexdigest()
    (args.output / "manifest.sha256.json").write_text(json.dumps(source_hashes, indent=2), encoding="utf-8")
    print(f"Exported {len(descriptors)} tools to {args.output.resolve()}")


if __name__ == "__main__":
    main()
