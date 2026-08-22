#!/usr/bin/env python3
"""Generate the nonsaturated-census manifest from checked run artifacts."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def records(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def file_entry(relative: str) -> dict[str, object]:
    path = ROOT / relative
    return {"file": relative, "records": records(path), "sha256": sha256(path)}


def same_bytes(left: str, right: str) -> bool:
    left_path, right_path = ROOT / left, ROOT / right
    if left_path.stat().st_size != right_path.stat().st_size:
        return False
    with left_path.open("rb") as first, right_path.open("rb") as second:
        while True:
            a, b = first.read(1 << 20), second.read(1 << 20)
            if a != b:
                return False
            if not a:
                return True


def automorphism_counts() -> dict[str, int]:
    result: dict[str, int] = {}
    path = ROOT / "results/nonsaturated_automorphism_counts.txt"
    for line in path.read_text().splitlines():
        group, count = line.split()
        result[group] = int(count)
    return result


def main() -> int:
    validation = json.loads(
        (ROOT / "results/nonsaturated_validation.json").read_text()
    )
    manifest = {
        "claim_scope": "non-K4-saturated Ramsey(4,5,22,112) graphs only",
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "source_catalogues": {
            "e113": file_entry("data/r45extreme/r4522.113.g6"),
            "e114": file_entry("data/r45extreme/r4522.114.g6"),
        },
        "primary_pipeline": {
            "all_deletions": file_entry("data/r4522.112.deletions.all.g6"),
            "valid_deletions": file_entry("data/r4522.112.deletions.valid.g6"),
            "ordinary_nauty_classes": file_entry(
                "data/r4522.112.nonsaturated.g6"
            ),
            "compressed_catalogue": {
                "file": "data/r4522.112.nonsaturated.g6.gz",
                "sha256": sha256(ROOT / "data/r4522.112.nonsaturated.g6.gz"),
            },
        },
        "canonicalization_crosscheck": {
            "traces_classes": file_entry(
                "data/r4522.112.nonsaturated.traces.g6"
            ),
            "ordinary_recanonicalization_of_traces": {
                **file_entry("data/r4522.112.nonsaturated.traces.recanon.g6"),
                "byte_identical_to_primary": same_bytes(
                    "data/r4522.112.nonsaturated.traces.recanon.g6",
                    "data/r4522.112.nonsaturated.g6",
                ),
            },
        },
        "property_validation": validation,
        "structural_statistics": {
            "automorphism_group_order_distribution": automorphism_counts(),
            "triangle_distribution": validation["triangle_distribution"],
        },
        "regression_114_to_113": {
            "all_deletions": file_entry("data/r4522.113.from114.all.g6"),
            "valid_deletions": file_entry("data/r4522.113.from114.valid.g6"),
            "nonisomorphic_children": file_entry(
                "data/r4522.113.from114.unique.g6"
            ),
            "all_children_in_published_113_catalogue": same_bytes(
                "data/r4522.113.published.canonical.g6",
                "data/r4522.113.published_plus_from114.g6",
            ),
            "published_113_nonsaturated": 3296,
            "published_113_saturated": 27680,
        },
        "tools": {
            "nauty_and_traces": "2.9300 (64 bits)",
            "shortg_sha256": sha256(ROOT / "third_party/nauty2_9_3/shortg"),
            "reproduction_script": "scripts/reproduce_nonsaturated.sh",
            "reproduction_script_sha256": sha256(
                ROOT / "scripts/reproduce_nonsaturated.sh"
            ),
            "validator_sha256": sha256(ROOT / "verify_nonsaturated.py"),
        },
    }
    expected = {
        "source113": (30976, "1e1a54b719dcdebb57581ee6f3cd4e1721e828680a72128010f1f888a4dda9db"),
        "source114": (133, "54dffec4ecab0f863b75620ccf8b228e5d6299c799e2d6b284fd51c51aa96ed7"),
        "all": (3500288, "c75e1ff8d9911bc76a505814f3a55f72da97e18f2998de3ae8a6a5a84349ca01"),
        "valid": (887138, "0f35a09c6f6f6d91b5e115144809ab70aecb57a3bddd54e1c8053fff9ca70d28"),
        "final": (785888, "d2c556f52d13dd4d38ed955bedd3db5f52b883faafc45fe5561e611afa5cd6a2"),
    }
    observed = {
        "source113": manifest["source_catalogues"]["e113"],
        "source114": manifest["source_catalogues"]["e114"],
        "all": manifest["primary_pipeline"]["all_deletions"],
        "valid": manifest["primary_pipeline"]["valid_deletions"],
        "final": manifest["primary_pipeline"]["ordinary_nauty_classes"],
    }
    for name, (expected_records, expected_hash) in expected.items():
        item = observed[name]
        if item["records"] != expected_records or item["sha256"] != expected_hash:
            raise ValueError(f"unexpected {name} artifact: {item}")
    destination = ROOT / "results/nonsaturated_manifest.json"
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
