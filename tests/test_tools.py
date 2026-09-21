import ast
import math
import random
import unittest
from fractions import Fraction
from pathlib import Path

from harness_grpo.tools import REGISTRY, call_tool, catalog


class InitialToolsTest(unittest.TestCase):
    def test_exactly_fifty_callable_documented_tools(self):
        self.assertEqual(len(REGISTRY), 50)
        self.assertEqual({d: sum(t.domain == d for t in REGISTRY.values()) for d in ("math", "code", "life")}, {"math": 18, "code": 17, "life": 15})
        for item in catalog():
            self.assertTrue(item["description"])
            self.assertFalse(item["invokes_llm"])

    def test_all_fifty_declared_examples(self):
        for name, tool in REGISTRY.items():
            with self.subTest(tool=name):
                self.assertEqual(call_tool(name, tool.example), tool.expected)

    def test_integer_invariants_against_independent_arithmetic(self):
        rng = random.Random(319)
        for _ in range(100):
            a, b = rng.randint(-10000, 10000), rng.randint(-10000, 10000)
            result = call_tool("extended_gcd", {"a": a, "b": b})
            self.assertEqual(result["gcd"], math.gcd(a, b))
            self.assertEqual(a * result["x"] + b * result["y"], result["gcd"])
        for n in range(1, 150):
            factors = call_tool("prime_factorization", {"n": n})
            self.assertEqual(math.prod(p ** k for p, k in factors), n)
            self.assertTrue(all(call_tool("is_prime", {"n": p}) for p, _ in factors))
            self.assertEqual(call_tool("positive_divisors", {"n": n}), [d for d in range(1, n + 1) if n % d == 0])

    def test_linear_solver_satisfies_original_equations(self):
        matrix = [["1/2", 2, 0], [1, -1, 3], [0, 2, 1]]
        rhs = [3, 7, 5]
        solution = list(map(Fraction, call_tool("solve_linear_system", {"matrix": matrix, "rhs": rhs})))
        for row, target in zip(matrix, rhs):
            self.assertEqual(sum(Fraction(a) * b for a, b in zip(row, solution)), target)
        with self.assertRaises(ValueError):
            call_tool("solve_linear_system", {"matrix": [[1, 1], [2, 2]], "rhs": [1, 2]})

    def test_source_transform_guard_and_compile_without_execution(self):
        source = 'raise RuntimeError("must never execute")\n'
        self.assertEqual(call_tool("compile_check", {"source": source}), {"valid": True})
        with self.assertRaises(ValueError):
            call_tool("replace_text_exact", {"source": "x+x", "old": "x", "new": "y", "expected_count": 1})
        self.assertEqual(call_tool("replace_number_literals", {"source": "x = True; y = 1", "old": 1, "new": 2, "expected_count": 1}), "x = True\ny = 2")

    def test_graph_unreachable_negative_weights_cycles_and_alias_ambiguity(self):
        self.assertIsNone(call_tool("shortest_unweighted_path", {"graph": {"a": ["b"]}, "start": "b", "goal": "a"}))
        with self.assertRaises(ValueError):
            call_tool("shortest_weighted_path", {"graph": {"a": {"b": -1}}, "start": "a", "goal": "b"})
        with self.assertRaises(ValueError):
            call_tool("topological_order", {"graph": {"a": ["b"], "b": ["a"]}})
        places = [{"id": "a", "name": "park"}, {"id": "b", "name": "park"}]
        self.assertEqual(call_tool("resolve_place_name", {"places": places, "name": "park"}), ["a", "b"])

    def test_no_llm_network_or_process_dependencies_in_initial_tools(self):
        root = Path(__file__).resolve().parents[1] / "src" / "harness_grpo" / "tools"
        forbidden = {"openai", "anthropic", "requests", "httpx", "urllib", "subprocess", "socket"}
        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse({a.name.split(".")[0] for a in node.names} & forbidden)
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".")[0], forbidden)


if __name__ == "__main__":
    unittest.main()
