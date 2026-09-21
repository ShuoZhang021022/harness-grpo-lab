import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from harness_grpo.config import load_config, unresolved
from harness_grpo.dataset import validate_experiment_dataset


def main():
    parser = argparse.ArgumentParser(description="List unresolved experiment decisions without supplying implicit methodological defaults.")
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.json"))
    parser.add_argument("--validate-data", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    pending = unresolved(config)
    print(json.dumps({"formal_experiment_ready": not pending, "unresolved": pending}, ensure_ascii=False, indent=2))
    if args.validate_data:
        data = config["data"]
        if any(data[key] is None for key in ("train_manifest", "test_manifest", "public_assets_root")):
            raise ValueError("Dataset paths are not configured")
        print(validate_experiment_dataset(data["train_manifest"], data["test_manifest"], data["public_assets_root"]))
    if pending:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
