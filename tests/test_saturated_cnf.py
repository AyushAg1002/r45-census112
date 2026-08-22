from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import saturated_cnf as sc  # noqa: E402


class SaturatedCNFTests(unittest.TestCase):
    def test_sms_edge_numbering(self) -> None:
        variables = sc.edge_variables(4)
        self.assertEqual(
            variables,
            {(0, 1): 1, (0, 2): 2, (0, 3): 3, (1, 2): 4, (1, 3): 5, (2, 3): 6},
        )

    def test_formula_dimensions(self) -> None:
        clauses, stats = sc.build_formula()
        self.assertEqual(stats.edge_variables, 231)
        self.assertEqual(stats.counter_aux_variables, 25_871)
        self.assertEqual(stats.saturation_witness_variables, 43_890)
        self.assertEqual(stats.variables, 69_992)
        self.assertEqual(stats.k4_clauses, 7_315)
        self.assertEqual(stats.independent5_clauses, 26_334)
        self.assertEqual(stats.exact_edge_clauses, 103_152)
        self.assertEqual(stats.saturation_clauses, 219_681)
        self.assertEqual(stats.clauses, 356_482)
        self.assertEqual(len(clauses), stats.clauses)
        self.assertLessEqual(max(abs(lit) for clause in clauses for lit in clause), stats.variables)

    def test_graph6_roundtrip(self) -> None:
        edges = {(0, 1), (0, 3), (1, 2), (2, 3)}
        record = sc.encode_graph6(4, edges)
        self.assertEqual(sc.decode_graph6(record), (4, edges))

    def test_small_exact_counter_exhaustively(self) -> None:
        try:
            from pysat.solvers import Solver
        except ImportError:
            self.skipTest("python-sat is not installed")

        for count in range(2, 7):
            inputs = list(range(1, count + 1))
            for bound in range(1, count):
                clauses, _, _ = sc.encode_exactly_leansms(inputs, bound, count + 1)
                with Solver(name="minisat22", bootstrap_with=clauses) as solver:
                    for bits in itertools.product((False, True), repeat=count):
                        assumptions = [var if bit else -var for var, bit in zip(inputs, bits)]
                        self.assertEqual(solver.solve(assumptions=assumptions), sum(bits) == bound)


if __name__ == "__main__":
    unittest.main()
