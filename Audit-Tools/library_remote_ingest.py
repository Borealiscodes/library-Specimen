#!/usr/bin/env python3
"""
Audit-Tools/library_remote_ingest.py
Zero-clone GitHub Trees API scanner for `Borealiscodes/library-Specimen`.
Fetches the complete recursive tree in one lightweight JSON request (< 200 KB),
avoiding heavy .mp3 and .pdf downloads while auditing multi-format stem parity,
INDEX.md coverage, and conceptual Graph Laplacian incidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any

OWNER = "Borealiscodes"
REPO = "library-Specimen"
BRANCH = "main"

TEXT_EXTENSIONS = frozenset({".txt", ".tex", ".md", ".html", ".vtt"})
BINARY_EXTENSIONS = frozenset({".pdf", ".mp3", ".png", ".jpg", ".jpeg"})

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


def github_get_json(url: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "NDH-Zero-Clone-Library-Audit/1.0",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_raw_text(rel_path: str) -> str:
    url = f"https://githubusercontent.com{OWNER}/{REPO}/{BRANCH}/{rel_path}"
    req = urllib.request.Request(url, headers={"User-Agent": "NDH-Zero-Clone-Library-Audit/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def build_remote_manifest() -> dict[str, Any]:
    tree_url = f"https://github.com{OWNER}/{REPO}/git/trees/{BRANCH}?recursive=1"
    tree_data = github_get_json(tree_url)
    entries = tree_data.get("tree", [])

    index_text = fetch_raw_text("INDEX.md").lower() if any(e["path"] == "INDEX.md" for e in entries) else ""

    stem_formats: dict[str, list[str]] = defaultdict(list)
    text_docs: list[dict[str, Any]] = []
    incidence_matrix: list[list[int]] = []
    skipped_binary_bytes = 0

    for item in sorted(entries, key=lambda x: x["path"].lower()):
        if item.get("type") != "blob":
            continue
        rel_path = item["path"]
        if rel_path.startswith("Audit-Tools/"):
            continue

        p = Path(rel_path)
        ext = p.suffix.lower()
        stem = p.with_suffix("").as_posix()
        size_bytes = int(item.get("size", 0))

        if ext in TEXT_EXTENSIONS or ext in BINARY_EXTENSIONS:
            stem_formats[stem].append(ext)

        if ext in BINARY_EXTENSIONS:
            skipped_binary_bytes += size_bytes
            continue

        if ext not in TEXT_EXTENSIONS or p.name in {"README.md", "INDEX.md", "CONTRIBUTING.md", "THIRD-PARTY-NOTICES.md"}:
            continue

        searchable = rel_path.lower()
        row = [1 if tok in searchable else 0 for tok in CONCEPT_TOKENS]
        incidence_matrix.append(row)

        text_docs.append({
            "path": rel_path,
            "stem": stem,
            "ext": ext,
            "git_blob_sha": item["sha"],
            "size_bytes": size_bytes,
            "indexed_in_index_md": (p.name.lower() in index_text) or (p.stem.lower() in index_text),
            "matched_concepts": [tok for tok, bit in zip(CONCEPT_TOKENS, row) if bit == 1],
        })

    unindexed_count = sum(1 for d in text_docs if not d["indexed_in_index_md"])
    orphan_binaries = sorted(
        stem for stem, exts in stem_formats.items()
        if any(e in BINARY_EXTENSIONS for e in exts) and not any(e in {".txt", ".tex", ".md"} for e in exts)
    )

    total_docs = len(text_docs)
    index_coverage = Fraction(total_docs - unindexed_count, max(total_docs, 1))

    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "mode": "zero_clone_git_trees_api",
        "target_surface": f"{OWNER}/{REPO}",
        "tree_sha": tree_data.get("sha"),
        "truncated": bool(tree_data.get("truncated", False)),
        "skipped_binary_bytes": skipped_binary_bytes,
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
    out_path = Path(__file__).resolve().parent / "library_snapshot_manifest.json"
    manifest = build_remote_manifest()
    out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    saved_mb = round(manifest["skipped_binary_bytes"] / (1024 * 1024), 2)
    print(f"Zero-clone scan complete for {manifest['target_surface']} (tree {manifest['tree_sha'][:12]})")
    print(f"Binary blobs skipped    : {saved_mb} MB (.mp3 / .pdf / .png)")
    print(f"Text manuscripts audited: {manifest['total_text_manuscripts']}")
    print(f"INDEX.md coverage (p/q) : {manifest['index_coverage_pq']}")
    print(f"Orphan binary stems     : {len(manifest['orphan_binary_stems'])}")
    print(f"Manifest SHA-256        : {manifest['manifest_sha256']}")


if __name__ == "__main__":
    main()
