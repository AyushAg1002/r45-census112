#!/usr/bin/env python3
"""Generate and audit the saturated R(4,5,22,112) SAT instance.

The first 231 variables are graph edges in the row-major upper-triangle
ordering required by SAT Modulo Symmetries (SMS):

    (0,1), (0,2), ..., (0,21), (1,2), ..., (20,21).

The formula describes graphs with exactly 112 edges, no K4, no independent
5-set, and which are K4-saturated: adding any absent edge creates a K4.

The exact-cardinality encoding is a direct transcription of the verified
sequential counter in LeanSMS (commit f5e95289e85fd7b019e768ef759a11f736802f30).
Only one direction of each saturation witness is needed: if a nonedge uv is
selected, a witness xy must be true, and a true witness forces the five edges
ux, uy, vx, vy, xy.  This is equisatisfiable with K4-saturation while keeping
the CNF comparatively small.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


N = 22
TARGET_EDGES = 112


@dataclass(frozen=True)
class FormulaStats:
    vertices: int
    target_edges: int
    edge_variables: int
    counter_aux_variables: int
    saturation_witness_variables: int
    variables: int
    k4_clauses: int
    independent5_clauses: int
    exact_edge_clauses: int
    saturation_clauses: int
    clauses: int


def edge_pairs(n: int = N) -> list[tuple[int, int]]:
    return list(itertools.combinations(range(n), 2))


def edge_variables(n: int = N) -> dict[tuple[int, int], int]:
    return {pair: index for index, pair in enumerate(edge_pairs(n), start=1)}


def normalized_edge(u: int, v: int) -> tuple[int, int]:
    if u == v:
        raise ValueError("loops are not graph edges")
    return (u, v) if u < v else (v, u)


def encode_exactly_leansms(
    inputs: Sequence[int], bound: int, first_aux_variable: int
) -> tuple[list[list[int]], int, int]:
    """Encode exactly ``bound`` true inputs using LeanSMS's full counter.

    Returns ``(clauses, next_unused_variable, auxiliary_count)``.  Variable
    numbers are DIMACS-positive integers.  The construction matches
    ``LeanSMS.Encode.encodeExactlyK`` rather than relying on a SAT library.
    """
    count = len(inputs)
    if not 0 <= bound <= count:
        return ([[]], first_aux_variable, 0)
    if bound == 0:
        return ([[-var] for var in inputs], first_aux_variable, 0)
    if bound == count:
        return ([[var] for var in inputs], first_aux_variable, 0)

    # LeanSMS auxiliary index 0 corresponds to first_aux_variable in DIMACS.
    def aux(aux_index: int) -> int:
        return first_aux_variable + aux_index

    def counter_var(row: int, column: int) -> int:
        if row == 0:
            if column == 0:
                return inputs[0]
            return aux(column - 1)
        return aux((bound - 1) + (row - 1) * bound + column)

    clauses: list[list[int]] = []

    # Row zero cannot already contain two or more true inputs.
    for column in range(1, bound):
        clauses.append([-counter_var(0, column)])

    # Exact recurrence: s[i+1,j] iff s[i,j] or (x[i+1] and s[i,j-1]).
    for row in range(count - 1):
        next_input = inputs[row + 1]
        clauses.append([-next_input, counter_var(row + 1, 0)])
        for column in range(bound):
            previous = counter_var(row, column)
            current = counter_var(row + 1, column)
            clauses.append([-previous, current])
            clauses.append([previous, next_input, -current])
            if column < bound - 1:
                incremented = counter_var(row + 1, column + 1)
                clauses.append([-previous, -next_input, incremented])
                clauses.append([previous, -incremented])

    # At most bound.
    for row in range(count - 1):
        clauses.append([-counter_var(row, bound - 1), -inputs[row + 1]])

    # At least bound.
    clauses.append([counter_var(count - 1, bound - 1)])

    auxiliary_count = (bound - 1) + (count - 1) * bound
    return clauses, first_aux_variable + auxiliary_count, auxiliary_count


def build_formula(n: int = N, target_edges: int = TARGET_EDGES) -> tuple[list[list[int]], FormulaStats]:
    if n != N or target_edges != TARGET_EDGES:
        raise ValueError("the saturated census formula is intentionally fixed at n=22, e=112")

    edge_var = edge_variables(n)
    clauses: list[list[int]] = []

    # No K4.
    for vertices in itertools.combinations(range(n), 4):
        clauses.append([-edge_var[pair] for pair in itertools.combinations(vertices, 2)])
    k4_clause_count = len(clauses)

    # No independent 5-set.
    for vertices in itertools.combinations(range(n), 5):
        clauses.append([edge_var[pair] for pair in itertools.combinations(vertices, 2)])
    independent5_clause_count = len(clauses) - k4_clause_count

    counter_clauses, next_variable, counter_aux_count = encode_exactly_leansms(
        list(edge_var.values()), target_edges, len(edge_var) + 1
    )
    clauses.extend(counter_clauses)
    exact_edge_clause_count = len(counter_clauses)

    # K4-saturation.  If uv is absent, some adjacent pair x,y lies in the
    # common neighbourhood of u and v.  A witness variable implies all five
    # required edges; the long clause requires at least one witness.
    first_witness_variable = next_variable
    saturation_clause_count = 0
    for u, v in edge_pairs(n):
        remaining = [vertex for vertex in range(n) if vertex not in (u, v)]
        witnesses: list[int] = []
        for x, y in itertools.combinations(remaining, 2):
            witness = next_variable
            next_variable += 1
            witnesses.append(witness)
            required_edges = ((u, x), (u, y), (v, x), (v, y), (x, y))
            for a, b in required_edges:
                clauses.append([-witness, edge_var[normalized_edge(a, b)]])
                saturation_clause_count += 1
        clauses.append([edge_var[u, v], *witnesses])
        saturation_clause_count += 1

    stats = FormulaStats(
        vertices=n,
        target_edges=target_edges,
        edge_variables=len(edge_var),
        counter_aux_variables=counter_aux_count,
        saturation_witness_variables=next_variable - first_witness_variable,
        variables=next_variable - 1,
        k4_clauses=k4_clause_count,
        independent5_clauses=independent5_clause_count,
        exact_edge_clauses=exact_edge_clause_count,
        saturation_clauses=saturation_clause_count,
        clauses=len(clauses),
    )
    return clauses, stats


def write_dimacs(path: Path, clauses: Sequence[Sequence[int]], variable_count: int) -> str:
    hasher = hashlib.sha256()
    with path.open("wb") as handle:
        header = f"p cnf {variable_count} {len(clauses)}\n".encode()
        handle.write(header)
        hasher.update(header)
        for clause in clauses:
            line = (" ".join(map(str, clause)) + " 0\n").encode()
            handle.write(line)
            hasher.update(line)
    return hasher.hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


def encode_graph6(n: int, edges: Iterable[tuple[int, int]]) -> str:
    if not 0 <= n <= 62:
        raise ValueError("this helper supports graph6's one-byte order only")
    edge_set = {normalized_edge(*edge) for edge in edges}
    bits = [1 if (u, v) in edge_set else 0 for v in range(1, n) for u in range(v)]
    bits.extend([0] * ((-len(bits)) % 6))
    payload = []
    for start in range(0, len(bits), 6):
        value = 0
        for bit in bits[start : start + 6]:
            value = 2 * value + bit
        payload.append(chr(value + 63))
    return chr(n + 63) + "".join(payload)


def decode_graph6(record: str) -> tuple[int, set[tuple[int, int]]]:
    record = record.strip()
    if not record or record.startswith(">>"):
        raise ValueError("expected a headerless, nonempty graph6 record")
    n = ord(record[0]) - 63
    if not 0 <= n <= 62:
        raise ValueError("this helper supports graph6's one-byte order only")
    bits: list[int] = []
    for char in record[1:]:
        value = ord(char) - 63
        if not 0 <= value < 64:
            raise ValueError("invalid graph6 character")
        bits.extend((value >> shift) & 1 for shift in range(5, -1, -1))
    pairs = [(u, v) for v in range(1, n) for u in range(v)]
    if len(bits) < len(pairs):
        raise ValueError("truncated graph6 record")
    return n, {pair for pair, bit in zip(pairs, bits, strict=False) if bit}


def is_k4_saturated(n: int, edges: set[tuple[int, int]]) -> bool:
    neighbours = [set() for _ in range(n)]
    for u, v in edges:
        neighbours[u].add(v)
        neighbours[v].add(u)
    for u, v in itertools.combinations(range(n), 2):
        if (u, v) in edges:
            continue
        common = neighbours[u] & neighbours[v]
        if not any(normalized_edge(x, y) in edges for x, y in itertools.combinations(common, 2)):
            return False
    return True


def audit_graph(n: int, edges: set[tuple[int, int]]) -> dict[str, object]:
    edge_count = len(edges)
    k4_free = all(
        any(pair not in edges for pair in itertools.combinations(vertices, 2))
        for vertices in itertools.combinations(range(n), 4)
    )
    independent5_free = all(
        any(pair in edges for pair in itertools.combinations(vertices, 2))
        for vertices in itertools.combinations(range(n), 5)
    )
    saturated = is_k4_saturated(n, edges)
    degrees = sorted(
        (sum(vertex in pair for pair in edges) for vertex in range(n)), reverse=True
    )
    return {
        "vertices": n,
        "edges": edge_count,
        "degree_sequence": degrees,
        "k4_free": k4_free,
        "independent5_free": independent5_free,
        "k4_saturated": saturated,
        "valid": n == N
        and edge_count == TARGET_EDGES
        and k4_free
        and independent5_free
        and saturated,
    }


def solve_formula(clauses: Sequence[Sequence[int]], solver_name: str) -> list[int] | None:
    try:
        from pysat.solvers import Solver
    except ImportError as error:  # pragma: no cover - exercised only without dependency
        raise RuntimeError("solving requires python-sat") from error
    with Solver(name=solver_name, bootstrap_with=clauses) as solver:
        if not solver.solve():
            return None
        return solver.get_model()


def pysat_version() -> str:
    try:
        import pysat
    except ImportError as error:  # pragma: no cover - exercised only without dependency
        raise RuntimeError("solving requires python-sat") from error
    return str(pysat.__version__)


def positive_edge_model(model: Sequence[int], n: int = N) -> set[tuple[int, int]]:
    positive = {literal for literal in model if literal > 0}
    return {pair for pair, variable in edge_variables(n).items() if variable in positive}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnf", type=Path, help="write the deterministic DIMACS instance")
    parser.add_argument("--manifest", type=Path, help="write formula dimensions and SHA-256")
    parser.add_argument("--solve", action="store_true", help="find one saturated witness")
    parser.add_argument("--solver", default="kissat404", help="PySAT solver name")
    parser.add_argument("--witness", type=Path, help="write a found witness in graph6 format")
    parser.add_argument("--audit-witness", type=Path, help="audit the first graph6 record in this file")
    args = parser.parse_args()

    if args.audit_witness:
        record = args.audit_witness.read_text().splitlines()[0]
        n, edges = decode_graph6(record)
        audit = audit_graph(n, edges)
        result = {
            "audit": audit,
            "environment": {
                "platform": platform.platform(),
                "python": sys.version.split()[0],
            },
            "witness": {
                "graph6": record,
                "path": str(args.audit_witness),
                "sha256": sha256_file(args.audit_witness),
            },
        }
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        print(rendered, end="")
        if args.manifest:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(rendered)
        return 0 if audit["valid"] else 1

    clauses, stats = build_formula()
    digest = None
    if args.cnf:
        args.cnf.parent.mkdir(parents=True, exist_ok=True)
        digest = write_dimacs(args.cnf, clauses, stats.variables)

    result: dict[str, object] = {"formula": asdict(stats)}
    if args.cnf:
        result["cnf"] = {"path": str(args.cnf), "sha256": digest}

    if args.solve:
        start = time.perf_counter()
        model = solve_formula(clauses, args.solver)
        result["elapsed_seconds"] = time.perf_counter() - start
        result["environment"] = {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "pysat": pysat_version(),
        }
        result["solver"] = args.solver
        result["status"] = "SAT" if model is not None else "UNSAT"
        if model is not None:
            edges = positive_edge_model(model)
            record = encode_graph6(N, edges)
            audit = audit_graph(N, edges)
            result["witness"] = {"graph6": record, "audit": audit}
            if args.witness:
                args.witness.parent.mkdir(parents=True, exist_ok=True)
                args.witness.write_text(record + "\n")
                result["witness"]["path"] = str(args.witness)
                result["witness"]["sha256"] = sha256_file(args.witness)

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(rendered)
    return 1 if args.solve and model is None else 0


if __name__ == "__main__":
    raise SystemExit(main())
