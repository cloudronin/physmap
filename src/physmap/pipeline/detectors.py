"""PhysMAP D3 detectors — baseline + corpus signals for the differentiator test.

Per LOCKED design v0.2 (docs/specs/PhysMAP_D3_Detector_Design_LOCKED_v0_2.md):

  - DistanceDetector:         Mahalanobis k-NN distance to training set (k=3).
  - GPVarianceDetector:       GP with NEUTRAL mean function (constant fit),
                              Matérn-5/2 kernel. Primary variance baseline.
  - EnsembleVarianceDetector: Bootstrapped degree-2 polynomial ensemble.
                              Secondary robustness check on GP.

All baseline detectors accept a configurable feature space:
  Sets A/B (within-Forrest): ["log10_Re", "Pr"]
  Sets C/D (cross-substrate): ["log10_Re", "Pr", "log10_Dh_mm", "alpha_star",
                               "heating_pattern_indicator", "roughness_relative"]

User-locked design choices (v0.2 pushbacks):
  1. Geometry features INCLUDED for Sets C/D distance baseline — steelman.
  2. Within-substrate training only (Forrest benign).
  3. GP mean is NEUTRAL (constant fit) — NOT closure-as-mean. Closure-as-mean
     would re-leak the closure into the baseline; variance would behave oddly
     at sub-critical Re because prior mean (the closure) fails there.
  5. Success criterion: baseline CEILING is primary; corpus floor secondary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel, WhiteKernel
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression



# ── feature-space specifications (locked design v0.2) ───────────────────────

FEATURE_SPACE_FORREST_INTERNAL = ["log10_Re", "Pr"]
FEATURE_SPACE_CROSS_SUBSTRATE = [
    "log10_Re", "Pr", "log10_Dh_mm", "alpha_star",
    "heating_pattern_indicator", "roughness_relative",
]

# Forrest defaults for substrate-internal feature extraction (Mudhafar rows
# always carry their own geometry meta; Forrest rows omit them and get these
# defaults so cross-substrate test sets work uniformly):
FORREST_DEFAULT_DH_MM = 3.79
FORREST_DEFAULT_ALPHA_STAR = 0.035
FORREST_DEFAULT_HEATING_PATTERN = 0.0   # one-sided
FORREST_DEFAULT_ROUGHNESS = 0.0          # smooth


def extract_features(meta: dict, feature_names: Sequence[str]) -> np.ndarray:
    """Extract a feature vector from a substrate row's meta dict.

    For Forrest rows that don't carry geometry meta, fall back to Forrest's
    standard geometry constants. For Mudhafar rows, the meta dict carries
    explicit Dh, alpha_star, etc. For NACA TN-1451 rows, meta carries
    x_over_D explicitly.

    Two separable feature spaces:
      - SURROGATE INPUT SPACE: what the practitioner's surrogate sees.
        e.g. (log10_Re, Pr) for aggregate HE. Used by baseline detectors.
      - PHYSICAL CONTEXT SPACE: full per-row metadata, including coords
        like x_over_D that the surrogate omits but the corpus knows about.
        Used by the validity-range-distance detector.

    The same meta dict carries both; the caller controls which subset gets
    extracted by passing different feature_names lists per detector.
    """
    features = []
    for fname in feature_names:
        if fname == "log10_Re":
            features.append(float(np.log10(meta["Re"])))
        elif fname == "Pr":
            features.append(float(meta["Pr"]))
        elif fname == "log10_Dh_mm":
            features.append(float(np.log10(meta.get("Dh_mm", FORREST_DEFAULT_DH_MM))))
        elif fname == "alpha_star":
            features.append(float(meta.get("alpha_star", FORREST_DEFAULT_ALPHA_STAR)))
        elif fname == "heating_pattern_indicator":
            features.append(float(meta.get("heating_pattern_indicator",
                                            FORREST_DEFAULT_HEATING_PATTERN)))
        elif fname == "roughness_relative":
            features.append(float(meta.get("roughness_relative",
                                            FORREST_DEFAULT_ROUGHNESS)))
        elif fname == "x_over_D":
            features.append(float(meta["x_over_D"]))
        elif fname == "log10_x_over_D":
            features.append(float(np.log10(meta["x_over_D"])))
        elif fname == "Ri":
            # Richardson number (buoyancy failure variable). Hard KeyError if
            # absent (like x_over_D) — a richardson_bands vehicle MUST carry it.
            features.append(float(meta["Ri"]))
        elif fname == "log10_Ri":
            ri = float(meta["Ri"])
            if ri <= 0:
                raise ValueError(f"log10_Ri requires Ri>0, got {ri}")
            features.append(float(np.log10(ri)))
        elif fname == "ratio_mu_w_b":
            features.append(float(meta["ratio_mu_w_b"]))
        elif fname == "Bu":
            # Liu buoyancy parameter (Jin sCO2 vertical-tube failure variable). Raw passthrough
            # (the validity detector compares raw Bu to the corpus max 1.3e-5 directly). Hard KeyError
            # if absent — a buoyancy_parameter_bands vehicle MUST carry it.
            features.append(float(meta["Bu"]))
        # ── aerospace / hypersonic-transition features (Casper, Marineau) ──
        # Raw passthroughs (no log): the Mahalanobis/GP baselines auto-scale via
        # the training covariance, so raw physical units are fine; the validity
        # detector compares raw values to corpus min/max directly.
        elif fname == "M":                     # Mach number (Casper surrogate input)
            features.append(float(meta["M"]))
        elif fname == "Re_per_m_e6":           # unit Reynolds /m, millions (Casper)
            features.append(float(meta["Re_per_m_e6"]))
        elif fname == "x_m":                   # axial position, m (Casper)
            features.append(float(meta["x_m"]))
        elif fname == "freestream_noise_pct":  # tunnel RMS-Pitot % (Casper validity coord)
            features.append(float(meta["freestream_noise_pct"]))
        elif fname == "Re_per_m":              # unit Reynolds /m (Marineau surrogate input)
            features.append(float(meta["Re_per_m"]))
        elif fname == "Rn_mm":                 # nose-tip radius, mm (Marineau surrogate input)
            features.append(float(meta["Rn_mm"]))
        elif fname == "st_xsw_ratio":          # entropy-layer/shock ratio S_T/X_SW (Marineau validity coord)
            features.append(float(meta["st_xsw_ratio"]))
        else:
            raise ValueError(f"Unknown feature: {fname}")
    return np.asarray(features, dtype=float)


# Feature-space specs for the entrance-region (NACA TN-1451) scenario:
#
# v0.3 (CURRENT, per user 2026-06-05 directive): baselines SEE x_over_D.
# This is the test of the simplified vehicle requirement — omitting x/D
# from baselines is the "omission contortion" explicitly forbidden. The
# honest test: does corpus add lift when baselines have access to x/D?
# If yes → corpus encoded literature knowledge baselines couldn't recover
# even with x/D in inputs. If no → differentiator fails (honest null).
FEATURE_SPACE_ENTRANCE_REGION = ["log10_Re", "Pr", "x_over_D"]

# v0.2 (DEPRECATED, retained for diagnostic comparison only): baselines
# omit x/D. The synthetic STRONG result that came out of this framing was
# the omission contortion — it manufactured lift by making baselines
# structurally blind to the failure axis. Do NOT use in real-data D3.
SURROGATE_INPUTS_NACA = ["log10_Re", "Pr"]                 # deprecated v0.2
PHYSICAL_CONTEXT_NACA = ["log10_Re", "Pr", "x_over_D"]     # same as ENTRANCE_REGION above


def extract_features_batch(metas: Sequence[dict],
                            feature_names: Sequence[str]) -> np.ndarray:
    """Stack feature vectors from a list of meta dicts into a (n, d) array."""
    return np.stack([extract_features(m, feature_names) for m in metas], axis=0)


# ── DistanceDetector ─────────────────────────────────────────────────────────

@dataclass
class DistanceDetector:
    """Mahalanobis k-NN distance to training set.

    Signal at a test point = mean Mahalanobis distance to k nearest training
    points (default k=3). Larger signal = farther from training distribution.

    The Mahalanobis metric uses the training-set covariance matrix, so it
    auto-handles per-feature scaling and feature correlations.
    """
    train_X: np.ndarray
    k: int = 3
    cov_regularization: float = 1e-6

    inv_cov: np.ndarray = field(init=False)

    def __post_init__(self):
        n, d = self.train_X.shape
        if n < 2:
            raise ValueError(f"DistanceDetector needs >= 2 training points, got {n}")
        if d == 1:
            var = self.train_X.var(ddof=1)
            self.inv_cov = np.array([[1.0 / max(var, self.cov_regularization)]])
        else:
            cov = np.cov(self.train_X, rowvar=False, ddof=1)
            cov_reg = cov + self.cov_regularization * np.eye(d)
            self.inv_cov = np.linalg.inv(cov_reg)

    def signal(self, test_X: np.ndarray) -> np.ndarray:
        n_test = len(test_X)
        scores = np.zeros(n_test, dtype=float)
        k_eff = min(self.k, len(self.train_X))
        for i, x in enumerate(test_X):
            diffs = self.train_X - x                     # (n_train, d)
            d2 = np.einsum('ij,jk,ik->i', diffs, self.inv_cov, diffs)
            d = np.sqrt(np.clip(d2, 0.0, None))
            d_sorted = np.sort(d)
            scores[i] = d_sorted[:k_eff].mean()
        return scores


# ── GPVarianceDetector ───────────────────────────────────────────────────────

@dataclass
class GPVarianceDetector:
    """GP regression with NEUTRAL mean function (constant), Matérn-5/2 kernel.

    Per locked design v0.2 (3): the mean function is NOT the matched closure.
    Closure-as-mean would re-leak the closure into the baseline — the GP's
    variance would behave oddly at sub-critical Re precisely because its
    prior mean (the closure) fails there. Constant mean keeps the GP
    genuinely closure-blind; variance grows from training-data distance only.

    Signal at a test point = posterior predictive std / posterior mean
    (relative variance). Larger signal = more uncertain prediction.
    """
    train_X: np.ndarray
    train_y: np.ndarray
    n_restarts: int = 3
    random_state: int = 20260605

    gp: GaussianProcessRegressor = field(init=False)

    def __post_init__(self):
        n, d = self.train_X.shape
        # Matérn-5/2 kernel with per-feature length scales, fit by marginal
        # likelihood. ConstantKernel on the front sets the prior signal
        # variance. WhiteKernel models noise; bounds let it be small if the
        # data is clean, larger if noisy.
        kernel = (
            ConstantKernel(constant_value=1.0, constant_value_bounds=(1e-3, 1e3))
            * Matern(
                length_scale=[1.0] * d,
                length_scale_bounds=(1e-2, 1e2),
                nu=2.5,
            )
            + WhiteKernel(noise_level=1.0, noise_level_bounds=(1e-5, 1e2))
        )
        self.gp = GaussianProcessRegressor(
            kernel=kernel,
            normalize_y=True,                # subtract train_y mean → "constant" prior mean
            n_restarts_optimizer=self.n_restarts,
            random_state=self.random_state,
        )
        self.gp.fit(self.train_X, self.train_y)

    def signal(self, test_X: np.ndarray) -> np.ndarray:
        mean, std = self.gp.predict(test_X, return_std=True)
        # Relative variance: std / max(|mean|, small_floor). Floor avoids
        # divide-by-near-zero artifacts when posterior mean is small.
        floor = max(1.0, float(np.abs(self.train_y).mean()) * 0.01)
        return std / np.maximum(np.abs(mean), floor)


# ── EnsembleVarianceDetector ─────────────────────────────────────────────────

@dataclass
class EnsembleVarianceDetector:
    """Bootstrapped polynomial ensemble. Secondary robustness check on GP.

    Closure-blind by construction: just polynomial regression of Nu against
    features, fit on bootstrap resamples of training data. Ensemble disagreement
    at test point = variance signal. Used to cross-check the GP's verdict.
    """
    train_X: np.ndarray
    train_y: np.ndarray
    n_bootstraps: int = 50
    degree: int = 2
    random_state: int = 20260605

    models: list = field(init=False, default_factory=list)
    poly: PolynomialFeatures = field(init=False)

    def __post_init__(self):
        self.poly = PolynomialFeatures(degree=self.degree, include_bias=False)
        train_X_poly = self.poly.fit_transform(self.train_X)
        rng = np.random.default_rng(self.random_state)
        n = len(self.train_y)
        self.models = []
        for _ in range(self.n_bootstraps):
            idx = rng.integers(0, n, size=n)
            model = LinearRegression().fit(train_X_poly[idx], self.train_y[idx])
            self.models.append(model)

    def signal(self, test_X: np.ndarray) -> np.ndarray:
        test_X_poly = self.poly.transform(test_X)
        preds = np.array([m.predict(test_X_poly) for m in self.models])  # (n_boot, n_test)
        means = preds.mean(axis=0)
        stds = preds.std(axis=0, ddof=1)
        floor = max(1.0, float(np.abs(self.train_y).mean()) * 0.01)
        return stds / np.maximum(np.abs(means), floor)


# ── comparison metric (Cohen's d) ────────────────────────────────────────────

def cohens_d(scores_a: np.ndarray, scores_b: np.ndarray) -> float:
    """Cohen's d for two independent samples (a vs b).

    Positive d means scores_a > scores_b on average (the signal fires more
    on set A). Returns nan if either sample has n < 2.
    """
    n_a, n_b = len(scores_a), len(scores_b)
    if n_a < 2 or n_b < 2:
        return float("nan")
    var_a = scores_a.var(ddof=1)
    var_b = scores_b.var(ddof=1)
    pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)
    pooled_std = float(np.sqrt(pooled_var))
    if pooled_std == 0:
        return 0.0
    return float((scores_a.mean() - scores_b.mean()) / pooled_std)
