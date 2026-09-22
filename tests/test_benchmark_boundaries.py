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

EXPECTED_RERUN = ("naca_tn1451", "velazquez_sco2")


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "physmap.cli", *args], capture_output=True, text=True
    )


def test_exactly_the_cleared_vehicles_are_rerunnable():
    assert rerunnable_ids() == EXPECTED_RERUN
    assert len(VEHICLES) == 7
    assert len(banked_only_ids()) == 5


def test_every_vehicle_states_a_redistribution_basis():
    for v in VEHICLES:
        assert v.redistribution_reason.strip(), v.vehicle_id
        assert v.source.strip() and v.how_values_were_produced.strip(), v.vehicle_id


def test_marineau_is_blocked_not_merely_excluded():
    """It is a finding, not a decision: no reuse licence exists. Collapsing it into
    'excluded by decision' would hide that the two are different things."""
    from physmap.benchmarks.registry import get

    assert get("marineau_hypersonic_transition").redistribution is Redistribution.BLOCKED_NO_LICENCE


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
    assert "2 of 7" in text


def test_report_marks_recomputed_rows_differently():
    fake = {"naca_tn1451": next(
        c for c in load_banked_matrix()["cells"] if c["vehicle_id"] == "naca_tn1451")}
    text = render_report(rerun_results=fake)
    assert "RECOMPUTED" in text
    assert "banked only" in text


def test_coverage_note_admits_the_subset_is_not_representative():
    note = coverage_note()
    assert "NOT a representative sample" in note
    assert "aerospace" in note
    # the two restraint outcomes are exactly what the public subset loses
    assert "DO_NO_HARM" in note and "BASELINE_VISIBLE" in note


@pytest.mark.parametrize("args", [("benchmark", "run"), ("benchmark", "report")])
def test_cli_always_states_it_does_not_reproduce_all_seven(args):
    r = _cli(*args)
    assert r.returncode == 0, r.stderr
    assert "DOES NOT REPRODUCE ALL SEVEN" in r.stdout


def test_cli_run_names_both_sets():
    r = _cli("benchmark", "run")
    assert "Rerunning 2 of 7" in r.stdout
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
