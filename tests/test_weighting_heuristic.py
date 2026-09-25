"""Config-time observability weighting heuristic — verification.

Anchors the spec's cases (docs/specs/PhysMAP_Ensemble_ConfigTime_Observability_Heuristic_Spec_v0_1.md)
to the real corpus + vehicles:
  • OBSERVABLE   (Forrest, Re in inputs)            → weight baseline; corpus ≈ 0
  • UNOBSERVABLE (NACA, x/D structural-binary)      → weight corpus
  • PARTIAL uncalibrated (dirker, Ri)               → DEFER (UNCERTAIN); no invented weight
  • PARTIAL calibrated   (Velázquez, μ_w/μ_b 0.575) → GRADED, traced to calibrated_by
plus the load-bearing invariants flagged in review: weight POLARITY, the POLE_BAND
judgment constant, single-source agreement with classify_observability, regime-specific
calibration, and the discipline guard (no degree computed at config/assessment time).
"""

from __future__ import annotations

import ast

import pytest

from physmap.guardrail import corpus_regimes as cr
from physmap.guardrail import weighting_heuristic as wh
from physmap.guardrail.aggregator_observability import ObservabilityWeightedAggregator
from physmap.guardrail.classify import classify_observability, load_default_corpus_index
from physmap.guardrail.enums import Disposition, Observability, Regime, Verdict
from physmap.pipeline.core import DetectorResult
from physmap.pipeline.validity_signal import PerBoundMargin

PV = Regime.INTERNAL_FORCED_CONVECTION_PROPERTY_VARIATION
SCO2 = "gnielinski-constprop-sco2"
MU = "viscosity_ratio_wall_bulk"


@pytest.fixture(scope="module")
def ci():
    return load_default_corpus_index()


def _decision(coord_coord):
    return {d.coord: d for d in coord_coord}


# ── config-time table: the four spec anchors ─────────────────────────────────

def test_observable_pole_forrest(ci):
    table = {d.coord: d for d in wh.config_time_weights(
        ["Re", "Pr"], Regime.INTERNAL_FORCED_CONVECTION_RECT_CHANNEL, ci)}
    for coord in ("reynolds_number", "prandtl_number"):
        d = table[coord]
        assert d.observability is Observability.OBSERVABLE
        assert d.weight_target == wh.WEIGHT_BASELINE
        assert (d.w_baseline, d.w_corpus) == (1.0, 0.0)  # corpus ≈ 0


def test_unobservable_pole_naca(ci):
    table = {d.coord: d for d in wh.config_time_weights(
        ["Re", "Pr"], Regime.ENTRANCE_REGION_PIPE, ci)}
    d = table["x_over_D"]
    assert d.observability is Observability.UNOBSERVABLE
    assert d.weight_target == wh.WEIGHT_CORPUS
    assert (d.w_baseline, d.w_corpus) == (0.0, 1.0)


def test_partial_uncalibrated_dirker_defers(ci):
    table = {d.coord: d for d in wh.config_time_weights(
        ["Re", "Pr"], Regime.MIXED_CONVECTION_HORIZONTAL_TUBE, ci)}
    d = table["richardson_number"]
    assert d.observability is Observability.PARTIAL
    assert d.weight_target == wh.WEIGHT_DEFER
    assert d.degree_status == "uncalibrated"
    assert d.w_baseline is None and d.w_corpus is None  # NO invented weight
    assert d.partial_degree is None and d.calibrated_by == ()


def test_partial_calibrated_velazquez_graded(ci):
    """The calibrated middle: classified PARTIAL, then graded from the banked degree,
    weight traceable to calibrated_by (not runtime derivation)."""
    table = {d.coord: d for d in wh.config_time_weights(["Re", "Pr"], PV, ci)}
    d = table[MU]
    assert d.observability is Observability.PARTIAL        # classified PARTIAL before grading
    assert d.weight_target == wh.WEIGHT_GRADED
    assert d.degree_status == "calibrated"
    assert d.partial_degree == pytest.approx(0.575)
    assert (d.w_baseline, d.w_corpus) == pytest.approx((0.575, 0.425))
    assert d.calibrated_by == ("velazquez_sco2",)          # provenance


# ── weight polarity (the silent-inversion risk) ──────────────────────────────

def test_graded_weights_polarity_and_endpoints():
    # degree 0 = baseline blind → all corpus; degree 1 = baseline sees it → all baseline.
    assert wh.graded_weights(0.0) == (0.0, 1.0)
    assert wh.graded_weights(1.0) == (1.0, 0.0)
    # monotone: higher observability ⇒ more baseline weight, less corpus weight.
    wb_lo, wc_lo = wh.graded_weights(0.2)
    wb_hi, wc_hi = wh.graded_weights(0.8)
    assert wb_hi > wb_lo and wc_hi < wc_lo
    # the banked Velázquez degree leans baseline (it is > 0.5).
    wb, wc = wh.graded_weights(0.575)
    assert wb > wc


def test_graded_weights_clamped():
    assert wh.graded_weights(-1.0) == (0.0, 1.0)
    assert wh.graded_weights(2.0) == (1.0, 0.0)


def test_pole_band_is_a_documented_judgment_constant():
    # Not a fitted number — just assert it exists, is in (0, 0.5), and drives the bands.
    assert 0.0 < wh.POLE_BAND < 0.5
    assert wh.graded_lean(wh.POLE_BAND / 2) == wh.LEAN_CORPUS_TRUST
    assert wh.graded_lean(1.0 - wh.POLE_BAND / 2) == wh.LEAN_BASELINE_TRUST
    assert wh.graded_lean(0.5) == wh.LEAN_SOFT_FLAG


# ── single source of truth + regime-specificity ──────────────────────────────

def test_config_time_weights_observability_matches_classifier(ci):
    """The heuristic's class column must equal the canonical classifier everywhere —
    the weight rule may not silently re-derive observability differently."""
    for regime, inputs in [
        (Regime.ENTRANCE_REGION_PIPE, ["Re", "Pr"]),
        (Regime.INTERNAL_FORCED_CONVECTION_RECT_CHANNEL, ["Re", "Pr"]),
        (Regime.MIXED_CONVECTION_HORIZONTAL_TUBE, ["Re", "Pr"]),
        (PV, ["Re", "Pr"]),
    ]:
        table = {d.coord: d.observability for d in wh.config_time_weights(inputs, regime, ci)}
        assert table == classify_observability(inputs, regime, ci), regime


def test_observable_when_axis_is_an_input(ci):
    """If the surrogate DOES consume μ_w/μ_b, the same bound flips to OBSERVABLE."""
    table = {d.coord: d for d in wh.config_time_weights(["Re", "Pr", "ratio_mu_w_b"], PV, ci)}
    assert table[MU].observability is Observability.OBSERVABLE
    assert table[MU].weight_target == wh.WEIGHT_BASELINE


def test_calibration_is_regime_specific():
    """A degree calibrated for the property-variation regime must not weight a
    deployment in a different regime — it falls back to the honest uncalibrated defer."""
    here = wh.resolve_partial(SCO2, MU, regime_value=PV.value)
    assert here.weight_target == wh.WEIGHT_GRADED
    elsewhere = wh.resolve_partial(SCO2, MU, regime_value="some_other_regime")
    assert elsewhere.weight_target == wh.WEIGHT_DEFER
    assert elsewhere.degree_status == "uncalibrated" and elsewhere.calibrated_by == ()


def test_velazquez_calibration_is_wired_with_provenance():
    """Guard the banked Layer-2c cell: real degree, stamped provenance, no laundering."""
    degree_map, status, calby = cr.partial_degree_for(SCO2, MU)
    assert status == "calibrated"
    assert degree_map == {PV.value: 0.575}
    assert calby == ["velazquez_sco2"]


# ── structural_lean hook (spec-optional; empty today → defer) ─────────────────

def test_structural_lean_absent_defers():
    assert wh.structural_lean_for(SCO2, "reynolds_number") is None


def test_structural_lean_when_present_is_labeled_not_weighted(monkeypatch):
    """A future qualitative lean routes to LEAN (labeled), never a numeric weight."""
    monkeypatch.setitem(wh.STRUCTURAL_LEAN_OVERRIDES,
                        ("aung-worku-mixed-convection-1986", "richardson_number"), "corpus_lean")
    d = wh.resolve_partial("aung-worku-mixed-convection-1986", "richardson_number",
                           regime_value=Regime.MIXED_CONVECTION_HORIZONTAL_TUBE.value)
    assert d.weight_target == wh.WEIGHT_LEAN
    assert d.structural_lean == "corpus_lean"
    assert d.w_baseline is None and d.w_corpus is None  # a lean is not a measured weight


# ── runtime aggregator: the graded PARTIAL branch end-to-end ──────────────────

def _corpus_fired(margin=0.5):
    return {"closure_validity": DetectorResult(
        "closure_validity", margin, True, None, "test point past validated bound")}


def _bound(coord=MU):
    return PerBoundMargin(coord=coord, feature_name="ratio_mu_w_b",
                          margin=0.5, bound_status="claimed", side="above")


def _combine(observability, *, degree_regime=PV, closure_id=SCO2, severities=None):
    agg = ObservabilityWeightedAggregator()
    return agg.combine(
        decision_signals=_corpus_fired(),
        observability=observability,
        fired_bound=_bound(),
        severities=severities or {"closure_validity": None},
        fired_closure_id=closure_id,
        regime=degree_regime,
    )


def test_aggregator_partial_calibrated_midrange_is_soft_flag():
    """Velázquez 0.575 is mid-axis → a calibrated WARN soft-flag, NOT the blind defer
    and NOT a hard reject."""
    out = _combine({MU: Observability.PARTIAL})
    assert out.verdict is Verdict.WARN
    assert out.rule == "partial-graded-softflag"
    assert out.disposition is Disposition.CHARACTERIZE_REGION


def test_aggregator_partial_uncalibrated_still_defers():
    """dirker's Ri (uncalibrated) keeps the honest UNCERTAIN — byte-for-byte the old
    behavior; graduation only happens where a degree is banked."""
    agg = ObservabilityWeightedAggregator()
    out = agg.combine(
        decision_signals=_corpus_fired(),
        observability={"richardson_number": Observability.PARTIAL},
        fired_bound=_bound("richardson_number"),
        severities={"closure_validity": None},
        fired_closure_id="aung-worku-mixed-convection-1986",
        regime=Regime.MIXED_CONVECTION_HORIZONTAL_TUBE,
    )
    assert out.verdict is Verdict.UNCERTAIN
    assert out.rule == "partial-defer"


def test_aggregator_graded_corpus_trust_near_unobservable_pole(monkeypatch):
    """A calibrated degree near 0 → trust the corpus fire (REJECT), like the
    unobservable pole."""
    monkeypatch.setitem(cr.PARTIAL_DEGREE_CALIBRATIONS, (SCO2, MU),
                        {"partial_degree": {PV.value: 0.05}, "calibrated_by": ["synthetic_test"]})
    out = _combine({MU: Observability.PARTIAL})
    assert out.verdict is Verdict.REJECT
    assert out.rule == "partial-graded-corpus-trust"


def test_aggregator_graded_baseline_trust_near_observable_pole(monkeypatch):
    """A calibrated degree near 1 → corpus redundant; defer to baselines. With only the
    corpus fired, the baselines are quiet → TRUSTWORTHY (do-no-harm)."""
    monkeypatch.setitem(cr.PARTIAL_DEGREE_CALIBRATIONS, (SCO2, MU),
                        {"partial_degree": {PV.value: 0.95}, "calibrated_by": ["synthetic_test"]})
    out = _combine({MU: Observability.PARTIAL})
    assert out.verdict is Verdict.TRUSTWORTHY
    assert out.rule == "baseline-verdict"


def test_aggregator_unobservable_and_observable_poles_unchanged():
    """Pole behavior is untouched by the new branch."""
    rej = _combine({MU: Observability.UNOBSERVABLE})
    assert rej.verdict is Verdict.REJECT and rej.rule == "unobservable-corpus-trusted"
    obs = _combine({MU: Observability.OBSERVABLE})
    assert obs.verdict is Verdict.TRUSTWORTHY and obs.rule == "baseline-verdict"


def test_combine_backward_compatible_without_new_kwargs():
    """Old call sites (no fired_closure_id/regime) keep working: a PARTIAL bound with
    no closure_id can't read Layer-2c, so it defers."""
    agg = ObservabilityWeightedAggregator()
    out = agg.combine(
        decision_signals=_corpus_fired(),
        observability={MU: Observability.PARTIAL},
        fired_bound=_bound(),
        severities={"closure_validity": None},
    )
    assert out.verdict is Verdict.UNCERTAIN and out.rule == "partial-defer"


# ── discipline: no observability degree is computed at config/assessment time ──

def test_no_degree_estimator_in_heuristic_or_aggregator():
    """Import-level guard (AST, so docstring prose can't trip it): neither the heuristic
    nor the aggregator may import the retrospective cv_r2_knn estimator module, nor
    reference its functions as identifiers anywhere. The graded weight is READ from a
    calibrated Layer-2c degree only — never computed at config/assessment time."""
    import physmap.guardrail.aggregator_observability as agg_mod
    forbidden_names = {"observability_score", "vehicle_observability"}
    for mod in (wh, agg_mod):
        tree = ast.parse(open(mod.__file__, encoding="utf-8").read())
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
            # no use of the estimator functions as identifiers / attributes either
            if isinstance(node, ast.Name):
                assert node.id not in forbidden_names, mod.__file__
            if isinstance(node, ast.Attribute):
                assert node.attr not in forbidden_names, mod.__file__
        assert "physmap.pipeline.observability" not in imported_modules, mod.__file__
