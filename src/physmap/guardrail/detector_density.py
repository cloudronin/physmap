"""GMM novelty-density detector — the steelman NVIDIA-style density baseline.

New code: the shipped pipeline had distance / GP-variance / ensemble / corpus /
closure-validity, but NO density detector, and the spec's default novelty slot is
GMM density. This fits a sklearn GaussianMixture on the training feature matrix;
the per-point signal is the negative log-likelihood (higher = lower density =
more novel). Two thresholds are calibrated from the TRAIN NLL distribution —
warn_pct and reject_pct — so the guardrail can tier WARN vs REJECT.

sklearn is imported lazily (inside fit) so importing this module stays import-safe
even without the experiment extra (the no-heavy-imports test imports every
submodule). DensityMethod.PCE and Device.CUDA are wired but raise
NotImplementedError — GPU is deferred per the locked scope (workloads are small).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from physmap.guardrail.enums import DensityMethod, Device

RANDOM_STATE = 20260605


@dataclass
class DensityNoveltyDetector:
    """A `.signal(test_X) -> ndarray` detector (the uniform inner interface),
    fitted at construction. Carries two thresholds for WARN/REJECT tiering."""

    train_X: np.ndarray
    components: int = 1
    warn_pct: float = 99.0
    reject_pct: float = 99.9
    method: DensityMethod = DensityMethod.GMM
    device: Device = Device.CPU
    random_state: int = RANDOM_STATE

    _gmm: object = field(init=False, default=None, repr=False)
    warn_threshold: float = field(init=False, default=0.0)
    reject_threshold: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        if self.method is not DensityMethod.GMM:
            raise NotImplementedError(
                f"density method {self.method.value!r} is not implemented; "
                f"only GMM ships now (PCE is deferred)."
            )
        if self.device is Device.CUDA:
            raise NotImplementedError(
                "CUDA density path is not implemented; device is wired but only "
                "CPU is built (workloads are small — GPU is deferred)."
            )
        from sklearn.mixture import GaussianMixture

        X = np.asarray(self.train_X, dtype=float)
        self._gmm = GaussianMixture(
            n_components=self.components,
            covariance_type="full",
            random_state=self.random_state,
        ).fit(X)
        train_nll = -self._gmm.score_samples(X)
        self.warn_threshold = float(np.percentile(train_nll, self.warn_pct))
        self.reject_threshold = float(np.percentile(train_nll, self.reject_pct))

    def signal(self, test_X: np.ndarray) -> np.ndarray:
        """Per-point negative log-likelihood under the fitted GMM.

        Higher = lower density = more novel. Compared against warn/reject
        thresholds (percentiles of the train NLL) by the guardrail.
        """
        X = np.asarray(test_X, dtype=float)
        return -np.asarray(self._gmm.score_samples(X), dtype=float)
