import tempfile
import unittest
from pathlib import Path

from harness_grpo.plotting import plot_results
from harness_grpo.records import DOMAINS, VARIANTS, EpisodeRecord, MainTrace, score


def numeric_plot_fixtures():
    """Only for rendering QA. These records never enter data/public or experiment outputs."""
    result = []
    for variant_index, variant in enumerate(VARIANTS):
        for domain in DOMAINS:
            for question in range(3):
                for index in range(8):
                    success = (index + question) % 8 <= variant_index
                    base, penalty, reward = score(success, 1)
                    result.append(EpisodeRecord("QA_ONLY_NOT_EXPERIMENT", variant, "test", 1, f"{domain}_{question}", domain,
                                  index, f"fixture_{variant}", 7, "completed", success, ["fixture"], base, penalty,
                                  reward, MainTrace()))
    return result


class PlottingTest(unittest.TestCase):
    def test_four_system_and_individual_attempt_charts(self):
        with tempfile.TemporaryDirectory() as directory:
            files = plot_results(numeric_plot_fixtures(), Path(directory) / "plots", 8, comparison=True)
            self.assertEqual(len(files), 5)
            self.assertTrue(all(p.read_bytes().startswith(b"\x89PNG") for p in files))

    def test_missing_baseline_and_empty_results_are_not_fabricated(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                plot_results([], Path(directory) / "empty", 8)
            with self.assertRaises(ValueError):
                plot_results([r for r in numeric_plot_fixtures() if r.variant != "trained_full"], Path(directory) / "missing", 8, comparison=True)


if __name__ == "__main__":
    unittest.main()
