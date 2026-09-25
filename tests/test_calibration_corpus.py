"""PhysMAP Calibration-Boundary Corpus — schema, validator, loader tests.

Mirrors the tests/test_seeds.py controlled-vocab + per-entry validation pattern.
Asserts:
  • the seeded corpus.jsonl loads cleanly and passes all 7 QC gates + invariants
  • the validator's gate-7 (confirmed needs primary_source + citation) is enforced
  • the validator rejects every shape violation (broken-corpus fixtures)
  • the loader API returns the expected ClosureEntry / CoordinateBound objects
  • is_in_calibration handles in-range / out-of-range / unknown-closure / unknown-coord
  • the CLI validate command exits non-zero on broken corpora and zero on the seed
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from physmap.corpus import calibration as cc


REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = REPO_ROOT / "src" / "physmap" / "corpus" / "data" / "corpus_seed.jsonl"


# ── seed integrity ────────────────────────────────────────────────────────────

def test_seed_file_exists():
    assert SEED_PATH.exists(), f"seed corpus missing at {SEED_PATH}"


def test_seed_loads_and_validates_clean():
    """The committed seed must pass the gates + corpus-wide invariants, in seed mode:
    the seed collapses every bound status to "seed", which the full gates reject."""
    entries = cc.load_corpus(SEED_PATH)
    assert entries, "seed corpus is empty"
    errs = cc.validate_corpus(entries, seed_tier=True)
    assert not errs, f"seed has validation errors: {errs}"


def test_seed_unique_closure_ids():
    entries = cc.load_corpus(SEED_PATH)
    ids = [e.closure_id for e in entries]
    assert len(ids) == len(set(ids)), f"duplicate closure_id in seed: {ids}"


def test_seed_families_in_controlled_vocab():
    entries = cc.load_corpus(SEED_PATH)
    for e in entries:
        assert e.closure_family in cc.CLOSURE_FAMILIES, (
            f"{e.closure_id}: family {e.closure_family!r} not in vocab"
        )


def test_seed_solver_availability_non_empty():
    entries = cc.load_corpus(SEED_PATH)
    for e in entries:
        assert e.solver_availability, f"{e.closure_id}: empty solver_availability"


def test_seed_weakener_link_populated():
    entries = cc.load_corpus(SEED_PATH)
    for e in entries:
        assert e.weakener_link, f"{e.closure_id}: weakener_link empty (gate 5)"


def test_seed_provenance_on_every_bound():
    entries = cc.load_corpus(SEED_PATH)
    for e in entries:
        for b in e.validated_range:
            assert isinstance(b.provenance, dict) and b.provenance, (
                f"{e.closure_id}.{b.coord}: provenance missing (gate 1)"
            )


# ── per-gate fixture-of-broken-corpus rejection ───────────────────────────────

def _valid_entry_dict() -> dict:
    return {
        "closure_id": "test-closure-2030",
        "closure_family": "single-phase-convection",
        "closure_name": "Test Closure",
        "physics_coordinates": ["reynolds_number"],
        "validated_range": [{
            "coord": "reynolds_number",
            "min": 1000.0, "max": 100000.0, "unit": "dimensionless",
            "bound_status": "claimed",
            "provenance": {"citation": "test", "primary_source": False},
            "contested_note": None,
        }],
        "fluid_context": ["air"],
        "regime_context": "fully developed turbulent pipe flow",
        "contested": False,
        "solver_availability": ["openfoam"],
        "weakener_link": ["extrapolated-closure"],
        "last_reviewed": "2026-06-03",
        "reviewer": "test",
    }


def test_validator_accepts_valid_entry():
    e = cc.entry_from_dict(_valid_entry_dict())
    assert cc.validate(e) == []


def test_gate_1_missing_provenance_rejected():
    d = _valid_entry_dict()
    d["validated_range"][0]["provenance"] = {}
    errs = cc.validate(cc.entry_from_dict(d))
    assert any("gate 1" in err or "provenance" in err for err in errs), errs


def test_gate_2_bad_bound_status_rejected():
    d = _valid_entry_dict()
    d["validated_range"][0]["bound_status"] = "yolo"
    errs = cc.validate(cc.entry_from_dict(d))
    assert any("bound_status" in err for err in errs), errs


def test_gate_3_contested_note_requires_contested_true():
    d = _valid_entry_dict()
    d["validated_range"][0]["contested_note"] = "sources disagree on the upper bound"
    d["contested"] = False
    errs = cc.validate(cc.entry_from_dict(d))
    assert any("gate 3" in err for err in errs), errs


def test_gate_4_solver_none_alone_requires_handbook_note():
    d = _valid_entry_dict()
    d["solver_availability"] = ["none"]
    d["regime_context"] = "no handbook reference here"
    errs = cc.validate(cc.entry_from_dict(d))
    assert any("gate 4" in err for err in errs), errs


def test_gate_5_empty_weakener_link_rejected():
    d = _valid_entry_dict()
    d["weakener_link"] = []
    errs = cc.validate(cc.entry_from_dict(d))
    assert any("gate 5" in err for err in errs), errs


def test_gate_6_geometry_in_physics_coordinates_rejected():
    d = _valid_entry_dict()
    d["physics_coordinates"] = ["reynolds_number", "diameter"]
    d["validated_range"].append({
        "coord": "diameter",
        "min": 0.001, "max": 0.1, "unit": "m",
        "bound_status": "claimed",
        "provenance": {"citation": "test"},
        "contested_note": None,
    })
    errs = cc.validate(cc.entry_from_dict(d))
    assert any("gate 6" in err for err in errs), errs


def test_gate_7_confirmed_without_primary_source_rejected():
    d = _valid_entry_dict()
    d["validated_range"][0]["bound_status"] = "confirmed"
    d["validated_range"][0]["provenance"] = {"citation": "handbook"}  # no primary_source
    errs = cc.validate(cc.entry_from_dict(d))
    assert any("gate 7" in err for err in errs), errs


def test_gate_7_confirmed_with_primary_source_accepted():
    d = _valid_entry_dict()
    d["validated_range"][0]["bound_status"] = "confirmed"
    d["validated_range"][0]["provenance"] = {
        "citation": "Primary Author (2020). Journal 12(3):45-67",
        "doi": "10.1234/example",
        "primary_source": True,
    }
    errs = cc.validate(cc.entry_from_dict(d))
    assert errs == [], errs


def test_duplicate_closure_id_caught_by_corpus_validator():
    e1 = cc.entry_from_dict(_valid_entry_dict())
    d2 = _valid_entry_dict()
    e2 = cc.entry_from_dict(d2)               # same closure_id
    errs = cc.validate_corpus([e1, e2])
    assert "__corpus__" in errs
    assert any("duplicate" in err for err in errs["__corpus__"])


def test_unknown_family_rejected():
    d = _valid_entry_dict()
    d["closure_family"] = "magic-new-family"
    errs = cc.validate(cc.entry_from_dict(d))
    assert any("closure_family" in err for err in errs), errs


def test_bad_iso_date_rejected():
    d = _valid_entry_dict()
    d["last_reviewed"] = "not-a-date"
    errs = cc.validate(cc.entry_from_dict(d))
    assert any("last_reviewed" in err for err in errs), errs


def test_min_greater_than_max_rejected():
    d = _valid_entry_dict()
    d["validated_range"][0]["min"] = 1000.0
    d["validated_range"][0]["max"] = 100.0
    errs = cc.validate(cc.entry_from_dict(d))
    assert any("min" in err and "max" in err for err in errs), errs


# ── loader API tests ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def seed_index() -> dict[str, cc.ClosureEntry]:
    return cc.index_by_id(cc.load_corpus(SEED_PATH))


def test_index_by_id_keys(seed_index):
    assert "dittus-boelter-1930" in seed_index
    assert seed_index["dittus-boelter-1930"].closure_family == "single-phase-convection"


def test_get_validated_range_returns_bound(seed_index):
    bound = cc.get_validated_range(seed_index, "dittus-boelter-1930", "reynolds_number")
    assert bound is not None
    assert bound.min == 10000.0
    assert bound.max == 1200000.0
    assert bound.unit == "dimensionless"
    assert bound.bound_status == "seed"   # the seed collapses every status to "seed"


def test_get_validated_range_unknown_closure(seed_index):
    bound = cc.get_validated_range(seed_index, "nonexistent-closure", "reynolds_number")
    assert bound is None


def test_get_validated_range_unknown_coord(seed_index):
    bound = cc.get_validated_range(seed_index, "dittus-boelter-1930", "magic_number")
    assert bound is None


def test_is_in_calibration_inside(seed_index):
    assert cc.is_in_calibration(seed_index, "dittus-boelter-1930", "reynolds_number", 50000.0) is True


def test_is_in_calibration_below_min(seed_index):
    assert cc.is_in_calibration(seed_index, "dittus-boelter-1930", "reynolds_number", 100.0) is False


def test_is_in_calibration_above_max(seed_index):
    assert cc.is_in_calibration(seed_index, "dittus-boelter-1930", "reynolds_number", 1e10) is False


def test_is_in_calibration_unknown_returns_none(seed_index):
    """Caller decides fallback when corpus has no entry — signals via None."""
    assert cc.is_in_calibration(seed_index, "nonexistent-closure", "reynolds_number", 1000.0) is None


# ── CLI smoke ─────────────────────────────────────────────────────────────────

def test_cli_validate_passes_on_seed():
    res = subprocess.run(
        [sys.executable, "-m", "physmap.corpus.calibration", "validate"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert res.returncode == 0, f"stderr: {res.stderr}\nstdout: {res.stdout}"
    assert "PASSED" in res.stdout


def test_cli_validate_fails_on_broken_fixture(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({**_valid_entry_dict(), "weakener_link": []}) + "\n",
                   encoding="utf-8")
    res = subprocess.run(
        [sys.executable, "-m", "physmap.corpus.calibration", "validate", "--path", str(bad)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert res.returncode != 0
    assert "FAILED" in res.stdout or "gate 5" in res.stdout


def test_cli_summary_works(tmp_path):
    res = subprocess.run(
        [sys.executable, "-m", "physmap.corpus.calibration", "summary"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert res.returncode == 0
    assert "entries" in res.stdout


# ── additive invariant: prior committed artifacts untouched ───────────────────

def test_torch_free():
    import sys
    assert "torch" not in sys.modules
