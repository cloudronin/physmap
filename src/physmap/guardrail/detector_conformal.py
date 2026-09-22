"""Observable-pole conformal statistical mode — the split-conformal residual detector.

Spec: docs/specs/PhysMAP_AxisAdaptive_Guardrail_Unified_Spec_v0_1.md (action #4 — the
observable-pole "competent statistical detector" mode).

At the OBSERVABLE pole the failure driver IS a surrogate input, so a GP emulator fit on
truth sees it and is a sound reference. This detector flags test points where the
SURROGATE's prediction falls OUTSIDE the GP's split-conformal prediction interval — a
DEPLOYABLE credibility signal (it needs the surrogate prediction, NOT the test truth) with
a distribution-free coverage guarantee.

Split conformal (Vovk; Lei et al. 2018):
  * fit a GP emulator (the locked Matérn-5/2 GPVarianceDetector) on a PROPER-train split;
  * on a held-out CALIBRATION split compute the studentized GP residual
        s_i = |y_i - mu(x_i)| / sigma(x_i)
    and take the conformal quantile q = the ceil((n_cal+1)(1-alpha))-th smallest s_i, so
    P(|y - mu(x)| / sigma(x) <= q) >= 1 - alpha for an exchangeable future point;
  * at DEPLOY, FIRE when the surrogate's prediction is outside that interval:
        |pred(x) - mu(x)| / sigma(x) > q.

WHY THIS IS NOT THE FLOORED gp_variance BASELINE (the honest comparison bar — the floor
already beats naive percentile-of-self, so beating naive would be hollow):
  * The floored gp_variance fires on the predictive-variance MAGNITUDE (sigma/|mu| above a
    floored percentile-of-self). It is structurally BLIND to a surrogate that is
    confidently WRONG at a point where the GP variance is LOW (a dense-training region):
    sigma is small there, so it stays quiet.
  * This detector fires on surrogate–GP DISAGREEMENT studentized by sigma, so a confident
    wrong surrogate at low variance lands far outside the (tight) conformal interval and
    FIRES — the failure class the floored gp_variance misses — while the conformal quantile
    is calibrated OUT-OF-SAMPLE (on a held-out split, not the in-sample self-scores that
    degenerate under dense training), so the in-distribution false-alarm rate is ~alpha: a
    coverage guarantee the percentile-of-self + floor heuristic does not provide.

DISCIPLINE: a competent, better-than-NAIVE statistical detector for OBSERVABLE regimes
(table stakes), NOT a moat and NOT aiming to beat a steelman OOD detector. It is OPT-IN
(absent from the default detector set and from the banked benchmark detector tuple), so it
is strictly ADDITIVE — the banked matrix is untouched.
"""
from __future__ import annotations

import numpy as np

from physmap.pipeline.core import DetectorResult
from physmap.pipeline.detectors import GPVarianceDetector

CONFORMAL_NAME = "conformal_residual"
_MIN_PROPER_TRAIN = 2          # the GP emulator needs at least this many proper-train rows
_STD_FLOOR_REL = 1e-6          # relative floor on sigma, applied identically to calib + test


class ConformalResidualDetector:
    """Split-conformal studentized-residual detector over the locked GP emulator.

    Calibration uses train TRUTH (the GP residual on a held-out split); the deploy-time
    FIRE condition uses the surrogate PREDICTION (no test truth) — so it is deployable.
    """

    def __init__(
        self,
        train_X: np.ndarray,
        train_y: np.ndarray,
        *,
        alpha: float = 0.1,
        calib_frac: float = 0.3,
        random_state: int = 20260605,
    ) -> None:
        train_X = np.asarray(train_X, dtype=float)
        train_y = np.asarray(train_y, dtype=float).ravel()
        n = train_X.shape[0]
        if n < _MIN_PROPER_TRAIN + 1:
            raise ValueError(
                f"conformal_residual needs >= {_MIN_PROPER_TRAIN + 1} train rows to split "
                f"into proper-train + calibration; got {n}.")
        self.alpha = float(alpha)
        self.calib_frac = float(calib_frac)

        rng = np.random.default_rng(random_state)
        perm = rng.permutation(n)
        n_cal = int(round(self.calib_frac * n))
        n_cal = min(max(n_cal, 1), n - _MIN_PROPER_TRAIN)   # keep >= _MIN_PROPER_TRAIN proper
        cal_idx, prop_idx = perm[:n_cal], perm[n_cal:]

        # Emulator on the PROPER-train split only (split-conformal exchangeability).
        self._gp = GPVarianceDetector(
            train_X[prop_idx], train_y[prop_idx], random_state=random_state)
        self._std_floor = max(float(np.abs(train_y).mean()) * _STD_FLOOR_REL, _STD_FLOOR_REL)

        mu, std = self._gp.gp.predict(train_X[cal_idx], return_std=True)
        std = np.maximum(std, self._std_floor)
        nonconf = np.abs(train_y[cal_idx] - mu) / std

        # Split-conformal quantile: the ceil((n_cal+1)(1-alpha))-th smallest calibration score.
        k = int(np.ceil((n_cal + 1) * (1.0 - self.alpha)))
        k = min(max(k, 1), n_cal)
        self.q = float(np.sort(nonconf)[k - 1])
        self.n_cal = int(n_cal)
        self.n_proper = int(len(prop_idx))

    def score(self, test_X: np.ndarray, test_pred: np.ndarray):
        """The studentized surrogate–GP residual |pred - mu| / sigma at each test point,
        plus (mu, sigma) for audit. Uses the surrogate prediction; NO test truth."""
        test_X = np.asarray(test_X, dtype=float)
        mu, std = self._gp.gp.predict(test_X, return_std=True)
        std = np.maximum(std, self._std_floor)
        pred = np.asarray(test_pred, dtype=float).ravel()
        return np.abs(pred - mu) / std, mu, std

    def evaluate(self, test_X: np.ndarray, test_pred) -> list[DetectorResult]:
        """One DetectorResult per test row. With no surrogate prediction the detector is
        honestly quiet (its signal is undefined without a prediction to test)."""
        n = np.asarray(test_X, dtype=float).shape[0]
        if test_pred is None:
            return [
                DetectorResult(
                    CONFORMAL_NAME, 0.0, False, self.q,
                    f"{CONFORMAL_NAME}: quiet (no surrogate prediction supplied)", "decision")
                for _ in range(n)
            ]
        scores, _mu, _std = self.score(test_X, test_pred)
        out: list[DetectorResult] = []
        for si in scores:
            si_f = float(si)
            fired = bool(si_f > self.q)   # NaN (missing pred) → False
            rationale = (
                f"{CONFORMAL_NAME}: {'FIRED' if fired else 'quiet'} "
                f"(studentized surrogate–GP residual={si_f:.3g} "
                f"{'>' if fired else '<='} conformal q(α={self.alpha:g})={self.q:.3g})")
            out.append(DetectorResult(CONFORMAL_NAME, si_f, fired, self.q, rationale, "decision"))
        return out
