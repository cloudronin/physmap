"""Tests for the observability score (D1).

Pins the two poles (NACA orthogonal ~0; Forrest degenerate ≡ 1), the
estimator-validity checks (cross-estimator pole agreement; subsampling
stability flagging), clipping, the small-n fallback, and estimator
swappability. The pole assertions are the D1 analogue of the locked NACA
verdict in test_phase1_gate.py — if they move, the axis endpoints moved.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from physmap.pipeline.observability import (
    ESTIMATORS,
    cross_estimator_agreement,
    observability_score,
    subsampling_stability,
    vehicle_observability,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
NACA_CSV = REPO_ROOT / "data" / "naca" / "wpd_fig10.csv"
FORREST_CSV = REPO_ROOT / "data" / "forrest" / "visual_estimates_fig5.csv"


# ── synthetic Row helper ─────────────────────────────────────────────────────

class _Row:
    """Minimal stand-in for substrate Row — observability only reads `.meta`."""
    def __init__(self, meta: dict):
        self.meta = meta


def _recoverable_region(n: int, seed: int = 0) -> list[_Row]:
    """Region where the failure var Ri == log10(Re) exactly (recoverable from
    the log10_Re input) → R^2 ≈ 1. Pr is held EXACTLY constant (like NACA's
    0.71): the z-score guard zeroes a constant column, so the k-NN distance is
    purely log10_Re and neighbours are clean."""
    re = np.geomspace(2000.0, 20000.0, n)
    return [_Row({"Re": float(r), "Pr": 0.71, "Ri": float(np.log10(r))}) for r in re]


# ── pole pins ────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not FORREST_CSV.exists(), reason="Forrest CSV missing")
def test_forrest_observability_is_one_degenerate():
    """Forrest: Re is a surrogate input (log10_Re) → observability ≡ 1 by
    definition, via the degenerate short-circuit (no fitting)."""
    res = vehicle_observability("forrest")
    assert res.degenerate_on_axis is True
    assert res.score == 1.0
    assert res.raw_statistic is None


@pytest.mark.skipif(not NACA_CSV.exists(), reason="NACA CSV missing")
def test_naca_observability_low():
    """NACA: x/D is the failure axis, NOT a surrogate input, and is orthogonal
    to (Re, Pr) by the experiment design → score ≈ 0 (well under 0.2)."""
    res = vehicle_observability("naca_tn1451")
    assert res.degenerate_on_axis is False
    assert res.score < 0.2
    assert res.n_region > 0


@pytest.mark.skipif(not (NACA_CSV.exists() and FORREST_CSV.exists()),
                    reason="pole CSVs missing")
def test_cross_estimator_agreement_at_poles():
    """All three estimators agree on pole placement: NACA all low, Forrest all
    exactly 1. Agreement is what licenses locking cv_r2_knn as the default."""
    naca = cross_estimator_agreement("naca_tn1451")
    forr = cross_estimator_agreement("forrest")
    assert naca["agree"] is True
    assert all(s < 0.3 for s in naca["scores"].values())
    assert forr["agree"] is True
    assert all(s == 1.0 for s in forr["scores"].values())


# ── estimator-validity mechanics ─────────────────────────────────────────────

def test_subsampling_stability_stable_on_large_recoverable_region():
    """A well-sampled recoverable region scores ~1 on every subsample →
    near-zero std → stable=True at the default tolerance. This is the physics-
    observable, well-sampled case a middle vehicle must reach to be trusted."""
    rows = _recoverable_region(40, seed=1)
    stab = subsampling_stability(rows, "Ri", ("log10_Re", "Pr"), n_boot=80)
    assert stab.stable is True
    assert stab.std < 0.15
    assert stab.mean > 0.7


def test_subsampling_stability_flag_responds_to_tolerance():
    """A small region is genuinely sampling-sensitive (std > 0) — exactly the
    'provisional until better sampled' case the gate exists for. The stable
    flag is std <= tolerance; verify it flips around the observed std. (Calls
    are deterministic given the seed, so std is identical across them.)"""
    rows = _recoverable_region(16, seed=2)
    stab = subsampling_stability(rows, "Ri", ("log10_Re", "Pr"), n_boot=120)
    assert stab.std > 0.0
    tight = subsampling_stability(rows, "Ri", ("log10_Re", "Pr"),
                                  n_boot=120, tolerance=stab.std * 0.5)
    loose = subsampling_stability(rows, "Ri", ("log10_Re", "Pr"),
                                  n_boot=120, tolerance=stab.std * 2.0 + 1e-9)
    assert tight.stable is False
    assert loose.stable is True


# ── core-score properties ────────────────────────────────────────────────────

def test_score_clipped_to_unit_interval():
    """Orthogonal region (Ri pure noise vs inputs) → negative raw R^2 clipped
    to exactly 0; score never leaves [0, 1]."""
    rng = np.random.default_rng(3)
    rows = [_Row({"Re": float(r), "Pr": 0.71, "Ri": float(rng.uniform())})
            for r in np.geomspace(2000, 20000, 20)]
    res = observability_score(rows, "Ri", ("log10_Re", "Pr"))
    assert 0.0 <= res.score <= 1.0
    assert res.score == 0.0
    assert res.raw_statistic is not None and res.raw_statistic <= 0.0 + 1e-9


def test_small_n_uses_in_sample_fallback():
    """n < 5 takes the in-sample fallback (no CV) and still returns a clipped
    score without crashing."""
    rows = _recoverable_region(4, seed=4)
    res = observability_score(rows, "Ri", ("log10_Re", "Pr"))
    assert "small_n" in res.notes
    assert 0.0 <= res.score <= 1.0


def test_estimator_strategy_swappable():
    """Every estimator runs on the same region and returns a [0,1] score; on a
    recoverable region each reports high observability."""
    rows = _recoverable_region(16, seed=5)
    for name in ESTIMATORS:
        res = observability_score(rows, "Ri", ("log10_Re", "Pr"), estimator=name)
        assert 0.0 <= res.score <= 1.0, name
        assert res.score > 0.5, f"{name} should see the recoverable region"


def test_degenerate_short_circuits_for_all_estimators():
    """When the failure var is itself an input, every estimator returns 1.0 via
    the degenerate branch (no fitting)."""
    rows = _recoverable_region(10, seed=6)
    for name in ESTIMATORS:
        res = observability_score(rows, "Re", ("log10_Re", "Pr"), estimator=name)
        assert res.degenerate_on_axis is True
        assert res.score == 1.0


def test_empty_region_is_nan_not_crash():
    res = observability_score([], "Ri", ("log10_Re", "Pr"))
    assert np.isnan(res.score)
    assert res.n_region == 0
