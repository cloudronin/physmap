"""The home baseline: labelled by provenance, derived beside the bank, never in place of it.

The detector counts stand for every vehicle. This file guards the reading that qualifies
them: each vehicle's home error is labelled by how it was obtained, the reading rule is
applied exactly as stated, and the original banked matrix is left untouched.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
from scipy.stats import fisher_exact

from physmap.benchmarks import home_baseline as hb
from physmap.benchmarks.report import load_banked_matrix, render_report

REPO = Path(__file__).resolve().parents[1]
FITTED = {"casper_hypersonic_transition", "marineau_hypersonic_transition", "dirker_water"}
#: The original result, as banked on 2026-09-22. The home baseline adds fields beside it.
MATRIX_SHA256 = "3c0dcc9eed30dee76f77bd85f36f0f4c3eefdcbd001804b484de93f2abe192ac"


@pytest.fixture(scope="module")
def bank():
    return hb.load_banked_home()


def test_the_original_bank_is_untouched():
    p = REPO / "data" / "benchmarks" / "v0_4" / "matrix_full_seven.json"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == MATRIX_SHA256


def test_every_vehicle_is_kept(bank):
    """No vehicle and no row is dropped: every banked vehicle has a home baseline, and its
    deployment counts are the banked matrix's own."""
    matrix = {c["vehicle_id"]: c for c in load_banked_matrix()["cells"]}
    assert {c["vehicle_id"] for c in bank["cells"]} == set(matrix)
    ref = str(bank["reference_pct"])
    for c in bank["cells"]:
        banked = (matrix[c["vehicle_id"]].get("per_pct") or {}).get(ref)
        if banked is not None:
            assert (c["deployment"]["n"], c["deployment"]["n_wrong"]) == (
                banked["n_test"], banked["n_wrong"]), c["vehicle_id"]


def test_home_error_is_labelled_by_how_it_was_obtained(bank):
    """Fitted to the home rows -> in-sample fit error, with a held-out refit beside it.
    A published correlation -> held-out home error, and no in-sample figure at all."""
    for c in bank["cells"]:
        vid = c["vehicle_id"]
        if vid in FITTED:
            assert c["home_in_sample"] is not None, vid
            assert c["home_held_out"]["method"] == "leave-one-out refit", vid
            assert c["home_evaluation_provenance"].startswith("in-sample fit error"), vid
        else:
            assert c["home_in_sample"] is None, vid
            assert c["home_evaluation_provenance"].startswith("held-out home error"), vid


def test_the_reading_rule_is_applied_as_stated(bank):
    for c in bank["cells"]:
        h, d = c["home_held_out"], c["deployment"]
        _, p = fisher_exact([[d["n_wrong"], d["n"] - d["n_wrong"]],
                             [h["n_wrong"], h["n"] - h["n_wrong"]]], alternative="greater")
        assert c["fisher_p"] == pytest.approx(p, rel=1e-12), c["vehicle_id"]
        expected = bool(h["n"] >= 2 and p < hb.ALPHA)
        assert c["supports_blind_spot"] is expected, c["vehicle_id"]
        assert c["reason"].startswith("yes:" if expected else "no:"), c["vehicle_id"]


def test_a_vehicle_that_fails_the_reading_keeps_its_counts(bank):
    """Qualified, not deleted: the report still prints every vehicle's detector counts."""
    text = render_report()
    for c in bank["cells"]:
        assert c["vehicle_id"] in text
    assert "What the closure-validity check adds" in text
    assert "Home baseline" in text


def test_the_fast_vehicles_recompute_to_the_bank(bank):
    """Every vehicle but Casper (159 refits) recomputed from the data. The refit is checked
    against the loader's own surrogate inside compute(), so this also proves the held-out
    error describes the same model."""
    fast = {c["vehicle_id"] for c in bank["cells"]} - {"casper_hypersonic_transition"}
    fresh = {c["vehicle_id"]: c for c in hb.compute(only=fast)["cells"]}
    for c in bank["cells"]:
        if c["vehicle_id"] in fast:
            assert fresh[c["vehicle_id"]] == c, c["vehicle_id"]


@pytest.mark.slow
def test_the_whole_home_baseline_recomputes_to_the_bank():
    cmp = hb.compare_with_bank(hb.compute())
    assert cmp.matches, cmp.drift[:5]


def test_the_report_labels_in_sample_error_as_such():
    out = subprocess.run([sys.executable, "-m", "physmap.cli", "benchmark", "report"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "in-sample fit error" in out.stdout
    assert "held-out home error (leave-one-out refit)" in out.stdout
    assert "published correlation, not fitted to these rows" in out.stdout
