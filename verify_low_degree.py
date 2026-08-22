#!/usr/bin/env python3
"""Verify the minimum-degree 5 and 6 extension cases for R(4,5,22,112).

If G is a Ramsey(4,5,22)-graph with 112 edges and v is a minimum-degree
vertex of degree d, then H=G-v is a Ramsey(4,5,21)-graph with 112-d edges.
Writing S=N_G(v), the extension is valid exactly when

  * |S|=d;
  * H[S] is triangle-free; and
  * S meets every independent 4-set of H.

This program checks those conditions on the complete public 106- and
107-edge catalogues.  It deliberately does not use nauty or NetworkX: the
trusted code consists of this file plus Python's standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence


ORDER = 21
TARGET_ORDER = 22
TARGET_EDGES = 112

CATALOGUES = {
    5: {
        "file": "r4521.107.g6",
        "edges": 107,
        "records": 31,
        "sha256": "6ef8619d5d6be9efa15cb9a5ccb6b0da7304cfbfd57fff29bb0dec2e46f81bef",
    },
    6: {
        "file": "r4521.106.g6",
        "edges": 106,
        "records": 10188,
        "sha256": "2be4df6ba89b1c55743624fb6e8141741aef82b06a922aa0a069923942389593",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def decode_graph6(record: bytes) -> list[int]:
    """Decode a small graph6 record to adjacency bitsets.

    Only the one-byte order header used by the order-21 inputs is accepted.
    Rejecting other graph6 variants keeps the parser small and auditable.
    """

    record = record.strip()
    if not record or record.startswith(b">>graph6<<"):
        raise ValueError("expected one headerless graph6 record")
    order = record[0] - 63
    if not 0 <= order <= 62:
        raise ValueError("extended graph6 orders are not supported")
    needed = (order * (order - 1) // 2 + 5) // 6
    if len(record) != needed + 1:
        raise ValueError(
            f"wrong graph6 length for order {order}: {len(record)} != {needed + 1}"
        )
    values = [byte - 63 for byte in record[1:]]
    if any(not 0 <= value <= 63 for value in values):
        raise ValueError("invalid graph6 character")

    adjacency = [0] * order
    bit_index = 0
    for right in range(1, order):
        for left in range(right):
            value = values[bit_index // 6]
            bit = (value >> (5 - bit_index % 6)) & 1
            if bit:
                adjacency[left] |= 1 << right
                adjacency[right] |= 1 << left
            bit_index += 1
    return adjacency


def edge_count(adjacency: Sequence[int]) -> int:
    return sum(neighbours.bit_count() for neighbours in adjacency) // 2


def independent_four_sets(adjacency: Sequence[int]) -> list[int]:
    """Return all independent 4-sets as vertex bitmasks."""

    result: list[int] = []
    for a, b, c, d in itertools.combinations(range(len(adjacency)), 4):
        if adjacency[a] & ((1 << b) | (1 << c) | (1 << d)):
            continue
        if adjacency[b] & ((1 << c) | (1 << d)):
            continue
        if adjacency[c] & (1 << d):
            continue
        result.append((1 << a) | (1 << b) | (1 << c) | (1 << d))
    return result


def contains_k4(adjacency: Sequence[int]) -> bool:
    """Check for a K4 by looking for an edge inside an edge's common cone."""

    order = len(adjacency)
    for a in range(order):
        higher_a = adjacency[a] & ~((1 << (a + 1)) - 1)
        while higher_a:
            b_bit = higher_a & -higher_a
            higher_a -= b_bit
            b = b_bit.bit_length() - 1
            common = adjacency[a] & adjacency[b]
            scan = common
            while scan:
                c_bit = scan & -scan
                scan -= c_bit
                c = c_bit.bit_length() - 1
                if adjacency[c] & scan:
                    return True
    return False


def contains_i5(adjacency: Sequence[int], independent4: Sequence[int]) -> bool:
    """Check whether an independent 4-set has a common non-neighbour."""

    full = (1 << len(adjacency)) - 1
    for four in independent4:
        candidates = full ^ four
        scan = four
        while scan and candidates:
            vertex_bit = scan & -scan
            scan -= vertex_bit
            vertex = vertex_bit.bit_length() - 1
            candidates &= ~adjacency[vertex]
        if candidates:
            return True
    return False


def can_add_without_triangle(adjacency: Sequence[int], chosen: int, vertex: int) -> bool:
    """Whether adding vertex to a triangle-free chosen set preserves that fact."""

    neighbours = adjacency[vertex] & chosen
    while neighbours:
        first = neighbours & -neighbours
        neighbours -= first
        first_vertex = first.bit_length() - 1
        if adjacency[first_vertex] & neighbours:
            return False
    return True


def is_triangle_free(adjacency: Sequence[int], chosen: int) -> bool:
    scan = chosen
    prefix = 0
    while scan:
        vertex_bit = scan & -scan
        scan -= vertex_bit
        vertex = vertex_bit.bit_length() - 1
        if not can_add_without_triangle(adjacency, prefix, vertex):
            return False
        prefix |= vertex_bit
    return True


@dataclass
class SearchStats:
    nodes: int = 0
    covered_states: int = 0


def transversal_candidates(
    adjacency: Sequence[int], independent4: Sequence[int], size: int
) -> tuple[set[int], SearchStats]:
    """Enumerate triangle-free size-``size`` transversals of independent4.

    At a partial set S, choose an independent 4-set E disjoint from S.  Every
    completion must contain at least one member of E, so branching on E is
    exhaustive.  If all hyperedges are met early, enumerate all triangle-free
    completions to the requested cardinality.  A set removes duplicates caused
    by reaching the same transversal through different branch orders.
    """

    order = len(adjacency)
    solutions: set[int] = set()
    stats = SearchStats()

    def complete(chosen: int, start: int) -> None:
        need = size - chosen.bit_count()
        if need == 0:
            solutions.add(chosen)
            return
        available = sum(
            1 for vertex in range(start, order) if not (chosen >> vertex) & 1
        )
        if available < need:
            return
        for vertex in range(start, order):
            bit = 1 << vertex
            if chosen & bit:
                continue
            if can_add_without_triangle(adjacency, chosen, vertex):
                complete(chosen | bit, vertex + 1)

    def search(chosen: int) -> None:
        stats.nodes += 1
        uncovered = next((edge for edge in independent4 if not edge & chosen), None)
        if uncovered is None:
            stats.covered_states += 1
            complete(chosen, 0)
            return
        if chosen.bit_count() == size:
            return
        choices = uncovered
        while choices:
            vertex_bit = choices & -choices
            choices -= vertex_bit
            vertex = vertex_bit.bit_length() - 1
            if can_add_without_triangle(adjacency, chosen, vertex):
                search(chosen | vertex_bit)

    search(0)
    return solutions, stats


def brute_force_candidates(
    adjacency: Sequence[int], independent4: Sequence[int], size: int
) -> set[int]:
    """Slow, structurally independent reference enumerator."""

    result: set[int] = set()
    for vertices in itertools.combinations(range(len(adjacency)), size):
        chosen = sum(1 << vertex for vertex in vertices)
        if not is_triangle_free(adjacency, chosen):
            continue
        if all(edge & chosen for edge in independent4):
            result.add(chosen)
    return result


def iter_records(path: Path) -> Iterator[bytes]:
    with path.open("rb") as handle:
        for line_number, record in enumerate(handle, 1):
            record = record.strip()
            if not record:
                raise ValueError(f"blank record at {path}:{line_number}")
            yield record


def verify_layer(
    degree: int,
    catalogue_dir: Path,
    validate_ramsey: bool,
    brute_force_prefix: int,
) -> dict[str, object]:
    metadata = CATALOGUES[degree]
    path = catalogue_dir / str(metadata["file"])
    actual_hash = sha256(path)
    if actual_hash != metadata["sha256"]:
        raise ValueError(
            f"SHA-256 mismatch for {path}: {actual_hash} != {metadata['sha256']}"
        )

    start = time.perf_counter()
    records = 0
    independent4_total = 0
    search_nodes = 0
    covered_states = 0
    candidate_total = 0
    seeds_with_candidates = 0
    first_candidate: dict[str, object] | None = None

    for index, record in enumerate(iter_records(path)):
        adjacency = decode_graph6(record)
        if len(adjacency) != ORDER:
            raise ValueError(f"record {index} has order {len(adjacency)}, expected {ORDER}")
        if edge_count(adjacency) != metadata["edges"]:
            raise ValueError(
                f"record {index} has {edge_count(adjacency)} edges, "
                f"expected {metadata['edges']}"
            )
        independent4 = independent_four_sets(adjacency)
        if validate_ramsey:
            if contains_k4(adjacency):
                raise ValueError(f"record {index} contains K4")
            if contains_i5(adjacency, independent4):
                raise ValueError(f"record {index} contains I5")

        candidates, stats = transversal_candidates(adjacency, independent4, degree)
        if index < brute_force_prefix:
            reference = brute_force_candidates(adjacency, independent4, degree)
            if candidates != reference:
                raise AssertionError(
                    f"optimized/reference mismatch at degree {degree}, record {index}"
                )

        records += 1
        independent4_total += len(independent4)
        search_nodes += stats.nodes
        covered_states += stats.covered_states
        candidate_total += len(candidates)
        if candidates:
            seeds_with_candidates += 1
            if first_candidate is None:
                chosen = min(candidates)
                first_candidate = {
                    "zero_based_seed_index": index,
                    "neighborhood_vertices": [
                        vertex for vertex in range(ORDER) if chosen >> vertex & 1
                    ],
                }

    if records != metadata["records"]:
        raise ValueError(f"record count {records} != expected {metadata['records']}")
    elapsed = time.perf_counter() - start
    return {
        "root_degree": degree,
        "seed_order": ORDER,
        "seed_edges": metadata["edges"],
        "catalogue": str(path),
        "catalogue_source": "https://users.cecs.anu.edu.au/~bdm/data/r45extreme.tar.gz",
        "catalogue_sha256": actual_hash,
        "catalogue_records": records,
        "ramsey_inputs_validated": validate_ramsey,
        "bruteforce_crosschecked_records": min(brute_force_prefix, records),
        "independent_four_sets_total": independent4_total,
        "transversal_search_nodes": search_nodes,
        "covered_partial_states": covered_states,
        "valid_labelled_neighborhoods": candidate_total,
        "seeds_with_valid_neighborhood": seeds_with_candidates,
        "first_candidate": first_candidate,
        "elapsed_seconds": elapsed,
        "conclusion": (
            f"no Ramsey(4,5,22,112) graph has minimum degree {degree}"
            if candidate_total == 0
            else "candidate extensions require canonicalization and direct validation"
        ),
    }


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalogue-dir",
        type=Path,
        default=here / "data" / "r45extreme",
        help="directory containing r4521.106.g6 and r4521.107.g6",
    )
    parser.add_argument(
        "--degree",
        type=int,
        choices=sorted(CATALOGUES),
        action="append",
        help="root degree to check; repeat as needed (default: both 5 and 6)",
    )
    parser.add_argument(
        "--skip-ramsey-validation",
        action="store_true",
        help="trust the input records' K4/I5 property (edge counts and hashes remain checked)",
    )
    parser.add_argument(
        "--bruteforce-prefix",
        type=int,
        default=0,
        help="cross-check the first N records per layer with direct subset enumeration",
    )
    parser.add_argument("--output", type=Path, help="also write the JSON result here")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.bruteforce_prefix < 0:
        raise SystemExit("--bruteforce-prefix must be nonnegative")
    degrees = sorted(set(args.degree or CATALOGUES))
    started = time.perf_counter()
    layers = [
        verify_layer(
            degree,
            args.catalogue_dir,
            not args.skip_ramsey_validation,
            args.bruteforce_prefix,
        )
        for degree in degrees
    ]
    result = {
        "claim": (
            "Every Ramsey(4,5,22)-graph with 112 edges has minimum degree at least 7"
            if degrees == [5, 6]
            and all(layer["valid_labelled_neighborhoods"] == 0 for layer in layers)
            else "partial minimum-degree extension check"
        ),
        "derivation": {
            "minimum_degree_lower_bound_before_computation": 5,
            "minimum_degree_upper_bound_from_average_degree": 10,
            "deleted_seed_edges_formula": "112-d",
            "extension_conditions": [
                "the d-vertex neighborhood is triangle-free",
                "the neighborhood intersects every independent 4-set of the seed",
            ],
        },
        "layers": layers,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "total_elapsed_seconds": time.perf_counter() - started,
    }
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(encoded, end="")
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
