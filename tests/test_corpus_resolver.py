"""Loader resolution order + tier detection.

resolve_corpus_path(): $PHYSMAP_CORPUS → premium-if-present → bundled seed.
active_tier(): content-based seed/premium detection.
"""
from __future__ import annotations

import json
from pathlib import Path

import physmap.corpus.calibration as cc

SEED = Path(cc.__file__).resolve().parent / "data" / "corpus_seed.jsonl"


def test_env_override_takes_precedence(tmp_path, monkeypatch):
    fake = tmp_path / "mycorpus.jsonl"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("PHYSMAP_CORPUS", str(fake))
    assert cc.resolve_corpus_path() == fake


def test_a_public_checkout_resolves_to_the_seed(monkeypatch):
    """This repository does not carry the closed corpus, so resolution falls to the seed."""
    monkeypatch.delenv("PHYSMAP_CORPUS", raising=False)
    p = cc.resolve_corpus_path()
    assert p == SEED
    assert cc.active_tier(p) == "seed"


def test_seed_fallback_when_premium_absent(monkeypatch):
    """With no env override and no premium present, resolution falls to the seed."""
    monkeypatch.delenv("PHYSMAP_CORPUS", raising=False)
    monkeypatch.setattr(cc, "DEFAULT_PATH", Path("/nonexistent/premium/corpus.jsonl"))
    monkeypatch.setattr(cc, "_premium_package_path", lambda: None)
    p = cc.resolve_corpus_path()
    assert p.name == "corpus_seed.jsonl"
    assert cc.active_tier(p) == "seed"


def test_active_tier_is_content_based(tmp_path):
    assert cc.active_tier(SEED) == "seed"             # all bounds collapsed to "seed"
    # A corpus whose bounds carry a real status is the closed tier, whatever its name.
    curated = tmp_path / "seed_named.jsonl"
    curated.write_text(json.dumps({"validated_range": [{"bound_status": "claimed"}]}) + "\n",
                       encoding="utf-8")
    assert cc.active_tier(curated) == "premium"


def test_load_corpus_defaults_to_resolver(monkeypatch):
    monkeypatch.setenv("PHYSMAP_CORPUS", str(SEED))
    entries = cc.load_corpus()
    assert len(entries) == 15
