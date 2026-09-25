"""Tests for the Dirker/Meyer/Reid (2018) water tube — the Stage-3 MIDDLE-axis
vehicle and the Ri machinery it required (detectors.extract_features Ri support,
the gnielinski richardson_number corpus ceiling, vehicle_spec richardson_bands
validity wiring, and the Path-A dirker_water_richardson_bands loader).

These pin the middle-axis structural contract: Ri is the failure variable,
OMITTED from the surrogate inputs but checked by the corpus, so the score lands
strictly in (0,1) and the surrogate is accurate at low Ri / wrong at high Ri.
"""

from __future__ import annotations

import numpy as np
import pytest

from physmap.pipeline.detectors import extract_features
from physmap.pipeline.validity_signal import ValidityRangeDistanceDetector
from physmap.pipeline.vehicle_spec import vehicle_spec
from physmap.pipeline.observability import vehicle_observability
from physmap.substrate.engine import build_substrate
from physmap.substrate.vehicle_config import load_named_vehicle
import physmap.substrate.loaders  # noqa: F401  (register loaders)


# ── extract_features: Ri / log10_Ri ─────────────────────────────────────────

def test_extract_features_ri():
    assert extract_features({"Ri": 5.0}, ("Ri",))[0] == 5.0
    np.testing.assert_allclose(
        extract_features({"Ri": 5.0}, ("log10_Ri",))[0], np.log10(5.0))


def test_extract_features_ri_missing_is_hard_keyerror():
    # Like x_over_D: a richardson vehicle MUST carry Ri (no silent default).
    with pytest.raises(KeyError):
        extract_features({"Re": 1000.0, "Pr": 6.5}, ("Ri",))


@pytest.mark.parametrize("bad_ri", [0.0, -1.0])
def test_extract_features_log10_ri_requires_positive(bad_ri):
    with pytest.raises(ValueError):
        extract_features({"Ri": bad_ri}, ("log10_Ri",))


# ── corpus richardson_number ceiling on gnielinski ──────────────────────────

def test_validity_detector_fires_high_ri_quiet_mid_ri():
    # The Ri bound lives on aung-worku-mixed-convection-1986 (Ri in [0.1, 10]),
    # NOT on the shared gnielinski (the entrance-region/NACA closure).
    det = ValidityRangeDistanceDetector("aung-worku-mixed-convection-1986", ("Ri",))
    fires = det.signal(np.array([[50.0]]))   # Ri=50 > 10 -> buoyancy-dominated, outside
    quiet = det.signal(np.array([[5.0]]))    # Ri=5 in [0.1, 10] -> mixed band, inside
    assert fires[0] > 0.0
    assert quiet[0] == 0.0


def test_richardson_bound_isolated_from_gnielinski():
    # The shared gnielinski (NACA's entrance-region closure) must NOT carry a
    # richardson bound — it lives only on the mixed-convection anchor. This keeps
    # NACA's guardrail/validity unpolluted (no spurious Ri-column requirement).
    gniel = ValidityRangeDistanceDetector("gnielinski-1976", ("log10_Re", "Pr"))
    assert "richardson_number" not in gniel.valid_ranges
    # And aung-worku's Ri bound is inert when Ri is not an extracted feature:
    aung = ValidityRangeDistanceDetector("aung-worku-mixed-convection-1986", ("log10_Re", "Pr"))
    assert aung.signal(np.array([[np.log10(1500.0), 6.5]]))[0] == 0.0


# ── vehicle_spec: dirker_water is a middle ──────────────────────────────────

def test_dirker_water_spec_is_middle():
    cfg = load_named_vehicle("dirker_water")
    assert cfg.cell_bands.type == "richardson_bands"
    spec = vehicle_spec(cfg)
    assert spec.failure_var == "Ri"
    # Ri OMITTED from surrogate inputs (the middle mechanism)...
    assert spec.baseline_feature_names == ("log10_Re", "Pr")
    assert "Ri" not in spec.baseline_feature_names
    # ...but Ri-ONLY for the corpus (Re excluded: gnielinski Re range is turbulent).
    assert spec.validity_feature_names == ("Ri",)
    # split at RI_CEIL=20
    assert spec.split.train_predicate({"Ri": 12.0}) is True
    assert spec.split.test_predicate({"Ri": 50.0}) is True


# ── loader: Path-A rows ─────────────────────────────────────────────────────

def test_dirker_water_loader_rows():
    rows, _ref, meta = build_substrate(load_named_vehicle("dirker_water"))
    assert len(rows) == 91
    for r in rows:
        assert "Ri" in r.meta and r.meta["Ri"] > 0
        assert isinstance(r.surrogate_prediction, float)
        assert r.truth_source == "experimental"
    # Path-A surrogate: accurate at low Ri, measurably wrong at high Ri for the
    # extreme (lower-heating) config.
    def err(r):
        return abs(r.surrogate_prediction - r.cfd_truth) / r.cfd_truth * 100.0
    low_ri = [r for r in rows if r.meta["Ri"] < 20.0]
    assert np.median([err(r) for r in low_ri]) < 10.0          # Gate 1: accurate
    hi_2b = [r for r in rows
             if r.meta.get("case") == "2B" and r.meta["Ri"] >= 50.0]
    assert max(err(r) for r in hi_2b) > 13.0                   # Gate 2: wrong


# ── observability: strictly middle, non-degenerate ──────────────────────────

def test_dirker_water_observability_is_middle_nondegenerate():
    obs = vehicle_observability("dirker_water")
    assert obs.degenerate_on_axis is False
    assert 0.0 < obs.score < 1.0
    assert obs.n_region > 0
