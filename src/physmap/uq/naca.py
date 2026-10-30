"""Q1 -- the coverage figure on NACA TN-1451: a statistical interval that cannot see x/D.

A (Re, Pr) -> Nu emulator is given a split-conformal interval at a nominal 90 %, calibrated on
fully developed points (x/D >= 10). x/D is not an emulator input, so every entrance point is
in-distribution to the interval and to any input-based detector. The interval's coverage is
then counted on fully developed test points and on the 45 entrance points, per Reynolds curve,
beside PhysMAP's W-SURR-05 flags from the same guardrail setup as examples/naca_entrance_region.py.

THE DATA DECIDES THE METHOD
The 40 fully developed points are 5 Reynolds curves of 8 reads each, and within a curve all 8
reads are the same number (the digitised asymptote). A data-trained interval therefore has 5
exchangeable units, and a 90 % split-conformal interval needs at least 9: it is unbounded.
Point-level splitting only hides this -- the "held-out" points are copies of training points.
That is the first kill criterion of this work, and it fires, so the figure uses the fallback it
names: the Gnielinski correlation as the emulator (nothing is fitted) with the digitisation's
declared noise model as synthetic replicates. Both attempts are recorded in the data tables.

The noise model is the CSV's own: 3 % paper reproducibility and a 5 % digitisation floor,
combined in quadrature. A replicate is Nu_read * (1 + s z), z standard normal. Calibration
replicates and test replicates use different seeds. Entrance points are scored as read.
"""

from __future__ import annotations

import csv
import math

import numpy as np

from physmap._paths import checkout_path
from physmap.uq.conformal import (
    binomial_band,
    conformal_half_width,
    conformal_index,
    covered,
    finite_interval_possible,
    min_calibration_size,
    relative_scores,
)

NOMINAL = 0.90
ALPHA = 1.0 - NOMINAL
FULLY_DEVELOPED = 10.0          # the closure's validated range starts here (x/D)
COORDS = ("Re", "Pr", "x_over_D")
CLOSURE_ID = "gnielinski-1976"
SEED_CALIBRATION = 1
SEED_TEST = 2
DATA = ("data", "naca", "cross_validated_fig10.csv")


def load_rows() -> list[dict]:
    path = checkout_path(*DATA, what="the NACA TN-1451 Fig 10 digitisation")
    with path.open() as fh:
        reader = csv.DictReader(line for line in fh if not line.lstrip().startswith("#"))
        rows = []
        for r in reader:
            rows.append({k: (_num(v) if _is_num(v) else v) for k, v in r.items()})
    return rows


def _is_num(v) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _num(v) -> float:
    return float(v)


def _curves(rows: list[dict]) -> list[float]:
    return sorted({r["Re"] for r in rows}, reverse=True)


# ── PhysMAP's flags, the example's own setup ─────────────────────────────────

def physmap_flags(train: list[dict], test: list[dict]) -> list[dict]:
    """W-SURR-05 on every entrance point, with the two input-based detectors beside it.
    Exactly examples/naca_entrance_region.py's guardrail: the surrogate sees Re and Pr only."""
    from physmap.guardrail import ColumnMap, CredibilityGuardrail, DetectorKind, Regime

    cols = list(COORDS)
    Xtr = np.array([[r[c] for c in cols] for r in train])
    ytr = np.array([r["Nu_meas"] for r in train])
    Xte = np.array([[r[c] for c in cols] for r in test])
    guard = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    guard.fit(Xtr, train_y=ytr, columns=ColumnMap(inputs=cols))
    out = []
    for a in guard.assess(Xte, columns=ColumnMap(inputs=cols)):
        out.append({
            "closure_validity_fired": bool(a.signals[DetectorKind.CLOSURE_VALIDITY].fired),
            "novelty_density_fired": bool(a.signals[DetectorKind.NOVELTY_DENSITY].fired),
            "gp_variance_fired": bool(a.signals[DetectorKind.GP_VARIANCE].fired),
            "verdict": a.verdict.name,
        })
    return out


# ── attempt A: a data-trained interval ───────────────────────────────────────

def data_trained_attempt(train: list[dict]) -> list[dict]:
    """What a surrogate fitted to the 40 fully developed reads can calibrate. Recorded, not used."""
    curves = _curves(train)
    per_curve = []
    for Re in curves:
        nus = [r["Nu_meas"] for r in train if r["Re"] == Re]
        per_curve.append({"Re": Re, "n_fully_developed": len(nus),
                          "n_distinct_values": len(set(nus))})
    n_units = len(curves)
    need = min_calibration_size(ALPHA)
    rows = [{
        "method": "split conformal, one unit per Reynolds curve",
        "calibration_units": n_units,
        "order_statistic_k": conformal_index(n_units, ALPHA),
        "finite_interval": finite_interval_possible(n_units, ALPHA),
        "half_width": math.inf,
        "note": (f"each curve's 8 fully developed reads are one value; {n_units} exchangeable "
                 f"units, a finite 90 % interval needs {need}"),
    }]
    # point-level split: odd x/D to the fit, even x/D to calibration, a log-log power law.
    fit = [r for r in train if int(r["x_over_D"]) % 2 == 1]
    cal = [r for r in train if int(r["x_over_D"]) % 2 == 0]
    A = np.column_stack([np.ones(len(fit)), np.log([r["Re"] for r in fit])])
    coef, *_ = np.linalg.lstsq(A, np.log([r["Nu_meas"] for r in fit]), rcond=None)
    pred = np.exp(coef[0] + coef[1] * np.log([r["Re"] for r in cal]))
    scores = relative_scores(pred, [r["Nu_meas"] for r in cal])
    rows.append({
        "method": "split conformal, one unit per read (power law Nu = a Re^b on odd x/D)",
        "calibration_units": len(cal),
        "order_statistic_k": conformal_index(len(cal), ALPHA),
        "finite_interval": finite_interval_possible(len(cal), ALPHA),
        "half_width": conformal_half_width(scores, ALPHA),
        "note": (f"the {len(cal)} calibration scores carry {len(set(np.round(scores, 12)))} "
                 f"distinct values, each the fit residual of its own curve: the held-out reads "
                 f"are copies of training reads and test nothing new"),
    })
    return per_curve, rows


# ── the fallback: Gnielinski as the emulator, synthetic replicates ───────────

def noise_sd(row: dict) -> float:
    """The CSV's declared relative noise: paper and digitisation terms in quadrature."""
    return math.hypot(row["Nu_unc_paper_pct"], row["Nu_unc_digitization_pct"])


def closure_prediction(rows: list[dict]) -> np.ndarray:
    from physmap.closures.registry import get_closure
    gn = get_closure(CLOSURE_ID)
    return np.asarray(gn.fn(Re=np.array([r["Re"] for r in rows]),
                            Pr=np.array([r["Pr"] for r in rows])), dtype=float)


def replicates(rows: list[dict], seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    nu = np.array([r["Nu_meas"] for r in rows])
    sd = np.array([noise_sd(r) for r in rows])
    return nu * (1.0 + sd * rng.standard_normal(len(rows)))


def compute() -> dict:
    """Everything the figure, its tables and the `physmap uq` example need."""
    rows = load_rows()
    train = [r for r in rows if r["x_over_D"] >= FULLY_DEVELOPED]
    test = [r for r in rows if r["x_over_D"] < FULLY_DEVELOPED]
    curves = _curves(rows)
    flags = physmap_flags(train, test)
    per_curve_reads, attempts = data_trained_attempt(train)

    # calibration on synthetic replicates of the fully developed reads
    pred_tr = closure_prediction(train)
    cal = replicates(train, SEED_CALIBRATION)
    half_width = conformal_half_width(relative_scores(pred_tr, cal), ALPHA)

    # test: fresh replicates of the fully developed reads, and the reads themselves
    rep = replicates(train, SEED_TEST)
    fd_rep_cov = covered(pred_tr, rep, half_width)
    fd_raw_cov = covered(pred_tr, [r["Nu_meas"] for r in train], half_width)
    pred_te = closure_prediction(test)
    en_cov = covered(pred_te, [r["Nu_meas"] for r in test], half_width)

    points = []
    for r, p, c, rp, rc in zip(train, pred_tr, fd_raw_cov, rep, fd_rep_cov):
        points.append({**_point(r, p, c), "region": "fully_developed",
                       "test_replicate_Nu": float(rp),
                       "test_replicate_error_pct": 100.0 * (p - rp) / rp,
                       "test_replicate_within": bool(rc),
                       "closure_validity_fired": None, "novelty_density_fired": None,
                       "gp_variance_fired": None})
    for r, p, c, f in zip(test, pred_te, en_cov, flags):
        points.append({**_point(r, p, c), "region": "entrance",
                       "test_replicate_Nu": None, "test_replicate_error_pct": None,
                       "test_replicate_within": None, **{k: f[k] for k in
                       ("closure_validity_fired", "novelty_density_fired", "gp_variance_fired")}})

    counts = []
    for Re in curves:
        fd = [p for p in points if p["Re"] == Re and p["region"] == "fully_developed"]
        en = [p for p in points if p["Re"] == Re and p["region"] == "entrance"]
        counts.append(_count_row(f"Re {Re:g}", Re, fd, en))
    fd_all = [p for p in points if p["region"] == "fully_developed"]
    en_all = [p for p in points if p["region"] == "entrance"]
    counts.append(_count_row("all five curves", None, fd_all, en_all))

    sd = sorted({noise_sd(r) for r in rows})
    return {
        "case": "naca_tn1451", "closure": CLOSURE_ID, "nominal": NOMINAL, "alpha": ALPHA,
        "fully_developed_from": FULLY_DEVELOPED,
        "emulator": "gnielinski-1976, not fitted (the data-trained attempt is recorded and unused)",
        "noise_model": {"paper_pct": rows[0]["Nu_unc_paper_pct"] * 100,
                        "digitisation_pct": rows[0]["Nu_unc_digitization_pct"] * 100,
                        "combined_relative_sd": sd[0] if len(sd) == 1 else sd},
        "seeds": {"calibration": SEED_CALIBRATION, "test": SEED_TEST},
        "n_calibration": len(train),
        "order_statistic_k": conformal_index(len(train), ALPHA),
        "half_width": half_width,
        "attempts": attempts, "reads_per_curve": per_curve_reads,
        "points": points, "counts": counts,
        "flags": {"closure_validity": sum(f["closure_validity_fired"] for f in flags),
                  "novelty_density": sum(f["novelty_density_fired"] for f in flags),
                  "gp_variance": sum(f["gp_variance_fired"] for f in flags),
                  "of": len(test)},
    }


def _point(r: dict, p: float, c: bool) -> dict:
    return {"Re": r["Re"], "Pr": r["Pr"], "x_over_D": r["x_over_D"], "Nu_measured": r["Nu_meas"],
            "emulator_Nu": float(p), "error_pct": 100.0 * (p - r["Nu_meas"]) / r["Nu_meas"],
            "within_interval": bool(c)}


def _count_row(label: str, Re, fd: list[dict], en: list[dict]) -> dict:
    n_fd, n_en = len(fd), len(en)
    rep_cov = sum(p["test_replicate_within"] for p in fd)
    raw_cov = sum(p["within_interval"] for p in fd)
    en_cov = sum(p["within_interval"] for p in en)
    fd_lo, fd_hi = binomial_band(n_fd, NOMINAL)
    en_lo, en_hi = binomial_band(n_en, NOMINAL)
    return {
        "curve": label, "Re": Re,
        "fully_developed_points": n_fd,
        "fully_developed_test_replicates_covered": rep_cov,
        "fully_developed_reads_covered": raw_cov,
        "fully_developed_band_low": fd_lo, "fully_developed_band_high": fd_hi,
        "fully_developed_inside_band": fd_lo <= rep_cov <= fd_hi,
        "entrance_points": n_en,
        "entrance_covered": en_cov,
        "entrance_band_low": en_lo, "entrance_band_high": en_hi,
        "entrance_inside_band": en_lo <= en_cov <= en_hi,
        "entrance_flagged_W_SURR_05": sum(bool(p["closure_validity_fired"]) for p in en),
        "entrance_input_based_fired": sum(bool(p["novelty_density_fired"] or p["gp_variance_fired"])
                                          for p in en),
    }


def uq_terms(record: dict) -> list[dict]:
    """The epistemic terms `physmap uq` takes for this case, one row per point.
    The emulator is the closure itself, so the emulation term is zero by construction."""
    rows = []
    for i, p in enumerate(record["points"]):
        inside = p["region"] == "fully_developed"
        rows.append({"point": f"Re{p['Re']:g}_xD{p['x_over_D']:g}", "Re": p["Re"],
                     "Pr": p["Pr"], "x_over_D": p["x_over_D"],
                     "emulation": 0.0,
                     "closure_status": "inside" if inside else "outside",
                     "validation": record["half_width"] if inside else "",
                     "extrapolation_band": "",
                     "materiality": 0.0})
    return rows


if __name__ == "__main__":
    import json
    rec = compute()
    print(json.dumps({k: v for k, v in rec.items() if k != "points"}, indent=1, default=str))
