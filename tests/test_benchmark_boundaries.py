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

EXPECTED_LICENSED = ("naca_tn1451", "velazquez_sco2")
EXPECTED_TRIAGE_ONLY = ("forrest",)


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "physmap.cli", *args], capture_output=True, text=True
    )


def test_all_seven_ship_and_none_is_banked_only():
    assert len(VEHICLES) == 7
    assert len(rerunnable_ids()) == 7
    assert banked_only_ids() == ()


def test_shipping_is_kept_distinct_from_licensing():
    """Three datasets ship without a licence. Folding them into CLEAR would hide the
    one thing a downstream reuser most needs to know."""
    from physmap.benchmarks.registry import licensed_ids, unlicensed_shipped_ids

    assert set(licensed_ids()) == set(EXPECTED_LICENSED)
    assert len(unlicensed_shipped_ids()) == 5
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


def test_report_shows_all_seven_and_separates_shipping_from_recomputing():
    text = render_report()
    for v in VEHICLES:
        assert v.vehicle_id in text
    assert "7 of 7 ship" in text
    # shipping is not reproducing: with no runner ported, nothing was recomputed
    assert "NOTHING WAS RECOMPUTED IN THIS RUN" in text


def test_report_marks_recomputed_rows_differently():
    fake = {"naca_tn1451": next(
        c for c in load_banked_matrix()["cells"] if c["vehicle_id"] == "naca_tn1451")}
    text = render_report(rerun_results=fake)
    assert "RECOMPUTED" in text
    assert "THIS RUN RECOMPUTED 1 OF 7 VEHICLES" in text
    # and the six that were not must still be distinguishable
    assert "ships, licensed" in text


def test_coverage_note_does_not_let_present_read_as_covered():
    """Every outcome class now ships. DO_NO_HARM is still not really demonstrated,
    because its only vehicle is triage-grade with one training row."""
    note = coverage_note()
    assert "DO_NO_HARM" in note
    assert "not benchmark-grade" in note


def test_report_alone_does_not_claim_a_reproduction():
    """`report` reads the bank; it runs nothing. It must not let seven shipped
    datasets read as seven reproduced results."""
    r = _cli("benchmark", "report")
    assert r.returncode == 0, r.stderr
    assert "NOTHING WAS RECOMPUTED IN THIS RUN" in r.stdout


@pytest.mark.slow
def test_cli_run_recomputes_and_checks_itself_against_the_bank():
    r = _cli("benchmark", "run")
    assert r.returncode == 0, r.stderr
    assert "Recomputed 7 vehicles." in r.stdout
    # Exactly on a machine like the one that banked it; on another numpy/BLAS build a float
    # can differ in its last bit, and the command then says it matched within 1e-9. Both pass.
    assert ("Every cell matches the banked matrix exactly." in r.stdout
            or "Every cell matches the banked matrix: matches within" in r.stdout), r.stdout
    assert "DRIFT" not in r.stdout


@pytest.mark.slow
def test_cli_run_states_the_licence_split():
    r = _cli("benchmark", "run")
    assert "Source data ships for 7 of 7" in r.stdout
    assert "Shipping is not licensing" in r.stdout


def test_data_quality_is_tracked_separately_from_redistribution():
    """A licence clearance must not launder a data-quality problem."""
    from physmap.benchmarks.registry import DataQuality, get, triage_only_ids

    assert triage_only_ids() == EXPECTED_TRIAGE_ONLY
    forrest = get("forrest")
    assert forrest.rerunnable and forrest.quality is DataQuality.TRIAGE_ONLY
    assert "triage" in forrest.quality_note.lower()


def test_report_and_coverage_flag_the_degenerate_outcome():
    """DO_NO_HARM is present again, but its only vehicle has one training row and no
    detector fit. Present-but-degenerate must not read as covered."""
    text = render_report()
    assert "TRIAGE_ONLY" in text
    note = coverage_note()
    assert "not benchmark-grade" in note
    assert "DO_NO_HARM" in note and "n_train=1" in note


def test_no_paper_shaped_file_ships():
    """Numbers only. The entire redistribution position rests on this being true."""
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    tracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    bad = [f for f in tracked
           if f.lower().endswith((".pdf", ".docx", ".doc", ".ps", ".epub", ".tif", ".tiff"))]
    assert bad == [], f"document-shaped files are tracked: {bad}"
