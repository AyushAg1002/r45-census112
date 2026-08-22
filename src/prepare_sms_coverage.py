#!/usr/bin/env python3
"""Stream SMS models and build the ordinary-SAT coverage instance.

The pinned SMS binary prints each graph as a Python edge list.  The ``extract``
subcommand ignores diagnostic lines, parses only lines beginning with ``[``,
audits every graph independently of SAT auxiliary variables, and writes the
SMS-labelled catalogue as graph6.

The ``cover`` subcommand concatenates the base CNF, a DIMACS file containing
*Lean-verified* symmetry clauses, and one edge-only blocker per catalogue
record.  An LRAT refutation of that resulting CNF is the ordinary-SAT half of
the coverage certificate.  This script does not claim to verify the symmetry
clauses; that is deliberately left to LeanSMS.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import platform
import sys
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from saturated_cnf import (
    N,
    TARGET_EDGES,
    decode_graph6,
    edge_pairs,
    edge_variables,
    encode_graph6,
    normalized_edge,
    sha256_file,
)


@dataclass(frozen=True)
class DimacsStats:
    variables: int
    clauses: int
    maximum_literal: int
    sha256: str


def environment() -> dict[str, str]:
    return {"platform": platform.platform(), "python": sys.version.split()[0]}


def parse_sms_edge_line(line: str, line_number: int = 0) -> set[tuple[int, int]]:
    """Parse one direct-``smsg`` Python edge-list record, fail closed."""
    prefix = f"line {line_number}: " if line_number else ""
    try:
        value = ast.literal_eval(line)
    except (SyntaxError, ValueError) as error:
        raise ValueError(prefix + "invalid SMS edge-list syntax") from error
    if not isinstance(value, list):
        raise ValueError(prefix + "SMS record is not a list")

    edges: set[tuple[int, int]] = set()
    for item in value:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ValueError(prefix + "edge is not a pair")
        u, v = item
        if isinstance(u, bool) or isinstance(v, bool) or not isinstance(u, int) or not isinstance(v, int):
            raise ValueError(prefix + "edge endpoints must be integers")
        if not (0 <= u < v < N):
            raise ValueError(prefix + f"edge {(u, v)} is outside the required 0 <= u < v < {N}")
        edge = (u, v)
        if edge in edges:
            raise ValueError(prefix + f"duplicate edge {edge}")
        edges.add(edge)
    return edges


def adjacency_masks(n: int, edges: Iterable[tuple[int, int]]) -> list[int]:
    adjacency = [0] * n
    for u, v in edges:
        adjacency[u] |= 1 << v
        adjacency[v] |= 1 << u
    return adjacency


def mask_has_edge(mask: int, adjacency: Sequence[int]) -> bool:
    while mask:
        bit = mask & -mask
        vertex = bit.bit_length() - 1
        mask ^= bit
        if adjacency[vertex] & mask:
            return True
    return False


def has_clique(adjacency: Sequence[int], size: int) -> bool:
    """Return whether the bitset graph contains a clique of ``size``."""
    all_vertices = (1 << len(adjacency)) - 1

    def search(candidates: int, remaining: int) -> bool:
        if remaining == 0:
            return True
        if candidates.bit_count() < remaining:
            return False
        while candidates.bit_count() >= remaining:
            bit = candidates & -candidates
            vertex = bit.bit_length() - 1
            candidates ^= bit
            if search(candidates & adjacency[vertex], remaining - 1):
                return True
        return False

    return search(all_vertices, size)


def audit_edges_fast(edges: set[tuple[int, int]]) -> dict[str, object]:
    """Audit a 22-vertex record using bitsets rather than SAT witnesses."""
    adjacency = adjacency_masks(N, edges)
    complete_mask = (1 << N) - 1

    k4_free = True
    saturated = True
    for u, v in edge_pairs(N):
        common = adjacency[u] & adjacency[v]
        if (u, v) in edges:
            if mask_has_edge(common, adjacency):
                k4_free = False
        elif not mask_has_edge(common, adjacency):
            saturated = False

    complement = [
        complete_mask & ~(adjacency[vertex] | (1 << vertex)) for vertex in range(N)
    ]
    independent5_free = not has_clique(complement, 5)
    degrees = sorted((mask.bit_count() for mask in adjacency), reverse=True)
    valid = (
        len(edges) == TARGET_EDGES
        and k4_free
        and independent5_free
        and saturated
    )
    return {
        "vertices": N,
        "edges": len(edges),
        "degree_sequence": degrees,
        "k4_free": k4_free,
        "independent5_free": independent5_free,
        "k4_saturated": saturated,
        "valid": valid,
    }


def iter_graph6(path: Path) -> Iterator[tuple[int, str, set[tuple[int, int]]]]:
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            record = line.strip()
            if not record or record.startswith(">>"):
                continue
            n, edges = decode_graph6(record)
            if n != N:
                raise ValueError(f"{path}:{line_number}: expected order {N}, found {n}")
            yield line_number, record, edges


def extract_models(models: Path, graph6_out: Path, manifest: Path | None) -> dict[str, object]:
    input_hash = hashlib.sha256()
    output_hash = hashlib.sha256()
    models_seen = 0
    ignored_nonempty_lines = 0
    duplicate_labelled_records = 0
    seen_records: set[str] = set()
    degree_sequences: Counter[str] = Counter()

    graph6_out.parent.mkdir(parents=True, exist_ok=True)
    with models.open("rb") as source, graph6_out.open("wb") as destination:
        for line_number, raw_line in enumerate(source, start=1):
            input_hash.update(raw_line)
            try:
                line = raw_line.decode("utf-8")
            except UnicodeDecodeError as error:
                raise ValueError(f"{models}:{line_number}: output is not UTF-8") from error
            if not line.lstrip().startswith("["):
                if line.strip():
                    ignored_nonempty_lines += 1
                continue
            edges = parse_sms_edge_line(line.strip(), line_number)
            audit = audit_edges_fast(edges)
            if not audit["valid"]:
                raise ValueError(
                    f"{models}:{line_number}: invalid saturated Ramsey graph: "
                    + json.dumps(audit, sort_keys=True)
                )
            record = encode_graph6(N, edges)
            if record in seen_records:
                duplicate_labelled_records += 1
            else:
                seen_records.add(record)
            degree_sequences[",".join(map(str, audit["degree_sequence"]))] += 1
            encoded = (record + "\n").encode()
            destination.write(encoded)
            output_hash.update(encoded)
            models_seen += 1

    result: dict[str, object] = {
        "catalogue": {
            "degree_sequence_distribution": dict(sorted(degree_sequences.items())),
            "duplicate_labelled_records": duplicate_labelled_records,
            "models": models_seen,
            "path": str(graph6_out),
            "sha256": output_hash.hexdigest(),
        },
        "environment": environment(),
        "sms_output": {
            "ignored_nonempty_lines": ignored_nonempty_lines,
            "path": str(models),
            "sha256": input_hash.hexdigest(),
        },
    }
    write_manifest(manifest, result)
    return result


def audit_graph6_catalogue(catalogue: Path, manifest: Path | None) -> dict[str, object]:
    """Audit saturated graph6 records with the bit-parallel implementation."""
    records = 0
    degree_sequences: Counter[str] = Counter()
    for line_number, _, edges in iter_graph6(catalogue):
        audit = audit_edges_fast(edges)
        if not audit["valid"]:
            raise ValueError(
                f"{catalogue}:{line_number}: invalid saturated Ramsey graph: "
                + json.dumps(audit, sort_keys=True)
            )
        degree_sequences[",".join(map(str, audit["degree_sequence"]))] += 1
        records += 1

    result: dict[str, object] = {
        "audit": {
            "all_valid": True,
            "degree_sequence_distribution": dict(sorted(degree_sequences.items())),
            "implementation": "bit-parallel audit_edges_fast",
            "records": records,
        },
        "catalogue": {
            "path": str(catalogue),
            "sha256": sha256_file(catalogue),
        },
        "environment": environment(),
    }
    write_manifest(manifest, result)
    return result


def iter_dimacs_clauses(path: Path) -> Iterator[list[int]]:
    current: list[int] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("c") or stripped.startswith("p"):
                continue
            for token in stripped.split():
                try:
                    literal = int(token)
                except ValueError as error:
                    raise ValueError(f"{path}:{line_number}: noninteger DIMACS token {token!r}") from error
                if literal == 0:
                    yield current
                    current = []
                else:
                    current.append(literal)
    if current:
        raise ValueError(f"{path}: final DIMACS clause lacks a terminating zero")


def scan_dimacs(path: Path) -> DimacsStats:
    header: tuple[int, int] | None = None
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("c"):
                continue
            if stripped.startswith("p"):
                fields = stripped.split()
                if len(fields) != 4 or fields[:2] != ["p", "cnf"]:
                    raise ValueError(f"{path}:{line_number}: malformed DIMACS header")
                if header is not None:
                    raise ValueError(f"{path}:{line_number}: duplicate DIMACS header")
                header = (int(fields[2]), int(fields[3]))
    if header is None:
        raise ValueError(f"{path}: no DIMACS header")

    clause_count = 0
    maximum_literal = 0
    for clause in iter_dimacs_clauses(path):
        clause_count += 1
        if clause:
            maximum_literal = max(maximum_literal, max(abs(literal) for literal in clause))
    if clause_count != header[1]:
        raise ValueError(
            f"{path}: header declares {header[1]} clauses, parsed {clause_count}"
        )
    if maximum_literal > header[0]:
        raise ValueError(
            f"{path}: literal {maximum_literal} exceeds declared variable count {header[0]}"
        )
    return DimacsStats(header[0], clause_count, maximum_literal, sha256_file(path))


def blocker_clause(edges: set[tuple[int, int]], style: str) -> list[int]:
    variables = edge_variables(N)
    if style == "present":
        if len(edges) != TARGET_EDGES:
            raise ValueError("present-edge blockers require exactly 112 catalogue edges")
        return [-variables[edge] for edge in sorted(edges)]
    if style == "full":
        return [
            -variable if edge in edges else variable
            for edge, variable in variables.items()
        ]
    raise ValueError(f"unknown blocker style {style!r}")


def write_clause(handle, hasher: hashlib._Hash, clause: Sequence[int]) -> None:  # type: ignore[name-defined]
    encoded = (" ".join(map(str, clause)) + " 0\n").encode()
    handle.write(encoded)
    hasher.update(encoded)


def build_coverage_cnf(
    base: Path,
    verified_symmetry: Path,
    catalogue: Path,
    output: Path,
    blocker_style: str,
    manifest: Path | None,
) -> dict[str, object]:
    base_stats = scan_dimacs(base)
    symmetry_stats = scan_dimacs(verified_symmetry)

    catalogue_count = 0
    degree_sequences: Counter[str] = Counter()
    for line_number, _, edges in iter_graph6(catalogue):
        audit = audit_edges_fast(edges)
        if not audit["valid"]:
            raise ValueError(
                f"{catalogue}:{line_number}: invalid saturated Ramsey graph: "
                + json.dumps(audit, sort_keys=True)
            )
        degree_sequences[",".join(map(str, audit["degree_sequence"]))] += 1
        catalogue_count += 1

    variables = max(base_stats.variables, symmetry_stats.variables)
    clauses = base_stats.clauses + symmetry_stats.clauses + catalogue_count
    output.parent.mkdir(parents=True, exist_ok=True)
    output_hash = hashlib.sha256()
    with output.open("wb") as destination:
        header = f"p cnf {variables} {clauses}\n".encode()
        destination.write(header)
        output_hash.update(header)
        for source in (base, verified_symmetry):
            for clause in iter_dimacs_clauses(source):
                write_clause(destination, output_hash, clause)
        for _, _, edges in iter_graph6(catalogue):
            write_clause(destination, output_hash, blocker_clause(edges, blocker_style))

    result: dict[str, object] = {
        "base_cnf": {"path": str(base), **asdict(base_stats)},
        "blocker_style": blocker_style,
        "catalogue": {
            "degree_sequence_distribution": dict(sorted(degree_sequences.items())),
            "models": catalogue_count,
            "path": str(catalogue),
            "sha256": sha256_file(catalogue),
        },
        "coverage_cnf": {
            "clauses": clauses,
            "path": str(output),
            "sha256": output_hash.hexdigest(),
            "variables": variables,
        },
        "environment": environment(),
        "verified_symmetry_cnf": {
            "path": str(verified_symmetry),
            **asdict(symmetry_stats),
        },
    }
    write_manifest(manifest, result)
    return result


def write_manifest(path: Path | None, result: dict[str, object]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="extract and audit direct SMS model output")
    extract.add_argument("--models", type=Path, required=True)
    extract.add_argument("--graph6-out", type=Path, required=True)
    extract.add_argument("--manifest", type=Path)

    audit = subparsers.add_parser(
        "audit", help="audit saturated graph6 records with the bit-parallel checker"
    )
    audit.add_argument("--catalogue", type=Path, required=True)
    audit.add_argument("--manifest", type=Path)

    cover = subparsers.add_parser("cover", help="build base + verified symmetry + blockers CNF")
    cover.add_argument("--base", type=Path, required=True)
    cover.add_argument("--verified-symmetry", type=Path, required=True)
    cover.add_argument("--catalogue", type=Path, required=True)
    cover.add_argument("--output", type=Path, required=True)
    cover.add_argument("--blocker-style", choices=("present", "full"), default="present")
    cover.add_argument("--manifest", type=Path)

    args = parser.parse_args()
    if args.command == "extract":
        result = extract_models(args.models, args.graph6_out, args.manifest)
    elif args.command == "audit":
        result = audit_graph6_catalogue(args.catalogue, args.manifest)
    else:
        result = build_coverage_cnf(
            args.base,
            args.verified_symmetry,
            args.catalogue,
            args.output,
            args.blocker_style,
            args.manifest,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
