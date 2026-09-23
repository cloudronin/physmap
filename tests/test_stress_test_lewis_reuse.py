"""The Lewis controlled model-reuse stress test, through the shipped code.

Runs the stress test ONCE (about two minutes) and checks the record against: its own
assertions, the pre-declared design-M run it must reproduce, the committed bank, and the
threshold-presentation rule. The assertions are also fed deliberately broken records, because
an assertion that cannot fail proves nothing.

Development demonstration: one run, stations are not cases, no performance metric.
"""
import copy
import json
from pathlib import Path

import pytest

from physmap import cli
from physmap.benchmarks.compare import compare_records
from physmap.stress_tests import lewis_reuse as st

REPO = Path(__file__).resolve().parents[1]
PREDECLARED = REPO / "results" / "lewis35A_head_to_head" / "design_M_matched.json"


@pytest.fixture(scope="module")
def record():
    return st.run()


# ── the two assertions the stress test exists to make ────────────────────────

def test_every_visible_deployment_input_is_an_exact_training_input(record):
    ic = record["input_contract"]
    assert ic["design_M_every_visible_input_exactly_in_training"] is True
    assert ic["surrogate_inputs"] == ic["ood_detector_inputs"] == ["Re", "Pr", "x_over_D"]
    for withheld in ("gravity", "Ri", "Gr", "wall heat flux"):
        assert withheld in ic["withheld_from_both"]


def test_ood_scores_are_unchanged_between_gravity_off_and_gravity_on(record):
    for design in ("headline_design_M", "secondary_design_A3"):
        assert record[design]["ood"]["identical_between_gravity_states"] is True
        for s in record[design]["stations"]:
            assert s["ood_gravity_off"] == s["ood_gravity_on"], (design, s["x_over_D"])


def test_the_record_passes_its_own_checks(record):
    assert st.check(record) == []


# ── the assertions are real: each catches the violation it names ────────────

def test_check_catches_an_ood_score_that_moved_with_gravity(record):
    broken = copy.deepcopy(record)
    s = broken["headline_design_M"]["stations"][6]
    s["ood_gravity_on"]["99"]["distance"]["score"] += 1e-6
    broken["headline_design_M"]["ood"]["identical_between_gravity_states"] = False
    assert any("OOD scores changed" in f for f in st.check(broken))


def test_check_catches_a_deployment_input_missing_from_training(record):
    broken = copy.deepcopy(record)
    broken["input_contract"]["design_M_every_visible_input_exactly_in_training"] = False
    assert any("not an exact training input" in f for f in st.check(broken))


def test_check_catches_a_surrogate_that_misses_the_accurate_control(record):
    broken = copy.deepcopy(record)
    broken["headline_design_M"]["stations"][4]["control_error_pct"] = 3.0
    assert any("no longer a trustworthy forced-convection model" in f for f in st.check(broken))


def test_check_catches_nonzero_materiality_with_gravity_off(record):
    broken = copy.deepcopy(record)
    broken["headline_design_M"]["stations"][8]["materiality_gravity_off"] = 0.01
    assert any("materiality with gravity off is not zero" in f for f in st.check(broken))


# ── what the record must contain ─────────────────────────────────────────────

def test_the_result_itself(record):
    """Design M, at the benchmark's reference percentile: the detector quiet at every
    comparable station in both states; materiality zero with gravity off and rising to about
    0.19 with gravity on; the surrogate right on the control and 17-18 % off downstream."""
    st_ = {round(s["x_over_D"], 2): s for s in record["headline_design_M"]["stations"]}
    comparable = [s for s in st_.values() if s["comparable"]]
    assert not any(s["ood_gravity_on"]["99"]["fired"] for s in comparable)
    assert all(s["materiality_gravity_off"] == 0.0 for s in st_.values())
    assert max(abs(s["control_error_pct"]) for s in comparable) < 0.1
    for x in (67.55, 101.69, 135.84):
        assert -18.5 < st_[x]["experimental_error_pct"] < -16.5
        assert st_[x]["materiality_gravity_on"] > 0.1
    # secondary: between training runs, the detector warns everywhere, in both states
    sec = record["secondary_design_A3"]["ood"]["comparable_stations_fired_by_pct"]["99"]
    assert sec == {"gravity_off": 9, "gravity_on": 9}


def test_matched_ablation_provenance_is_recorded(record):
    ma = record["matched_ablation"]
    assert ma["provenance"] == "matched_ablation"
    assert ma["full"]["gravity_on"] is True and ma["removed"]["gravity_on"] is False
    assert "constant/g" in ma["only_difference"]
    assert ma["full"]["reversed_cells_in_heated_section"] == 0
    assert "energy_closure_reference" in ma


def test_every_categorical_result_names_its_threshold(record):
    td = record["threshold_dependence"]
    assert all("threshold" in t for t in td)
    theta = [t for t in td if t["depends_on_unlocked_threshold"]]
    assert theta, "the PhysMAP flags depend on theta and must say so"
    assert all("UNLOCKED" in t["threshold"] for t in theta)
    anything = next(t for t in theta if "at least one" in t["result"])
    assert anything["holds_for_theta_up_to"] == pytest.approx(0.1948, abs=5e-4)
    ood = next(t for t in td if t["result"].startswith("OOD fired or quiet"))
    assert "operating percentile" in ood["threshold"]


def test_rendered_report_carries_the_framing_the_claim_and_the_disclaimers(record):
    text = st.render(record)
    assert "CONTROLLED MODEL-REUSE STRESS TEST" in text
    assert "reused in vertical heated flow" in text.replace("\n", " ")
    assert "cannot identify a change absent from its input contract" in " ".join(text.split())
    flat = " ".join(text.split())
    assert "OOD detectors do not fail in general" in flat
    assert "Gravity should not be omitted" in flat
    assert "Nothing is claimed about NVIDIA PhysicsNeMo" in flat
    assert "ILLUSTRATIVE theta = 0.10" in text
    assert "not a verdict" in text


# ── reproduction ─────────────────────────────────────────────────────────────

def test_reproduces_the_predeclared_design_m_run(record):
    """The shipped module must reproduce cfd/lewis_head_to_head.py's pre-declared run, at the
    precision that run banked."""
    pre = json.loads(PREDECLARED.read_text())
    on = pre["states"]["gravity_on_experiment"]["stations"]
    off = pre["states"]["gravity_off_control"]["stations"]
    for new, b_on, b_off in zip(record["headline_design_M"]["stations"], on, off):
        assert round(new["surrogate_prediction"], 4) == b_on["surrogate_prediction"]
        assert round(new["experimental_error_pct"], 3) == b_on["prediction_error_pct"]
        assert round(new["control_error_pct"], 3) == b_off["prediction_error_pct"]
        assert new["ood_gravity_on"]["99"]["distance"]["score"] == b_on["ood_ref"]["distance"]["score"]
        assert new["ood_gravity_on"]["99"]["gp_variance"]["score"] == b_on["ood_ref"]["gp_variance"]["score"]
        for pct, fired in b_on["ood_fired_by_pct"].items():
            assert new["ood_gravity_on"][pct]["fired"] == fired
        assert round(new["materiality_gravity_on"], 4) == b_on["physmap"]["materiality"]


def test_matches_the_committed_bank(record):
    cmp = compare_records(record, st.load_banked())
    assert cmp.matches, cmp.drift[:5]


# ── the command ──────────────────────────────────────────────────────────────

def test_the_command_lists_and_refuses_unknown_ids(capsys):
    assert cli.main(["stress-test", "--list"]) == 0
    assert "lewis-reuse" in capsys.readouterr().out
    assert cli.main(["stress-test", "no-such-test"]) == 2


def test_the_command_end_to_end_without_recomputing(record, monkeypatch, capsys):
    """The command's wiring -- report, assertions, bank comparison, exit code -- using the
    fixture's record rather than a second two-minute run."""
    monkeypatch.setattr(st, "run", lambda: record)
    assert cli.main(["stress-test", "lewis-reuse"]) == 0
    out = capsys.readouterr().out
    assert "Assertions hold" in out
    assert "matches the banked record" in out


def test_the_command_fails_when_an_assertion_fails(record, monkeypatch, capsys):
    broken = copy.deepcopy(record)
    broken["headline_design_M"]["ood"]["identical_between_gravity_states"] = False
    monkeypatch.setattr(st, "run", lambda: broken)
    assert cli.main(["stress-test", "lewis-reuse"]) == 1
    assert "ASSERTIONS FAILED" in capsys.readouterr().out


def test_the_stress_test_is_not_a_benchmark_action():
    """No conflation: a materiality result must never appear under the observability
    benchmark's command."""
    p = cli.build_parser()
    top = p._subparsers._group_actions[0].choices
    assert "stress-test" in top
    bench_actions = top["benchmark"]._subparsers._group_actions[0].choices
    assert not any("stress" in a or "lewis" in a for a in bench_actions)
