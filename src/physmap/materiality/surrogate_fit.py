"""Fit a forced-convection surrogate and measure how well it generalises.

This exists because of one number that was never recorded: the residual of the original
study's `Nu_forced(Re)` fit against the gravity-off CFD it was fitted to. Without it the
coupling between the flag and the surrogate error cannot be bounded -- see
`docs/findings/surrogate-and-truth-provenance.md`.

WHY THE INPUT IS A LIST OF CASES, NOT A MAPPING
-----------------------------------------------
An earlier version took `{Re: Nu}`. That is wrong for this grid. A 2-D `(Re, Gr*)` grid
contains **several cases at the same Re with different Gr, heat flux or entrance length**,
and a dict keyed on Re silently keeps the last one written. Cases would vanish without
any error, and the fit would be computed over a set nobody chose.

So ingestion is by `Case`, each with its own id and its full operating conditions.
Duplicate ids raise. Repeated `Re` values are legal and expected.

HOW A REPEATED `Re` IS HANDLED, EXPLICITLY
------------------------------------------
1. **All cases are kept and all are fitted.** Nothing is collapsed or averaged.
2. **A surrogate whose only input is `Re` cannot separate them.** Two cases at one `Re`
   with different `Nu` put a floor under the achievable residual. That floor is computed
   and reported as `irreducible_spread` rather than being discovered later as a mysterious
   fit error.
3. **The split groups by `Re`.** Every case sharing an `Re` goes to the same side. A case
   at `Re = 800` in the fit and another at `Re = 800` held out would leak, because the
   surrogate sees only `Re` and would already have been shown that abscissa.

Nothing here computes a label, a flag or a metric. It fits, predicts, and reports
residuals.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

__all__ = [
    "Case",
    "FitResult",
    "ResidualReport",
    "ingest",
    "fit_power_law",
    "residuals",
    "split_by_re",
    "fit_and_verify",
    "irreducible_spread",
]


@dataclass(frozen=True)
class Case:
    """One operating point. `conditions` carries everything the surrogate does NOT see --
    `Gr`, wall heat flux, `L/D`, `Pr`, flow direction -- so that what was discarded from
    the surrogate's inputs stays visible in the record."""

    case_id: str
    Re: float
    Nu: float
    conditions: Mapping[str, float | str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("every case needs an id; anonymous cases cannot be traced")
        if self.Re <= 0 or self.Nu <= 0:
            raise ValueError(
                f"{self.case_id}: Re and Nu must be positive for a log-space fit "
                f"(got Re={self.Re}, Nu={self.Nu})"
            )


def ingest(cases: Iterable[Case]) -> tuple[Case, ...]:
    """Validate a set of cases. Raises on duplicate ids."""
    out = tuple(cases)
    seen: dict[str, Case] = {}
    for c in out:
        if c.case_id in seen:
            raise ValueError(
                f"duplicate case id {c.case_id!r}. Ids must be unique, or cases are "
                f"silently lost -- which is the failure this ingestion exists to prevent."
            )
        seen[c.case_id] = c
    if not out:
        raise ValueError("no cases")
    return out


def by_re(cases: Sequence[Case]) -> dict[float, list[Case]]:
    groups: dict[float, list[Case]] = defaultdict(list)
    for c in cases:
        groups[c.Re].append(c)
    return dict(groups)


def irreducible_spread(cases: Sequence[Case]) -> dict[float, float]:
    """For each `Re` carrying more than one case, the relative spread in `Nu`.

    A surrogate seeing only `Re` cannot do better than the middle of this spread, so it
    is a floor on the residual and not a defect of the fit.
    """
    out: dict[float, float] = {}
    for re, group in by_re(cases).items():
        if len(group) < 2:
            continue
        nus = [c.Nu for c in group]
        out[re] = (max(nus) - min(nus)) / (sum(nus) / len(nus))
    return out


@dataclass(frozen=True)
class FitResult:
    """`Nu = coefficient * Re**exponent`, fitted in log space over all cases."""

    coefficient: float
    exponent: float
    n_cases: int
    n_distinct_re: int
    fitted_case_ids: tuple[str, ...]
    irreducible_spread: Mapping[float, float] = field(default_factory=dict)

    def predict(self, re: float) -> float:
        return self.coefficient * re**self.exponent


@dataclass(frozen=True)
class ResidualReport:
    label: str
    n: int
    max_abs_rel: float | None = None
    rms_rel: float | None = None
    mean_signed_rel: float | None = None
    per_case: tuple[tuple[str, float, float], ...] = field(default_factory=tuple)

    def summary(self) -> str:
        if not self.n:
            return f"{self.label}: no cases"
        return (
            f"{self.label}: n={self.n}  max|rel|={self.max_abs_rel:.4%}  "
            f"rms={self.rms_rel:.4%}  mean signed={self.mean_signed_rel:+.4%}"
        )


def fit_power_law(cases: Sequence[Case]) -> FitResult:
    """Least-squares fit of `Nu = C Re^n` in log space over every case given.

    Requires at least two DISTINCT `Re` values: many cases at one `Re` determine a
    coefficient but not an exponent.
    """
    cases = ingest(cases)
    groups = by_re(cases)
    if len(groups) < 2:
        raise ValueError(
            f"a power-law fit needs at least 2 distinct Re values, got {len(groups)} "
            f"across {len(cases)} case(s). The exponent is otherwise unidentifiable."
        )
    xs = [math.log(c.Re) for c in cases]
    ys = [math.log(c.Nu) for c in cases]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    exponent = sxy / sxx
    return FitResult(
        coefficient=math.exp(my - exponent * mx),
        exponent=exponent,
        n_cases=n,
        n_distinct_re=len(groups),
        fitted_case_ids=tuple(c.case_id for c in cases),
        irreducible_spread=irreducible_spread(cases),
    )


def residuals(fit: FitResult, cases: Sequence[Case], label: str) -> ResidualReport:
    if not cases:
        return ResidualReport(label=label, n=0)
    per = tuple(
        (c.case_id, c.Re, (fit.predict(c.Re) - c.Nu) / c.Nu)
        for c in sorted(cases, key=lambda q: (q.Re, q.case_id))
    )
    rels = [r for _, _, r in per]
    return ResidualReport(
        label=label,
        n=len(rels),
        max_abs_rel=max(abs(r) for r in rels),
        rms_rel=math.sqrt(sum(r * r for r in rels) / len(rels)),
        mean_signed_rel=sum(rels) / len(rels),
        per_case=per,
    )


def split_by_re(
    cases: Sequence[Case], holdout_re: Iterable[float]
) -> tuple[tuple[Case, ...], tuple[Case, ...]]:
    """Split so that every case sharing an `Re` lands on the same side.

    The surrogate's only input is `Re`, so splitting within an `Re` would show the fit an
    abscissa it is then scored on.
    """
    cases = ingest(cases)
    hold = set(holdout_re)
    unknown = hold - set(by_re(cases))
    if unknown:
        raise ValueError(f"held-out Re values not present in the cases: {sorted(unknown)}")
    fit_side = tuple(c for c in cases if c.Re not in hold)
    held_side = tuple(c for c in cases if c.Re in hold)
    if not fit_side:
        raise ValueError("every Re was held out; nothing left to fit")
    return fit_side, held_side


def fit_and_verify(
    fit_cases: Sequence[Case], held_out_cases: Sequence[Case]
) -> tuple[FitResult, ResidualReport, ResidualReport]:
    """Fit on one set of cases, report residuals on both.

    Raises if any `Re` appears on both sides -- the leak that makes a held-out residual a
    fitted residual under another name, and that is silent when unchecked.
    """
    fit_cases, held_out_cases = ingest(fit_cases), tuple(held_out_cases)
    if held_out_cases:
        ingest(held_out_cases)
    shared_ids = {c.case_id for c in fit_cases} & {c.case_id for c in held_out_cases}
    if shared_ids:
        raise ValueError(f"case ids appear on both sides: {sorted(shared_ids)}")
    shared_re = set(by_re(fit_cases)) & set(by_re(held_out_cases))
    if shared_re:
        raise ValueError(
            f"Re values appear on both sides: {sorted(shared_re)}. The surrogate sees "
            f"only Re, so the held-out residual would be a fitted residual under another "
            f"name. Use split_by_re() to divide the cases."
        )
    fit = fit_power_law(fit_cases)
    return (
        fit,
        residuals(fit, fit_cases, "fitted"),
        residuals(fit, held_out_cases, "held out"),
    )
