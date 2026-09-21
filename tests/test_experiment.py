import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness_grpo.dataset import main_agent_input, safe_asset, validate_tasks
from harness_grpo.episode import ActionStep, SolverResult, run_episode
from harness_grpo.records import EpisodeRecord, MainTrace, score
from harness_grpo.reporting import summarize, write_reports
from harness_grpo.training import collect_and_update_batches, evaluate_frozen_policy
from harness_grpo.verifiers import verify_aime, verify_code_test_report, verify_place


def task(identifier="q", domain="math", split="train"):
    return {"id": identifier, "domain": domain, "split": split, "description": "description " + identifier,
            "files": [], "source": {"kind": "test_fixture", "reference": "unit-tests", "item_id": identifier},
            "family_id": identifier, "answer_format": {"math": "integer_0_999", "code": "hidden_tests", "life": "place_id"}[domain]}


def record(index=0, success=True, identifier="q", batch=1, version="v0", variant="trained_full", split="train", count=2):
    base, penalty, reward = score(success, count)
    return EpisodeRecord("test_fixture", variant, split, batch, identifier, "math", index, version, 7,
                         "completed", success, [f"tool_{i}" for i in range(count)], base, penalty, reward,
                         MainTrace([1, 2], [3], [-0.4], "action"))


def action_steps(actions, requested=None):
    for i, action in enumerate(actions, 1):
        if requested is not None:
            requested.append(action["type"])
        yield ActionStep(action, MainTrace([1, 2], list(range(3, i + 3)), [-0.4] * i, json.dumps(actions[:i])))


class RewardAndReportingTest(unittest.TestCase):
    def test_confirmed_penalty_and_exact_similarity_override(self):
        self.assertEqual(score(True, 50), (1.0, 0.5, 0.5))
        self.assertEqual(score(False, 50), (-1.0, 0.5, -1.5))
        self.assertEqual(score(False, 50, True), (-1.0, 0.0, -1.0))

    def test_success_is_not_reward_sign_and_statistics_are_per_question(self):
        rows = [record(i, i < 3, count=150 if i < 3 else 1) for i in range(8)]
        rows += [record(i, False, identifier="q2", count=i) for i in range(8)]
        questions, batches = summarize(rows, 8)
        self.assertEqual(questions[0]["success_count"], 3)
        self.assertEqual(questions[0]["success_flags"], [True] * 3 + [False] * 5)
        self.assertEqual(batches[0]["success_histogram"]["3"], 1)
        self.assertEqual(batches[0]["success_histogram"]["0"], 1)
        # All-wrong outcomes can still have nonzero reward variance after tool penalties.
        self.assertGreater(questions[1]["reward_std"], 0)

    def test_no_silent_deduplication_missing_samples_or_cross_policy_groups(self):
        rows = [record(i) for i in range(8)]
        with self.assertRaises(ValueError):
            summarize(rows + [rows[0]], 8)
        with self.assertRaises(ValueError):
            summarize(rows[:-1], 8)
        questions, _ = summarize(rows[:-1], 8, allow_incomplete=True)
        self.assertIsNone(questions[0]["success_rate"])
        rows[-1].policy_version = "v1"
        with self.assertRaises(ValueError):
            summarize(rows, 8)

    def test_csv_and_jsonl_contain_all_eight_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "stats"
            write_reports([record(i, i == 0) for i in range(8)], output, 8)
            row = json.loads((output / "question_success.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(row["success_count"], 1)
            self.assertEqual(len(row["success_flags"]), 8)
            self.assertTrue((output / "batch_summary.csv").is_file())


class EpisodeControlTest(unittest.TestCase):
    def run_case(self, actions, judge, solver, requested=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_episode(task=task(), actions=action_steps(actions, requested), similarity_judge=judge,
                                 solver_runner=solver, public_root=root, scratch_root=root / "scratch",
                                 run_id="test_fixture", variant="trained_full", batch_id=1, sample_index=0,
                                 policy_version="v0", seed=7)
            self.assertEqual(list((root / "scratch").iterdir()), [])
            return result

    def test_rejection_stops_immediately_and_retains_rejected_tokens(self):
        requested = []
        candidate = {"id": "new_add", "description": "add", "source": "def run(arguments):\n    return arguments['a'] + arguments['b']\n"}
        def judge(tool, references):
            self.assertEqual(len(references), 50)
            return {"high_similarity": True, "matched_tool_id": "rational_arithmetic", "reason": "same addition functionality"}
        def solver(*args):
            self.fail("Solver must not be called after similarity rejection")
        result = self.run_case([{"type": "select", "tool_id": "integer_gcd"}, {"type": "create", "tool": candidate}, {"type": "finish"}], judge, solver, requested)
        self.assertEqual(requested, ["select", "create"])
        self.assertEqual(result.reward, -1)
        self.assertEqual(len(result.main_trace.output_token_ids), 2)
        self.assertEqual(result.similarity_checks[0]["candidate"]["source"], candidate["source"])

    def test_accepted_new_tools_are_compared_and_charged(self):
        counts = []
        def judge(tool, references):
            counts.append(len(references))
            return {"high_similarity": False, "matched_tool_id": None, "reason": "different declared functionality"}
        def solver(task, workspace, selected):
            self.assertEqual(len(selected), 2)
            return SolverResult(True, "completed", [t["id"] for t in selected], {"trusted_verifier": "fixture"})
        actions = [{"type": "create", "tool": {"id": f"new_{i}", "description": "fixture", "source": "def run(arguments):\n    return None\n"}} for i in range(2)] + [{"type": "finish"}]
        result = self.run_case(actions, judge, solver)
        self.assertEqual(counts, [50, 51])
        self.assertAlmostEqual(result.reward, .98)
        self.assertTrue(result.execution["all_received_tools_called"])

    def test_malformed_judge_is_infrastructure_error_not_negative_reward(self):
        actions = [{"type": "create", "tool": {"id": "new_a", "description": "fixture", "source": "def run(arguments):\n    return 1"}}]
        result = self.run_case(actions, lambda *args: {"high_similarity": "yes"}, lambda *args: self.fail())
        self.assertEqual(result.status, "infrastructure_error")
        self.assertIsNone(result.reward)
        self.assertIsNone(result.success)

    def test_invalid_generated_source_is_policy_failure(self):
        actions = [{"type": "create", "tool": {"id": "new_a", "description": "fixture", "source": "def bad("}}]
        result = self.run_case(actions, lambda *args: self.fail(), lambda *args: self.fail())
        self.assertEqual(result.status, "policy_invalid")
        self.assertEqual(result.reward, -1)

    def test_multifile_package_checked_as_one_tool(self):
        candidate = {"id": "new_package", "description": "test package", "files": {
            "pkg/__init__.py": "", "pkg/helper.py": "def helper(x):\n    return x + 1\n",
            "pkg/main.py": "from .helper import helper\ndef run(arguments):\n    return helper(arguments['x'])\n",
        }, "entrypoint": "pkg.main:run"}
        result = self.run_case([{"type": "create", "tool": candidate}, {"type": "finish"}],
                               lambda *args: {"high_similarity": False, "matched_tool_id": None, "reason": "fixture"},
                               lambda *args: SolverResult(True, "completed", ["new_package"], {}))
        self.assertEqual(result.selected_tool_ids, ["new_package"])
        self.assertAlmostEqual(result.reward, .99)

    def test_duplicate_selection_is_not_double_charged_and_compliance_is_diagnostic(self):
        actions = [{"type": "select", "tool_id": "integer_gcd"}] * 2 + [{"type": "finish"}]
        result = self.run_case(actions, lambda *args: self.fail(), lambda *args: SolverResult(True, "completed", [], {}))
        self.assertAlmostEqual(result.reward, .99)
        self.assertEqual(result.selected_tool_ids, ["integer_gcd"])
        self.assertFalse(result.execution["all_received_tools_called"])


class DataAndVerifierTest(unittest.TestCase):
    def test_main_agent_only_observes_description_and_catalog(self):
        value = task()
        value["files"] = ["buggy.py"]
        self.assertEqual(main_agent_input(value, []), {"problem_description": value["description"], "available_tools": []})

    def test_public_private_and_source_family_separation(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = task("a"), task("b", split="test")
            b["family_id"] = a["family_id"]
            with self.assertRaises(ValueError):
                validate_tasks([a, b], directory)
            a["answer"] = 1
            with self.assertRaises(ValueError):
                validate_tasks([a], directory)
            with self.assertRaises(ValueError):
                safe_asset(directory, "../answer.json")

    def test_exact_answers_and_trusted_code_tests(self):
        self.assertTrue(verify_aime(" 007 ", 7))
        self.assertFalse(verify_aime("Answer: 7", 7))
        self.assertFalse(verify_aime(True, 1))
        self.assertTrue(verify_place("park_01", "park_01", ["park_01"]))
        self.assertFalse(verify_place("the park", "park_01", ["park_01"]))
        self.assertFalse(verify_code_test_report({"runner_completed": True, "test_results": {"target": True, "regression": False}}, ["target", "regression"]))
        with self.assertRaises(ValueError):
            verify_code_test_report({"runner_completed": True, "test_results": {"target": True}}, ["target", "regression"])


class BatchOrderingTest(unittest.TestCase):
    def test_100_questions_800_samples_then_update_before_next_batch(self):
        tasks = [task(f"q{i:03}") for i in range(200)]
        events = []
        def collect(value, batch, sample, version):
            self.assertEqual(version, f"v{batch - 1}")
            if batch == 2:
                self.assertIn(("update", 1, 800), events)
            events.append(("collect", batch, sample))
            return record(sample, identifier=value["id"], batch=batch, version=version)
        def update(records, version, batch):
            self.assertEqual(len(records), 800)
            self.assertEqual(len({r.task_id for r in records}), 100)
            events.append(("update", batch, len(records)))
            return f"v{batch}"
        with tempfile.TemporaryDirectory() as directory:
            version = collect_and_update_batches(tasks=tasks, task_ids=[t["id"] for t in tasks], initial_version="v0",
                                                 collect_episode=collect, update_policy=update, output_dir=Path(directory) / "run", resolved_config={"purpose": "unit_test"})
            self.assertEqual(version, "v2")
            self.assertEqual(events[800], ("update", 1, 800))

    def test_service_error_preserved_and_no_update(self):
        tasks = [task(f"q{i}") for i in range(100)]
        def collect(value, batch, sample, version):
            result = record(sample, identifier=value["id"])
            result.status, result.success, result.base_reward, result.reward = "infrastructure_error", None, None, None
            result.tool_penalty = 0.0
            return result
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            with self.assertRaises(RuntimeError):
                collect_and_update_batches(tasks=tasks, task_ids=[t["id"] for t in tasks], initial_version="v0", collect_episode=collect,
                                           update_policy=lambda *args: self.fail(), output_dir=output, resolved_config={})
            self.assertTrue((output / "batch_001" / "partial_trajectories.jsonl").is_file())

    def test_evaluation_keeps_every_frozen_policy_attempt(self):
        def collect(value, batch, sample, version):
            return record(sample, sample % 2 == 0, value["id"], batch, version, split="test")
        with tempfile.TemporaryDirectory() as directory:
            records = evaluate_frozen_policy(tasks=[task("a", split="test"), task("b", split="test")], samples_per_question=8,
                                             policy_version="v30", collect_episode=collect, output_dir=Path(directory) / "eval")
            self.assertEqual(len(records), 16)
            self.assertEqual(sum(r.success for r in records), 8)


if __name__ == "__main__":
    unittest.main()
