"""PhysMAP Corpus-Query Runtime Test — four-arm verdict comparison on held-out test points.

Adds a fourth verdict — a corpus-query consult of accumulated closure-vs-truth
observations near a prediction's physics coordinates — to Step 0's three-arm comparison
(guardrails, naive, causal), plus a PDE-residual baseline stand-in. Scored on test points
held out from the corpus build, with a sparse-vs-dense split as the honesty separator.

G-not-just-interpolation is the HEADLINE gate: the sparse region is the deployment surface
for any rare-but-catastrophic framing of the corpus mechanism, so the lift must hold there,
not just in dense regions where the mechanism approaches near-duplicate interpolation.

Run: python -m physmap.infra.corpus_runtime
Torch-free: numpy + scikit-learn + matplotlib. Step 0 artifacts / physics_causal.py /
gate_ledger.json untouched (purely additive).
"""

from __future__ import annotations

import csv
import inspect
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.neighbors import NearestNeighbors

from physmap.infra.blindspot_oracle import (
    EMAX,
    SMAX,
    THETA_MAT,
    TOL,
    T_CAL_E,
    TAU_CAL_S,
    Dataset,
    build_dataset,
)

# The experiment runner that used this is not ported; kept only so module-level
# references resolve.
OUT_DIR = Path(__file__).parent.parent / "results" / "physmap_corpus_runtime"
SCALE = SMAX + EMAX
BOUND = SMAX + EMAX  # saturating ceiling — the only universal physics constraint here

# defaults (all documented in `_scope` and `params`)
K_DEFAULT = 5
THETA_ERR = 0.05         # same normalized scale as TOL — symmetric, not tuned
TRAIN_FRAC = 0.5
SPARSE_PCT = 50          # median split of test points by k-th NN corpus distance
SPLIT_SEED = 0

# robustness sweep bands
K_GRID = [3, 5, 8]
THETA_ERR_GRID = [0.03, 0.05, 0.08]
TOL_GRID = [0.03, 0.05, 0.08]
SPLIT_SEED_GRID = [0, 1]


# ── physics coordinates (transfer-premise stub) ───────────────────────────────

def physics_coords(X: np.ndarray) -> np.ndarray:
    """Degenerate here (return X). The slot the cross-geometry version fills:
    map each point to a coordinate the corpus is indexed by."""
    return np.asarray(X, float)


# ── corpus build (train-point truth) ──────────────────────────────────────────

@dataclass
class Entry:
    """One closure-vs-truth observation at a training-point coordinate."""
    coords: np.ndarray       # (2,) [tau, t]
    closure: float           # HI_clo(p)
    truth: float             # HI_true(p) — independent truth at THIS point only
    error: float             # HI_true(p) − HI_clo(p)
    qoi_contrib_s: float     # closure-derived shear materiality fraction
    qoi_contrib_e: float     # closure-derived exposure materiality fraction
    truth_source_weight: float = 1.0   # trivial here (algebraic = equal); slot for real-data


def build_corpus(ds: Dataset, train_idx: np.ndarray) -> list[Entry]:
    total = ds.c_s + ds.c_e
    ms = ds.c_s / total
    me = ds.c_e / total
    return [
        Entry(
            coords=ds.X[i].copy(),
            closure=float(ds.hi_clo[i]),
            truth=float(ds.hi_true[i]),
            error=float(ds.hi_true[i] - ds.hi_clo[i]),
            qoi_contrib_s=float(ms[i]),
            qoi_contrib_e=float(me[i]),
        )
        for i in train_idx
    ]


# ── corpus-query verdict (leak-safe; signature has no truth at test point) ────

def _dedup_corpus_against_test_X(test_X: np.ndarray,
                                  corpus: list[Entry]) -> list[Entry]:
    """Return a copy of `corpus` with any entry whose coords exactly match a
    coord in `test_X` removed.

    This is the substrate-independent leak guard for k-NN error lookups: if a
    test point and a corpus entry share the same coordinate (e.g. because the
    underlying grid has duplicate coords across the train/test split, as
    `build_dataset`'s query_grid does at 3 points on the synthetic substrate),
    the k-NN at distance 0 would read that entry's truth value — effectively
    the test point's own truth, since the truth function is deterministic in
    coords. Excluding such entries before the lookup prevents the leak
    regardless of substrate.

    On the grounded Lance & Smith vehicle (Track D), continuous measurements
    at distinct (X, time) points make this filter a no-op; on the synthetic
    substrate it drops a small number of cross-fold duplicates. The invariant
    is: no distance-0 cross-fold neighbor in the queried corpus.
    """
    if len(corpus) == 0:
        return corpus
    test_coord_set = {tuple(x.tolist()) for x in np.asarray(test_X)}
    return [e for e in corpus
            if tuple(e.coords.tolist()) not in test_coord_set]


def _query_weighted_err(test_X: np.ndarray, corpus: list[Entry],
                         k: int) -> np.ndarray:
    """k-NN weighted-mean |error| at each row of `test_X`, computed against a
    leak-guarded corpus (cross-fold-coord duplicates filtered out via
    `_dedup_corpus_against_test_X`).

    Returns a zero vector when the corpus is empty after dedup (degenerate
    safe-default). Caller is responsible for any downstream thresholding.
    """
    safe_corpus = _dedup_corpus_against_test_X(test_X, corpus)
    if len(safe_corpus) == 0:
        return np.zeros(len(test_X), dtype=float)
    coords = np.stack([e.coords for e in safe_corpus], axis=0)
    weights = np.array([e.truth_source_weight for e in safe_corpus], float)
    errors = np.abs(np.array([e.error for e in safe_corpus], float))
    k_eff = min(k, len(safe_corpus))
    nbrs = NearestNeighbors(n_neighbors=k_eff).fit(physics_coords(coords))
    _, idx = nbrs.kneighbors(physics_coords(test_X))
    w = weights[idx]
    e = errors[idx]
    return (w * e).sum(axis=1) / w.sum(axis=1)


def corpus_verdict(test_X: np.ndarray, test_c_s: np.ndarray, test_c_e: np.ndarray,
                   corpus: list[Entry], k: int = K_DEFAULT, theta_err: float = THETA_ERR,
                   theta_mat: float = THETA_MAT) -> np.ndarray:
    """Untrustworthy iff k nearest corpus entries (by physics_coords) show weighted-mean
    |error| ≥ theta_err AND closure-derived materiality at the test point clears theta_mat.

    Signature deliberately excludes any test-point truth array (G-no-leak). Also
    drops any corpus entry whose coords exactly match a test_X coord before the
    k-NN lookup (substrate-independent leak guard — no distance-0 cross-fold
    neighbor in the queried corpus, regardless of whether the substrate has
    duplicate coords)."""
    if len(corpus) == 0:
        return np.zeros(len(test_X), dtype=bool)
    weighted_err = _query_weighted_err(test_X, corpus, k=k)

    total = np.asarray(test_c_s, float) + np.asarray(test_c_e, float)
    ms_test = np.asarray(test_c_s, float) / total
    me_test = np.asarray(test_c_e, float) / total
    material = (ms_test >= theta_mat) | (me_test >= theta_mat)

    return (weighted_err >= theta_err) & material


def corpus_error_magnitude(test_X: np.ndarray, corpus: list[Entry],
                            k: int = K_DEFAULT) -> np.ndarray:
    """Per-test-row weighted-mean |error| over the k nearest corpus entries by
    physics_coords. The continuous scalar `corpus_verdict` thresholds internally,
    exposed here for use as a magnitude in the ranking formula (PR-3 attach point).

    Signature deliberately excludes any test-point truth array (G-no-leak). Also
    drops any corpus entry whose coords exactly match a test_X coord before the
    k-NN lookup (substrate-independent leak guard). The materiality gate that
    `corpus_verdict` ANDs in is a separate concern; the ranking formula needs
    magnitudes for ALL rows, so this function does NOT short-circuit on it.
    """
    if len(corpus) == 0:
        return np.zeros(len(test_X), dtype=float)
    return _query_weighted_err(test_X, corpus, k=k)


# ── PDE-residual baseline (bound-only stand-in for NVIDIA's PDE guardrail) ────

def pde_residual_flag(hi_sur: np.ndarray, bound: float = BOUND) -> np.ndarray:
    """Flag iff prediction violates the saturating-truth bound [0, bound].
    A real PDE-residual check requires real fields; this is the cheapest stand-in in
    this algebraic world (the overshooting closures route bound violations through the
    surrogate at extrapolation, so this baseline has actual teeth — and is documented
    in `_scope` as the conceptual limit)."""
    a = np.asarray(hi_sur, float)
    return (a > bound) | (a < 0)


# ── train/test split + sparse/dense split + coverage stats ────────────────────

def _bootstrap_ci(diff: np.ndarray, b: int = 2000, seed: int = 0) -> tuple:
    """Verbatim from the monorepo's blindspot_pilot, moved here rather than imported.

    That import was the last edge reaching blindspot_causal and therefore rdflib. The
    body is copied unchanged -- same default b, same seed, same percentiles -- so
    every bootstrap interval this repository produces is bit-identical to the banked
    ones. Do not "clean it up".
    """
    if len(diff) == 0:
        return (None, None)
    rng = np.random.default_rng(seed)
    boots = [float(rng.choice(diff, len(diff), replace=True).mean()) for _ in range(b)]
    return (round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3))


def split_train_test(n: int, train_frac: float = TRAIN_FRAC,
                     seed: int = SPLIT_SEED) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic shuffle-and-cut split of n indices."""
    rng = np.random.default_rng(seed)
    idx = np.arange(n)
    rng.shuffle(idx)
    n_train = int(round(train_frac * n))
    return np.sort(idx[:n_train]), np.sort(idx[n_train:])


def sparse_dense_split(test_X: np.ndarray, corpus: list[Entry], k: int = K_DEFAULT,
                       pct: float = SPARSE_PCT):
    """Per test point: distance to k-th nearest corpus entry. Above pct percentile = sparse.
    Returns (sparse_mask, dense_mask, threshold, kth_distances)."""
    coords = np.stack([e.coords for e in corpus], axis=0)
    k_eff = min(k, len(corpus))
    nbrs = NearestNeighbors(n_neighbors=k_eff).fit(physics_coords(coords))
    dists, _ = nbrs.kneighbors(physics_coords(test_X))
    kth = dists[:, -1]
    threshold = float(np.percentile(kth, pct))
    sparse = kth > threshold
    dense = ~sparse
    return sparse, dense, threshold, kth


def _summary(arr: np.ndarray) -> dict:
    if len(arr) == 0:
        return {k: None for k in ("min", "p10", "p25", "median", "p75", "p90", "max", "mean")}
    return {
        "min": round(float(arr.min()), 4),
        "p10": round(float(np.percentile(arr, 10)), 4),
        "p25": round(float(np.percentile(arr, 25)), 4),
        "median": round(float(np.median(arr)), 4),
        "p75": round(float(np.percentile(arr, 75)), 4),
        "p90": round(float(np.percentile(arr, 90)), 4),
        "max": round(float(arr.max()), 4),
        "mean": round(float(arr.mean()), 4),
    }


def coverage_stats(dists: np.ndarray, sparse_mask: np.ndarray, dense_mask: np.ndarray) -> dict:
    """k-th NN distance distribution for the reader: dense median near zero = near-duplicate
    interpolation (a dense-only win would be definitional); dense median well above the grid
    step = legitimate generalization signal."""
    return {
        "overall": _summary(dists),
        "sparse":  _summary(dists[sparse_mask]),
        "dense":   _summary(dists[dense_mask]),
    }

# ---------------------------------------------------------------------------
# The step-0 fixture experiment path -- compute_runtime, metrics_four_arm,
# gates, robustness_sweep, plotting and the __main__ runner -- is NOT ported.
# It reached blindspot_pilot, which reaches blindspot_causal, which imports
# rdflib, and none of it is used by the benchmark. What remains above is the
# corpus primitive set the substrate actually calls: Entry, build_corpus,
# corpus_verdict, corpus_error_magnitude, pde_residual_flag, split_train_test.
# ---------------------------------------------------------------------------
