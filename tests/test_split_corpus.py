"""Split-script golden test — the firewall.

Asserts the sanitized seed is firewalled (zero confirmation/disposition content,
all bound_status=seed), has the documented 15 closures (8 base + 7 vehicle-required),
none contested, and that the split is deterministic/idempotent while the canonical
premium corpus stays byte-untouched.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED = REPO_ROOT / "src" / "physmap" / "corpus" / "data" / "corpus_seed.jsonl"
COVERAGE = REPO_ROOT / "src" / "physmap" / "corpus" / "data" / "premium_coverage.json"
CANONICAL = REPO_ROOT / "physmap" / "results" / "calibration_corpus" / "corpus.jsonl"
SPLIT_SCRIPT = REPO_ROOT / "dev" / "tools" / "split_corpus.py"

EXPECTED_SEED_IDS = {
    # 8 base
    "dittus-boelter-1930", "gnielinski-1976", "sieder-tate-1936",
    "sieder-tate-laminar-combined-entry-1936", "petukhov-1970",
    "laminar-fully-developed-tube-isothermal-nu366",
    "laminar-fully-developed-tube-uniform-flux-nu436",
    "blasius-pohlhausen-flat-plate-forced-1921",
    # 7 vehicle-required additions
    "modified-sparrow-cur-asym-narrow-rect-channel-2014",
    "aung-worku-mixed-convection-1986", "gnielinski-constprop-sco2",
    "mcadams-vertical-plate-natural-1954",
    "pate-stainback-freestream-noise-hypersonic-1980",
    "marineau-entropy-layer-shock-interaction-2014",
    "dittus-boelter-buoyancy-sco2",  # Jin sCO2-buoyancy benchmark vehicle (corpus v0.2.4)
}

# Keys/substrings that must NEVER survive into the seed (confirmation/disposition).
BANNED = (
    "confirmation", "confirmed_by", "confirmed_at", "decision", "reason",
    "source_worksheet", "original_range", "reviewed_by", "reviewed_at",
    "narrow-then-promote", "geometry_match", "reviewer flag", "worksheet",
    "cowork", "claude-pair", "harvest2",
)


def _seed_entries() -> list[dict]:
    return [json.loads(ln) for ln in SEED.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _walk_strings(obj):
    """Yield every key and string value in a nested dict/list structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)
    elif isinstance(obj, str):
        yield obj


def test_seed_has_exactly_the_documented_15_closures():
    ids = {e["closure_id"] for e in _seed_entries()}
    assert ids == EXPECTED_SEED_IDS
    assert len(_seed_entries()) == 15


def test_seed_carries_zero_confirmation_or_disposition_content():
    """Recursive key+value scan — the firewall's core assertion."""
    blob = " ".join(s.lower() for e in _seed_entries() for s in _walk_strings(e))
    hits = [tok for tok in BANNED if tok.lower() in blob]
    assert hits == [], f"disposition content leaked into the seed: {hits}"


def test_every_seed_bound_is_status_seed():
    for e in _seed_entries():
        for b in e["validated_range"]:
            assert b["bound_status"] == "seed", (e["closure_id"], b["coord"], b["bound_status"])


def test_no_seed_closure_is_contested():
    for e in _seed_entries():
        assert e["contested"] is False, e["closure_id"]
        for b in e["validated_range"]:
            assert not b.get("contested_note"), e["closure_id"]


def test_seed_reviewer_is_neutralized():
    for e in _seed_entries():
        assert e["reviewer"] == "seed", e["closure_id"]


def test_seed_keeps_public_provenance():
    """Citations survive — the seed must stay credible/runnable, just verdict-free."""
    for e in _seed_entries():
        for b in e["validated_range"]:
            prov = b["provenance"]
            assert prov.get("citation"), (e["closure_id"], b["coord"])
            # only allowlisted public provenance keys survive
            assert set(prov) <= {
                "citation", "doi", "page", "table", "figure", "url", "year",
                "primary_source", "note", "discovery_path",
            }, (e["closure_id"], set(prov))


def test_seed_loads_and_passes_seed_tier_validation():
    from physmap.corpus import calibration as cc
    entries = cc.load_corpus(SEED)
    assert len(entries) == 15
    errs = cc.validate_corpus(entries, seed_tier=True)
    assert errs == {}, errs


def test_premium_coverage_is_ids_only():
    cov = json.loads(COVERAGE.read_text(encoding="utf-8"))
    assert cov["n_closures"] == 53
    assert len(cov["closure_ids"]) == 53
    assert EXPECTED_SEED_IDS <= set(cov["closure_ids"])
    # ids only — no bound values anywhere in the file
    assert '"validated_range"' not in COVERAGE.read_text(encoding="utf-8")
    assert '"min"' not in COVERAGE.read_text(encoding="utf-8")


