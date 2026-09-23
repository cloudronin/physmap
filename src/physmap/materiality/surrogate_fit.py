"""Fit a forced-convection surrogate and measure how well it generalises.

This exists because of one number that was never recorded: the residual of the original
study's `Nu_forced(Re)` fit against the gravity-off CFD it was fitted to. Without it, the
coupling between the flag and the surrogate error cannot be bounded -- see
`docs/findings/surrogate-and-truth-provenance.md`.

**The split is by operating condition, never by row.** Fitting on some conditions and
evaluating on others is what turns the residual into a generalisation error rather than a
residual against the very value that also forms the materiality numerator. A random row
split would leak the evaluation conditions into the fit and reproduce the original
problem in a new form.

Nothing here computes a label, a flag or a metric. It fits, predicts, and reports
residuals.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

__all__ = ["FitResult", "fit_power_law", "ResidualReport", "residuals"]


@dataclass(frozen=True)
class FitResult:
    """`Nu = coefficient * Re**exponent`, fitted in log space."""

    coefficient: float
    exponent: float
    n_fitted: int
    fitted_conditions: tuple[float, ...]

    def predict(self, re: float) -> float:
        return self.coefficient * re**self.exponent


@dataclass(frozen=True)
class ResidualReport:
    """Relative residuals on one set of conditions. `None` where the set is empty."""

    label: str
    n: int
    max_abs_rel: float | None = None
    rms_rel: float | None = None
    mean_signed_rel: float | None = None
    per_point: tuple[tuple[float, float], ...] = field(default_factory=tuple)

    def summary(self) -> str:
        if not self.n:
            return f"{self.label}: no conditions"
        return (
            f"{self.label}: n={self.n}  max|rel|={self.max_abs_rel:.4%}  "
            f"rms={self.rms_rel:.4%}  mean signed={self.mean_signed_rel:+.4%}"
        )


def fit_power_law(conditions: dict[float, float]) -> FitResult:
    """Least-squares fit of `Nu = C Re^n` in log space, over {Re: Nu}."""
    if len(conditions) < 2:
        raise ValueError(
            f"a power-law fit needs at least 2 conditions, got {len(conditions)}. "
            f"Fitting fewer would produce a curve with no residual to report, which is "
            f"the situation this module exists to avoid."
        )
    xs = [math.log(re) for re in conditions]
    ys = [math.log(nu) for nu in conditions.values()]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0.0:
        raise ValueError("all conditions share one Re; the exponent is unidentifiable")
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    exponent = sxy / sxx
    coefficient = math.exp(my - exponent * mx)
    return FitResult(coefficient, exponent, n, tuple(sorted(conditions)))


def residuals(fit: FitResult, conditions: dict[float, float], label: str) -> ResidualReport:
    """Relative residuals of `fit` against `conditions`, which may be held out."""
    if not conditions:
        return ResidualReport(label=label, n=0)
    per = tuple(
        (re, (fit.predict(re) - nu) / nu) for re, nu in sorted(conditions.items())
    )
    rels = [r for _, r in per]
    return ResidualReport(
        label=label,
        n=len(rels),
        max_abs_rel=max(abs(r) for r in rels),
        rms_rel=math.sqrt(sum(r * r for r in rels) / len(rels)),
        mean_signed_rel=sum(rels) / len(rels),
        per_point=per,
    )


def fit_and_verify(
    fit_conditions: dict[float, float],
    held_out_conditions: dict[float, float],
) -> tuple[FitResult, ResidualReport, ResidualReport]:
    """Fit on one set of conditions, report residuals on both sets.

    Raises if the two sets share a condition: that is the leak this guards against, and
    it is silent if unchecked -- the held-out residual simply comes back optimistic.
    """
    shared = set(fit_conditions) & set(held_out_conditions)
    if shared:
        raise ValueError(
            f"conditions appear in both the fit and the held-out set: {sorted(shared)}. "
            f"The held-out residual would then be a fitted residual wearing another name."
        )
    fit = fit_power_law(fit_conditions)
    return (
        fit,
        residuals(fit, fit_conditions, "fitted"),
        residuals(fit, held_out_conditions, "held out"),
    )
