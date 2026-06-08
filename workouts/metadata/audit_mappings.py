#!/usr/bin/env python3
"""Validate exercise→muscle mappings in workouts/data.py against muscle_taxonomy.

Run from homelab-api root:
    python3 workouts/metadata/audit_mappings.py

Exits 0 when clean; exits 1 and prints issues otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DATA_PY = Path(__file__).resolve().parents[1] / "data.py"


def _extract_block(content: str, marker: str, end: str = 'ON CONFLICT') -> str:
    start = content.index(marker)
    chunk = content[start:]
    end_idx = chunk.index(end)
    return chunk[:end_idx]


def _parse_meta(section: str) -> dict[tuple[str, str], str]:
    rows = re.findall(
        r"\('([^']+)','([^']*)',\s*'([^']+)',\s*'([^']+)'\)", section
    )
    return {(n, v): vt for n, v, _, vt in rows}


def _parse_taxonomy(section: str) -> set[str]:
    return set(re.findall(r"\('([^']+)'", section))


def _parse_mappings(section: str) -> list[tuple[str, str, str, float]]:
    return [
        (n, v, p, float(c))
        for n, v, p, c in re.findall(
            r"\('([^']+)','([^']*)',\s*'([^']+)',\s*([0-9.]+)\)", section
        )
    ]


def main() -> int:
    content = DATA_PY.read_text()

    tax_paths = _parse_taxonomy(
        _extract_block(content, "INSERT INTO muscle_taxonomy(path")
    )
    meta = _parse_meta(_extract_block(content, "INSERT INTO exercise_meta"))
    mappings = _parse_mappings(
        re.search(r'TAXONOMY_MAPPING_SQL = """(.*?)"""', content, re.DOTALL).group(1)
    )

    mapped_pairs = {(n, v) for n, v, _, _ in mappings}
    errors: list[str] = []
    warnings: list[str] = []

    for n, v, p, c in mappings:
        if p not in tax_paths:
            errors.append(f"invalid taxonomy path: {n!r}/{v!r} → {p!r}")
        if c <= 0 or c > 1.0:
            warnings.append(f"unusual contribution {c}: {n!r}/{v!r} → {p!r}")

    for (n, v), vt in sorted(meta.items()):
        if (n, v) in mapped_pairs:
            continue
        base = (n, "")
        if vt == "minor" and base in mapped_pairs:
            continue
        if vt == "minor":
            warnings.append(f"minor variation without base mapping: {n!r}/{v!r}")
        else:
            errors.append(f"major exercise without mapping: {n!r}/{v!r}")

    # depth-3 muscle-level check for major exercises with own mappings
    for (n, v), vt in meta.items():
        if vt != "major" or (n, v) not in mapped_pairs:
            continue
        depth3 = [p for nn, vv, p, _ in mappings if nn == n and vv == v
                  if len(p.split(".")) == 3]
        if not depth3:
            warnings.append(f"major mapping lacks depth-3 muscle rows: {n!r}/{v!r}")

    print(f"taxonomy nodes: {len(tax_paths)}")
    print(f"exercise meta:  {len(meta)}")
    print(f"mapping rows:   {len(mappings)}")
    print(f"mapped pairs:   {len(mapped_pairs)}")

    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  WARN: {w}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  ERR:  {e}")
        return 1

    print("\nAudit passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
