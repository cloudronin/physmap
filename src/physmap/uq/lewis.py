"""UQAIS Q2 -- the materiality-interval figure on Lewis (1992) Test 35A.

The headline design M surrogate is a Gaussian process trained on gravity-off CFD (13 runs,
532 rows; see physmap.stress_tests.lewis_reuse). Its emulation-error interval is calibrated
the only honest way the data allows: hold out one whole DOE run, refit on the rest, score the
held-out run; repeat for all 12 DOE runs (the matched run stays in training, as design M
has it). The nonconformity unit is a run, not a row -- rows along one tube are not exchangeable
with each other -- so the 90 % split-conformal half-width is the order statistic of the 12
per-run worst relative errors, k = ceil(0.9 * 13) = 12: the largest of them.

The interval is a function of (Re, Pr, x/D) only. Those columns are identical with gravity off
and on (the bank asserts it), so the interval is identical too; this module asserts that as
well. What opens at the gravity-on stations is PhysMAP's W-SURR-06 term: the materiality from
the matched ablation, applied where it reaches the illustrative theta. theta is not locked.

Refitting twelve Gaussian processes takes minutes, so the held-out scores are banked in
docs/uq/data/ and read from there; `python -m physmap.uq.lewis --recompute` rebuilds them.
"""

from __future__ import annotations

import json
import math
import warnings

import numpy as np

from physmap._paths import checkout_path
from physmap.uq.conformal import conformal_half_width, conformal_index

NOMINAL = 0.90
ALPHA = 1.0 - NOMINAL
ILLUSTRATIVE_THETA = 0.10        # the original study's value; illustrative, not endorsed
HELDOUT_BANK = ("docs", "uq", "data", "uq_2_lewis_emulation_heldout.json")
THREE_DOWNSTREAM = (67.55, 101.69, 135.84)


# ── emulation error from held-out runs ───────────────────────────────────────

def heldout_runs(progress=None) -> dict:
    """Leave-one-DOE-run-out on design M's training set. Slow: twelve GP fits."""
    from physmap.stress_tests import lewis_reuse as st
    inp = st._load_inputs()
    rows = st._training_rows(inp, "M")
    matched = inp["cfd"]["matched_training_run"]["case"]
    runs = sorted({r["run"] for r in rows} - {matched})
    folds = []
    for run in runs:
        held = [r for r in rows if r["run"] == run]
        train = [r for r in rows if r["run"] != run]
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", module="sklearn")   # as lewis_reuse.run does
            pred = st._fit_surrogate(train)(held)
        rel = pred / np.array([r["Nu"] for r in held]) - 1.0
        folds.append({"run": run, "Re": held[0]["Re"], "Pr": held[0]["Pr"],
                      "n_rows": len(held), "x_over_D": [r["x_over_D"] for r in held],
                      "relative_error": [float(e) for e in rel],
                      "worst_abs_relative_error": float(np.max(np.abs(rel)))})
        if progress:
            progress(f"held out {run}: worst |error| {folds[-1]['worst_abs_relative_error']:.3%}")
    return {"design": "M", "training_rows": len(rows), "matched_run_kept_in_training": matched,
            "folds": folds, "surrogate": "physmap.stress_tests.lewis_reuse._fit_surrogate"}


def load_heldout() -> dict:
    return json.loads(checkout_path(*HELDOUT_BANK,
                                    what="the banked held-out emulation scores").read_text())


def emulation_half_width(heldout: dict) -> dict:
    worst = [f["worst_abs_relative_error"] for f in heldout["folds"]]
    rows = [abs(e) for f in heldout["folds"] for e in f["relative_error"]]
    return {"unit": "run", "n_units": len(worst), "order_statistic_k": conformal_index(len(worst), ALPHA),
            "half_width": conformal_half_width(worst, ALPHA),
            "row_level_half_width_for_information": conformal_half_width(rows, ALPHA),
            "n_rows": len(rows)}


# ── the figure's record ──────────────────────────────────────────────────────

def compute(heldout: dict | None = None, theta: float = ILLUSTRATIVE_THETA) -> dict:
    from physmap.stress_tests.lewis_reuse import load_banked
    bank = load_banked()
    heldout = heldout or load_heldout()
    emul = emulation_half_width(heldout)
    q = emul["half_width"]
    stations = []
    for s in bank["headline_design_M"]["stations"]:
        p = s["surrogate_prediction"]
        m = s["materiality_gravity_on"]
        flagged = m >= theta
        # the interval from the gravity-off rows and from the gravity-on rows: same inputs,
        # same prediction, same half-width
        off = (p * (1 - q), p * (1 + q))
        on = (p * (1 - q), p * (1 + q))
        assert off == on
        stations.append({
            "x_over_D": s["x_over_D"], "comparable": s["comparable"], "why_not": s["why_not"],
            "surrogate_prediction": p,
            "control_gravity_off_Nu": s["control_gravity_off_truth"],
            "experiment_Nu": s["experiment_Nu"],
            "control_error_pct": s["control_error_pct"],
            "experimental_error_pct": s["experimental_error_pct"],
            "measurement_relative_to_prediction_pct": 100.0 * (s["experiment_Nu"] / p - 1.0),
            "control_relative_to_prediction_pct": 100.0 * (s["control_gravity_off_truth"] / p - 1.0),
            "statistical_low": off[0], "statistical_high": off[1],
            "statistical_half_width": q,
            "materiality_gravity_off": s["materiality_gravity_off"],
            "materiality_gravity_on": m,
            "materiality_term_at_theta": m if flagged else 0.0,
            "flag_at_illustrative_theta": bool(s["physmap_flag_gravity_on_at_illustrative_theta"]),
            "materiality_low": p * (1 - (m if flagged else 0.0)),
            "materiality_high": p * (1 + (m if flagged else 0.0)),
            "measurement_within_statistical": abs(s["experiment_Nu"] / p - 1.0) <= q,
            "control_within_statistical": abs(s["control_gravity_off_truth"] / p - 1.0) <= q,
        })
    for s in stations:
        assert s["flag_at_illustrative_theta"] == (s["materiality_gravity_on"] >= theta)
    three = {s["x_over_D"]: s["materiality_term_at_theta"] for s in stations
             if s["x_over_D"] in THREE_DOWNSTREAM}
    return {
        "case": "lewis_35A", "design": "M", "nominal": NOMINAL, "alpha": ALPHA,
        "theta_illustrative": theta,
        "emulation": emul, "heldout_folds": heldout["folds"],
        "interval_identical_between_gravity_states": True,
        "inputs_identical_between_gravity_states":
            bank["headline_design_M"]["ood"]["identical_between_gravity_states"],
        "stations": stations,
        "materiality_at_three_downstream": three,
        "flagged_stations": [s["x_over_D"] for s in stations if s["flag_at_illustrative_theta"]],
        "flagged_comparable": [s["x_over_D"] for s in stations
                               if s["flag_at_illustrative_theta"] and s["comparable"]],
    }


def uq_terms(record: dict) -> list[dict]:
    """The epistemic terms `physmap uq` takes for this case, one row per station.
    No closure is involved in the surrogate (a GP), so the closure status is 'inside' with a
    zero validation term declared against the gravity-off CFD control. The bound behind that
    status is of the point kind: every deployment input is exactly a training condition (design
    M), tolerance zero. The mechanism term is the materiality, gated at the illustrative theta
    by the command's --theta."""
    q = record["emulation"]["half_width"]
    return [{"point": f"xD{s['x_over_D']:g}", "x_over_D": s["x_over_D"],
             "comparable": s["comparable"],
             "emulation": q, "closure_status": "inside", "bound_kind": "point", "validation": 0.0,
             "extrapolation_band": "", "materiality": s["materiality_gravity_on"]}
            for s in record["stations"]]


def main(argv=None) -> int:
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser(prog="python -m physmap.uq.lewis")
    ap.add_argument("--recompute", action="store_true",
                    help="refit the twelve held-out GPs and rewrite the banked scores")
    args = ap.parse_args(argv)
    if args.recompute:
        held = heldout_runs(progress=print)
        out = checkout_path("docs", "uq", "data", what="the uq data directory") / HELDOUT_BANK[-1]
        Path(out).write_text(json.dumps(held, indent=1) + "\n")
        print(f"wrote {out}")
    rec = compute()
    print(json.dumps({k: v for k, v in rec.items() if k not in ("stations", "heldout_folds")},
                     indent=1))
    for s in rec["stations"]:
        print(f"x/D {s['x_over_D']:7.2f}  pred {s['surrogate_prediction']:6.3f}  "
              f"meas vs pred {s['measurement_relative_to_prediction_pct']:+6.1f} %  "
              f"stat ±{100 * s['statistical_half_width']:.3f} %  "
              f"materiality {s['materiality_gravity_on']:.3f}  term {s['materiality_term_at_theta']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
