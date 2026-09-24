#!/usr/bin/env python3
"""Audit a built wheel or sdist: what must be inside, and what must never be.

Run locally the same way CI and the release workflow run it:

    python -m build
    python dev/tools/audit_wheel.py dist/physmap-*.whl
    python dev/tools/audit_wheel.py dist/physmap-*.tar.gz

Both go to PyPI, so both are audited against the same firewall. The sdist additionally
must not carry the repository's top-level `data/` or `results/` trees -- the benchmark and
Lewis data are checkout-only by design.

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
import tarfile
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

#: The same, as laid out in an sdist (`physmap-<version>/...`).
REQUIRED_SDIST = (
    "*/src/physmap/closures/data/closure_index.json",
    "*/src/physmap/corpus/data/corpus_seed.jsonl",
    "*/src/physmap/corpus/data/evidence_claims_seed.jsonl",
    "*/src/physmap/corpus/data/evidence_sources_seed.jsonl",
    "*/LICENSE",
    "*/LICENSE-CORPUS",
    "*/NOTICE",
)

#: Top-level directories of the repository that must never reach an sdist.
FORBIDDEN_SDIST_TOPLEVEL = ("data", "results")

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
    ap.add_argument("wheel", type=Path, help="a built .whl or .tar.gz sdist")
    a = ap.parse_args()

    sdist = a.wheel.name.endswith(".tar.gz")
    index_raw = None
    if sdist:
        with tarfile.open(a.wheel) as t:
            names = [m.name for m in t.getmembers() if m.isfile()]
            for n in names:
                if n.endswith("closures/data/closure_index.json"):
                    index_raw = t.extractfile(n).read()
    else:
        with zipfile.ZipFile(a.wheel) as z:
            names = z.namelist()
            for n in names:
                if n.endswith("closures/data/closure_index.json"):
                    index_raw = z.read(n)

    problems: list[str] = []

    for pattern in (REQUIRED_SDIST if sdist else REQUIRED):
        if not any(fnmatch.fnmatch(n, pattern) for n in names):
            problems.append(f"MISSING: {pattern}")

    for pattern in FORBIDDEN:
        hits = [n for n in names if fnmatch.fnmatch(n, pattern)]
        problems.extend(f"MUST NOT SHIP: {h}  (matched {pattern})" for h in hits)

    if sdist:
        # Checked by path segment, not by glob: fnmatch's `*` crosses `/`, so a pattern like
        # `physmap-*/data/*` would also catch the package's own src/physmap/corpus/data/.
        for n in names:
            parts = n.split("/")
            if len(parts) > 2 and parts[1] in FORBIDDEN_SDIST_TOPLEVEL:
                problems.append(f"MUST NOT SHIP: {n}  (the repository's top-level "
                                f"{parts[1]}/ is checkout-only)")

    if index_raw is None:
        problems.append("MISSING: the closure index is not in the wheel at all")
    else:
        n = len(json.loads(index_raw)["closures"])
        if n != EXPECTED_INDEX_SIZE:
            problems.append(
                f"closure index has {n} entries, expected {EXPECTED_INDEX_SIZE}. "
                f"An index that fails to load comes back EMPTY rather than raising."
            )

    kind = "sdist" if sdist else "wheel"
    print(f"{kind}: {a.wheel.name}  ({len(names)} entries)")
    if problems:
        print("\nFAILED:")
        for p in problems:
            print(f"  {p}")
        return 1
    required = REQUIRED_SDIST if sdist else REQUIRED
    print(f"clean: all {len(required)} required entries present, "
          f"no forbidden entries, closure index = {EXPECTED_INDEX_SIZE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
