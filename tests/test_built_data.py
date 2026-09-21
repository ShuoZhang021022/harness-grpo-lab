import json
import unittest
from collections import Counter
from pathlib import Path

from harness_grpo.dataset import validate_experiment_dataset
from harness_grpo.records import read_jsonl


class BuiltDatasetTest(unittest.TestCase):
    @unittest.skipUnless(Path("data/public/train.jsonl").is_file(), "Dataset has not been built")
    def test_actual_counts_private_labels_and_source_scope(self):
        counts = validate_experiment_dataset("data/public/train.jsonl", "data/public/test.jsonl", "data/public/assets")
        self.assertEqual(list(counts.values()), [1000, 1000, 1000, 100, 100, 100])
        public = list(read_jsonl("data/public/train.jsonl")) + list(read_jsonl("data/public/test.jsonl"))
        private = list(read_jsonl("data/private/labels/verifiers.jsonl"))
        self.assertEqual({t["id"] for t in public}, {t["id"] for t in private})
        self.assertEqual(len(private), 3300)
        self.assertTrue(all("answer" not in t and "tests" not in t for t in public))
        math_test = [t for t in public if t["domain"] == "math" and t["split"] == "test"]
        self.assertEqual(Counter(t["source"]["kind"] for t in math_test), {"aime_genuine_source_mirror": 100})
        for label in private:
            if label["domain"] == "code":
                self.assertGreater(label["buggy_test_failure_count"], 0)
                self.assertGreaterEqual(len(label["tests"]), 15)
            if label["domain"] == "math":
                self.assertEqual(label["verification_status"], "source_reference_not_independently_audited")


if __name__ == "__main__":
    unittest.main()
