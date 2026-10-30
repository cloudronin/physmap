"""The UQ block: conformal arithmetic, the `physmap uq` propagation, and the two cases.

Q3's acceptance is asserted here on the committed example inputs: on NACA's fully developed
points the box width is the emulation term plus the validation term; entrance points are
UNBOUNDED; on Lewis the box widens by the materiality exactly where the illustrative theta
flags, and nowhere else. The second kill criterion -- a fully developed NACA box wider than the
measured error band by more than the emulation term -- is checked in the same place.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from physmap import cli
from physmap.uq import conformal, pbox

REPO = Path(__file__).resolve().parents[1]
UQ = REPO / "docs" / "uq"
EX = UQ / "examples"


# ── conformal arithmetic ─────────────────────────────────────────────────────

def test_a_90_percent_interval_needs_nine_calibration_scores():
    assert conformal.min_calibration_size(0.10) == 9
    assert not conformal.finite_interval_possible(5, 0.10)
    assert math.isinf(conformal.conformal_half_width([0.1, 0.2, 0.3, 0.4, 0.5], 0.10))


def test_the_half_width_is_the_right_order_statistic():
    scores = [i / 100 for i in range(1, 41)]            # 0.01 .. 0.40
    assert conformal.conformal_index(40, 0.10) == 37
    assert conformal.conformal_half_width(scores, 0.10) == pytest.approx(0.37)


def test_the_binomial_band_brackets_the_nominal_count():
    lo, hi = conformal.binomial_band(40, 0.90)
    assert lo <= 36 <= hi and lo >= 30 and hi <= 40


# ── the propagation, on hand-made inputs ─────────────────────────────────────

def _terms(**kw):
    row = {"emulation": "0.01", "closure_status": "inside", "validation": "0.05",
           "extrapolation_band": "", "materiality": "0"}
    row.update({k: str(v) for k, v in kw.items()})
    return row


def test_box_width_is_the_sum_of_the_term_widths():
    import numpy as np
    y = np.array([9.0, 10.0, 11.0])
    terms = pbox.terms_for_point("p", _terms(), theta=None)
    low, high = pbox.total_interval(terms)
    assert (low, high) == pytest.approx((-0.06, 0.06))
    box = pbox.pbox(y, low, high, [0.5])["0.5"]
    assert box["lower"] == pytest.approx(10 * 0.94) and box["upper"] == pytest.approx(10 * 1.06)


def test_outside_the_validated_range_is_unbounded_unless_a_band_is_declared():
    t = {x.name: x for x in pbox.terms_for_point("p", _terms(closure_status="outside"), None)}
    assert t["model_form_unvalidated"].status == "unbounded" and t["model_form_unvalidated"].unbounded
    t = {x.name: x for x in pbox.terms_for_point(
        "p", _terms(closure_status="outside", extrapolation_band="0.3"), None)}
    assert t["model_form_unvalidated"].status == "declared"
    assert (t["model_form_unvalidated"].low, t["model_form_unvalidated"].high) == (-0.3, 0.3)


def test_materiality_is_gated_by_theta_and_reported_either_way():
    quiet = {x.name: x for x in pbox.terms_for_point("p", _terms(materiality="0.06"), theta=0.10)}
    assert quiet["omitted_mechanism"].status == "not_applied" and "0.06" in quiet["omitted_mechanism"].note
    fired = {x.name: x for x in pbox.terms_for_point("p", _terms(materiality="0.154"), theta=0.10)}
    assert fired["omitted_mechanism"].status == "declared"
    assert fired["omitted_mechanism"].width == pytest.approx(2 * 0.154)
    assert "illustrative" in fired["omitted_mechanism"].note


def test_an_undeclared_term_is_an_error_not_a_zero():
    with pytest.raises(pbox.UQInputError, match="emulation term is not declared"):
        pbox.terms_for_point("p", _terms(emulation=""), None)
    na = {x.name: x for x in pbox.terms_for_point("p", _terms(materiality="none"), None)}
    assert na["omitted_mechanism"].status == "not_assessed"


def test_the_cli_refuses_bad_input_in_one_sentence(tmp_path, capsys):
    s = tmp_path / "s.csv"
    s.write_text("point,Re\na,1\n")
    pr = tmp_path / "p.csv"
    pr.write_text("point,prediction\na,10\n")
    t = tmp_path / "t.csv"
    t.write_text("point,emulation,closure_status,validation,materiality\na,0.1,sideways,0.1,0\n")
    rc = cli.main(["uq", "--samples", str(s), "--predictions", str(pr), "--terms", str(t)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "closure_status" in err and "Traceback" not in err


def test_the_cli_runs_without_a_checkout(tmp_path, monkeypatch, capsys):
    from physmap import _paths
    monkeypatch.setattr(_paths, "repo_root", lambda: None)
    s = tmp_path / "s.csv"
    s.write_text("point,Re,Pr\na,30000,0.71\na,31000,0.71\nb,20000,0.71\n")
    t = tmp_path / "t.csv"
    t.write_text("point,emulation,closure_status,validation,extrapolation_band,materiality\n"
                 "a,0,inside,0.19,,0\nb,0,outside,,,0\n")
    out = tmp_path / "r.json"
    rc = cli.main(["uq", "--samples", str(s), "--predict", "physmap.closures.formulas:gnielinski_nu",
                   "--terms", str(t), "--out", str(out)])
    assert rc == 0
    rep = json.loads(out.read_text())
    a, b = rep["points"]
    assert a["relative_box_width"] == pytest.approx(0.38) and a["n_samples"] == 2
    assert b["total_epistemic"] == "unbounded"
    assert "UNBOUNDED" in capsys.readouterr().out


def test_bare_import_stays_free_of_the_scientific_stack():
    code = ("import sys, physmap, physmap.cli, physmap.uq; "
            "physmap.cli.build_parser(); "
            "print(','.join(m for m in ('numpy', 'scipy', 'sklearn') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == ""


# ── the two cases, against the committed package ─────────────────────────────

@pytest.fixture(scope="module")
def naca():
    import warnings
    from physmap.uq import naca as mod
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", module="sklearn")
        return mod.compute()


def test_naca_kill_criterion_one_fired_and_the_fallback_is_recorded(naca):
    grouped = naca["attempts"][0]
    assert grouped["calibration_units"] == 5 and grouped["finite_interval"] is False
    assert all(c["n_distinct_values"] == 1 and c["n_fully_developed"] == 8
               for c in naca["reads_per_curve"])
    assert naca["emulator"].startswith("gnielinski-1976, not fitted")


def test_naca_fully_developed_coverage_is_inside_the_binomial_band(naca):
    total = naca["counts"][-1]
    assert total["fully_developed_points"] == 40
    assert total["fully_developed_inside_band"] is True
    assert total["entrance_points"] == 45 and total["entrance_flagged_W_SURR_05"] == 45
    assert total["entrance_input_based_fired"] == 0
    for c in naca["counts"][:-1]:
        assert c["fully_developed_points"] == 8 and c["entrance_points"] == 9


def test_naca_q3_acceptance_on_the_committed_example(naca):
    from physmap.uq import figures
    report = json.loads((EX / "naca_report.json").read_text())
    assert figures.acceptance("naca", report, N=naca) == []
    # and the committed terms are the ones this computation gives
    want = figures.naca_examples(naca)["naca_terms.csv"]
    assert (EX / "naca_terms.csv").read_text() == want


def test_lewis_reproduces_the_bank_and_q3_acceptance(tmp_path):
    from physmap.uq import figures, lewis
    L = lewis.compute()
    three = L["materiality_at_three_downstream"]
    assert three[67.55] == pytest.approx(0.111, abs=5e-4)
    assert three[101.69] == pytest.approx(0.154, abs=5e-4)
    assert three[135.84] == pytest.approx(0.195, abs=5e-4)
    assert L["flagged_comparable"] == [67.55, 101.69, 135.84]
    assert L["interval_identical_between_gravity_states"] is True
    assert L["inputs_identical_between_gravity_states"] is True
    assert L["emulation"]["n_units"] == 12 and L["emulation"]["order_statistic_k"] == 12
    assert all(s["control_within_statistical"] for s in L["stations"])
    report = json.loads((EX / "lewis_report.json").read_text())
    assert figures.acceptance("lewis", report, L=L) == []
    assert figures.lewis_tables(L)["uq_2_lewis_stations.csv"] == \
        (UQ / "figures" / "data" / "uq_2_lewis_stations.csv").read_text()


def test_the_committed_uq_package_is_what_the_code_gives(naca):
    from physmap.uq import figures
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = figures.check()
    assert rc == 0, buf.getvalue()
