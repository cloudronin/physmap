"""Controls for the causal-materiality path.

Every test here exercises shipped code, not a mock. Several assert a REFUSAL, because
the refusals are the load-bearing part: a method that cannot decline is a method that
always answers, and a method that always answers cannot be trusted when it does.
"""

from __future__ import annotations

import pytest

from physmap.core.mechanism import CalibrationWindow, Mechanism
from physmap.core.signals import Signal, SignalKind
from physmap.materiality.estimator import (
    AblationInputs,
    AblationProvenance,
    MaterialityStatus,
    estimate_materiality,
    materiality_signal,
)
from physmap.materiality.independence import (
    CircularTruthError,
    TruthIndependence,
    may_report_performance,
    require_independent_truth,
)
from physmap.release import EvidenceState

SYNTH = EvidenceState.SYNTHETIC_FIXTURE
THETA = 0.20


def _mech(value: float, lo: float = 0.0, hi: float = 1.0) -> Mechanism:
    return Mechanism(
        mechanism_id="m1", name="test mechanism",
        window=CalibrationWindow("v", lo, hi), operating_value=value,
    )


def _inputs(full=100.0, ablated=60.0, prov=AblationProvenance.MATCHED_ABLATION):
    return AblationInputs(qoi_full=full, qoi_ablated=ablated, provenance=prov)


# ── the counterfactual itself ────────────────────────────────────────────────

def test_materiality_is_the_ablation_fraction():
    r = estimate_materiality(_mech(0.5), "q", _inputs(100.0, 60.0), evidence_state=SYNTH)
    assert r.status is MaterialityStatus.ESTIMATED
    assert r.value == pytest.approx(0.40)


def test_both_inputs_are_persisted_so_the_division_can_be_redone():
    r = estimate_materiality(_mech(0.5), "q", _inputs(100.0, 60.0), evidence_state=SYNTH)
    assert r.inputs.qoi_full == 100.0
    assert r.inputs.qoi_ablated == 60.0
    assert 1.0 - r.inputs.qoi_ablated / r.inputs.qoi_full == pytest.approx(r.value)


def test_a_genuine_zero_is_distinguishable_from_a_failure():
    """Ablation changed nothing: materiality 0.0, status ESTIMATED. This must not look
    like the missing-input case, which is the whole point of carrying a status."""
    r = estimate_materiality(_mech(0.5), "q", _inputs(100.0, 100.0), evidence_state=SYNTH)
    assert r.status is MaterialityStatus.ESTIMATED
    assert r.value == pytest.approx(0.0)
    assert r.is_usable()


# ── missing evidence is never an inferred zero ───────────────────────────────

@pytest.mark.parametrize("kwargs", [
    {"full": None}, {"ablated": None}, {"prov": None}, {"full": None, "ablated": None},
])
def test_missing_input_gives_insufficient_evidence_and_no_value(kwargs):
    r = estimate_materiality(_mech(0.5), "q", _inputs(**kwargs), evidence_state=SYNTH)
    assert r.status is MaterialityStatus.INSUFFICIENT_EVIDENCE
    assert r.value is None, "a missing input must not become a zero materiality"
    assert not r.is_usable()


def test_result_cannot_be_constructed_with_a_value_on_a_failed_status():
    from physmap.materiality.estimator import MaterialityResult

    with pytest.raises(ValueError, match="must not carry a value"):
        MaterialityResult(
            mechanism_id="m1", qoi="q",
            status=MaterialityStatus.INSUFFICIENT_EVIDENCE,
            inputs=AblationInputs(), evidence_state=SYNTH,
            reason="forced", value=0.0,
        )


def test_zero_denominator_is_insufficient_not_infinite():
    r = estimate_materiality(_mech(0.5), "q", _inputs(0.0, 0.0), evidence_state=SYNTH)
    assert r.status is MaterialityStatus.INSUFFICIENT_EVIDENCE
    assert r.value is None


# ── refused provenance ───────────────────────────────────────────────────────

def test_flat_plate_correlation_is_refused_by_name():
    r = estimate_materiality(
        _mech(0.5), "q",
        _inputs(prov=AblationProvenance.FLAT_PLATE_CORRELATION),
        evidence_state=SYNTH,
    )
    assert r.status is MaterialityStatus.REFUSED_PROVENANCE
    assert r.value is None
    assert "different geometry" in r.reason


def test_geometry_matched_correlation_is_admissible():
    r = estimate_materiality(
        _mech(0.5), "q",
        _inputs(prov=AblationProvenance.GEOMETRY_MATCHED_CORRELATION),
        evidence_state=SYNTH,
    )
    assert r.status is MaterialityStatus.ESTIMATED


# ── the flag rule needs BOTH halves ──────────────────────────────────────────

def test_outside_and_material_fires():
    m = _mech(5.0)                                  # outside [0, 1]
    r = estimate_materiality(m, "q", _inputs(100.0, 60.0), evidence_state=SYNTH)
    s = materiality_signal(m, r, theta=THETA)       # 0.40 >= 0.20
    assert s.fired and s.kind is SignalKind.CAUSAL_MATERIALITY


def test_outside_but_immaterial_stays_quiet():
    """The disc-region case: the excursion is real but does not reach the QoI. This is
    exactly where the causal method must differ from the naive box check."""
    m = _mech(5.0)
    r = estimate_materiality(m, "q", _inputs(100.0, 95.0), evidence_state=SYNTH)  # 0.05
    s = materiality_signal(m, r, theta=THETA)
    assert not s.fired
    assert "does not reach the quantity of interest" in s.rationale


def test_material_but_inside_calibration_stays_quiet():
    """A mechanism can dominate the QoI and be perfectly well calibrated."""
    m = _mech(0.5)
    r = estimate_materiality(m, "q", _inputs(100.0, 10.0), evidence_state=SYNTH)  # 0.90
    s = materiality_signal(m, r, theta=THETA)
    assert not s.fired
    assert "not a defect on its own" in s.rationale


def test_causal_flag_differs_from_the_naive_box_check():
    """Same excursion, different verdicts. If these ever agree on every case, the
    materiality term is doing no work."""
    m = _mech(5.0)
    naive_fires = m.outside_calibration()
    immaterial = estimate_materiality(m, "q", _inputs(100.0, 95.0), evidence_state=SYNTH)
    causal = materiality_signal(m, immaterial, theta=THETA)
    assert naive_fires is True
    assert causal.fired is False


def test_unusable_materiality_cannot_fire_and_cannot_clear():
    m = _mech(5.0)
    r = estimate_materiality(m, "q", _inputs(full=None), evidence_state=SYNTH)
    s = materiality_signal(m, r, theta=THETA)
    assert not s.fired
    assert s.value is None
    assert "NOT ASSESSED" in s.rationale
    assert "not a causal verdict either way" in s.rationale


# ── the independence guard ───────────────────────────────────────────────────

def test_same_closure_truth_is_refused():
    with pytest.raises(CircularTruthError, match="closure under test"):
        require_independent_truth(TruthIndependence.SAME_CLOSURE)


def test_unknown_truth_is_refused_rather_than_assumed_innocent():
    with pytest.raises(CircularTruthError, match="unknown"):
        require_independent_truth(TruthIndependence.UNKNOWN)


def test_fixture_truth_is_refused_for_performance_claims():
    with pytest.raises(CircularTruthError, match="cannot back a performance claim"):
        require_independent_truth(TruthIndependence.FIXTURE)


@pytest.mark.parametrize("src", [
    TruthIndependence.EXPERIMENTAL, TruthIndependence.INDEPENDENT_HIGH_FIDELITY,
])
def test_independent_sources_pass(src):
    assert require_independent_truth(src) is src
    assert may_report_performance(src)


@pytest.mark.parametrize("src", ["same_closure", "unknown", "fixture", "nonsense"])
def test_may_report_performance_is_false_for_everything_else(src):
    assert not may_report_performance(src)


# ── the no-conflation rule ───────────────────────────────────────────────────

def test_a_signal_must_declare_its_kind():
    with pytest.raises(TypeError, match="must be a SignalKind"):
        Signal(kind="causal_materiality", fired=False, rationale="x")


def test_a_signal_that_could_not_be_computed_cannot_fire():
    with pytest.raises(ValueError, match="must not fire"):
        Signal(kind=SignalKind.CAUSAL_MATERIALITY, fired=True, rationale="x", value=None)
