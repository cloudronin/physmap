"""PhysMAP D3 — explicit Surrogate class for the real-surrogate protocol.

Per prereg v0.3 (locked 2026-06-05): the surrogate is an explicit
first-class object trained on a defined set, with .predict() and
.predict_variance() methods. The GP-variance baseline is the surrogate's
own posterior std — NOT a separately-fit GP. This removes the E1
ambiguity by making "what the surrogate predicts" a measurable quantity
distinct from baseline detectors.

Locked v0.3 choices:
  - Model class: GP (sklearn GaussianProcessRegressor)
  - Mean function: neutral (constant; normalize_y=True; NOT closure-as-mean)
  - Inputs: (log10_Re, Pr) — surrogate inputs locked in prereg
  - Kernel: one of {matern_5_2, matern_3_2, rbf} — selected per v0.4 screen
  - Training set: fully-developed (x/D >= 10) ONLY; developing never in
    training (per non-negotiable #2)

Surrogate-error categorization (locked v0.3, threshold values deferred
to v0.4 per calibration formulas):
  ACCURATE: error <= accuracy_threshold (do-no-harm cell input)
  MARGINAL: accuracy_threshold < error <= lift_threshold (dead band)
  WRONG:    error > lift_threshold (lift target)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Sequence

import numpy as np

from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import (
    Matern, RBF, ConstantKernel, WhiteKernel,
)


ErrorBucket = Literal["ACCURATE", "MARGINAL", "WRONG"]

KERNEL_MENU_V0_3 = ("matern_5_2", "matern_3_2", "rbf")


def make_kernel(kernel_name: str, n_features: int):
    """Build a sklearn kernel from the v0.3-locked menu."""
    if kernel_name == "matern_5_2":
        inner = Matern(length_scale=[1.0]*n_features,
                        length_scale_bounds=(1e-2, 1e2), nu=2.5)
    elif kernel_name == "matern_3_2":
        inner = Matern(length_scale=[1.0]*n_features,
                        length_scale_bounds=(1e-2, 1e2), nu=1.5)
    elif kernel_name == "rbf":
        inner = RBF(length_scale=[1.0]*n_features,
                    length_scale_bounds=(1e-2, 1e2))
    else:
        raise ValueError(f"Unknown kernel '{kernel_name}'; must be one of "
                          f"{KERNEL_MENU_V0_3}")
    return (
        ConstantKernel(constant_value=1.0, constant_value_bounds=(1e-3, 1e3))
        * inner
        + WhiteKernel(noise_level=1.0, noise_level_bounds=(1e-5, 1e2))
    )


@dataclass
class Surrogate:
    """Explicit surrogate trained on a defined set.

    Per prereg v0.3: the surrogate is a GP with NEUTRAL mean (normalize_y=True
    centers training y; equivalent to a constant prior mean), one of the
    locked kernels, fit on training_X (n_train × n_features) + training_y.

    .predict(test_X) returns the surrogate's prediction (the practitioner's
    deployed prediction). .predict_variance(test_X) returns the surrogate's
    own posterior std — this IS the GP-variance baseline (no separate fit).
    """
    training_X: np.ndarray
    training_y: np.ndarray
    kernel_name: str = "matern_5_2"
    n_restarts: int = 3
    random_state: int = 20260605

    _gp: GaussianProcessRegressor = field(init=False, default=None)
    _n_features: int = field(init=False, default=0)

    def __post_init__(self):
        n, d = self.training_X.shape
        if n < 2:
            raise ValueError(f"Surrogate needs >= 2 training points, got {n}")
        self._n_features = d
        kernel = make_kernel(self.kernel_name, d)
        self._gp = GaussianProcessRegressor(
            kernel=kernel,
            normalize_y=True,        # constant-mean prior via training-y centering
            n_restarts_optimizer=self.n_restarts,
            random_state=self.random_state,
        )
        self._gp.fit(self.training_X, self.training_y)

    @property
    def n_train(self) -> int:
        return len(self.training_y)

    @property
    def fitted_kernel(self):
        return self._gp.kernel_

    def predict(self, test_X: np.ndarray) -> np.ndarray:
        """Surrogate's prediction (posterior mean) at each test point."""
        return self._gp.predict(test_X, return_std=False)

    def predict_variance(self, test_X: np.ndarray) -> np.ndarray:
        """Surrogate's posterior std at each test point.
        This IS the GP-variance baseline (no separate fit per prereg v0.3)."""
        _, std = self._gp.predict(test_X, return_std=True)
        return std

    def predict_relative_variance(self, test_X: np.ndarray) -> np.ndarray:
        """Posterior std divided by surrogate predicted mean magnitude.
        The relative variance is what the GP-variance detector reports."""
        mean, std = self._gp.predict(test_X, return_std=True)
        floor = max(1.0, float(np.abs(self.training_y).mean()) * 0.01)
        return std / np.maximum(np.abs(mean), floor)


# ── surrogate error analysis ────────────────────────────────────────────────

@dataclass
class SurrogateError:
    """Per-test-point surrogate prediction vs measured Nu, with categorization."""
    test_X: np.ndarray
    predicted_Nu: np.ndarray         # surrogate's prediction
    measured_Nu: np.ndarray          # ground truth at test point
    accuracy_threshold_pct: float    # ACCURATE iff |error|/|measured| <= this
    lift_threshold_pct: float        # WRONG iff |error|/|measured| > this

    @property
    def abs_error(self) -> np.ndarray:
        return np.abs(self.predicted_Nu - self.measured_Nu)

    @property
    def rel_error_pct(self) -> np.ndarray:
        return self.abs_error / np.maximum(np.abs(self.measured_Nu), 1e-9) * 100.0

    def bucket(self) -> list[ErrorBucket]:
        """Per-point bucket: ACCURATE / MARGINAL / WRONG."""
        rel_pct = self.rel_error_pct
        buckets: list[ErrorBucket] = []
        for r in rel_pct:
            if r <= self.accuracy_threshold_pct:
                buckets.append("ACCURATE")
            elif r > self.lift_threshold_pct:
                buckets.append("WRONG")
            else:
                buckets.append("MARGINAL")
        return buckets

    def is_accurate(self) -> np.ndarray:
        return self.rel_error_pct <= self.accuracy_threshold_pct

    def is_wrong(self) -> np.ndarray:
        return self.rel_error_pct > self.lift_threshold_pct


# ── threshold calibration (from prereg-locked formulas) ──────────────────────

@dataclass
class ThresholdCalibration:
    """Implements the prereg-locked calibration formulas.

    sigma_combined := sqrt(paper_unc_pct² + dig_unc_pct²) measured from dev
    accuracy_threshold := 2.0 × sigma_combined  (ACCURATE iff <=)
    lift_threshold     := 3.0 × sigma_combined  (WRONG iff >)

    Per user-directed decomposition (2026-06-05):
      paper_uncertainty_pct = 3.0  (NACA TN-1451 line 329 REPRODUCIBILITY,
        explicit text: 'reproducibility of values of fc was found to be
        within 3 percent'). NOT 5%; the 5% is the MAX TOTAL EXPERIMENTAL
        ERROR (different statistic that includes systematic + reading +
        calibration bias on top of reproducibility). For sigma_combined
        we use the per-measurement noise floor (3% reproducibility), which
        is the right object to combine with digitization noise.
      digitization_uncertainty_pct = MEASURED FROM WPD per-marker scatter
        in the asymptotic region (where the true value is ~flat so
        observed scatter is mostly digitization noise + paper-noise).
        Use `dig_unc_from_observed_asymptotic_cv()` for the proper
        quadrature-subtraction with the floor.
      visual-vs-WPD delta: used to VERIFY the dig_unc estimate, NOT to
        re-derive total noise from the figure (that would conflate
        the two sources — the paper already gave us paper_unc).

    v0.4 plugs in WPD-measured dig_unc; v0.4 may NOT change formulas.
    """
    paper_uncertainty_pct: float = 3.0          # NACA TN-1451 reproducibility (line 329)
    digitization_uncertainty_pct: float = 3.0   # WPD typical default; v0.4 sets from data
    wpd_instrument_precision_floor_pct: float = 1.0  # WPD's stated reading precision

    @staticmethod
    def dig_unc_from_observed_asymptotic_cv(
        observed_asymptotic_cv_pct: float,
        paper_unc_pct: float = 3.0,
        wpd_instrument_floor_pct: float = 1.0,
    ) -> tuple[float, str]:
        """Compute dig_unc by quadrature-subtracting paper noise from observed.

        Per user 2026-06-05 directive (prevents imaginary-sqrt crash):
        if the WPD asymptotic CV is ≤ paper_unc, the quadrature subtraction
        sqrt(CV² − paper²) would go imaginary. That's NOT 'negative noise';
        it's 'asymptotic scatter is below the paper-noise resolution floor'.
        In that case, fall back to the WPD instrument's stated reading
        precision (default 1%) as the dig_unc floor.

        Returns (dig_unc_pct, regime_tag) where regime_tag describes
        which branch was taken (informational, not used in calibration).
        """
        if observed_asymptotic_cv_pct > paper_unc_pct:
            # Normal regime: scatter dominated by dig noise above paper floor
            dig_unc = float(np.sqrt(observed_asymptotic_cv_pct ** 2 -
                                     paper_unc_pct ** 2))
            return dig_unc, "above_paper_floor"
        else:
            # Quiet asymptote regime: scatter ≤ paper noise; use WPD instrument floor
            return wpd_instrument_floor_pct, "below_paper_floor_use_instrument_precision"

    @property
    def sigma_combined(self) -> float:
        return float(np.sqrt(self.paper_uncertainty_pct ** 2 +
                              self.digitization_uncertainty_pct ** 2))

    @property
    def accuracy_threshold_pct(self) -> float:
        return 2.0 * self.sigma_combined

    @property
    def lift_threshold_pct(self) -> float:
        return 3.0 * self.sigma_combined

    @property
    def dead_band_pct(self) -> tuple[float, float]:
        return (self.accuracy_threshold_pct, self.lift_threshold_pct)

    # Gate 1 derived thresholds (per locked formulas)
    @property
    def gate_1_median_fd_holdout_error_pct_max(self) -> float:
        return 2.0 * self.sigma_combined

    @property
    def gate_1_p95_fd_holdout_error_pct_max(self) -> float:
        return max(25.0, 3.0 * self.sigma_combined)

    def gate_1_median_gp_relative_std_max(self, train_y: np.ndarray) -> float:
        return 0.5 * float(train_y.std()) / max(float(np.abs(train_y).mean()), 1e-9)
