#!/usr/bin/env python3
"""Attach hashes and byte-comparison results to the independent-run manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_SOURCE_SHA256 = (
    "1e1a54b719dcdebb57581ee6f3cd4e1721e828680a72128010f1f888a4dda9db"
)
EXPECTED_VALID_SHA256 = (
    "0f35a09c6f6f6d91b5e115144809ab70aecb57a3bddd54e1c8053fff9ca70d28"
)
EXPECTED_CANONICAL_SHA256 = (
    "d2c556f52d13dd4d38ed955bedd3db5f52b883faafc45fe5561e611afa5cd6a2"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def records(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def byte_identical(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as left_handle, right.open("rb") as right_handle:
        while True:
            left_block = left_handle.read(1 << 20)
            right_block = right_handle.read(1 << 20)
            if left_block != right_block:
                return False
            if not left_block:
                return True


def checked_hash(path: Path, expected: str) -> str:
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: {actual} != {expected}")
    return actual


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--valid", type=Path, required=True)
    parser.add_argument("--primary-valid", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--reference-canonical", type=Path, required=True)
    parser.add_argument("--canonicalizer", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    source_hash = checked_hash(args.source, EXPECTED_SOURCE_SHA256)
    valid_hash = checked_hash(args.valid, EXPECTED_VALID_SHA256)
    canonical_hash = checked_hash(args.canonical, EXPECTED_CANONICAL_SHA256)
    valid_matches = byte_identical(args.valid, args.primary_valid)
    canonical_matches = byte_identical(
        args.canonical, args.reference_canonical
    )
    if not valid_matches or not canonical_matches:
        raise ValueError("independent output differs from the primary pipeline")

    manifest["source_sha256"] = source_hash
    manifest["independent_valid_output"] = {
        "file": str(args.valid),
        "records": records(args.valid),
        "sha256": valid_hash,
    }
    manifest["comparison_to_primary_valid_stream"] = {
        "file": str(args.primary_valid),
        "sha256": sha256(args.primary_valid),
        "byte_identical": valid_matches,
    }
    manifest["canonicalization"] = {
        "separate_from_generation_and_filter": True,
        "tool": "nauty 2.9.3 shortg",
        "executable": str(args.canonicalizer),
        "executable_sha256": sha256(args.canonicalizer),
        "output": str(args.canonical),
        "records": records(args.canonical),
        "sha256": canonical_hash,
        "reference": str(args.reference_canonical),
        "reference_sha256": sha256(args.reference_canonical),
        "byte_identical_to_reference": canonical_matches,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
