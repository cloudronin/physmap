"""PhysMAP Regime → Observability Mapping — consistency + classifier-agreement tests.

Asserts the spec's done-gate (docs/specs/PhysMAP_Regime_Observability_Mapping_Spec_v0_1.md)
against the GENERATED artifact:
  • the committed mapping.jsonl equals a fresh build (no silent drift from the sources)
  • the committed artifact validates clean (all gates)
  • enum ↔ regimes agreement; every regime → ≥1 closure → ≥1 bound; closures ∈ corpus
  • every Layer-1 bound variable has a Layer-2a row; per-variable class is consistent
  • known-partial → uncalibrated|calibrated slot; structural-binary → no degree
  • honesty gate: no faked degrees (validator rejects the tamper fixtures)
  • the classifier's NACA/Forrest/richardson classes follow from the mapping alone
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from physmap.corpus import calibration as cc
from physmap.guardrail import regime_observability as rom
from physmap.guardrail.classify import (
    classify_observability,
    coord_input_aliases,
    load_default_corpus_index,
)
from physmap.guardrail.corpus_regimes import observability_class_for
from physmap.guardrail.enums import Observability, Regime

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = rom.DEFAULT_PATH


@pytest.fixture(scope="module")
def corpus_index() -> dict[str, cc.ClosureEntry]:
    return cc.index_by_id(cc.load_corpus())


@pytest.fixture(scope="module")
def mapping() -> rom.RegimeObservabilityMapping:
    return rom.load_mapping(ARTIFACT)


# ── artifact integrity ────────────────────────────────────────────────────────

def test_artifact_exists():
    assert ARTIFACT.exists(), f"mapping artifact missing at {ARTIFACT} (run `build`)"


def test_committed_equals_fresh_build(mapping, corpus_index):
    """The committed file must equal a fresh projection — it cannot silently drift."""
    assert mapping == rom.build_mapping(corpus_index=corpus_index)


def test_committed_validates_clean(mapping, corpus_index):
    errs = rom.validate_mapping(mapping, corpus_index)
    assert not errs, f"committed mapping has validation errors: {errs}"


def test_fresh_build_validates_clean(corpus_index):
    m = rom.build_mapping(corpus_index=corpus_index)
    assert rom.validate_mapping(m, corpus_index) == {}


def test_fingerprint_shape():
    fp = rom.mapping_fingerprint(ARTIFACT)
    assert fp["version"] == rom.MAPPING_VERSION
    assert len(fp["sha256"]) == 64
    assert fp["n_records"] == len(mapping_records())


def mapping_records() -> list[dict]:
    return [json.loads(ln) for ln in ARTIFACT.read_text(encoding="utf-8").splitlines() if ln.strip()]


# ── done-gate invariants ──────────────────────────────────────────────────────

def test_enum_regimes_agreement(mapping):
    expected = {r.value for r in Regime if r is not Regime.UNLISTED}
    present = {row.regime for row in mapping.regimes}
    assert present == expected
    assert Regime.UNLISTED.value not in present  # statistical-only; excluded by design


def test_every_regime_resolves_to_closures_and_bounds(mapping):
    cb = {c.closure_id: c for c in mapping.closure_bounds}
    for row in mapping.regimes:
        assert row.closures, f"{row.regime}: no closures"
        for cid in row.closures:
            assert cid in cb, f"{row.regime}: closure {cid} has no closure_bounds row"
            assert cb[cid].bounds, f"{cid}: no bounds"


def test_closures_exist_in_corpus(mapping, corpus_index):
    for c in mapping.closure_bounds:
        assert c.closure_id in corpus_index, f"{c.closure_id} not in calibration corpus"


def test_every_bound_variable_has_observability_row(mapping):
    vo = {v.variable for v in mapping.variable_observability}
    bound_vars = {b.variable for c in mapping.closure_bounds for b in c.bounds}
    assert bound_vars <= vo, f"Layer 2a gap: {sorted(bound_vars - vo)}"


def test_variable_class_consistent_across_closures(mapping):
    """A variable's observability_class must match its authoritative (closure,coord) source
    everywhere it appears — the per-variable model holds."""
    vo = {v.variable: v.observability_class for v in mapping.variable_observability}
    for c in mapping.closure_bounds:
        for b in c.bounds:
            assert observability_class_for(c.closure_id, b.variable) == vo[b.variable], (
                f"{b.variable}: class differs between source and row"
            )


def test_known_partial_has_uncalibrated_slot(mapping):
    kp = [v for v in mapping.variable_observability if v.observability_class == "known-partial"]
    assert any(v.variable == "richardson_number" for v in kp), "expected richardson_number known-partial"
    for v in kp:
        assert v.degree_status in ("uncalibrated", "calibrated")
        if v.degree_status == "uncalibrated":
            assert v.partial_degree is None and v.calibrated_by == []


def test_structural_binary_has_no_degree(mapping):
    for v in mapping.variable_observability:
        if v.observability_class == "structural-binary":
            assert v.partial_degree is None
            assert v.degree_status == "n/a"
            assert v.calibrated_by == []


# ── honesty gate: the validator rejects tamper fixtures ───────────────────────

def _kp_row(m: rom.RegimeObservabilityMapping) -> rom.VariableObservabilityRow:
    return next(v for v in m.variable_observability if v.variable == "richardson_number")


def _sb_row(m: rom.RegimeObservabilityMapping) -> rom.VariableObservabilityRow:
    return next(v for v in m.variable_observability if v.variable == "reynolds_number")


def test_validator_rejects_faked_uncalibrated_degree(mapping, corpus_index):
    m = copy.deepcopy(mapping)
    _kp_row(m).partial_degree = {"mixed_convection_horizontal_tube": 0.5}  # still uncalibrated
    errs = rom.validate_mapping(m, corpus_index)
    assert any("faked" in e or "uncalibrated" in e for e in errs.get("variable_observability", [])), errs


def test_validator_rejects_calibrated_without_provenance(mapping, corpus_index):
    m = copy.deepcopy(mapping)
    v = _kp_row(m)
    v.degree_status = "calibrated"
    v.partial_degree = {"mixed_convection_horizontal_tube": 0.5}
    v.calibrated_by = []  # missing provenance
    errs = rom.validate_mapping(m, corpus_index)
    assert any("calibrated_by" in e for e in errs.get("variable_observability", [])), errs


def test_validator_rejects_structural_binary_with_degree(mapping, corpus_index):
    m = copy.deepcopy(mapping)
    _sb_row(m).partial_degree = {"x": 1.0}
    errs = rom.validate_mapping(m, corpus_index)
    assert errs.get("variable_observability"), errs


def test_validator_rejects_class_inconsistency(mapping, corpus_index):
    m = copy.deepcopy(mapping)
    _sb_row(m).observability_class = "known-partial"  # disagrees with source
    errs = rom.validate_mapping(m, corpus_index)
    assert any("disagrees with source" in e for e in errs.get("variable_observability", [])), errs


def test_validator_rejects_missing_layer2a_row(mapping, corpus_index):
    m = copy.deepcopy(mapping)
    m.variable_observability = [v for v in m.variable_observability if v.variable != "x_over_D"]
    errs = rom.validate_mapping(m, corpus_index)
    assert any("no observability_class row" in e for e in errs.get("variable_observability", [])), errs


def test_validator_rejects_dangling_closure(mapping, corpus_index):
    m = copy.deepcopy(mapping)
    m.regimes[0].closures = list(m.regimes[0].closures) + ["ghost-closure-9999"]
    errs = rom.validate_mapping(m, corpus_index)
    assert any("ghost-closure-9999" in e for e in errs.get("closure_bounds", [])), errs


def test_validator_rejects_missing_regime(mapping, corpus_index):
    m = copy.deepcopy(mapping)
    m.regimes = m.regimes[1:]  # drop one
    errs = rom.validate_mapping(m, corpus_index)
    assert any("missing regime row" in e for e in errs.get("regimes", [])), errs


# ── classifier agreement: the classes follow from the mapping alone ───────────

def _expected_from_mapping(
    m: rom.RegimeObservabilityMapping, regime: Regime, inputs,
) -> dict[str, Observability]:
    """Reproduce the classifier's verdict using ONLY the mapping (Layer 1 + 2a) plus
    the per-deployment set-membership (Layer 2b)."""
    ins = set(inputs)
    row = next(r for r in m.regimes if r.regime == regime.value)
    vo = {v.variable: v for v in m.variable_observability}
    cb = {c.closure_id: c for c in m.closure_bounds}
    out: dict[str, Observability] = {}
    for cid in row.closures:
        for b in cb[cid].bounds:
            coord = b.variable
            if any(a in ins for a in coord_input_aliases(coord)):
                out[coord] = Observability.OBSERVABLE
            elif vo[coord].observability_class == "known-partial":
                out[coord] = Observability.PARTIAL
            else:
                out[coord] = Observability.UNOBSERVABLE
    return out


_VEHICLES = [
    (Regime.ENTRANCE_REGION_PIPE, ["Re", "Pr"]),
    (Regime.INTERNAL_FORCED_CONVECTION_RECT_CHANNEL, ["Re", "Pr"]),
    (Regime.MIXED_CONVECTION_HORIZONTAL_TUBE, ["Re", "Pr"]),
]


def test_classifier_matches_mapping(mapping, corpus_index):
    for regime, inputs in _VEHICLES:
        assert classify_observability(inputs, regime, corpus_index) == _expected_from_mapping(
            mapping, regime, inputs
        ), regime


def test_naca_forrest_richardson_predicted_classes(mapping):
    naca = _expected_from_mapping(mapping, Regime.ENTRANCE_REGION_PIPE, ["Re", "Pr"])
    assert naca["x_over_D"] is Observability.UNOBSERVABLE
    assert naca["reynolds_number"] is Observability.OBSERVABLE

    forrest = _expected_from_mapping(mapping, Regime.INTERNAL_FORCED_CONVECTION_RECT_CHANNEL, ["Re", "Pr"])
    assert forrest["reynolds_number"] is Observability.OBSERVABLE

    rich = _expected_from_mapping(mapping, Regime.MIXED_CONVECTION_HORIZONTAL_TUBE, ["Re", "Pr"])
    assert rich["richardson_number"] is Observability.PARTIAL


# ── CLI smoke ─────────────────────────────────────────────────────────────────

def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "physmap.guardrail.regime_observability", *args],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )


def test_cli_validate_passes_on_committed():
    res = _run("validate")
    assert res.returncode == 0, f"stderr: {res.stderr}\nstdout: {res.stdout}"
    assert "PASSED" in res.stdout


def test_cli_summary_works():
    res = _run("summary")
    assert res.returncode == 0
    assert "known-partial" in res.stdout


def test_cli_validate_fails_on_broken_fixture(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({
        "table": "variable_observability", "variable": "zzz", "variable_short": "zzz",
        "observability_class": "bogus", "partial_degree": None, "degree_status": "n/a",
        "calibrated_by": [],
    }) + "\n", encoding="utf-8")
    res = _run("validate", "--path", str(bad))
    assert res.returncode != 0
    assert "FAILED" in res.stdout


def test_torch_free():
    import sys as _sys
    assert "torch" not in _sys.modules
