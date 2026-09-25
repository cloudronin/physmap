"""Registry/bounds resolution semantics — cases 1, 2a, 2b, 3.

Exercised under the SEED tier (via PHYSMAP_CORPUS) so premium-only closures are
genuinely absent from the active corpus. Direct closure_id= naming must work for
the case-2b/3 closures (the higher-fidelity demand signal).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import physmap.corpus.calibration as cc
from physmap import CredibilityGuardrail, Regime
from physmap.closures.index import (
    ClosureResolutionError,
    ResolutionCase,
    classify_closure,
    issue_url,
    match_closure,
)

SEED = Path(cc.__file__).resolve().parent / "data" / "corpus_seed.jsonl"


@pytest.fixture()
def seed_tier(monkeypatch):
    """Force the active corpus to the bundled seed for the duration of a test."""
    monkeypatch.setenv("PHYSMAP_CORPUS", str(SEED))
    assert cc.active_tier() == "seed"


def _guard(**kw):
    return CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], **kw)


# ── case 1: bounds in the active corpus → normal operation ────────────────────
def test_case1_regime_resolves_in_seed(seed_tier):
    g = _guard(regime=Regime.ENTRANCE_REGION_PIPE)   # gnielinski-1976 is in the seed
    assert g._resolution is None
    assert g.resolved_closures == ["gnielinski-1976"]


def test_case1_direct_name_active(seed_tier):
    g = _guard(regime=Regime.UNLISTED, closure_id="gnielinski-1976")
    assert g._resolution is None


# ── case 2a: bounds in premium but not the active (seed) corpus ───────────────
def test_case2a_direct_premium_only(seed_tier):
    g = _guard(regime=Regime.UNLISTED, closure_id="rohsenow-pool-boiling-1952")
    name, case, _ = g._resolution
    assert case is ResolutionCase.PREMIUM_ONLY
    with pytest.raises(ClosureResolutionError) as ei:
        g.fit(np.zeros((4, 2)))
    assert "premium corpus" in str(ei.value)
    assert ei.value.case is ResolutionCase.PREMIUM_ONLY


# ── case 2b: registered in the index, no bounds curated in any tier ───────────
def test_case2b_direct_registered_no_bounds(seed_tier):
    g = _guard(regime=Regime.UNLISTED, closure_id="churchill-mixed-convection-flat-plate")
    name, case, _ = g._resolution
    assert case is ResolutionCase.NO_BOUNDS
    with pytest.raises(ClosureResolutionError) as ei:
        g.fit(np.zeros((4, 2)))
    msg = str(ei.value)
    assert "not yet curated" in msg
    assert "github.com/cloudronin/physmap/issues/new" in msg  # pre-filled issue URL


# ── case 3: nothing registered for the requested name ─────────────────────────
def test_case3_direct_unregistered(seed_tier):
    g = _guard(regime=Regime.UNLISTED, closure_id="totally-made-up-closure-2099")
    name, case, _ = g._resolution
    assert case is ResolutionCase.UNREGISTERED
    with pytest.raises(ClosureResolutionError) as ei:
        g.fit(np.zeros((4, 2)))
    msg = str(ei.value)
    assert "no closure registered" in msg
    assert "issues/new" in msg


# ── direct free-text naming + issue-URL construction ──────────────────────────
def test_free_text_matches_alias():
    assert match_closure("SST") == "menter-sst-1994"
    assert match_closure("Dittus-Boelter") == "dittus-boelter-1930"
    assert match_closure("nope nope nope") is None


def test_issue_url_is_prefilled_and_inert():
    url = issue_url("foo-bar-1999", {"regime": "ENTRANCE_REGION_PIPE"})
    assert url.startswith("https://github.com/cloudronin/physmap/issues/new?")
    assert "title=closure-request" in url
    assert "foo-bar-1999" in url


def test_classify_closure_partitions(seed_tier):
    active_ids = {e.closure_id for e in cc.load_corpus()}  # seed ids
    assert classify_closure("gnielinski-1976", active_ids) is ResolutionCase.ACTIVE
    assert classify_closure("rohsenow-pool-boiling-1952", active_ids) is ResolutionCase.PREMIUM_ONLY
    assert classify_closure("churchill-mixed-convection-flat-plate", active_ids) is ResolutionCase.NO_BOUNDS
    assert classify_closure("does-not-exist", active_ids) is ResolutionCase.UNREGISTERED


# ── existing statistical-only behaviour preserved ─────────────────────────────
def test_unlisted_regime_stays_statistical_only(seed_tier):
    g = _guard(regime=Regime.UNLISTED)
    assert g._resolution is None     # no raise — statistical-only, unchanged
    assert g.mode == "statistical_only"
