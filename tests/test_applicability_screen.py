"""The applicability screen and the two declarative fixtures."""

from __future__ import annotations

import pytest

from physmap.applicability.fixtures import FIXTURE_IDS, get_fixture
from physmap.applicability.screen import Applicability, ReasonCode, screen_case
from physmap.explain.causal import render_screen
from physmap.release import EvidenceState

SYNTH = EvidenceState.SYNTHETIC_FIXTURE


def _screen(**over):
    kw = dict(
        qoi_decomposes=True, mechanisms_separable=True,
        has_calibration_window=True, ablation_available=True,
        evidence_state=SYNTH,
    )
    kw.update(over)
    return screen_case("case", "q", **kw)


def test_all_preconditions_met_is_applicable():
    r = _screen()
    assert r.applicability is Applicability.APPLICABLE
    assert r.reason_code is ReasonCode.SATISFIED


@pytest.mark.parametrize("field,code", [
    ("qoi_decomposes", ReasonCode.QOI_DOES_NOT_DECOMPOSE),
    ("mechanisms_separable", ReasonCode.MECHANISMS_NOT_SEPARABLE),
    ("has_calibration_window", ReasonCode.NO_CALIBRATION_WINDOW),
    ("ablation_available", ReasonCode.NO_ABLATION_AVAILABLE),
])
def test_each_failed_precondition_has_its_own_reason_code(field, code):
    r = _screen(**{field: False})
    assert r.applicability is Applicability.NOT_APPLICABLE
    assert r.reason_code is code


@pytest.mark.parametrize("field", [
    "qoi_decomposes", "mechanisms_separable", "has_calibration_window",
    "ablation_available",
])
def test_unestablished_is_not_the_same_as_false(field):
    """None means 'not established'. Collapsing it to False would turn an unanswered
    question into a negative finding."""
    r = _screen(**{field: None})
    assert r.applicability is Applicability.INSUFFICIENT_EVIDENCE
    assert r.applicability is not Applicability.NOT_APPLICABLE


# ── the two screened-out cases ───────────────────────────────────────────────

@pytest.mark.parametrize("case_id", FIXTURE_IDS)
def test_fixtures_refuse_and_are_marked_declarative(case_id):
    r = get_fixture(case_id)
    assert r.applicability is Applicability.NOT_APPLICABLE
    assert r.evidence_state is EvidenceState.DECLARATIVE
    assert r.is_declarative


@pytest.mark.parametrize("case_id", FIXTURE_IDS)
def test_fixture_output_says_it_is_not_evidence_backed(case_id):
    text = render_screen(get_fixture(case_id))
    assert "declarative" in text
    assert "not an evidence-backed case" in text
    assert "no precision, recall or F1" in text


def test_the_two_fixtures_refuse_for_different_reasons():
    """If both refused for the same reason, only one of them would be demonstrating
    anything."""
    codes = {get_fixture(c).reason_code for c in FIXTURE_IDS}
    assert len(codes) == len(FIXTURE_IDS)


def test_unknown_fixture_raises():
    with pytest.raises(KeyError, match="unknown screening fixture"):
        get_fixture("no-such-case")


def test_explanations_are_deterministic():
    a = render_screen(get_fixture("fda-blood-pump"))
    b = render_screen(get_fixture("fda-blood-pump"))
    assert a == b
