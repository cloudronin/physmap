#!/usr/bin/env python3
"""Audit a built wheel: what must be inside, and what must never be.

Run locally the same way CI runs it:

    python -m pip wheel --no-deps -w dist .
    python dev/tools/audit_wheel.py dist/physmap-*.whl

The package-data checks are not ceremony. Under the src/ layout the data globs
resolve only because pyproject sets `where = ["src"]`; lose that line and the JSON
silently vanishes from the wheel, the closure index loads as EMPTY, nothing raises,
and every registered closure starts reporting as unregistered.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
import zipfile
from pathlib import Path

EXPECTED_INDEX_SIZE = 201

#: Must be present, or the wheel is broken.
REQUIRED = (
    "physmap/closures/data/closure_index.json",
    "physmap/corpus/data/corpus_seed.jsonl",
    "physmap/corpus/data/evidence_claims_seed.jsonl",
    "physmap/corpus/data/evidence_sources_seed.jsonl",
    "*.dist-info/licenses/LICENSE",
    "*.dist-info/licenses/LICENSE-CORPUS",
    "*.dist-info/licenses/NOTICE",
)

#: Must be absent. The premium corpus is the moat; the PDFs are in copyright; the
#: benchmark data is checkout-only by design.
FORBIDDEN = (
    "*.pdf",
    "*/results/calibration_corpus/*",
    "*corpus_premium*",
    "*/corpus.jsonl",
    "*expected_metrics.json",
    "*/data/naca/*",
    "*/data/benchmarks/*",
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("wheel", type=Path)
    a = ap.parse_args()

    with zipfile.ZipFile(a.wheel) as z:
        names = z.namelist()
        index_raw = None
        for n in names:
            if n.endswith("closures/data/closure_index.json"):
                index_raw = z.read(n)

    problems: list[str] = []

    for pattern in REQUIRED:
        if not any(fnmatch.fnmatch(n, pattern) for n in names):
            problems.append(f"MISSING: {pattern}")

    for pattern in FORBIDDEN:
        hits = [n for n in names if fnmatch.fnmatch(n, pattern)]
        problems.extend(f"MUST NOT SHIP: {h}  (matched {pattern})" for h in hits)

    if index_raw is None:
        problems.append("MISSING: the closure index is not in the wheel at all")
    else:
        n = len(json.loads(index_raw)["closures"])
        if n != EXPECTED_INDEX_SIZE:
            problems.append(
                f"closure index has {n} entries, expected {EXPECTED_INDEX_SIZE}. "
                f"An index that fails to load comes back EMPTY rather than raising."
            )

    print(f"wheel: {a.wheel.name}  ({len(names)} entries)")
    if problems:
        print("\nFAILED:")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"clean: all {len(REQUIRED)} required entries present, "
          f"no forbidden entries, closure index = {EXPECTED_INDEX_SIZE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
