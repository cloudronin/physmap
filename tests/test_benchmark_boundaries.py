"""The rerunnable subset, and the labels that must travel with it.

These guard a claim that is easy to make by accident: that the public command reproduces
the benchmark. It reruns two of seven, and every surface that shows a number has to say
which two.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from physmap.benchmarks.registry import (
    VEHICLES,
    Redistribution,
    banked_only_ids,
    rerunnable_ids,
)
from physmap.benchmarks.report import coverage_note, load_banked_matrix, render_report

EXPECTED_RERUN = (
    "naca_tn1451", "velazquez_sco2",
    "marineau_hypersonic_transition", "dirker_water", "jin_sco2_buoyancy",
)
EXPECTED_LICENSED = ("naca_tn1451", "velazquez_sco2")


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "physmap.cli", *args], capture_output=True, text=True
    )


def test_exactly_the_shipped_vehicles_are_rerunnable():
    assert set(rerunnable_ids()) == set(EXPECTED_RERUN)
    assert len(VEHICLES) == 7
    assert len(banked_only_ids()) == 2


def test_shipping_is_kept_distinct_from_licensing():
    """Three datasets ship without a licence. Folding them into CLEAR would hide the
    one thing a downstream reuser most needs to know."""
    from physmap.benchmarks.registry import licensed_ids, unlicensed_shipped_ids

    assert set(licensed_ids()) == set(EXPECTED_LICENSED)
    assert set(unlicensed_shipped_ids()) == set(EXPECTED_RERUN) - set(EXPECTED_LICENSED)
    assert set(licensed_ids()) & set(unlicensed_shipped_ids()) == set()


def test_every_vehicle_states_a_redistribution_basis():
    for v in VEHICLES:
        assert v.redistribution_reason.strip(), v.vehicle_id
        assert v.source.strip() and v.how_values_were_produced.strip(), v.vehicle_id


def test_the_three_unlicensed_datasets_carry_the_right_basis():
    """Marineau has no prohibition; Dirker and Jin are published against one. Those are
    different risks and the registry must not blur them."""
    from physmap.benchmarks.registry import get

    assert get("marineau_hypersonic_transition").redistribution is (
        Redistribution.NO_LICENCE_FACTS_BASIS)
    for vid in ("dirker_water", "jin_sco2_buoyancy"):
        assert get(vid).redistribution is Redistribution.AGAINST_PUBLISHER_TERMS
        assert not get(vid).licensed


def test_report_warns_that_shipping_is_not_licensing():
    text = render_report()
    assert "Shipping is not licensing" in text
    assert "ships, NOT licensed" in text
    assert "ships, AGAINST publisher terms" in text
    assert "removed on objection" in text.lower()


def test_the_banked_matrix_carries_no_third_party_measurements():
    """It is publishable only because it holds counts, verdicts and our own thresholds.
    A raw measurement column appearing here would leak data five publishers did not
    licence."""
    matrix = load_banked_matrix()
    allowed_prefixes = (
        "vehicle_id", "domain", "regime", "failure_", "expected_", "observability",
        "caveat", "surrogate_inputs", "n_", "calib", "clean_lift", "misaligned",
        "min_baseline", "ref_", "empirical_outcome", "per_pct",
        # prose about OUR method on that cell, e.g. "observable degenerate pole;
        # only 1 train rows (thin)". Carries no measured values.
        "rationale",
    )
    for cell in matrix["cells"]:
        unknown = [k for k in cell if not k.startswith(allowed_prefixes)]
        assert unknown == [], f"{cell['vehicle_id']}: unexpected fields {unknown}"


def test_report_shows_all_seven_and_marks_the_two():
    text = render_report()
    for v in VEHICLES:
        assert v.vehicle_id in text
    assert "THIS COMMAND DOES NOT REPRODUCE ALL SEVEN VEHICLES." in text
    assert "5 of 7" in text


def test_report_marks_recomputed_rows_differently():
    fake = {"naca_tn1451": next(
        c for c in load_banked_matrix()["cells"] if c["vehicle_id"] == "naca_tn1451")}
    text = render_report(rerun_results=fake)
    assert "RECOMPUTED" in text
    assert "banked only" in text


def test_coverage_note_admits_the_subset_is_not_representative():
    note = coverage_note()
    assert "NOT a representative sample" in note
    # DO_NO_HARM has one vehicle, forrest, which is excluded -- so the case where the
    # guard correctly stays quiet still cannot be rerun.
    assert "DO_NO_HARM" in note


@pytest.mark.parametrize("args", [("benchmark", "run"), ("benchmark", "report")])
def test_cli_always_states_it_does_not_reproduce_all_seven(args):
    r = _cli(*args)
    assert r.returncode == 0, r.stderr
    assert "DOES NOT REPRODUCE ALL SEVEN" in r.stdout


def test_cli_run_names_both_sets():
    r = _cli("benchmark", "run")
    assert "Rerunning 5 of 7" in r.stdout
    for vid in banked_only_ids():
        assert vid in r.stdout


def test_excluded_vehicle_data_does_not_ship():
    """The determination is only real if the files are actually absent."""
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    tracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    for vid in banked_only_ids():
        stem = vid.split("_")[0]
        hits = [f for f in tracked if stem in f.lower() and f.endswith(".csv")]
        assert hits == [], f"{vid} source data is tracked but not cleared: {hits}"
