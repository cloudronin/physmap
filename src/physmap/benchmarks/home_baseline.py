"""The home baseline: is each vehicle's surrogate accurate where it is meant to work?

The benchmark counts, per vehicle, the wrong deployment predictions that only PhysMAP
flags. Those counts stand for every vehicle. But they support the reading "deployment
created a failure the input-based detectors could not see" only if the vehicle has a
credible home baseline -- the surrogate was accurate enough where it was fitted, or where
it is claimed valid -- from which deployment produced a distinguishable failure. This
module measures that baseline from the same committed data. It adds fields; it changes
nothing in the banked matrix, and no row is removed.

Two kinds of home error, never mixed:

  * in-sample fit error -- the surrogate was fitted to the home rows (Casper, Marineau,
    Dirker). It flatters the surrogate, so each is also refitted without each home row in
    turn and scored on that row: the held-out home error (leave-one-out).
  * held-out home error -- the surrogate is a published correlation, never fitted to these
    rows (NACA, Jin, Velazquez, Forrest). Whether the rows lie inside the correlation's
    validated range, as the corpus records it, is reported beside it.

A prediction is wrong exactly as in the benchmark: its relative error exceeds the vehicle's
existing lift threshold. No threshold is new. Some home error is expected; what matters is
whether the vehicle has a credible home baseline from which deployment produces a failure
the home rows do not show.

No gate decides that. The counts and rates are the evidence, and each vehicle carries a
written interpretation of them (INTERPRETATION below), reviewed against the exact counts it
was written for: if a recomputation moves a count, a test fails until the prose is reread.
A one-sided Fisher exact test is kept only as exploratory analysis -- it was chosen after
the counts were seen, and it decides nothing.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from physmap.benchmarks.benchmark_v0_4 import (
    _DETECTORS,
    REFERENCE_PCT,
    _write_csv,
    discover_benchmark_vehicles,
)

__all__ = ["SURROGATES", "INTERPRETATION", "compute", "load_banked_home",
           "compare_with_bank", "report_lines"]

_BANK_NAME = "home_baseline.json"

EXPLORATORY_NOTE = ("Exploratory only: a one-sided Fisher exact test of deployment error "
                    "against held-out home error, chosen after the counts were seen. It "
                    "decides nothing.")

#: Evidence-based reading per vehicle -- prose, not a thresholded gate. `{...}` fields are
#: filled from the computed counts; `written_for` records the (wrong, of) counts the prose
#: was reviewed against, and tests/test_home_baseline.py fails if a recomputation moves them.
INTERPRETATION = {
    "casper_hypersonic_transition": {
        "written_for": {"home": (6, 159), "deployment": (8, 8)},
        "text": "Held out, the surrogate is wrong on {home} home rows ({home_rate}); deployed "
                "on the quiet tunnel, on {deployment} ({deployment_rate}). The failure appears "
                "on deployment, and its cause, freestream noise, is not a surrogate input."},
    "dirker_water": {
        "written_for": {"home": (0, 31), "deployment": (11, 60)},
        "text": "Held out, the straight-line surrogate is wrong on {home} low-Richardson home "
                "rows; deployed, on {deployment} ({deployment_rate}). The failures appear as "
                "buoyancy grows, a cause the surrogate's inputs see only partly."},
    "naca_tn1451": {
        "written_for": {"home": (0, 40), "deployment": (9, 45)},
        "text": "Gnielinski is wrong on {home} fully developed home rows and on {deployment} "
                "entrance rows ({deployment_rate}), all near the inlet. The failures appear in "
                "the entrance region, which the correlation does not cover."},
    "jin_sco2_buoyancy": {
        "written_for": {"home": (17, 17), "deployment": (26, 27)},
        "text": "The constant-property correlation is wrong on {home} home rows ({home_rate}) "
                "and {deployment} deployed rows ({deployment_rate}); {inside} home rows lie "
                "inside its validated range. It is wrong almost everywhere in this "
                "near-critical CO2 data, so the counts cannot show that deployment created "
                "the failure."},
    "velazquez_sco2": {
        "written_for": {"home": (386, 393), "deployment": (67, 67)},
        "text": "The constant-property correlation is wrong on {home} home rows ({home_rate}) "
                "and {deployment} deployed rows ({deployment_rate}); only {inside} home rows "
                "lie inside its validated range. It is wrong almost everywhere, so the counts "
                "cannot show that deployment created the failure."},
    "marineau_hypersonic_transition": {
        "written_for": {"home": (5, 9), "deployment": (6, 6)},
        "text": "In-sample the surrogate looks perfect ({in_sample}); held out, it is wrong on "
                "{home} home rows ({home_rate}); deployed, on {deployment}. Nine home rows "
                "cannot separate the two. Its role is the control where the cause is a "
                "surrogate input: the input-based detectors see it, and PhysMAP adds nothing."},
    "forrest": {
        "written_for": {"home": (0, 1), "deployment": (4, 4)},
        "text": "One home row, so there is no home baseline; its values are visual triage "
                "estimates, not benchmark-grade."},
}

#: What each vehicle's surrogate is, read from its loader in physmap.substrate.loaders.
#: `refit` names the loader's own fit function, for the leave-one-out home error.
SURROGATES = {
    "casper_hypersonic_transition": {
        "surrogate": "a Gaussian process on (Mach, unit Reynolds, axial x)",
        "home": "the noisy-tunnel rows, which the Gaussian process is fitted to",
        "refit": "casper"},
    "marineau_hypersonic_transition": {
        "surrogate": "a Gaussian process on (unit Reynolds, nose radius)",
        "home": "the benign-regime rows, which the Gaussian process is fitted to",
        "refit": "marineau"},
    "dirker_water": {
        "surrogate": "a straight-line fit of Nu against log10(Re)",
        "home": "the low-Richardson rows, which the line is fitted to",
        "refit": "dirker"},
    "naca_tn1451": {
        "surrogate": "the Gnielinski correlation (1976)",
        "home": "the fully developed rows (x/D at or above the entrance cut)",
        "refit": None},
    "jin_sco2_buoyancy": {
        "surrogate": "the constant-property Dittus-Boelter correlation",
        "home": "the rows the vehicle's split assigns to training",
        "refit": None},
    "velazquez_sco2": {
        "surrogate": "the constant-property Gnielinski correlation",
        "home": "the rows the vehicle's split assigns to training",
        "refit": None},
    "forrest": {
        "surrogate": "the modified Sparrow-Cur correlation (2014)",
        "home": "the rows the vehicle's split assigns to training",
        "refit": None},
}


# ── leave-one-out refits, through the loaders' own fit functions ──────────────

def _loo_predictions(kind: str, home_rows) -> np.ndarray:
    from physmap.substrate import loaders as L

    if kind == "casper":
        X = np.array([[r.meta["M"], r.meta["Re_per_m_e6"], r.meta["x_m"]] for r in home_rows])
        fit = lambda Xa, ya, Xb: L.casper_gp_fit(Xa, ya)(Xb)              # noqa: E731
    elif kind == "marineau":
        X = np.array([[r.meta["Re_per_m"], r.meta["Rn_mm"]] for r in home_rows])
        fit = lambda Xa, ya, Xb: L.marineau_gp_fit(Xa, ya)(Xb)            # noqa: E731
    elif kind == "dirker":
        X = np.array([[np.log10(r.meta["Re"])] for r in home_rows])
        fit = lambda Xa, ya, Xb: np.polyval(L.dirker_forced_fit(Xa[:, 0], ya), Xb[:, 0])  # noqa: E731
    else:
        raise ValueError(kind)
    y = np.array([r.cfd_truth for r in home_rows], dtype=float)

    # The refit must BE the loader's surrogate: fitted on every home row it reproduces the
    # loader's predictions. If it did not, the held-out error would describe another model.
    full = np.asarray(fit(X, y, X), dtype=float)
    native = np.array([r.surrogate_prediction for r in home_rows], dtype=float)
    if not np.allclose(full, native, rtol=1e-9, atol=0.0):
        raise RuntimeError(f"the {kind} refit does not reproduce the loader's surrogate")

    out = np.empty(len(y))
    for i in range(len(y)):
        keep = np.arange(len(y)) != i
        out[i] = float(np.atleast_1d(fit(X[keep], y[keep], X[i:i + 1]))[0])
    return out


def _n_wrong(pred, truth, threshold_pct: float) -> int:
    pred, truth = np.asarray(pred, float), np.asarray(truth, float)
    rel = np.abs(pred - truth) / np.maximum(np.abs(truth), 1e-9) * 100.0
    return int((rel > threshold_pct).sum())


def _inside_validated_range(bench, home_rows) -> int | None:
    """Home rows on which PhysMAP's own closure check stays quiet -- inside the matched
    closure's validated range as the corpus records it. None when the detectors cannot be
    fitted (fewer than three home rows)."""
    from physmap.guardrail.configs import ColumnMap
    from physmap.guardrail.enums import DetectorKind
    from physmap.guardrail.guardrail import CredibilityGuardrail

    if len(home_rows) < 3:
        return None
    cm = ColumnMap(inputs=list(bench.column_inputs), truth="truth", prediction="prediction")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "home.csv"
        _write_csv(home_rows, bench.column_inputs, p)
        g = CredibilityGuardrail(surrogate_inputs=list(bench.surrogate_inputs),
                                 regime=bench.regime, detectors=_DETECTORS,
                                 operating_pct=REFERENCE_PCT)
        g.fit(p, columns=cm)
        fired = [a.signals[DetectorKind.CLOSURE_VALIDITY].fired for a in g.assess(p, columns=cm)]
    return int(len(fired) - sum(fired))


def _fisher_p(dep_wrong, dep_n, home_wrong, home_n) -> float:
    from scipy.stats import fisher_exact
    _, p = fisher_exact([[dep_wrong, dep_n - dep_wrong], [home_wrong, home_n - home_wrong]],
                        alternative="greater")
    return float(p)


def _pct(k: int, n: int) -> str:
    return f"{round(100 * k / n)}%" if n else "-"


def _counts(block: dict) -> dict:
    """A count block with its rate: wrong rows, rows evaluated, and the fraction wrong."""
    return {**block, "rate": round(block["n_wrong"] / block["n"], 6) if block["n"] else None}


def interpretation(cell: dict) -> str:
    """The vehicle's written reading, filled from its computed counts."""
    h, d, s = cell["home_held_out"], cell["deployment"], cell["home_in_sample"]
    inside = cell["home_inside_validated_range"]
    return INTERPRETATION[cell["vehicle_id"]]["text"].format(
        home=f"{h['n_wrong']} of {h['n']}", home_rate=_pct(h["n_wrong"], h["n"]),
        deployment=f"{d['n_wrong']} of {d['n']}",
        deployment_rate=_pct(d["n_wrong"], d["n"]),
        in_sample="" if s is None else f"{s['n_wrong']} of {s['n']} wrong",
        inside="" if inside is None else f"{inside} of {h['n']}")


def compute(only: set[str] | None = None) -> dict:
    """Every field, recomputed from the committed data. Deployment counts are cross-checked
    against the banked matrix; a mismatch is a calculation error and raises. `only` limits
    it to some vehicles -- for tests; the bank always holds all of them."""
    from physmap.benchmarks.report import load_banked_matrix
    from physmap.pipeline.vehicle_spec import vehicle_spec
    from physmap.substrate.engine import build_substrate
    from physmap.substrate.vehicle_config import load_named_vehicle

    bank = {c["vehicle_id"]: c for c in load_banked_matrix()["cells"]}
    ref = str(int(REFERENCE_PCT))
    cells = []
    for bench in discover_benchmark_vehicles():
        vid = bench.vehicle_id
        if only is not None and vid not in only:
            continue
        info = SURROGATES[vid]
        cfg = load_named_vehicle(vid)
        rows, _r, _m = build_substrate(cfg)
        v = vehicle_spec(cfg)
        home = [r for r in rows if v.split.train_predicate(r.meta)]
        dep = [r for r in rows if v.split.test_predicate(r.meta)]
        thr = float(bench.calib.lift_threshold_pct)
        truth_h = [r.cfd_truth for r in home]

        native_home = _counts({"n": len(home), "n_wrong": _n_wrong(
            [r.surrogate_prediction for r in home], truth_h, thr)})
        if info["refit"]:
            held = _n_wrong(_loo_predictions(info["refit"], home), truth_h, thr)
            held_out = _counts({"n": len(home), "n_wrong": held,
                                "method": "leave-one-out refit"})
            in_sample = native_home
        else:
            held_out = {**native_home,
                        "method": "published correlation, not fitted to these rows"}
            in_sample = None
        deployment = _counts({"n": len(dep), "n_wrong": _n_wrong(
            [r.surrogate_prediction for r in dep], [r.cfd_truth for r in dep], thr)})

        banked = (bank[vid].get("per_pct") or {}).get(ref)
        if banked is not None and (banked["n_test"], banked["n_wrong"]) != (
                deployment["n"], deployment["n_wrong"]):
            raise RuntimeError(f"{vid}: deployment counts {deployment} disagree with the "
                               f"banked matrix ({banked['n_wrong']} of {banked['n_test']})")

        cell = {
            "vehicle_id": vid,
            "surrogate": info["surrogate"],
            "home_definition": info["home"],
            "home_evaluation_provenance": (
                "in-sample fit error; held-out home error by leave-one-out refit"
                if info["refit"] else "held-out home error: published correlation, not "
                                      "fitted to these rows"),
            "threshold_pct": round(thr, 6),
            "home_in_sample": in_sample,
            "home_held_out": held_out,
            "home_inside_validated_range": _inside_validated_range(bench, home),
            "deployment": deployment,
            "deployment_counts_match_bank": banked is not None,
            "exploratory": {
                "fisher_exact_one_sided_p": _fisher_p(deployment["n_wrong"], deployment["n"],
                                                      held_out["n_wrong"], held_out["n"]),
                "note": EXPLORATORY_NOTE},
        }
        cell["interpretation"] = interpretation(cell)
        cells.append(cell)
    from physmap.benchmarks.benchmark_v0_4 import BANK_VERSION
    return {
        "benchmark": f"PhysMAP Benchmark v{BANK_VERSION} -- home baseline",
        "bank_version": BANK_VERSION,
        "derived": ("Derived from the committed vehicle data. Adds fields beside the banked "
                    "matrix and changes none of it; no row is removed."),
        "reading": ("No gate. The counts and rates are the evidence; each vehicle's "
                    "interpretation is written prose, reviewed against the counts it quotes."),
        "reference_pct": int(REFERENCE_PCT),
        "cells": cells,
    }


def load_banked_home() -> dict:
    from physmap._paths import checkout_path
    from physmap.benchmarks.benchmark_v0_4 import BANK_DIR
    return json.loads(checkout_path(*BANK_DIR, _BANK_NAME,
                                    what="the banked home baseline").read_text("utf-8"))


def write_bank(record: dict) -> Path:
    from physmap._paths import checkout_path
    from physmap.benchmarks.benchmark_v0_4 import BANK_DIR
    p = checkout_path(*BANK_DIR, what="the benchmark bank directory") / _BANK_NAME
    p.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return p


def compare_with_bank(fresh: dict):
    from physmap.benchmarks.compare import compare_records
    return compare_records(fresh, load_banked_home())


def report_lines(record: dict) -> list[str]:
    """The section `physmap benchmark report` prints."""
    out = [
        "Home baseline -- is each surrogate accurate where it is meant to work?",
        "  A wrong deployment prediction that only PhysMAP flags shows a failure that",
        "  deployment created only if the surrogate was accurate at home. Wrong means the",
        "  benchmark's own threshold. Every row and every count above stands. No gate",
        "  decides the reading: the counts and rates are the evidence, and each vehicle's",
        "  interpretation is written prose.",
        "",
    ]
    for c in record["cells"]:
        h, d = c["home_held_out"], c["deployment"]
        out.append(f"  {c['vehicle_id']}")
        out.append(f"    surrogate: {c['surrogate']}; home: {c['home_definition']}")
        if c["home_in_sample"] is not None:
            s = c["home_in_sample"]
            out.append(f"    in-sample fit error: {s['n_wrong']} of {s['n']} home rows wrong "
                       f"({_pct(s['n_wrong'], s['n'])})")
            out.append(f"    held-out home error (leave-one-out refit): {h['n_wrong']} of "
                       f"{h['n']} wrong ({_pct(h['n_wrong'], h['n'])})")
        else:
            inside = c["home_inside_validated_range"]
            where = ("" if inside is None else
                     f"; {inside} of {h['n']} inside the correlation's validated range")
            out.append(f"    held-out home error (published correlation, not fitted to these "
                       f"rows): {h['n_wrong']} of {h['n']} wrong ({_pct(h['n_wrong'], h['n'])})"
                       f"{where}")
        out.append(f"    deployment: {d['n_wrong']} of {d['n']} wrong ({_pct(d['n_wrong'], d['n'])}), "
                   f"threshold {c['threshold_pct']:.1f}%")
        out.append(f"    interpretation: {c['interpretation']}")
    out.append("")
    out.append(f"  {EXPLORATORY_NOTE}")
    out.append("    " + "; ".join(
        f"{c['vehicle_id']} p = {c['exploratory']['fisher_exact_one_sided_p']:.2g}"
        for c in record["cells"]))
    return out


def main(argv: list[str] | None = None) -> int:
    """Maintainer entry point: `python -m physmap.benchmarks.home_baseline --write`."""
    import sys
    argv = sys.argv[1:] if argv is None else argv
    rec = compute()
    if "--write" in argv:
        print(f"banked: {write_bank(rec)}")
    print("\n".join(report_lines(rec)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
