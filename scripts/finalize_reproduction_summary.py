#!/usr/bin/env python3
"""Hash the frozen code and result set after a complete reproduction run."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def entries(paths: list[Path]) -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted(paths)
        if path.is_file() and "__pycache__" not in path.parts
    }


def main() -> int:
    code_paths = [ROOT / "Makefile", ROOT / "verify_low_degree.py", ROOT / "verify_nonsaturated.py"]
    for directory in ("src", "scripts", "tests"):
        code_paths.extend((ROOT / directory).rglob("*"))
    result_paths = [
        path
        for path in (ROOT / "results").glob("*")
        if path.name not in {"reproduction.log", "reproduction_summary.json"}
    ]
    artifact_paths = [
        ROOT / "data/r4522.112.nonsaturated.g6",
        ROOT / "data/r4522.112.nonsaturated.g6.gz",
        ROOT / "data/r4522.112.saturated.cnf",
        ROOT / "data/r4522.112.saturated.witness.canonical.g6",
    ]
    try:
        import pysat

        pysat_version: str | None = str(pysat.__version__)
    except ImportError:
        pysat_version = None
    summary = {
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "pysat": pysat_version,
        },
        "code_sha256": entries(code_paths),
        "result_sha256": entries(result_paths),
        "principal_artifact_sha256": entries(artifact_paths),
        "claims": {
            "nonsaturated_classes": 785888,
            "full_layer_minimum_degree_lower_bound": 7,
            "saturated_witness_valid": True,
            "full_saturated_census_complete": False,
        },
        "external_trusted_boundary": (
            "completeness of the published Ramsey input catalogues"
        ),
    }
    destination = ROOT / "results/reproduction_summary.json"
    destination.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
