"""Observability score — how recoverable a vehicle's failure-driving variable
is from its surrogate inputs, over the failure region. 0 (orthogonal, NACA-like
— only the literature corpus can see the failure) → 1 (on-axis, Forrest-like —
the failure axis IS an input, so baselines see it and the corpus is redundant).

LOCKED DEFAULT + INTERFACE; MIDDLE SCORES PROVISIONAL
-----------------------------------------------------
The locked default estimator is cross-validated R² of a k-NN regression of the
standardized failure variable on the standardized surrogate inputs, clipped to
[0,1] (`cv_r2_knn`). The estimator is a pluggable strategy; `max_spearman` and
`nmi_kraskov` are cross-checks.

CV-R² conflates "the failure variable IS an input" with "the failure variable
is recoverable in THIS dataset." These coincide at the poles (NACA orthogonal
by design → 0; Forrest Re is an input → 1) but can diverge in the middle, where
the score becomes sampling-dependent. Therefore:

  * `cross_estimator_agreement` checks all three estimators agree on pole
    placement (NACA ≈ 0, Forrest ≡ 1) — agreement is what licenses the lock.
  * `subsampling_stability` resamples the region and flags a score `provisional`
    if it is unstable — a middle vehicle's score is not trusted until it passes.
    Poles pass naturally (orthogonal → stably ~0; degenerate → exactly 1).

The measure is locked in `physmap/results/prereg/observability_v0_1.json`
before any vehicle is classified, so the axis is not tuned to the verdicts it
is later plotted against.
"""

from __future__ import annotations

from dataclasses import dataclass, replace as dc_replace
from typing import Sequence

import numpy as np

from physmap.pipeline.detectors import extract_features_batch
from physmap.pipeline.vehicle_spec import vehicle_spec
from physmap.substrate.engine import build_substrate
from physmap.substrate.vehicle_config import load_named_vehicle


# ── locked parameters (mirror observability_v0_1.json) ──────────────────────

DEFAULT_ESTIMATOR = "cv_r2_knn"
RNG_SEED = 20260605
K_NEIGHBORS = 5
SMALL_N_MIN = 5            # n < this -> no CV, in-sample fallback
CV_MIN_N = 8              # SMALL_N_MIN <= n < this -> LOO; else 5-fold
DEFAULT_STABILITY_TOLERANCE = 0.15   # subsampling std bar for "stable"
POLE_AGREEMENT_TOLERANCE = 0.25      # cross-estimator spread bar at the poles

# A failure-driving variable (a meta key) would appear in the surrogate-input
# space under one of these standardized feature names. If any is an input, the
# failure axis is directly observable → observability ≡ 1 by definition.
_FAILURE_VAR_INPUT_ALIASES: dict[str, tuple[str, ...]] = {
    "Re": ("log10_Re", "Re"),
    "x_over_D": ("x_over_D", "log10_x_over_D"),
    "Dh_um": ("log10_Dh_mm", "Dh_um", "Dh_mm"),
    "Ri": ("Ri", "log10_Ri"),
}


# ── result schemas ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ObservabilityResult:
    score: float                 # in [0, 1] (NaN only for an empty region)
    estimator_name: str
    n_region: int
    degenerate_on_axis: bool     # failure var IS a surrogate input
    raw_statistic: float | None  # pre-clip statistic (None if degenerate)
    notes: str
    provisional: bool = False    # middle-vehicle score not yet stability-confirmed
    stability: dict | None = None

    def as_dict(self) -> dict:
        return {
            "score": self.score, "estimator": self.estimator_name,
            "n_region": self.n_region, "degenerate_on_axis": self.degenerate_on_axis,
            "raw_statistic": self.raw_statistic, "notes": self.notes,
            "provisional": self.provisional, "stability": self.stability,
        }


@dataclass(frozen=True)
class StabilityResult:
    mean: float
    std: float
    spread_p5_p95: float
    n_boot: int
    tolerance: float
    stable: bool
    estimator_name: str
    notes: str = ""

    def as_dict(self) -> dict:
        return {
            "mean": self.mean, "std": self.std, "spread_p5_p95": self.spread_p5_p95,
            "n_boot": self.n_boot, "tolerance": self.tolerance, "stable": self.stable,
            "estimator": self.estimator_name, "notes": self.notes,
        }


# ── estimators (pluggable strategies; cv_r2_knn is the locked default) ───────

def _zscore(M: np.ndarray) -> np.ndarray:
    M = np.asarray(M, dtype=float)
    mu = M.mean(axis=0)
    sd = M.std(axis=0)
    sd = np.where(sd == 0.0, 1.0, sd)
    return (M - mu) / sd


def _est_cv_r2_knn(Y: np.ndarray, X: np.ndarray, rng_seed: int,
                   k_neighbors: int = K_NEIGHBORS) -> tuple[float, str]:
    """Cross-validated R² of k-NN regression: failure var ~ surrogate inputs.

    This is "fraction of the failure variable's variance recoverable from the
    inputs." 0 when inputs carry no info (NACA: x/D varies at fixed Re,Pr →
    negative R² → clipped to 0). Robust at small n via an LOO / in-sample
    ladder.
    """
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.model_selection import KFold, LeaveOneOut, cross_val_score
    from sklearn.metrics import r2_score

    n = len(Y)
    Xs = _zscore(X)
    Ys = _zscore(Y.reshape(-1, 1)).ravel()

    if n < SMALL_N_MIN:
        k = min(k_neighbors, max(1, n - 1))
        model = KNeighborsRegressor(n_neighbors=k)
        model.fit(Xs, Ys)
        r2 = float(r2_score(Ys, model.predict(Xs)))   # optimistic in-sample
        return r2, f"cv_r2_knn:small_n_in_sample(n={n},k={k})"

    if n < CV_MIN_N:
        # LOO: each train fold is all-but-one — no sorted-data fold artifact.
        splitter = LeaveOneOut()
        k = min(k_neighbors, max(1, n - 2))             # train fold has n-1 pts
        note = f"cv_r2_knn:loo(n={n},k={k})"
    else:
        # SHUFFLED 5-fold. Without shuffle, KFold makes contiguous folds, which
        # on Re-sorted rows become extrapolation blocks and wreck R^2 — a fold
        # artifact, not a property of the data. Shuffle (seeded) fixes it.
        splitter = KFold(n_splits=5, shuffle=True, random_state=rng_seed)
        k = min(k_neighbors, max(1, (n - n // 5) - 1))
        note = f"cv_r2_knn:5fold_shuffled(n={n},k={k})"

    model = KNeighborsRegressor(n_neighbors=k)
    scores = cross_val_score(model, Xs, Ys, cv=splitter, scoring="r2")
    return float(np.mean(scores)), note


def _est_max_spearman(Y: np.ndarray, X: np.ndarray, rng_seed: int,
                      k_neighbors: int = K_NEIGHBORS) -> tuple[float, str]:
    """Max |Spearman rho| between the failure var and any single input.
    Cheapest, most robust at tiny n; per-input + monotone-only cross-check."""
    import warnings
    from scipy.stats import ConstantInputWarning, spearmanr
    best = 0.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConstantInputWarning)
        for j in range(X.shape[1]):
            rho, _ = spearmanr(X[:, j], Y)   # NaN if a column is constant
            if not np.isnan(rho):
                best = max(best, abs(float(rho)))
    return best, "max_abs_spearman"


def _est_nmi_kraskov(Y: np.ndarray, X: np.ndarray, rng_seed: int,
                     k_neighbors: int = 3) -> tuple[float, str]:
    """Kraskov k-NN mutual information (per input), mapped to a correlation-
    equivalent on [0,1) via the Gaussian relation rho = sqrt(1 - exp(-2·MI)).
    A nonlinear-dependence cross-check; uses the strongest single input as a
    lower bound on joint recoverability."""
    from sklearn.feature_selection import mutual_info_regression
    n = len(Y)
    mi = mutual_info_regression(
        X, Y, n_neighbors=min(k_neighbors, max(1, n - 1)), random_state=rng_seed,
    )
    mi_max = float(np.max(mi)) if len(mi) else 0.0
    nmi = float(np.sqrt(1.0 - np.exp(-2.0 * max(0.0, mi_max))))
    return nmi, "nmi_kraskov_gaussian_equiv(max_input)"


ESTIMATORS = {
    "cv_r2_knn": _est_cv_r2_knn,
    "max_spearman": _est_max_spearman,
    "nmi_kraskov": _est_nmi_kraskov,
}


# ── core score ───────────────────────────────────────────────────────────────

def observability_score(
    rows: Sequence,
    failure_var: str,
    surrogate_inputs: Sequence[str],
    region_mask: np.ndarray | None = None,
    estimator: str = DEFAULT_ESTIMATOR,
    *,
    rng_seed: int = RNG_SEED,
    k_neighbors: int = K_NEIGHBORS,
) -> ObservabilityResult:
    """Observability of `failure_var` from `surrogate_inputs` over the region.

    Order of operations:
      1. Restrict to the region (region_mask, or all rows).
      2. Degenerate check: if the failure variable IS a surrogate input,
         return 1.0 without fitting (Forrest path).
      3. Otherwise run the estimator; clip the raw statistic to [0,1].
    """
    if estimator not in ESTIMATORS:
        raise ValueError(f"unknown estimator {estimator!r}; choices: {sorted(ESTIMATORS)}")

    if region_mask is not None:
        region_mask = np.asarray(region_mask, dtype=bool)
        region_rows = [r for r, m in zip(rows, region_mask) if m]
    else:
        region_rows = list(rows)
    n = len(region_rows)

    # Degenerate (on-axis) check — purely structural, independent of the data.
    aliases = _FAILURE_VAR_INPUT_ALIASES.get(failure_var, (failure_var,))
    inputs = tuple(surrogate_inputs)
    hit = next((a for a in aliases if a in inputs), None)
    if hit is not None:
        return ObservabilityResult(
            score=1.0, estimator_name=estimator, n_region=n,
            degenerate_on_axis=True, raw_statistic=None,
            notes=(f"failure var {failure_var!r} is a surrogate input "
                   f"(as {hit!r}); observability = 1 by definition"),
        )

    if n < 3:
        return ObservabilityResult(
            score=float("nan"), estimator_name=estimator, n_region=n,
            degenerate_on_axis=False, raw_statistic=None,
            notes=f"region too small to estimate (n={n} < 3)",
        )

    Y = np.array([float(r.meta[failure_var]) for r in region_rows], dtype=float)
    if float(np.std(Y)) == 0.0:
        # Failure var constant over the region → nothing to recover; treat as
        # orthogonal (no information gradient for the inputs to track).
        return ObservabilityResult(
            score=0.0, estimator_name=estimator, n_region=n,
            degenerate_on_axis=False, raw_statistic=0.0,
            notes=f"failure var {failure_var!r} constant over region; score=0",
        )

    X = extract_features_batch([r.meta for r in region_rows], list(surrogate_inputs))
    raw, note = ESTIMATORS[estimator](Y, X, rng_seed, k_neighbors)
    score = float(np.clip(raw, 0.0, 1.0))
    return ObservabilityResult(
        score=score, estimator_name=estimator, n_region=n,
        degenerate_on_axis=False, raw_statistic=float(raw), notes=note,
    )


# ── per-vehicle convenience wrapper ──────────────────────────────────────────

def vehicle_observability(
    vehicle_id: str,
    *,
    estimator: str = DEFAULT_ESTIMATOR,
    region: str = "failure",
    csv_override: str | None = None,
    check_stability: bool = False,
    stability_tolerance: float = DEFAULT_STABILITY_TOLERANCE,
    rng_seed: int = RNG_SEED,
) -> ObservabilityResult:
    """Observability of a named vehicle. Uses `vehicle_spec()` so the region is
    the SAME failure region the Stage-1 sweep evaluates (D1/D2 must agree)."""
    cfg = load_named_vehicle(vehicle_id)
    if csv_override is not None:
        from dataclasses import replace as _dc
        cfg = _dc(cfg, data_source=_dc(cfg.data_source, path=csv_override))
    spec = vehicle_spec(cfg)
    rows, _, _ = build_substrate(cfg)

    if region == "failure":
        mask = np.array([spec.split.test_predicate(r.meta) for r in rows], dtype=bool)
    elif region == "all":
        mask = np.ones(len(rows), dtype=bool)
    else:
        raise ValueError(f"region must be 'failure' or 'all', got {region!r}")

    res = observability_score(
        rows, spec.failure_var, spec.baseline_feature_names,
        region_mask=mask, estimator=estimator, rng_seed=rng_seed,
    )

    # Stability gate: non-degenerate vehicles only. Poles pass naturally
    # (orthogonal → stably ~0), so no hardcoded pole-exemption list is needed.
    if check_stability and not res.degenerate_on_axis and res.n_region >= 4:
        region_rows = [r for r, m in zip(rows, mask) if m]
        stab = subsampling_stability(
            region_rows, spec.failure_var, spec.baseline_feature_names,
            estimator=estimator, tolerance=stability_tolerance, rng_seed=rng_seed,
        )
        res = dc_replace(res, provisional=(not stab.stable), stability=stab.as_dict())
    return res


# ── estimator-validity checks (gate whether the axis means anything) ─────────

def subsampling_stability(
    region_rows: Sequence,
    failure_var: str,
    surrogate_inputs: Sequence[str],
    *,
    estimator: str = DEFAULT_ESTIMATOR,
    n_boot: int = 200,
    frac: float = 0.8,
    tolerance: float = DEFAULT_STABILITY_TOLERANCE,
    rng_seed: int = RNG_SEED,
) -> StabilityResult:
    """Resample the failure region (subsample `frac` without replacement) and
    recompute the score `n_boot` times. A score is `stable` if its bootstrap
    std is within `tolerance` — distinguishing physics-observability (stable
    under resampling) from a sampling-design artifact (unstable). This is the
    required gate before a MIDDLE vehicle's score is trusted on the axis."""
    n = len(region_rows)
    if n < 4:
        return StabilityResult(
            mean=float("nan"), std=float("nan"), spread_p5_p95=float("nan"),
            n_boot=0, tolerance=tolerance, stable=False, estimator_name=estimator,
            notes=f"region too small to bootstrap (n={n} < 4)",
        )
    rng = np.random.default_rng(rng_seed)
    size = max(3, int(round(frac * n)))
    scores: list[float] = []
    for b in range(n_boot):
        idx = rng.choice(n, size=size, replace=False)
        sub = [region_rows[i] for i in idx]
        r = observability_score(
            sub, failure_var, surrogate_inputs,
            estimator=estimator, rng_seed=rng_seed + b + 1,
        )
        if not np.isnan(r.score):
            scores.append(r.score)
    arr = np.array(scores, dtype=float)
    std = float(np.std(arr))
    spread = float(np.percentile(arr, 95) - np.percentile(arr, 5))
    return StabilityResult(
        mean=float(np.mean(arr)), std=std, spread_p5_p95=spread,
        n_boot=len(scores), tolerance=tolerance, stable=(std <= tolerance),
        estimator_name=estimator,
        notes=f"subsample frac={frac} without replacement",
    )


def cross_estimator_agreement(
    vehicle_id: str,
    *,
    estimators: Sequence[str] = ("cv_r2_knn", "max_spearman", "nmi_kraskov"),
    region: str = "failure",
    tolerance: float = POLE_AGREEMENT_TOLERANCE,
    csv_override: str | None = None,
) -> dict:
    """Run every estimator on a pole and check they agree on its placement
    (spread within `tolerance`). Agreement at the endpoints is what licenses
    the locked default — if the estimator choice changed the score, it would
    be the estimator, not the physics, doing the work."""
    scores = {
        est: vehicle_observability(
            vehicle_id, estimator=est, region=region, csv_override=csv_override,
        ).score
        for est in estimators
    }
    vals = [v for v in scores.values() if not np.isnan(v)]
    spread = (max(vals) - min(vals)) if vals else float("nan")
    return {
        "vehicle_id": vehicle_id, "region": region, "scores": scores,
        "spread": spread, "tolerance": tolerance,
        "agree": bool(vals and spread <= tolerance),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute a vehicle's observability score (0=orthogonal, 1=on-axis)."
    )
    parser.add_argument("vehicle_id", help="e.g. naca_tn1451, forrest")
    parser.add_argument("--estimator", default=DEFAULT_ESTIMATOR, choices=sorted(ESTIMATORS))
    parser.add_argument("--region", default="failure", choices=["failure", "all"])
    parser.add_argument("--stability", action="store_true",
                        help="run the subsampling-stability gate (sets provisional)")
    parser.add_argument("--agreement", action="store_true",
                        help="report cross-estimator pole-agreement instead")
    parser.add_argument("--csv-override", default=None)
    args = parser.parse_args(argv)

    if args.agreement:
        rep = cross_estimator_agreement(
            args.vehicle_id, region=args.region, csv_override=args.csv_override,
        )
        print(f"cross-estimator agreement for {args.vehicle_id} ({args.region} region):")
        for est, sc in rep["scores"].items():
            print(f"  {est:>14}: {sc:.4f}")
        print(f"  spread={rep['spread']:.4f}  agree={rep['agree']} (tol={rep['tolerance']})")
        return 0

    res = vehicle_observability(
        args.vehicle_id, estimator=args.estimator, region=args.region,
        csv_override=args.csv_override, check_stability=args.stability,
    )
    print(f"vehicle:    {args.vehicle_id}")
    print(f"estimator:  {res.estimator_name}")
    print(f"region n:   {res.n_region}")
    print(f"degenerate: {res.degenerate_on_axis}")
    print(f"raw stat:   {res.raw_statistic}")
    print(f"SCORE:      {res.score:.4f}")
    print(f"provisional:{res.provisional}")
    if res.stability:
        s = res.stability
        print(f"stability:  std={s['std']:.4f} (tol={s['tolerance']}) stable={s['stable']}")
    print(f"notes:      {res.notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
