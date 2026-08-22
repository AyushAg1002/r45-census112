#!/usr/bin/env python3
"""Build deterministic public-release archives."""

from __future__ import annotations

import gzip
import hashlib
import io
import shutil
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "release" / "public"
PREFIX = "r45-census-1.0.0"

COMMON_FILES = [
    "README.md",
    "LOW_DEGREE.md",
    "GLUING_ROUTE.md",
    "Makefile",
    "requirements-sat.txt",
    "LICENSE",
    ".gitignore",
    "CITATION.cff",
    "verify_low_degree.py",
    "verify_nonsaturated.py",
]
COMMON_DIRS = ["src", "scripts", "tests", "results", "notes"]
EXCLUDED_PATHS = {"notes/DRAFT_NOTE.md", "results/reproduction.log"}
DATA_FILES = [
    "data/r4522.112.saturated.cnf",
    "data/r4522.112.saturated.witness.g6",
    "data/r4522.112.saturated.witness.canonical.g6",
    "data/r4522.112.saturated.witness.traces.g6",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def selected_files() -> list[Path]:
    files = [ROOT / name for name in COMMON_FILES + DATA_FILES]
    files.append(ROOT / "paper" / "main.tex")
    files.append(ROOT / "paper" / "README.md")
    for directory in COMMON_DIRS:
        files.extend(
            path
            for path in (ROOT / directory).rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.relative_to(ROOT).as_posix() not in EXCLUDED_PATHS
        )
    unique = sorted(set(files), key=lambda path: path.relative_to(ROOT).as_posix())
    missing = [path for path in unique if not path.exists()]
    if missing:
        raise FileNotFoundError("missing release files: " + ", ".join(map(str, missing)))
    return unique


def tar_info(name: str, data: bytes, executable: bool = False) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mode = 0o755 if executable else 0o644
    return info


def write_deterministic_tar_gz(
    destination: Path, entries: list[tuple[str, bytes, bool]]
) -> None:
    uncompressed = io.BytesIO()
    with tarfile.open(fileobj=uncompressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, data, executable in sorted(entries):
            archive.addfile(tar_info(name, data, executable), io.BytesIO(data))
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as zipped:
            zipped.write(uncompressed.getvalue())


def source_entries(files: list[Path]) -> list[tuple[str, bytes, bool]]:
    entries: list[tuple[str, bytes, bool]] = []
    manifest_lines: list[str] = []
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        manifest_lines.append(f"{sha256_bytes(data)}  {relative}")
        executable = data.startswith(b"#!")
        entries.append((f"{PREFIX}/{relative}", data, executable))
    status = (
        "PUBLIC RELEASE 1.0.0\n"
        "Approved by Ayush Agarwal on August 22, 2026.\n"
        "Code: MIT; manuscript/docs: CC BY 4.0; data/manifests: CC0 1.0.\n"
    ).encode()
    entries.append((f"{PREFIX}/RELEASE_STATUS.txt", status, False))
    entries.append(
        (
            f"{PREFIX}/MANIFEST.sha256",
            ("\n".join(manifest_lines) + "\n").encode(),
            False,
        )
    )
    return entries


def arxiv_entries(files: list[Path]) -> list[tuple[str, bytes, bool]]:
    entries: list[tuple[str, bytes, bool]] = [
        ("main.tex", (ROOT / "paper" / "main.tex").read_bytes(), False),
        (
            "anc/README.txt",
            (
                "Ancillary files for the public preprint release.\n"
                "Repository: https://github.com/AyushAg1002/r45-census112\n"
                "The versioned Zenodo DOI is recorded in main.tex.\n"
                "Third-party Ramsey catalogues are not redistributed; use scripts/fetch_inputs.sh.\n"
            ).encode(),
            False,
        ),
    ]
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if relative == "paper/main.tex" or relative.startswith("publication/"):
            continue
        if relative == "data/r4522.112.saturated.cnf":
            continue
        data = path.read_bytes()
        executable = data.startswith(b"#!")
        entries.append((f"anc/{relative}", data, executable))
    return entries


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = selected_files()
    source_archive = OUTPUT / f"{PREFIX}-source-and-manifests.tar.gz"
    arxiv_archive = OUTPUT / f"{PREFIX}-arxiv-source.tar.gz"
    write_deterministic_tar_gz(source_archive, source_entries(files))
    write_deterministic_tar_gz(arxiv_archive, arxiv_entries(files))

    pdf = OUTPUT / f"{PREFIX}.pdf"
    catalogue = OUTPUT / "r4522.112.nonsaturated.g6.gz"
    shutil.copyfile(ROOT / "output" / "pdf" / "main.pdf", pdf)
    shutil.copyfile(ROOT / "data" / "r4522.112.nonsaturated.g6.gz", catalogue)

    assets = [arxiv_archive, source_archive, pdf, catalogue]
    sums = "".join(f"{sha256_file(path)}  {path.name}\n" for path in sorted(assets))
    (OUTPUT / "SHA256SUMS").write_text(sums)
    print(sums, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
