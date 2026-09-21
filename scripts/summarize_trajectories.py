import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from harness_grpo.reporting import load_records, write_reports


def main():
    parser = argparse.ArgumentParser(description="Record independent trajectory successes per question and batch; reject duplicate or missing samples.")
    parser.add_argument("--input", nargs="+", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--samples-per-question", required=True, type=int)
    parser.add_argument("--allow-incomplete", action="store_true", help="Diagnostics only: incomplete groups have a null success rate")
    args = parser.parse_args()
    questions, batches = write_reports(load_records(args.input), args.output, args.samples_per_question, args.allow_incomplete)
    print(f"Wrote {len(questions)} question rows and {len(batches)} batch rows to {args.output.resolve()}")


if __name__ == "__main__":
    main()
