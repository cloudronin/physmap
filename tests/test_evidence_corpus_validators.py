"""PhysMAP Evidence Corpus — validator unit tests.

Mirrors tests/test_calibration_corpus.py style. Per-gate negative tests are the
core asset: each gate gets at least one explicit failing fixture and one passing
fixture. Provenance-discipline gates (9, 10) get extra coverage since they are
the user-stated correctness conditions for this corpus.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from physmap.corpus import evidence as ec


REPO_ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_PATH = (
    REPO_ROOT / "src" / "physmap" / "corpus" / "data" / "corpus_seed.jsonl"
)


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_source() -> ec.Source:
    return ec.Source(
        source_id="forrest-2014",
        citation="Forrest, E.C., et al. (2014). J. Heat Transfer 138(2):021704.",
        doi="10.1115/1.4031646",
        year=2014,
        source_type="validation-study",
        source_status="populated",
        notes="tested 5 closures simultaneously",
    )


@pytest.fixture
def stub_source() -> ec.Source:
    return ec.Source(
        source_id="incropera-7th",
        citation="Bergman/Incropera 2011 Fundamentals of Heat & Mass Transfer (7th).",
        doi=None,
        year=2011,
        source_type="handbook",
        source_status="stub",
        notes="acquisition pending",
    )


@pytest.fixture
def conditions_water_narrow_rect() -> ec.Conditions:
    return ec.Conditions(
        re_range=ec.Range(min=10000.0, max=70000.0),
        pr_range=ec.Range(min=2.2, max=5.4),
        geometry_class="narrow-rect-channel-one-sided",
        fluid="water",
    )


@pytest.fixture
def bound_re_above_10k() -> ec.Bound:
    return ec.Bound(
        variable="reynolds_number",
        valid_above=10000.0,
        valid_below=70000.0,
        condition="modified Sparrow-Cur validated range",
    )


@pytest.fixture
def calibration_ids() -> set[str]:
    """Subset of real closure_ids used in tests."""
    return {
        "gnielinski-1976",
        "dittus-boelter-1930",
        "sieder-tate-1936",
        "modified-sparrow-cur-asym-narrow-rect-channel-2014",
    }


_UNSET = object()


def make_claim(
    *,
    claim_id: str = "test-claim-1",
    closure_id: str = "modified-sparrow-cur-asym-narrow-rect-channel-2014",
    source_id: str = "forrest-2014",
    claim_type: str = "validated-bound",
    role: str = "validate",
    bound: ec.Bound | None = None,
    measured_divergence=_UNSET,  # sentinel: None means "force null"; UNSET → default
    conditions: ec.Conditions | None = None,
    status: str = "confirmed",
    supersedes_claim_id: str | None = None,
    contradicts_claim_id: str | None = None,
) -> ec.Claim:
    """Factory with sensible defaults for a primary-source validate claim.

    `measured_divergence=None` explicitly sets the field to null (useful for
    gate-4 negative tests). Omit the kwarg to get the default — a populated
    MeasuredDivergence iff role == 'validate'.
    """
    if bound is None:
        bound = ec.Bound(
            variable="reynolds_number", valid_above=10000.0, valid_below=70000.0,
            condition="Forrest 2014 Table 4 validated range",
        )
    if conditions is None:
        conditions = ec.Conditions(
            re_range=ec.Range(min=10000.0, max=70000.0),
            pr_range=ec.Range(min=2.2, max=5.4),
            geometry_class="narrow-rect-channel-one-sided",
            fluid="water",
        )
    if measured_divergence is _UNSET:
        if role == "validate":
            measured_divergence = ec.MeasuredDivergence(
                magnitude_pct=6.1,
                region="Re 10k-70k, Pr 2.2-5.4 (full validated rectangle)",
                measure="MAE",
                extraction_method="primary-source",
                page_or_table="Table 4",
            )
        else:
            measured_divergence = None
    return ec.Claim(
        claim_id=claim_id, closure_id=closure_id, source_id=source_id,
        claim_type=claim_type, role=role, bound=bound,
        measured_divergence=measured_divergence, conditions=conditions,
        status=status, supersedes_claim_id=supersedes_claim_id,
        contradicts_claim_id=contradicts_claim_id,
    )


# ── happy path ────────────────────────────────────────────────────────────────


def test_canonical_claim_validates_clean(sample_source, calibration_ids):
    """A well-formed primary-source validate claim passes all 12 gates."""
    claim = make_claim()
    errs = ec.validate_claim(
        claim,
        source_index={sample_source.source_id: sample_source},
        calibration_closure_ids=calibration_ids,
        claim_ids_in_corpus={claim.claim_id},
    )
    assert errs == [], f"expected zero errors, got: {errs}"


def test_canonical_source_validates_clean(sample_source):
    assert ec.validate_source(sample_source) == []


# ── Gate 1 — atomic provenance ────────────────────────────────────────────────


def test_gate1_missing_source_id_fails(sample_source, calibration_ids):
    claim = make_claim(source_id="")
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 1" in e for e in errs)


# ── Gate 2 — source_id resolves (and is not a stub) ───────────────────────────


def test_gate2_unknown_source_id_fails(sample_source, calibration_ids):
    claim = make_claim(source_id="nonexistent-source")
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 2" in e and "not found" in e for e in errs)


def test_gate2_claim_against_stub_source_fails(stub_source, calibration_ids):
    """The honest-coverage rule: no claims may cite a stub source."""
    claim = make_claim(
        source_id="incropera-7th",
        role="synthesize",
        claim_type="consensus-bound",
        measured_divergence=None,
    )
    errs = ec.validate_claim(
        claim, {stub_source.source_id: stub_source}, calibration_ids, {claim.claim_id}
    )
    assert any("stub" in e for e in errs)


# ── Gate 3 — closure_id join validator ────────────────────────────────────────


def test_gate3_orphan_closure_id_fails(sample_source):
    claim = make_claim(closure_id="not-a-real-closure")
    errs = ec.validate_claim(
        claim,
        {sample_source.source_id: sample_source},
        calibration_closure_ids={"some-other-closure"},
        claim_ids_in_corpus={claim.claim_id},
    )
    assert any("gate 3" in e for e in errs)


# ── Gate 4 — measured_divergence biconditional ────────────────────────────────


def test_gate4_validate_without_divergence_fails(sample_source, calibration_ids):
    claim = make_claim(measured_divergence=None)
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 4" in e and "null" in e for e in errs)


def test_gate4_non_validate_with_divergence_fails(sample_source, calibration_ids):
    claim = make_claim(
        role="originate",
        claim_type="originating-bound",
        measured_divergence=ec.MeasuredDivergence(
            magnitude_pct=6.1, region="x", measure="MAE",
            extraction_method="primary-source", page_or_table="Table 4",
        ),
    )
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 4" in e and "must NOT" in e for e in errs)


# ── Gate 5 — role vocab ───────────────────────────────────────────────────────


def test_gate5_invalid_role_fails(sample_source, calibration_ids):
    claim = make_claim(role="invent")
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 5" in e for e in errs)


# ── Gate 6 — claim_type vocab ─────────────────────────────────────────────────


def test_gate6_invalid_claim_type_fails(sample_source, calibration_ids):
    claim = make_claim(claim_type="nonsense-type")
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 6" in e for e in errs)


# ── Gate 7 — supersedes/contradicts FK resolution ─────────────────────────────


def test_gate7_supersedes_must_resolve(sample_source, calibration_ids):
    claim = make_claim(supersedes_claim_id="not-a-real-claim")
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 7" in e and "supersedes_claim_id" in e for e in errs)


def test_gate7_contradicts_must_resolve(sample_source, calibration_ids):
    claim = make_claim(contradicts_claim_id="not-a-real-claim")
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 7" in e and "contradicts_claim_id" in e for e in errs)


def test_gate7_passes_when_fk_target_present(sample_source, calibration_ids):
    target = make_claim(claim_id="target-claim")
    claim = make_claim(
        claim_id="supersedes-target", supersedes_claim_id="target-claim",
    )
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source},
        calibration_ids, {"target-claim", "supersedes-target"},
    )
    assert errs == [], f"expected clean, got: {errs}"


# ── Gate 8 — status vocab ─────────────────────────────────────────────────────


def test_gate8_invalid_status_fails(sample_source, calibration_ids):
    claim = make_claim(status="provisionally-supposed")
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 8" in e for e in errs)


# ── Gate 9 — no provenance laundering (the user-stated correctness condition) ─


def test_gate9_calibration_lift_extraction_method_fails(sample_source, calibration_ids):
    """The headline rule: lifting a divergence from a calibration-corpus
    provenance note is provenance laundering and must FAIL validation."""
    claim = make_claim(
        measured_divergence=ec.MeasuredDivergence(
            magnitude_pct=6.1,
            region="full validated rectangle",
            measure="MAE",
            extraction_method="calibration-provenance-lift",  # disallowed
            page_or_table="Table 4",
        ),
    )
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 9" in e for e in errs), (
        "the calibration-provenance-lift path must fail gate 9 — "
        "this is the user-stated correctness condition for the corpus"
    )
    assert any("laundering" in e for e in errs)


def test_gate9_primary_source_passes(sample_source, calibration_ids):
    claim = make_claim()  # default extraction_method='primary-source'
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert all("gate 9" not in e for e in errs)


def test_gate9_visual_estimate_passes(sample_source, calibration_ids):
    """visual-estimate-rendered-pdf is one of the two allowed extraction methods."""
    claim = make_claim(
        measured_divergence=ec.MeasuredDivergence(
            magnitude_pct=82.1,
            region="sub-critical laminar (Re~3900, Pr=5.4)",
            measure="median_gap",
            extraction_method="visual-estimate-rendered-pdf",
            page_or_table="Figure 5",
            magnitude_uncertainty_pct=17.0,
            n_points=4,
            resolvability_ratio=4.88,
        ),
    )
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert all("gate 9" not in e for e in errs)


# ── Gate 10 — uncertainty discipline for visual-estimate claims ───────────────


@pytest.mark.parametrize("missing_field", [
    "magnitude_uncertainty_pct", "n_points", "resolvability_ratio",
])
def test_gate10_visual_estimate_missing_uncertainty_field_fails(
    sample_source, calibration_ids, missing_field
):
    """A visual-estimate claim missing any of the uncertainty triple must fail
    gate 10. This is the coarser-tier self-documenting discipline."""
    md_kwargs = dict(
        magnitude_pct=82.1, region="sub-critical", measure="median_gap",
        extraction_method="visual-estimate-rendered-pdf", page_or_table="Figure 5",
        magnitude_uncertainty_pct=17.0, n_points=4, resolvability_ratio=4.88,
    )
    md_kwargs[missing_field] = None
    claim = make_claim(measured_divergence=ec.MeasuredDivergence(**md_kwargs))
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 10" in e and missing_field in e for e in errs)


def test_gate10_primary_source_may_have_null_uncertainty(sample_source, calibration_ids):
    """Primary-source claims (e.g. MAE summaries) don't require uncertainty
    triple — they typically report magnitude only."""
    claim = make_claim()  # default primary-source, no uncertainty fields set
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert all("gate 10" not in e for e in errs)


# ── Gate 11 — page_or_table required ──────────────────────────────────────────


def test_gate11_missing_page_or_table_fails(sample_source, calibration_ids):
    claim = make_claim(
        measured_divergence=ec.MeasuredDivergence(
            magnitude_pct=6.1, region="x", measure="MAE",
            extraction_method="primary-source", page_or_table="",
        ),
    )
    errs = ec.validate_claim(
        claim, {sample_source.source_id: sample_source}, calibration_ids, {claim.claim_id}
    )
    assert any("gate 11" in e for e in errs)


# ── Gate 12 — claim_id uniqueness (corpus-wide) ───────────────────────────────


def test_gate12_duplicate_claim_id_fails(sample_source):
    claim_a = make_claim(claim_id="dup")
    claim_b = make_claim(claim_id="dup")
    errs_by_id = ec.validate_corpus(
        sources=[sample_source],
        claims=[claim_a, claim_b],
        calibration_closure_ids={claim_a.closure_id},
    )
    corpus_errs = errs_by_id.get("__corpus__", [])
    assert any("gate 12" in e and "dup" in e for e in corpus_errs)


# ── source-level validators ──────────────────────────────────────────────────


def test_source_invalid_slug_fails():
    s = ec.Source(
        source_id="Forrest 2014",  # bad: has space, has caps
        citation="x", doi=None, year=2014,
        source_type="validation-study", source_status="populated", notes="",
    )
    errs = ec.validate_source(s)
    assert any("slug" in e for e in errs)


def test_source_invalid_year_fails():
    s = ec.Source(
        source_id="x", citation="x", doi=None, year=99,
        source_type="handbook", source_status="populated", notes="",
    )
    errs = ec.validate_source(s)
    assert any("year" in e for e in errs)


def test_source_invalid_type_fails():
    s = ec.Source(
        source_id="x", citation="x", doi=None, year=2014,
        source_type="trash-paper", source_status="populated", notes="",
    )
    errs = ec.validate_source(s)
    assert any("source_type" in e for e in errs)


# ── (de)serialization round-trip ─────────────────────────────────────────────


def test_claim_round_trip():
    claim = make_claim(claim_id="rt-1")
    d = ec.claim_to_dict(claim)
    rebuilt = ec.claim_from_dict(d)
    assert rebuilt == claim


def test_source_round_trip(sample_source):
    d = ec.source_to_dict(sample_source)
    rebuilt = ec.source_from_dict(d)
    assert rebuilt == sample_source


# ── v0.6 JSON-LD export ──────────────────────────────────────────────────────


def test_v06_jsonld_shape(sample_source):
    claim = make_claim(claim_id="rt-jsonld")
    out = ec.claim_to_v06_jsonld(claim, sample_source)
    assert out["@type"] == "CredibilityFactor"
    assert out["id"] == "evidence-corpus:rt-jsonld"
    assert out["factorType"] == "ValidatedBound"
    assert out["factorStatus"] == "confirmed"
    assert out["factorStandard"] == sample_source.doi
    assert out["wasDerivedFrom"] == f"source:{sample_source.source_id}"
    assert out["hasEvidence"]["@type"] == "Discrepancy"
    assert out["hasEvidence"]["discrepancyMagnitude"] == 6.1


def test_v06_jsonld_no_doi_falls_back_to_citation():
    src = ec.Source(
        source_id="naca-tn1451-1948",
        citation="NACA TN-1451 (1948).",
        doi=None, year=1948, source_type="validation-study",
        source_status="populated", notes="",
    )
    claim = make_claim(claim_id="rt-nodoi", source_id="naca-tn1451-1948")
    out = ec.claim_to_v06_jsonld(claim, src)
    assert out["factorStandard"] == src.citation


# ── query helpers ────────────────────────────────────────────────────────────


def test_query_validity_story_groups_by_closure():
    cl_a = make_claim(claim_id="a", closure_id="x", source_id="forrest-2014")
    cl_b = make_claim(claim_id="b", closure_id="y", source_id="forrest-2014")
    cl_c = make_claim(claim_id="c", closure_id="x", source_id="forrest-2014")
    result = ec.query_validity_story([cl_a, cl_b, cl_c], "x")
    assert {c.claim_id for c in result} == {"a", "c"}


def test_query_source_contributions():
    cl_a = make_claim(claim_id="a", source_id="forrest-2014")
    cl_b = make_claim(claim_id="b", source_id="naca-tn1451-1948")
    result = ec.query_source_contributions([cl_a, cl_b], "forrest-2014")
    assert [c.claim_id for c in result] == ["a"]


def test_query_disagreements_includes_contested_and_contradicts():
    cl_a = make_claim(claim_id="a", status="contested")
    cl_b = make_claim(claim_id="b", contradicts_claim_id="a")
    cl_c = make_claim(claim_id="c")
    result = ec.query_disagreements([cl_a, cl_b, cl_c])
    assert {c.claim_id for c in result} == {"a", "b"}


def test_query_provenance_for_assessment_filters_by_re_pr():
    """Claim Conditions envelope contains the (Re, Pr) operating point."""
    cl_inside = make_claim(claim_id="inside")  # Re 10k-70k, Pr 2.2-5.4
    cl_outside = make_claim(
        claim_id="outside",
        conditions=ec.Conditions(
            re_range=ec.Range(min=100000.0, max=500000.0),
            pr_range=ec.Range(min=2.2, max=5.4),
            geometry_class="narrow-rect-channel-one-sided", fluid="water",
        ),
    )
    result = ec.query_provenance_for_assessment(
        [cl_inside, cl_outside], cl_inside.closure_id, re_value=20000.0, pr_value=3.5,
    )
    assert [c.claim_id for c in result] == ["inside"]


# ── join with the real calibration corpus ─────────────────────────────────────


def test_real_calibration_corpus_ids_loadable():
    """The join domain for gate 3 is the live calibration corpus."""
    ids = ec.load_calibration_closure_ids(CALIBRATION_PATH)
    assert "gnielinski-1976" in ids
    assert "dittus-boelter-1930" in ids
    assert "sieder-tate-1936" in ids
    assert "modified-sparrow-cur-asym-narrow-rect-channel-2014" in ids


# ── seed integrity (lights up once Step 4 lands) ──────────────────────────────




