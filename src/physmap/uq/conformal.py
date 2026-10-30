"""Split-conformal intervals, and the small-sample arithmetic that decides whether one exists.

Split conformal (Vovk; Lei et al. 2018): with n calibration nonconformity scores and a nominal
miscoverage alpha, the interval half-width is the k-th smallest score, k = ceil((1 - alpha)(n + 1)).
If k > n there is no finite interval at that nominal level -- the honest answer is "unbounded",
not a quantile of too few points. At 90 % that needs at least 9 calibration scores.

Scores here are relative: |prediction - value| / value. A prediction covers a value when that
relative error is at most the half-width.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = [
    "conformal_index",
    "finite_interval_possible",
    "min_calibration_size",
    "conformal_half_width",
    "relative_scores",
    "covered",
    "binomial_band",
]


def conformal_index(n_cal: int, alpha: float) -> int:
    """The 1-based order statistic split conformal takes: ceil((1 - alpha)(n + 1))."""
    return math.ceil((1.0 - alpha) * (n_cal + 1))


def finite_interval_possible(n_cal: int, alpha: float) -> bool:
    return conformal_index(n_cal, alpha) <= n_cal


def min_calibration_size(alpha: float) -> int:
    """The smallest calibration set that gives a finite interval at this nominal level."""
    n = 1
    while not finite_interval_possible(n, alpha):
        n += 1
    return n


def conformal_half_width(scores, alpha: float) -> float:
    """The split-conformal half-width, or math.inf when the calibration set is too small."""
    s = np.sort(np.asarray(scores, dtype=float))
    k = conformal_index(len(s), alpha)
    if k > len(s):
        return math.inf
    return float(s[k - 1])


def relative_scores(prediction, value) -> np.ndarray:
    p, v = np.asarray(prediction, dtype=float), np.asarray(value, dtype=float)
    return np.abs(p - v) / np.abs(v)


def covered(prediction, value, half_width: float) -> np.ndarray:
    """True where the value lies inside prediction * (1 ± half_width), in relative terms."""
    return relative_scores(prediction, value) <= half_width


def binomial_band(n: int, p: float, confidence: float = 0.95) -> tuple[int, int]:
    """The central `confidence` band of Binomial(n, p), as counts (inclusive).

    A coverage count inside it is consistent with the nominal level at this n; a count below it
    is under-coverage that this many points can already show.
    """
    from scipy.stats import binom
    tail = (1.0 - confidence) / 2.0
    lo = int(binom.ppf(tail, n, p))
    hi = int(binom.ppf(1.0 - tail, n, p))
    return lo, hi
