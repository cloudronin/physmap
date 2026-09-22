"""The benchmark must never read as evidence for the causal-materiality result.

These are different claims resting on different evidence, and the whole project exists
because conflating them is easy and consequential. The separation is asserted here rather
than left to documentation, because documentation does not fail a build.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from physmap.benchmarks.registry import VEHICLES
from physmap.benchmarks.report import load_banked_matrix, render_report
from physmap.core.signals import SignalKind
from physmap.explain.benchmark import BENCHMARK_MEASURES, NOT_EVIDENCE_FOR, render_cell


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "physmap.cli", *args], capture_output=True, text=True
    )


def test_the_benchmark_measures_closure_and_observability_not_materiality():
    assert set(BENCHMARK_MEASURES) == {
        SignalKind.CLOSURE_VALIDITY, SignalKind.OBSERVABILITY}
    assert NOT_EVIDENCE_FOR is SignalKind.CAUSAL_MATERIALITY
    assert NOT_EVIDENCE_FOR not in BENCHMARK_MEASURES


@pytest.mark.parametrize("vehicle", [v.vehicle_id for v in VEHICLES])
def test_every_cell_explanation_disclaims_the_causal_result(vehicle):
    cells = {c["vehicle_id"]: c for c in load_banked_matrix()["cells"]}
    text = render_cell(cells[vehicle])
    assert "NOT evidence for causal_materiality" in text
    assert "closure_validity + observability" in text


def test_no_benchmark_cell_carries_a_materiality_or_metric_field():
    """If a materiality or a precision/recall field ever appears in a cell, the
    benchmark has started measuring something it is not entitled to measure."""
    forbidden = ("materiality", "precision", "recall", "f1", "nu_f", "nu_m", "qoi")
    for cell in load_banked_matrix()["cells"]:
        hits = [k for k in cell if any(f in k.lower() for f in forbidden)]
        assert hits == [], f"{cell['vehicle_id']}: {hits}"


def test_the_vehicle_nearest_the_causal_case_is_named_not_denied():
    """An earlier version of the disclaimer said this benchmark contains no
    mixed-convection vertical-pipe vehicle. That was FALSE -- jin_sco2_buoyancy is
    exactly that. The honest disclaimer names the nearest vehicle and says why it
    still is not causal evidence, which is stronger than a denial that a reader can
    check and find wrong.
    """
    from physmap.explain.benchmark import NEAREST_TO_CAUSAL_CASE

    cells = {c["vehicle_id"]: c for c in load_banked_matrix()["cells"]}
    nearest = cells[NEAREST_TO_CAUSAL_CASE]
    assert "mixed_convection_vertical" in nearest["regime"], (
        "the named nearest vehicle is no longer a mixed-convection vertical tube; "
        "re-pick it rather than leaving the claim stale"
    )
    # and it must be named in every rendering, not quietly omitted
    for vid in cells:
        assert NEAREST_TO_CAUSAL_CASE in render_cell(cells[vid])


def test_the_report_never_uses_causal_vocabulary_for_an_outcome():
    text = render_report()
    for outcome in ("PHYSMAP_WINS", "PARTIAL", "DO_NO_HARM", "BASELINE_VISIBLE"):
        assert outcome in text
    for banned in ("materiality", "precision", "recall", "F1"):
        # permitted only in the sentence stating no such claim is made
        for line in text.splitlines():
            if banned.lower() in line.lower():
                assert "no precision" in line.lower() or "not licensed" in line.lower(), line


def test_explain_separates_the_two_kinds_of_subject():
    r = _cli("explain", "--list")
    assert r.returncode == 0
    out = r.stdout
    assert "closure validity + observability" in out
    assert "causal-materiality applicability, declarative" in out
    # a benchmark vehicle and a screening case must not appear under the same heading
    bench_block, _, screen_block = out.partition("screening cases")
    assert "naca_tn1451" in bench_block and "naca_tn1451" not in screen_block
    assert "fda-blood-pump" in screen_block


def test_forrest_explanation_states_its_outcome_is_not_earned():
    cells = {c["vehicle_id"]: c for c in load_banked_matrix()["cells"]}
    text = render_cell(cells["forrest"])
    assert "TRIAGE_ONLY" in text
    assert "short-circuited rather than earned" in text
    assert "1 training row" in text or "only 1 train rows" in text
