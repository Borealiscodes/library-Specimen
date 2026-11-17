#!/usr/bin/env python3
"""
Audit-Tools/library_ingest.py
Stage 1 & 2: Zero-dependency corpus scanner, multi-format stem parity auditor,
SHA-256 manifest builder, and conceptual incidence matrix extractor for `library-Specimen`.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any

TEXT_EXTENSIONS = frozenset({".txt", ".tex", ".md", ".html", ".vtt"})
BINARY_EXTENSIONS = frozenset({".pdf", ".mp3", ".png", ".jpg", ".jpeg"})
SKIP_DIRS = frozenset({".git", "Audit-Tools", "__pycache__", "fonts"})

CONCEPT_TOKENS = (
    "rsvp",
    "constraint",
    "closure",
    "persistence",
    "witness",
    "non-injective",
    "projection",
    "active-inference",
    "thermodynamic",
    "reachability",
    "spectral",
    "universality",
    "entropy",
    "phaneroscopy",
    "clypeus",
    "agency",
    "computation",
    "foraging",
    "cladistics",
    "swarm",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_library_corpus(repo_root: Path) -> dict[str, Any]:
    stem_formats: dict[str, list[str]] = defaultdict(list)
    text_docs: list[dict[str, Any]] = []
    incidence_matrix: list[list[int]] = []

    index_path = repo_root / "INDEX.md"
    index_text = index_path.read_text(encoding="utf-8", errors="ignore").lower() if index_path.exists() else ""

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for fname in sorted(files):
            fpath = Path(root) / fname
            rel_path = fpath.relative_to(repo_root).as_posix()
            ext = fpath.suffix.lower()
            stem = fpath.with_suffix("").relative_to(repo_root).as_posix()

            if ext in TEXT_EXTENSIONS or ext in BINARY_EXTENSIONS:
                stem_formats[stem].append(ext)

            if ext not in TEXT_EXTENSIONS or fname in {"README.md", "INDEX.md", "CONTRIBUTING.md", "THIRD-PARTY-NOTICES.md"}:
                continue

            raw_text = fpath.read_text(encoding="utf-8", errors="ignore")
            searchable = f"{rel_path} {raw_text[:25000]}".lower()
            row = [1 if tok in searchable else 0 for tok in CONCEPT_TOKENS]
            incidence_matrix.append(row)

            text_docs.append({
                "path": rel_path,
                "stem": stem,
                "ext": ext,
                "sha256": sha256_file(fpath),
                "indexed_in_index_md": (fname.lower() in index_text) or (Path(stem).name.lower() in index_text),
                "matched_concepts": [tok for tok, bit in zip(CONCEPT_TOKENS, row) if bit == 1],
            })

    # Audit multi-format parity (e.g., .tex/.txt source vs compiled .pdf or .mp3 audio)
    unindexed_count = sum(1 for d in text_docs if not d["indexed_in_index_md"])
    orphan_binaries = sorted(
        stem for stem, exts in stem_formats.items()
        if any(e in BINARY_EXTENSIONS for e in exts) and not any(e in {".txt", ".tex", ".md"} for e in exts)
    )

    total_docs = len(text_docs)
    index_coverage = Fraction(total_docs - unindexed_count, max(total_docs, 1))

    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "target_surface": "Borealiscodes/library-Specimen",
        "total_text_manuscripts": total_docs,
        "unindexed_manuscripts": unindexed_count,
        "index_coverage_pq": f"{index_coverage.numerator}/{index_coverage.denominator}",
        "orphan_binary_stems": orphan_binaries,
        "concept_tokens": list(CONCEPT_TOKENS),
        "incidence_matrix": incidence_matrix,
        "manuscripts": text_docs,
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return manifest


def main() -> None:
    audit_dir = Path(__file__).resolve().parent
    repo_root = audit_dir.parent
    out_path = audit_dir / "library_snapshot_manifest.json"

    manifest = scan_library_corpus(repo_root)
    out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Audited {manifest['total_text_manuscripts']} text manuscripts in library-Specimen")
    print(f"INDEX.md coverage (p/q) : {manifest['index_coverage_pq']}")
    print(f"Orphan binary stems     : {len(manifest['orphan_binary_stems'])}")
    print(f"Manifest SHA-256        : {manifest['manifest_sha256']}")


if __name__ == "__main__":
    main()
