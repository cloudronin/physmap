#!/usr/bin/env python3
"""Firewall the evidence corpus down to the open seed. Deterministic, idempotent.

The calibration corpus already ships as a 15-closure seed while the 53-closure
premium corpus stays private. The evidence corpus -- the claims and sources that
justify each validity bound -- needs the SAME firewall, or it leaks bounds for
closures the seed deliberately withholds.

The rule is an ALLOWLIST, not a blacklist: a claim ships only if its closure_id
appears in the seed corpus. Judgement calls about whether a particular premium
claim "really" reveals anything are exactly how an allowlist rots, so none are
made here. A source ships only if a surviving claim cites it.

Usage:
    python dev/tools/split_evidence_corpus.py --premium-dir PATH [--check]

--check re-derives the seed and exits non-zero if the committed files differ.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SEED_CORPUS = REPO / "src" / "physmap" / "corpus" / "data" / "corpus_seed.jsonl"
OUT_DIR = REPO / "src" / "physmap" / "corpus" / "data"
OUT_CLAIMS = OUT_DIR / "evidence_claims_seed.jsonl"
OUT_SOURCES = OUT_DIR / "evidence_sources_seed.jsonl"


def _read_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text("utf-8").splitlines() if line.strip()]


def _write_jsonl(p: Path, rows: list[dict]) -> None:
    p.write_text("".join(json.dumps(r, ensure_ascii=True, sort_keys=True) + "\n" for r in rows), "utf-8")


def split(premium_dir: Path) -> tuple[list[dict], list[dict], dict]:
    seed_ids = {e["closure_id"] for e in _read_jsonl(SEED_CORPUS) if e.get("closure_id")}
    claims = _read_jsonl(premium_dir / "claims.jsonl")
    sources = _read_jsonl(premium_dir / "sources.jsonl")

    kept_claims = sorted(
        (c for c in claims if c.get("closure_id") in seed_ids),
        key=lambda c: c["claim_id"],
    )
    cited = {c["source_id"] for c in kept_claims if c.get("source_id")}
    kept_sources = sorted((s for s in sources if s["source_id"] in cited), key=lambda s: s["source_id"])

    dropped_closures = sorted({c["closure_id"] for c in claims} - seed_ids)
    report = {
        "seed_closures": len(seed_ids),
        "claims_in": len(claims), "claims_out": len(kept_claims),
        "sources_in": len(sources), "sources_out": len(kept_sources),
        "dropped_closures": dropped_closures,
    }
    return kept_claims, kept_sources, report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--premium-dir", type=Path, required=True,
                    help="directory holding the premium claims.jsonl and sources.jsonl")
    ap.add_argument("--check", action="store_true",
                    help="verify the committed seed matches a fresh split; do not write")
    a = ap.parse_args()

    claims, sources, report = split(a.premium_dir)
    for k, v in report.items():
        print(f"  {k}: {v}")

    if a.check:
        ok = True
        for path, rows in ((OUT_CLAIMS, claims), (OUT_SOURCES, sources)):
            fresh = "".join(json.dumps(r, ensure_ascii=True, sort_keys=True) + "\n" for r in rows)
            if not path.exists() or path.read_text("utf-8") != fresh:
                print(f"DRIFT: {path.name} differs from a fresh split", file=sys.stderr)
                ok = False
        print("check:", "clean" if ok else "DRIFT")
        return 0 if ok else 1

    _write_jsonl(OUT_CLAIMS, claims)
    _write_jsonl(OUT_SOURCES, sources)
    print(f"wrote {OUT_CLAIMS.name} and {OUT_SOURCES.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
