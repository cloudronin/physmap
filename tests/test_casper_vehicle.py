"""Casper hypersonic-transition standard-vehicle wiring (aerospace PHYSMAP_WINS).

Guards that the YAML + loader + vehicle_spec + freestream-noise corpus bound
reproduce the G6 v0.2 differentiator STRUCTURE: on the QUIET deploy the corpus
fires, the noisy-trained surrogate is measurably wrong, and the deploy is
INTERIOR in the surrogate inputs (so the steelman baseline is silent) -> the
clean-lift conditions hold. The original G6 differentiator script (CORPUS_LIFT 8/8)
is research code that was not published; this test pins the same structure.
"""
from __future__ import annotations

import numpy as np

from physmap.guardrail.classify import classify_observability, load_default_corpus_index
from physmap.guardrail.enums import Observability, Regime
from physmap.pipeline.vehicle_spec import vehicle_spec
from physmap.substrate.engine import build_substrate
from physmap.substrate.vehicle_config import load_named_vehicle

VID = "casper_hypersonic_transition"
INPUTS = ["M", "Re_per_m_e6", "x_m"]


def _load():
    cfg = load_named_vehicle(VID)
    rows, _ref, _meta = build_substrate(cfg)   # also exercises the geometry-match invariant
    spec = vehicle_spec(cfg)
    train = [r for r in rows if spec.split.train_predicate(r.meta)]
    test = [r for r in rows if spec.split.test_predicate(r.meta)]
    return cfg, rows, spec, train, test


def test_casper_loads_and_splits():
    _cfg, _rows, spec, train, test = _load()
    assert spec.failure_var == "freestream_noise_pct"
    assert spec.baseline_feature_names == tuple(INPUTS)
    assert spec.validity_feature_names == (*INPUTS, "freestream_noise_pct")
    # G6 v0.2 selection: 159 noisy train + 8 quiet deploy (single Re, M=6.0).
    assert len(train) == 159, f"expected 159 noisy train, got {len(train)}"
    assert len(test) == 8, f"expected 8 quiet deploy, got {len(test)}"


def test_casper_freestream_is_unobservable():
    obs = classify_observability(INPUTS, Regime.HYPERSONIC_TRANSITION_DISTURBANCE,
                                 load_default_corpus_index())
    assert obs.get("freestream_noise_rms_pitot_pct") is Observability.UNOBSERVABLE


def test_casper_clean_lift_conditions_on_quiet_deploy():
    _cfg, _rows, spec, train, test = _load()
    Xtr = np.array([[r.meta[k] for k in INPUTS] for r in train])
    Xte = np.array([[r.meta[k] for k in INPUTS] for r in test])
    # (1) quiet deploy is genuinely INTERIOR in the surrogate inputs (the v0.2
    # Mach-confound fix) -> the steelman baseline is silent, NOT arranged.
    zmax = float(np.max(np.abs((Xte - Xtr.mean(0)) / Xtr.std(0))))
    assert zmax < 3.0, f"quiet deploy is not interior (max|z|={zmax:.2f})"
    # (2) the corpus freestream-noise bound fires on EVERY quiet deploy point.
    assert all(r.meta["freestream_noise_pct"] < 0.5 for r in test)
    # (3) the noisy-trained surrogate is measurably wrong on the quiet deploy.
    rel = np.array([abs(r.surrogate_prediction - r.cfd_truth) / abs(r.cfd_truth) for r in test])
    assert (rel > 0.10).all(), f"surrogate not wrong on all quiet pts (rel={rel.round(2)})"
