from __future__ import annotations

import itertools
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import prepare_sms_coverage as pc  # noqa: E402
import saturated_cnf as sc  # noqa: E402


class PrepareSMSCoverageTests(unittest.TestCase):
    def test_parse_sms_edge_line(self) -> None:
        self.assertEqual(pc.parse_sms_edge_line("[(0,1),(2,21)]"), {(0, 1), (2, 21)})
        with self.assertRaises(ValueError):
            pc.parse_sms_edge_line("[(1,0)]")
        with self.assertRaises(ValueError):
            pc.parse_sms_edge_line("[(0,1),(0,1)]")

    def test_known_graph6_order(self) -> None:
        edges = {(0, 1), (0, 3), (1, 2), (2, 3)}
        self.assertEqual(sc.encode_graph6(4, edges), "Cl")

    def test_fast_audit_matches_simple_audit_on_witness(self) -> None:
        record = (ROOT / "data/r4522.112.saturated.witness.g6").read_text().strip()
        n, edges = sc.decode_graph6(record)
        simple = sc.audit_graph(n, edges)
        fast = pc.audit_edges_fast(edges)
        self.assertEqual(fast, simple)

    def test_audit_graph6_catalogue(self) -> None:
        catalogue = ROOT / "data/r4522.112.saturated.witness.canonical.g6"
        result = pc.audit_graph6_catalogue(catalogue, None)
        self.assertEqual(result["audit"]["records"], 1)
        self.assertTrue(result["audit"]["all_valid"])

    def test_blockers(self) -> None:
        edges = set(itertools.islice(sc.edge_pairs(), sc.TARGET_EDGES))
        variables = sc.edge_variables()
        present = pc.blocker_clause(edges, "present")
        full = pc.blocker_clause(edges, "full")
        self.assertEqual(len(present), sc.TARGET_EDGES)
        self.assertEqual(len(full), len(variables))
        self.assertEqual(set(present), {-variables[edge] for edge in edges})

    def test_dimacs_multiline_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "small.cnf"
            path.write_text("c test\np cnf 3 2\n1 -2\n3 0\n0\n")
            stats = pc.scan_dimacs(path)
            self.assertEqual(stats.variables, 3)
            self.assertEqual(stats.clauses, 2)
            self.assertEqual(list(pc.iter_dimacs_clauses(path)), [[1, -2, 3], []])


if __name__ == "__main__":
    unittest.main()
