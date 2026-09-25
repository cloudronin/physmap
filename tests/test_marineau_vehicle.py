"""Marineau hypersonic-transition standard-vehicle wiring (aerospace NEGATIVE CONTROL).

Guards that the YAML + loader + vehicle_spec + entropy-layer/shock corpus bound
reproduce the G4 baseline-VISIBLE result: a citable validity bound exists and the
corpus fires on the large-bluntness deploy, but nose radius IS a surrogate input
so the deploy is EXTERIOR in (Re/m, Rn) -> the steelman baseline ALSO fires ->
no clean lift (PhysMAP correctly declines). The original G4 baseline-invisibility
script (verdict FAIL_baseline_visible_via_Rn) is research code that was not
published; this test pins the same result.
"""
from __future__ import annotations

import numpy as np

from physmap.guardrail.classify import classify_observability, load_default_corpus_index
from physmap.guardrail.enums import Observability, Regime
from physmap.pipeline.vehicle_spec import vehicle_spec
from physmap.substrate.engine import build_substrate
from physmap.substrate.vehicle_config import load_named_vehicle

VID = "marineau_hypersonic_transition"
INPUTS = ["Re_per_m", "Rn_mm"]


def _load():
    cfg = load_named_vehicle(VID)
    rows, _ref, _meta = build_substrate(cfg)   # also exercises the geometry-match invariant
    spec = vehicle_spec(cfg)
    train = [r for r in rows if spec.split.train_predicate(r.meta)]
    test = [r for r in rows if spec.split.test_predicate(r.meta)]
    return cfg, rows, spec, train, test


def test_marineau_loads_and_splits():
    _cfg, _rows, spec, train, test = _load()
    assert spec.failure_var == "st_xsw_ratio"
    assert spec.baseline_feature_names == tuple(INPUTS)
    assert spec.validity_feature_names == (*INPUTS, "st_xsw_ratio")
    # Marineau Table 3: 9 benign (S_T/X_SW >= 0.1) + 6 deploy (< 0.1).
    assert len(train) == 9, f"expected 9 benign train, got {len(train)}"
    assert len(test) == 6, f"expected 6 deploy, got {len(test)}"


def test_marineau_st_xsw_is_observable():
    # S_T/X_SW is recoverable from nose radius (a surrogate input) -> OBSERVABLE
    # (baseline-visible). This is what makes Marineau a negative control, not a win.
    obs = classify_observability(INPUTS, Regime.HYPERSONIC_TRANSITION_ENTROPY,
                                 load_default_corpus_index())
    assert obs.get("entropy_layer_shock_ratio") is Observability.OBSERVABLE


def test_marineau_negative_control_conditions():
    _cfg, _rows, spec, train, test = _load()
    rn_benign = np.array([r.meta["Rn_mm"] for r in train])
    rn_deploy = np.array([r.meta["Rn_mm"] for r in test])
    # (1) deploy is genuinely EXTERIOR in nose radius -> the steelman baseline
    # FIRES on the deploy (the negative control is earned by the data).
    assert rn_deploy.min() > rn_benign.max(), (
        f"deploy not exterior in Rn (deploy min {rn_deploy.min()} <= benign max {rn_benign.max()})"
    )
    # (2) the corpus entropy-layer/shock bound ALSO fires on every deploy point
    # (a citable bound exists) -> corpus fires AND baseline fires -> no clean lift.
    assert all(r.meta["st_xsw_ratio"] < 0.1 for r in test)
