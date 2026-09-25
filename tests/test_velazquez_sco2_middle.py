"""Tests for the Velazquez sCO2 property-variation MIDDLE vehicle.

Data is EXACT from the paper's SI Appendix D (Velazquez et al. 2026, ATE
285:129206; NOT figure-digitized); fluid properties precomputed via CoolProp
(validated vs the paper's REFPROP) and banked in
`velazquez_sco2_local_alpha_with_properties.csv`. The failure driver is the
wall/bulk viscosity ratio mu_w/mu_b — OMITTED from the constant-property (Re, Pr)
surrogate — which blows up near the pseudo-critical point. Buoyancy is isolated
by pressure (>= 15 MPa, where the paper's Fig. 11 shows it negligible).

These pin: the YAML loads + spec resolves to the property-variation middle; the
substrate builds with a buoyancy-clean near-pseudo-critical failure region where
the constant-property closure is massively wrong; and the observability score is
a genuine, stability-confirmed MIDDLE (distinct from the NACA~0 / Forrest~1 poles).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from physmap.pipeline.observability import vehicle_observability
from physmap.pipeline.vehicle_spec import vehicle_spec
from physmap.substrate.engine import build_substrate
from physmap.substrate.vehicle_config import load_named_vehicle


REPO_ROOT = Path(__file__).resolve().parents[1]
PROPS_CSV = (REPO_ROOT / "data" / "velazquez_sco2"
             / "velazquez_sco2_local_alpha_with_properties.csv")


def test_yaml_loads_and_spec_is_property_variation_middle():
    cfg = load_named_vehicle("velazquez_sco2")
    assert cfg.vehicle_id == "velazquez_sco2"
    assert cfg.cell_bands.type == "property_variation_bands"
    # regime-specific constant-property closure (carries the property bound; NOT the
    # shared gnielinski-1976, per the dirker lesson)
    assert cfg.matched_closure_id == "gnielinski-constprop-sco2"
    spec = vehicle_spec(cfg)
    assert spec.failure_var == "ratio_mu_w_b"
    # The property driver is OMITTED from the surrogate (baseline) inputs — the middle
    # mechanism — but the corpus DOES see it via validity_feature_names (the wiring that
    # lets the corpus fire where a (Re,Pr) baseline stays quiet).
    assert spec.baseline_feature_names == ("log10_Re", "Pr")
    assert "ratio_mu_w_b" not in spec.baseline_feature_names
    assert "ratio_mu_w_b" in spec.validity_feature_names
    # Failure region = near pseudo-critical AND buoyancy-clean (p >= 15 MPa);
    # train = far from pseudo-critical, same pressure subset.
    assert spec.split.test_predicate({"p_MPa": 20.0, "abs_dT_pc": 3.0}) is True
    assert spec.split.train_predicate({"p_MPa": 20.0, "abs_dT_pc": 30.0}) is True
    # 10 MPa is buoyancy-confounded -> excluded from BOTH train and test.
    assert spec.split.test_predicate({"p_MPa": 10.0, "abs_dT_pc": 3.0}) is False
    assert spec.split.train_predicate({"p_MPa": 10.0, "abs_dT_pc": 30.0}) is False


@pytest.mark.skipif(not PROPS_CSV.exists(), reason="velazquez properties CSV missing")
def test_substrate_builds_and_failure_region_is_clean_near_pc():
    cfg = load_named_vehicle("velazquez_sco2")
    rows, _reference, _meta = build_substrate(cfg)
    assert len(rows) == 560                          # 28 tests x 20 thermocouple stations
    spec = vehicle_spec(cfg)
    fr = [r for r in rows if spec.split.test_predicate(r.meta)]
    assert len(fr) > 20
    # Every failure-region point is buoyancy-clean (>= 15 MPa) and near pseudo-critical.
    assert all(r.meta["p_MPa"] >= 15.0 and r.meta["abs_dT_pc"] < 10.0 for r in fr)
    # The constant-property Gnielinski surrogate is MASSIVELY wrong there
    # (the surrogate failure exists — Phase-D2 "measurably wrong").
    mape = 100.0 * np.mean(
        [abs(r.surrogate_prediction - r.meta["Nu_meas"]) / r.meta["Nu_meas"] for r in fr]
    )
    assert mape > 100.0


@pytest.mark.skipif(not PROPS_CSV.exists(), reason="velazquez properties CSV missing")
def test_observability_is_a_stability_confirmed_middle():
    res = vehicle_observability("velazquez_sco2", check_stability=True)
    # Genuine MIDDLE: not a pole, and the driver is genuinely omitted (not an input).
    assert res.degenerate_on_axis is False
    assert 0.35 < res.score < 0.80
    # Stability-confirmed (subsampling std < 0.15 tolerance) -> not provisional.
    # NB near-threshold pass (canonical run: std ~0.139); a regression past 0.15
    # would flip this and is worth catching.
    assert res.stability is not None
    assert res.provisional is False
