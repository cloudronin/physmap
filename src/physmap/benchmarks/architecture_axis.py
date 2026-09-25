"""The architecture axis: does it matter what kind of model the surrogate is?

PhysMAP's detectors read a prediction's inputs and the closure's validity bounds. None of
them looks inside the model, so on a given vehicle they flag the same rows whatever the
surrogate is. What a different model changes is its predictions -- and so which of the
flagged rows are wrong. This module trains three structurally different models on each
vehicle whose YAML sets `architecture_axis: true`, and counts, for each, the wrong
predictions that PhysMAP flags and the input-based detectors do not.

  * gp        -- a Gaussian process (scikit-learn), the reference model type.
  * deeponet  -- a DeepONet: a branch-trunk operator network, written here in PyTorch.
  * gbt       -- gradient-boosted trees: small-data friendly, and nothing like a GP.

Each model is trained on the vehicle's surrogate inputs against the measured truth. These
are NOT the benchmark matrix's surrogates, which are each vehicle's native model (on the
NACA vehicle, the Gnielinski correlation).

Every model must first pass an accuracy gate: its error on training rows it did not see
(leave-one-out for gp and gbt, one seeded 80/20 holdout for deeponet), against the
vehicle's locked gate-1 limits. A model that fails is recorded as NOT_TRAINABLE and left
out of the comparison: a model too inaccurate to deploy says nothing about how its
failures are guarded. So the comparison is per vehicle, and it means something only
where at least two model types pass.

Needs a checkout (the vehicle data) and PyTorch (`pip install "physmap[architectures]"`).
A full run takes about twenty minutes, most of it leave-one-out Gaussian-process fits on
the largest vehicle. `physmap benchmark architectures` runs it and compares the result
with the committed bank, data/benchmarks/v0_4_1/architecture_axis.json.

The numerics -- models, settings, seeds and gate -- are ported unchanged from the
research version this benchmark was developed with.
"""

from __future__ import annotations

import json
import platform
import sys
import tempfile
from pathlib import Path

import numpy as np

from physmap._paths import TorchRequired
from physmap.benchmarks.benchmark_v0_4 import (
    BANK_DIR as _BANK_DIR,
    _DETECTORS,
    OPERATING_PERCENTILES,
    REFERENCE_PCT,
    _write_csv,
    discover_benchmark_vehicles,
)
from physmap.guardrail.configs import ColumnMap
from physmap.guardrail.enums import DetectorKind
from physmap.guardrail.guardrail import CredibilityGuardrail
from physmap.pipeline.detectors import extract_features_batch
from physmap.pipeline.surrogate import Surrogate, ThresholdCalibration
from physmap.pipeline.vehicle_spec import vehicle_spec
from physmap.substrate.engine import build_substrate
from physmap.substrate.vehicle_config import load_named_vehicle

__all__ = [
    "ARCHITECTURES", "TorchRequired", "run_axis", "load_banked_axis", "compare_with_bank",
    "render_axis", "summary_lines", "trainability_gate",
]

_BASELINE_KINDS = (DetectorKind.DISTANCE_TO_TRAINING, DetectorKind.GP_VARIANCE)
_CORPUS_KIND = DetectorKind.CLOSURE_VALIDITY

_BANK_NAME = "architecture_axis.json"

SEED = 20260605

#: Recorded in the bank, so a reader can see exactly what was trained.
SETTINGS = {
    "seed": SEED,
    "gp": "physmap.pipeline.surrogate.Surrogate: scikit-learn Gaussian process, "
          "Matern-5/2 with constant and white-noise terms, 3 optimizer restarts",
    "gbt": {"n_estimators": 200, "max_depth": 2, "learning_rate": 0.05},
    "deeponet": {"branch_and_trunk_hidden": [40, 40], "latent": 32, "activation": "tanh",
                 "optimizer": "Adam", "learning_rate": 1e-3, "epochs": 4000,
                 "dtype": "float32"},
    "gate": "leave-one-out for gp and gbt; one seeded 80/20 holdout for deeponet",
}


def _require_torch() -> None:
    try:
        import torch  # noqa: F401
    except ImportError as e:
        raise TorchRequired() from e


# ── the three model types (a uniform fit -> predict protocol) ──────────────────

def _fit_predict_gp(Xtr, ytr, Xte):
    """The reference model type: a Gaussian process (physmap.pipeline.surrogate.Surrogate)."""
    return Surrogate(training_X=Xtr, training_y=ytr).predict(Xte)


def _fit_predict_gbt(Xtr, ytr, Xte):
    """Gradient-boosted trees: a small-data friendly family, structurally unlike a GP."""
    from sklearn.ensemble import GradientBoostingRegressor
    m = GradientBoostingRegressor(n_estimators=200, max_depth=2, learning_rate=0.05,
                                  random_state=SEED)
    m.fit(Xtr, ytr)
    return m.predict(Xte)


def _fit_predict_deeponet(Xtr, ytr, Xte, *, epochs: int = 4000, seed: int = SEED):
    """A DeepONet (branch-trunk operator network) in PyTorch. The branch encodes the input
    feature vector; the trunk encodes a single, degenerate query coordinate; the prediction
    is their inner product plus a bias -- the DeepONet form. Standardised inputs and output;
    full-batch Adam."""
    import torch

    torch.manual_seed(seed)
    Xtr = np.asarray(Xtr, float); ytr = np.asarray(ytr, float).reshape(-1, 1)
    Xte = np.asarray(Xte, float)
    xmu, xsd = Xtr.mean(0), Xtr.std(0); xsd = np.where(xsd > 0, xsd, 1.0)
    ymu, ysd = float(ytr.mean()), float(ytr.std() or 1.0)
    Xtr_z = torch.tensor((Xtr - xmu) / xsd, dtype=torch.float32)
    ytr_z = torch.tensor((ytr - ymu) / ysd, dtype=torch.float32)
    Xte_z = torch.tensor((Xte - xmu) / xsd, dtype=torch.float32)
    d, p = Xtr.shape[1], 32

    def mlp(n_in):
        return torch.nn.Sequential(
            torch.nn.Linear(n_in, 40), torch.nn.Tanh(),
            torch.nn.Linear(40, 40), torch.nn.Tanh(), torch.nn.Linear(40, p))

    branch, trunk = mlp(d), mlp(1)
    bias = torch.nn.Parameter(torch.zeros(1))
    trunk_in = torch.zeros((1, 1))           # single degenerate query coordinate

    def forward(Xz):
        b = branch(Xz)                       # (n, p)
        t = trunk(trunk_in)                  # (1, p)
        return (b * t).sum(1, keepdim=True) + bias   # DeepONet inner product

    params = list(branch.parameters()) + list(trunk.parameters()) + [bias]
    opt = torch.optim.Adam(params, lr=1e-3)
    lossf = torch.nn.MSELoss()
    for _ in range(epochs):
        opt.zero_grad(); loss = lossf(forward(Xtr_z), ytr_z); loss.backward(); opt.step()
    with torch.no_grad():
        pred_z = forward(Xte_z).numpy().reshape(-1)
    return pred_z * ysd + ymu


ARCHITECTURES = {
    "gp": _fit_predict_gp,
    "deeponet": _fit_predict_deeponet,
    "gbt": _fit_predict_gbt,
}


# ── the accuracy gate (gate 1: error on unseen training rows, at the vehicle's n) ──

def trainability_gate(fit_predict, X, y, calib: ThresholdCalibration, *, loo: bool) -> dict:
    """Leave-one-out for the cheap models; one seeded 80/20 holdout for the DeepONet (n
    refits of a network would be slow). Passes iff the median relative error is within
    the gate-1 median limit AND the 95th percentile within the gate-1 p95 limit, both from
    the locked calibration formulas."""
    n = len(y)
    rel = []
    if loo:
        for i in range(n):
            mask = np.arange(n) != i
            try:
                pred = float(np.atleast_1d(fit_predict(X[mask], y[mask], X[i:i + 1]))[0])
            except Exception as exc:            # untrainable on a fold
                return {"trainable": False, "reason": f"fit error: {type(exc).__name__}",
                        "method": "loo"}
            rel.append(abs(pred - y[i]) / max(abs(y[i]), 1e-9) * 100.0)
    else:
        rng = np.random.default_rng(SEED)
        idx = rng.permutation(n); cut = max(2, int(0.8 * n))
        tr, va = idx[:cut], idx[cut:]
        try:
            pred = np.atleast_1d(fit_predict(X[tr], y[tr], X[va]))
        except Exception as exc:
            return {"trainable": False, "reason": f"fit error: {type(exc).__name__}",
                    "method": "holdout80"}
        rel = [abs(float(pred[j]) - y[va[j]]) / max(abs(y[va[j]]), 1e-9) * 100.0
               for j in range(len(va))]
    rel = np.asarray(rel)
    median, p95 = float(np.median(rel)), float(np.percentile(rel, 95))
    ok = (median <= calib.gate_1_median_fd_holdout_error_pct_max
          and p95 <= calib.gate_1_p95_fd_holdout_error_pct_max)
    return {"trainable": bool(ok), "median_err_pct": round(median, 2),
            "p95_err_pct": round(p95, 2),
            "gate1_median_max": round(calib.gate_1_median_fd_holdout_error_pct_max, 2),
            "gate1_p95_max": round(calib.gate_1_p95_fd_holdout_error_pct_max, 2),
            "method": "loo" if loo else "holdout80"}


# ── per vehicle: the data, and the detector fires (which never see a prediction) ──

def _vehicle_data(bench):
    """Training and deployment rows, as the features the surrogate sees and the truth."""
    cfg = load_named_vehicle(bench.vehicle_id)
    rows, _r, _m = build_substrate(cfg)
    v = vehicle_spec(cfg)
    train = [r for r in rows if v.split.train_predicate(r.meta)]
    test = [r for r in rows if v.split.test_predicate(r.meta)]
    feats = list(v.baseline_feature_names)
    Xtr = extract_features_batch([r.meta for r in train], feats)
    ytr = np.array([r.cfd_truth for r in train], float)
    Xte = extract_features_batch([r.meta for r in test], feats)
    yte = np.array([r.cfd_truth for r in test], float)
    return train, test, Xtr, ytr, Xte, yte


def _vehicle_fires(bench, train, test) -> dict[int, list[tuple[bool, bool]]]:
    """Run the real CredibilityGuardrail and capture, per operating percentile and per
    deployment row, (closure check fired, an input-based detector fired). Neither depends
    on any prediction, so one pass serves every model type."""
    cm = ColumnMap(inputs=list(bench.column_inputs), truth="truth", prediction="prediction")
    fires_by_pct: dict[int, list[tuple[bool, bool]]] = {}
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        _write_csv(train, bench.column_inputs, tdp / "tr.csv")
        _write_csv(test, bench.column_inputs, tdp / "te.csv")
        for pct in OPERATING_PERCENTILES:
            g = CredibilityGuardrail(
                surrogate_inputs=list(bench.surrogate_inputs), regime=bench.regime,
                detectors=_DETECTORS, operating_pct=float(pct))
            g.fit(tdp / "tr.csv", columns=cm)
            A = g.assess(tdp / "te.csv", columns=cm)
            fires_by_pct[pct] = [
                (bool(a.signals[_CORPUS_KIND].fired),
                 any(a.signals[k].fired for k in _BASELINE_KINDS)) for a in A]
    return fires_by_pct


def run_arch_cell(bench, arch_name, fit_predict, shared) -> dict:
    Xtr, ytr, Xte, yte, fires_by_pct = shared
    loo = arch_name != "deeponet"            # leave-one-out for cheap models; holdout for the net
    gate = trainability_gate(fit_predict, Xtr, ytr, bench.calib, loo=loo)
    cell = {"vehicle_id": bench.vehicle_id, "architecture": arch_name, "gate1": gate}
    if not gate["trainable"]:
        cell["outcome"] = "NOT_TRAINABLE"
        return cell
    pred = np.atleast_1d(fit_predict(Xtr, ytr, Xte)).astype(float)
    rel = np.abs(pred - yte) / np.maximum(np.abs(yte), 1e-9) * 100.0
    is_wrong = rel > bench.calib.lift_threshold_pct
    clean_by_pct = {}
    for pct, fires in fires_by_pct.items():
        clean_by_pct[pct] = int(sum(
            1 for (cf, bf), w in zip(fires, is_wrong) if cf and not bf and w))
    cell.update({
        "outcome": "TRAINABLE",
        "gate2_n_wrong_in_deploy": int(is_wrong.sum()), "n_deploy": int(len(yte)),
        "deploy_median_rel_err_pct": round(float(np.median(rel)), 1),
        "clean_lift_max": max(clean_by_pct.values()),
        "clean_lift_by_pct": clean_by_pct,
    })
    return cell


def agreement(cells: list[dict], vehicle_ids: list[str]) -> dict:
    """Per vehicle: which model types passed the gate, and whether every one that did shows
    at least one wrong prediction that only PhysMAP flags."""
    out = {}
    for vid in vehicle_ids:
        vc = [c for c in cells if c["vehicle_id"] == vid and c["outcome"] == "TRAINABLE"]
        out[vid] = {
            "trainable_architectures": [c["architecture"] for c in vc],
            "all_show_corpus_lift": bool(vc) and all(c["clean_lift_max"] > 0 for c in vc),
            "not_trainable": [c["architecture"] for c in cells
                              if c["vehicle_id"] == vid and c["outcome"] == "NOT_TRAINABLE"],
        }
    return out


def _environment() -> dict:
    import scipy
    import sklearn
    import torch

    from physmap.corpus.calibration import active_tier
    return {"python": platform.python_version(), "machine": platform.machine(),
            "numpy": np.__version__, "scipy": scipy.__version__,
            "scikit-learn": sklearn.__version__, "torch": torch.__version__,
            "corpus_tier": active_tier()}


def home_rows(Xtr, ytr) -> dict:
    """How many home rows there are, and how many are distinct. Where rows repeat, leave-one-out
    keeps copies of each held-out row in the fit, and the gate says little."""
    distinct = {tuple(np.round(np.append(x, y), 12)) for x, y in zip(Xtr, ytr)}
    return {"n": int(len(ytr)), "distinct": len(distinct)}


def run_axis(*, write: bool = False) -> dict:
    """Train every model type on every flagged vehicle and gate it. `write=True` replaces
    the committed bank; the CLI never does that -- it compares against the bank instead."""
    _require_torch()
    specs = [s for s in discover_benchmark_vehicles() if s.architecture_axis]
    cells, rows = [], {}
    for bench in specs:
        train, test, Xtr, ytr, Xte, yte = _vehicle_data(bench)
        rows[bench.vehicle_id] = home_rows(Xtr, ytr)
        shared = (Xtr, ytr, Xte, yte, _vehicle_fires(bench, train, test))
        for arch_name, fp in ARCHITECTURES.items():
            cells.append(run_arch_cell(bench, arch_name, fp, shared))
    vids = [s.vehicle_id for s in specs]
    out = {
        "benchmark": "PhysMAP Benchmark v0.4 -- architecture axis",
        "question": ("Per vehicle: do structurally different surrogates, each accurate enough "
                     "to pass the same gate, leave wrong predictions that PhysMAP flags and "
                     "the input-based detectors do not? The detectors never see a "
                     "prediction, so their flags are the same for every model type."),
        "reference_pct": int(REFERENCE_PCT),
        "settings": SETTINGS,
        "vehicles": vids,
        "home_rows": rows,
        "cells": cells,
        "agreement": agreement(cells, vids),
        "environment": _environment(),
    }
    # Percentile keys become strings, exactly as they are in the bank.
    out = json.loads(json.dumps(out))
    if write:
        from physmap._paths import checkout_path
        d = checkout_path(*_BANK_DIR, what="the benchmark bank directory")
        (d / _BANK_NAME).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


# ── the bank and the drift check ───────────────────────────────────────────────

def load_banked_axis() -> dict:
    from physmap._paths import checkout_path
    p = checkout_path(*_BANK_DIR, _BANK_NAME, what="the banked architecture axis")
    return json.loads(p.read_text(encoding="utf-8"))


#: Error percentages are compared to 0.05 percentage points; everything else as the
#: benchmark matrix is (floats to 1e-9 relative, the rest exactly). Outcomes, gate
#: decisions and every count must match exactly. Measured: an x86-64 machine (Python 3.13,
#: scikit-learn 1.8.0) and an arm64 one (Python 3.11, scikit-learn 1.9.1), both torch
#: 2.12.0, produced bit-identical results. The DeepONet trains in float32 for 4000 steps,
#: so the tolerance is a margin for other builds, not an observed drift.
AXIS_ERROR_ABS_TOL = 0.05
AXIS_TOLERANCE_NOTE = "0.05 percentage points for error percentages, 1e-9 relative otherwise"


def axis_tolerance(path: str) -> tuple[float, float]:
    from physmap.benchmarks.compare import DEFAULT_REL_TOL
    if path.endswith("_err_pct"):
        return 0.0, AXIS_ERROR_ABS_TOL
    return DEFAULT_REL_TOL, 0.0


def _comparable(record: dict) -> dict:
    """Everything that is a result. The environment block records where it ran, and is
    expected to differ."""
    return {k: record[k] for k in ("reference_pct", "settings", "vehicles", "home_rows",
                                   "cells", "agreement")}


def compare_with_bank(fresh: dict):
    from physmap.benchmarks.compare import compare_records
    return compare_records(_comparable(fresh), _comparable(load_banked_axis()),
                           tolerance=axis_tolerance, tolerance_note=AXIS_TOLERANCE_NOTE)


# ── rendering ──────────────────────────────────────────────────────────────────

def _cell(record: dict, vid: str, arch: str) -> dict | None:
    return next((c for c in record["cells"]
                 if c["vehicle_id"] == vid and c["architecture"] == arch), None)


def _caught(c: dict, ref: str) -> str:
    if c is None:
        return "-"
    if c["outcome"] != "TRAINABLE":
        return "fails gate"
    return f"{c['clean_lift_by_pct'][ref]} of {c['gate2_n_wrong_in_deploy']}"


def summary_lines(record: dict) -> list[str]:
    """The short version, for `physmap benchmark report`."""
    ref = str(record["reference_pct"])
    archs = list(ARCHITECTURES)
    out = [
        "Does the kind of model matter? The architecture axis",
        "  The detectors never look inside the model, so they flag the same rows for any",
        "  surrogate. Three model types are trained on each vehicle below; each must first",
        "  pass the same accuracy gate. Count: wrong predictions that only PhysMAP flags, at",
        f"  percentile {ref}, per model type.",
        "",
        "  " + f"{'vehicle':32}" + "".join(f"{a:14}" for a in archs),
    ]
    for vid in record["vehicles"]:
        out.append("  " + f"{vid:32}" + "".join(
            f"{_caught(_cell(record, vid, a), ref):14}" for a in archs))
    testable = [v for v, a in record["agreement"].items()
                if len(a["trainable_architectures"]) >= 2]
    out.append("")
    out.append(f"  Two or more model types pass the gate on {len(testable)} of "
               f"{len(record['vehicles'])} vehicles: {', '.join(testable) or 'none'}.")
    for vid, hr in record.get("home_rows", {}).items():
        if hr["distinct"] < hr["n"]:
            out.append(f"  On {vid} the gate says little: its {hr['n']} home rows hold "
                       f"{hr['distinct']} distinct values, so leave-one-out keeps copies of "
                       "each held-out row.")
    out.append("  `physmap benchmark architectures` recomputes this; it needs PyTorch.")
    return out


def render_axis(record: dict, *, recomputed: bool) -> str:
    """The full table, for `physmap benchmark architectures`."""
    ref = str(record["reference_pct"])
    out = [record["benchmark"], ""]
    if not recomputed:
        out.append("NOTHING WAS RECOMPUTED IN THIS RUN. Every number below is read from the "
                   "banked result.")
        out.append("")
    out.append("Each model is trained on the vehicle's surrogate inputs against the measured")
    out.append("truth, and must first pass the accuracy gate: its error on training rows it")
    out.append("did not see, against the vehicle's locked limits. A model that fails is not")
    out.append("compared -- too inaccurate to deploy, it says nothing about how its failures")
    out.append("are guarded.")
    out.append("")
    hdr = (f"{'vehicle':32}{'model':10}{'gate':7}{'median err':>11}{'limit':>7}"
           f"{'p95 err':>9}{'limit':>7}   {'wrong':11}only PhysMAP flags (pct {ref})")
    out.append(hdr)
    out.append("-" * len(hdr))
    for c in record["cells"]:
        g = c["gate1"]
        med = f"{g['median_err_pct']:.2f}%" if "median_err_pct" in g else "-"
        p95 = f"{g['p95_err_pct']:.2f}%" if "p95_err_pct" in g else "-"
        passed = "pass" if g["trainable"] else "FAIL"
        if c["outcome"] == "TRAINABLE":
            wrong = f"{c['gate2_n_wrong_in_deploy']} of {c['n_deploy']}"
            caught = str(c["clean_lift_by_pct"][ref])
        else:
            wrong, caught = "-", "-"
        out.append(f"{c['vehicle_id']:32}{c['architecture']:10}{passed:7}{med:>11}"
                   f"{g.get('gate1_median_max', '-'):>7}{p95:>9}{g.get('gate1_p95_max', '-'):>7}"
                   f"   {wrong:11}{caught}")
    out.append("")
    for vid, a in record["agreement"].items():
        n = len(a["trainable_architectures"])
        hr = record.get("home_rows", {}).get(vid)
        if hr and hr["distinct"] < hr["n"]:
            out.append(f"  {vid}: its {hr['n']} home rows hold {hr['distinct']} distinct values, "
                       "so leave-one-out keeps copies of each held-out row in the fit -- the "
                       "gate says little here.")
        if n >= 2:
            verdict = ("every one of them leaves wrong predictions that only PhysMAP flags"
                       if a["all_show_corpus_lift"] else
                       "NOT every one leaves wrong predictions that only PhysMAP flags")
            out.append(f"  {vid}: {n} model types pass the gate; {verdict}.")
        else:
            out.append(f"  {vid}: {n} model type(s) pass the gate -- not testable here.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """Maintainer entry point: `python -m physmap.benchmarks.architecture_axis --write`
    recomputes and REPLACES the bank. Users run `physmap benchmark architectures`, which
    only compares."""
    argv = sys.argv[1:] if argv is None else argv
    out = run_axis(write="--write" in argv)
    print(render_axis(out, recomputed=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
