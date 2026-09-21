import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from harness_grpo.plotting import plot_results
from harness_grpo.reporting import load_records


def main():
    parser = argparse.ArgumentParser(description="Plot individual outcomes, batch statistics, and four-system test comparisons from actual trajectory records.")
    parser.add_argument("--input", nargs="+", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--samples-per-question", required=True, type=int)
    parser.add_argument("--comparison", action="store_true", help="Requires complete results for all four systems on the same test tasks")
    args = parser.parse_args()
    paths = plot_results(load_records(args.input), args.output, args.samples_per_question, args.comparison)
    for path in paths:
        print(path.resolve())


if __name__ == "__main__":
    main()
