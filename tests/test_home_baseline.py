"""The home baseline: labelled by provenance, derived beside the bank, read without a gate.

The detector counts stand for every vehicle. This file guards what qualifies them: each
vehicle's home error is labelled by how it was obtained, its interpretation is prose
reviewed against the exact counts it quotes, the Fisher test is exploratory and decides
nothing, and the original v0.4 banks are kept byte for byte.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from scipy.stats import fisher_exact

from physmap.benchmarks import home_baseline as hb
from physmap.benchmarks.benchmark_v0_4 import BANK_DIR, BANK_VERSION, HISTORICAL_BANKS
from physmap.benchmarks.report import load_banked_matrix, render_report

REPO = Path(__file__).resolve().parents[1]
FITTED = {"casper_hypersonic_transition", "marineau_hypersonic_transition", "dirker_water"}
#: The original v0.4 result, as banked on 2026-09-22 (matrix) and 2026-09-25 (the home
#: baseline and architecture axis derived from it). History, kept for audit, never edited.
HISTORICAL_SHA256 = {
    "matrix_full_seven.json": "3c0dcc9eed30dee76f77bd85f36f0f4c3eefdcbd001804b484de93f2abe192ac",
    "home_baseline.json": "d91da18b9fe04bfbec2a19620254cc161a6ec2399dda5f51c8f6cb036d1ae6c3",
    "architecture_axis.json": "7ae6e2f077c318227a8d521f307a99d831d5882e0a431f4ac81b6b7aac4184d1",
}


@pytest.fixture(scope="module")
def bank():
    return hb.load_banked_home()


@pytest.mark.parametrize("name", sorted(HISTORICAL_SHA256))
def test_the_original_v0_4_banks_are_untouched(name):
    p = REPO.joinpath(*HISTORICAL_BANKS["0.4"], name)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == HISTORICAL_SHA256[name]


def test_the_current_bank_differs_from_the_original_only_in_the_naca_cell():
    """0.4.1 corrects one vehicle's source data. Every other cell must be the original's."""
    old = json.loads(REPO.joinpath(*HISTORICAL_BANKS["0.4"], "matrix_full_seven.json").read_text())
    new = load_banked_matrix()
    assert new["bank_version"] == BANK_VERSION and BANK_VERSION != "0.4"
    old_cells = {c["vehicle_id"]: c for c in old["cells"]}
    new_cells = {c["vehicle_id"]: c for c in new["cells"]}
    assert set(old_cells) == set(new_cells)
    changed = {v for v in old_cells if old_cells[v] != new_cells[v]}
    assert changed == {"naca_tn1451"}


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


def test_rates_are_the_counts(bank):
    for c in bank["cells"]:
        for block in (c["home_held_out"], c["deployment"], c["home_in_sample"]):
            if block is not None:
                assert block["rate"] == pytest.approx(block["n_wrong"] / block["n"], abs=1e-6)


def test_no_gate_decides_the_reading(bank):
    """The reading is prose. No boolean verdict, no threshold, anywhere in the record."""
    for c in bank["cells"]:
        assert "supports_blind_spot" not in c and "reason" not in c, c["vehicle_id"]
        assert c["interpretation"], c["vehicle_id"]
    assert "p < 0.05" not in json.dumps(bank)


def test_each_interpretation_was_written_for_these_counts(bank):
    """If a recomputation moves a count, the prose that quotes it must be reread."""
    for c in bank["cells"]:
        w = hb.INTERPRETATION[c["vehicle_id"]]["written_for"]
        got = {"home": (c["home_held_out"]["n_wrong"], c["home_held_out"]["n"]),
               "deployment": (c["deployment"]["n_wrong"], c["deployment"]["n"])}
        assert got == {k: tuple(v) for k, v in w.items()}, (
            f"{c['vehicle_id']}: the interpretation was written for {w}; the counts are now "
            f"{got}. Reread and rewrite it.")
        assert c["interpretation"] == hb.interpretation(c)


def test_the_fisher_test_is_exploratory_and_recomputable(bank):
    for c in bank["cells"]:
        h, d, ex = c["home_held_out"], c["deployment"], c["exploratory"]
        _, p = fisher_exact([[d["n_wrong"], d["n"] - d["n_wrong"]],
                             [h["n_wrong"], h["n"] - h["n_wrong"]]], alternative="greater")
        assert ex["fisher_exact_one_sided_p"] == pytest.approx(p, rel=1e-12), c["vehicle_id"]
        assert ex["note"].startswith("Exploratory only") and "decides nothing" in ex["note"]


def test_a_vehicle_keeps_its_counts_whatever_its_reading(bank):
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


def test_the_report_labels_error_kinds_and_the_exploratory_test():
    out = subprocess.run([sys.executable, "-m", "physmap.cli", "benchmark", "report"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "in-sample fit error" in out.stdout
    assert "held-out home error (leave-one-out refit)" in out.stdout
    assert "published correlation, not fitted to these rows" in out.stdout
    assert "Exploratory only" in out.stdout and "decides nothing" in out.stdout
    assert f"Bank v{BANK_VERSION}" in out.stdout and "/".join(BANK_DIR) in out.stdout
