#!/usr/bin/env python3
"""Independently validate the nonsaturated R(4,5,22,112) catalogue.

This checker uses only Python's standard library.  It validates the pinned
catalogue hash, every graph6 record, the Ramsey constraints, and the defining
property that at least one nonedge can be added without producing a K4.
It also records exact structural distributions for the research note.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from collections import Counter
from pathlib import Path
from typing import Sequence


EXPECTED_SHA256 = "d2c556f52d13dd4d38ed955bedd3db5f52b883faafc45fe5561e611afa5cd6a2"
EXPECTED_RECORDS = 785_888
ORDER = 22
EDGES = 112


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def decode_graph6(record: bytes) -> list[int]:
    record = record.strip()
    if not record:
        raise ValueError("empty graph6 record")
    n = record[0] - 63
    if not 0 <= n <= 62:
        raise ValueError("only one-byte graph6 orders are supported")
    bit_count = n * (n - 1) // 2
    if len(record) != 1 + (bit_count + 5) // 6:
        raise ValueError("incorrect graph6 record length")
    encoded = [byte - 63 for byte in record[1:]]
    if any(value < 0 or value > 63 for value in encoded):
        raise ValueError("invalid graph6 byte")
    adjacency = [0] * n
    position = 0
    for right in range(1, n):
        for left in range(right):
            if (encoded[position // 6] >> (5 - position % 6)) & 1:
                adjacency[left] |= 1 << right
                adjacency[right] |= 1 << left
            position += 1
    return adjacency


def has_edge(adjacency: Sequence[int], vertices: int) -> bool:
    scan = vertices
    while scan:
        vertex_bit = scan & -scan
        scan -= vertex_bit
        vertex = vertex_bit.bit_length() - 1
        if adjacency[vertex] & scan:
            return True
    return False


def has_clique(adjacency: Sequence[int], size: int, candidates: int) -> bool:
    if size == 0:
        return True
    while candidates.bit_count() >= size:
        vertex_bit = candidates & -candidates
        candidates -= vertex_bit
        vertex = vertex_bit.bit_length() - 1
        if has_clique(adjacency, size - 1, candidates & adjacency[vertex]):
            return True
    return False


def contains_k4(adjacency: Sequence[int]) -> bool:
    all_vertices = (1 << len(adjacency)) - 1
    return has_clique(adjacency, 4, all_vertices)


def contains_i5(adjacency: Sequence[int]) -> bool:
    all_vertices = (1 << len(adjacency)) - 1
    complement = [
        all_vertices & ~(neighbours | (1 << vertex))
        for vertex, neighbours in enumerate(adjacency)
    ]
    return has_clique(complement, 5, all_vertices)


def addable_nonedges(adjacency: Sequence[int]) -> int:
    """Count nonedges whose addition does not create a K4."""

    count = 0
    n = len(adjacency)
    for left in range(n):
        for right in range(left + 1, n):
            if adjacency[left] & (1 << right):
                continue
            common = adjacency[left] & adjacency[right]
            if not has_edge(adjacency, common):
                count += 1
    return count


def triangle_count(adjacency: Sequence[int]) -> int:
    """Count triangles by summing common neighbours over their three edges."""

    edge_cones = 0
    for left in range(len(adjacency)):
        higher_neighbours = adjacency[left] & ~((1 << (left + 1)) - 1)
        scan = higher_neighbours
        while scan:
            right_bit = scan & -scan
            scan -= right_bit
            right = right_bit.bit_length() - 1
            edge_cones += (adjacency[left] & adjacency[right]).bit_count()
    if edge_cones % 3:
        raise AssertionError("triangle incidence count is not divisible by three")
    return edge_cones // 3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalogue",
        type=Path,
        default=Path("data/r4522.112.nonsaturated.g6"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/nonsaturated_validation.json"),
    )
    parser.add_argument("--expected-sha256", default=EXPECTED_SHA256)
    args = parser.parse_args()

    actual_hash = file_hash(args.catalogue)
    if actual_hash != args.expected_sha256:
        raise ValueError(
            f"catalogue SHA-256 mismatch: {actual_hash} != {args.expected_sha256}"
        )

    started = time.perf_counter()
    record_count = 0
    addable_distribution: Counter[int] = Counter()
    minimum_degree_distribution: Counter[int] = Counter()
    maximum_degree_distribution: Counter[int] = Counter()
    triangle_distribution: Counter[int] = Counter()
    degree_sequence_distribution: Counter[str] = Counter()

    with args.catalogue.open("rb") as handle:
        for line_number, line in enumerate(handle, 1):
            adjacency = decode_graph6(line)
            if len(adjacency) != ORDER:
                raise ValueError(f"line {line_number}: order is not {ORDER}")
            edge_total = sum(row.bit_count() for row in adjacency) // 2
            if edge_total != EDGES:
                raise ValueError(f"line {line_number}: edge count is not {EDGES}")
            if contains_k4(adjacency):
                raise ValueError(f"line {line_number}: contains K4")
            if contains_i5(adjacency):
                raise ValueError(f"line {line_number}: contains independent 5-set")
            addable = addable_nonedges(adjacency)
            if addable == 0:
                raise ValueError(f"line {line_number}: graph is K4-saturated")

            degrees = sorted(row.bit_count() for row in adjacency)
            addable_distribution[addable] += 1
            minimum_degree_distribution[degrees[0]] += 1
            maximum_degree_distribution[degrees[-1]] += 1
            triangle_distribution[triangle_count(adjacency)] += 1
            degree_sequence_distribution[",".join(map(str, degrees))] += 1
            record_count += 1

    if record_count != EXPECTED_RECORDS:
        raise ValueError(f"record count {record_count} != {EXPECTED_RECORDS}")

    result = {
        "claim": (
            "There are exactly 785888 nonisomorphic non-K4-saturated "
            "Ramsey(4,5,22)-graphs with 112 edges, conditional on the "
            "published completeness of the 113-edge input catalogue"
        ),
        "catalogue": str(args.catalogue),
        "catalogue_sha256": actual_hash,
        "records": record_count,
        "order": ORDER,
        "edges": EDGES,
        "all_records_ramsey_45": True,
        "all_records_non_k4_saturated": True,
        "addable_nonedge_distribution": dict(sorted(addable_distribution.items())),
        "minimum_degree_distribution": dict(
            sorted(minimum_degree_distribution.items())
        ),
        "maximum_degree_distribution": dict(
            sorted(maximum_degree_distribution.items())
        ),
        "triangle_distribution": dict(sorted(triangle_distribution.items())),
        "distinct_degree_sequences": len(degree_sequence_distribution),
        "degree_sequence_distribution": dict(
            sorted(degree_sequence_distribution.items())
        ),
        "elapsed_seconds": time.perf_counter() - started,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "records",
        "addable_nonedge_distribution",
        "minimum_degree_distribution",
        "maximum_degree_distribution",
        "triangle_distribution",
        "distinct_degree_sequences",
        "elapsed_seconds",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
