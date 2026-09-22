"""Deterministic explanation renderer — no LLM.

Each renderer composes a FIXED template over STRUCTURED facts: the closure + the
bound that fired (calibration corpus), the bound variable + its observability
class, the evidence-corpus provenance (source citation + measured divergence),
and the baseline state. Same inputs → same string (regression-testable); no model
call. Determinism: provenance claims are picked after sorting by claim_id, floats
use a fixed precision, and no timestamps appear.
"""

from __future__ import annotations

from typing import Sequence

from physmap.corpus.evidence import Claim, Source
from physmap.guardrail.enums import Observability
from physmap.pipeline.validity_signal import PerBoundMargin


_OBS_PHRASE = {
    Observability.UNOBSERVABLE: "is not a surrogate input (unobservable to statistical detectors)",
    Observability.PARTIAL: "is not a surrogate input but is correlated with one (only partially observable)",
    Observability.OBSERVABLE: "is a surrogate input (observable to statistical detectors)",
}


def _fmt_interval(lo: float | None, hi: float | None) -> str:
    """Human-friendly bound text. A huge upper bound reads as a one-sided ≥."""
    if lo is not None and (hi is None or hi >= 1e8):
        return f"≥ {lo:.3g}"
    if hi is not None and (lo is None or lo <= 0.0):
        return f"≤ {hi:.3g}"
    if lo is not None and hi is not None:
        return f"[{lo:.3g}, {hi:.3g}]"
    return "(unbounded)"


def _pick_provenance(claims_for_closure: Sequence[Claim], variable: str) -> Claim | None:
    """Deterministically choose the provenance claim FOR THE FIRED VARIABLE.

    Only ever returns a claim about `variable` — never borrows a divergence
    measured on a different axis (that would be provenance laundering: a Re
    divergence is not evidence about an x/D bound). Prefer a variable-matching
    claim carrying a measured_divergence; else a variable-matching originating
    claim (source citation only, no magnitude). Sorted by claim_id for stability.
    """
    var_claims = sorted(
        (c for c in claims_for_closure if c.bound and c.bound.variable == variable),
        key=lambda c: c.claim_id,
    )
    for c in var_claims:
        if c.measured_divergence is not None:
            return c
    return var_claims[0] if var_claims else None


def _provenance_phrase(
    claim: Claim | None, sources_index: dict[str, Source],
) -> str:
    if claim is None:
        return "no evidence-corpus claim is recorded for this bound"
    src = sources_index.get(claim.source_id)
    cite = src.citation if src is not None else claim.source_id
    md = claim.measured_divergence
    if md is not None and md.magnitude_pct is not None:
        return (f"the literature ({cite}) reports divergence up to "
                f"{md.magnitude_pct:.3g}% past this bound")
    return f"the literature ({cite}) documents this bound"


def render_unobservable(
    *,
    closure_id: str,
    fired_bound: PerBoundMargin,
    bound_interval: tuple[float | None, float | None],
    baseline_fired: bool,
    claims_for_closure: Sequence[Claim],
    sources_index: dict[str, Source],
) -> str:
    """THE product-value explanation: the corpus fired on a bound the baselines
    are structurally blind to, so their silence is expected, not reassuring."""
    var = fired_bound.coord
    obs_phrase = _OBS_PHRASE[Observability.UNOBSERVABLE]
    prov = _provenance_phrase(_pick_provenance(claims_for_closure, var), sources_index)
    bound_txt = _fmt_interval(*bound_interval)
    baseline_txt = (
        "A statistical baseline also fired."
        if baseline_fired
        else f"Statistical baselines are silent because they cannot observe {var}."
    )
    return (
        f"Prediction relies on {closure_id} beyond its validated {var} bound "
        f"({var} {bound_txt}); {var} {obs_phrase}, and {prov}. {baseline_txt}"
    )


def render_partial(
    *,
    closure_id: str,
    fired_bound: PerBoundMargin,
    bound_interval: tuple[float | None, float | None],
) -> str:
    """PARTIAL deferral — honest interim until the middle-vehicle calibration
    table exists. We do not over-fire; we flag for review."""
    var = fired_bound.coord
    bound_txt = _fmt_interval(*bound_interval)
    return (
        f"Prediction relies on {closure_id} beyond its validated {var} bound "
        f"({var} {bound_txt}); {var} {_OBS_PHRASE[Observability.PARTIAL]}. Set "
        f"membership cannot yet weight this axis against the baselines, so the "
        f"verdict is deferred for review rather than over-fired."
    )


def render_partial_graded(
    *,
    closure_id: str,
    fired_bound: PerBoundMargin,
    bound_interval: tuple[float | None, float | None],
    degree: float,
    calibrated_by: Sequence[str],
    soft_flag: bool,
) -> str:
    """Graded PARTIAL — a real vehicle has calibrated this (regime, variable)'s Layer-2c
    observability degree, so we weight the corpus fire by (1 - degree) instead of
    deferring. soft_flag → calibrated mid-axis WARN; else → corpus-trust near the
    unobservable pole. The weight traces to `calibrated_by` (provenance, not runtime)."""
    var = fired_bound.coord
    bound_txt = _fmt_interval(*bound_interval)
    by = ", ".join(calibrated_by) or "(unknown)"
    if soft_flag:
        tail = (
            f"its calibrated observability (degree={degree:g}, from {by}) places it "
            f"mid-axis, so the corpus fire is a calibrated soft-flag (corpus weight "
            f"{1.0 - degree:g}) raised for review, scaled against the baselines rather "
            f"than over-fired."
        )
    else:
        tail = (
            f"its calibrated observability (degree={degree:g}, from {by}) places it near "
            f"the unobservable pole, so the corpus fire is trusted — the baselines are "
            f"largely blind on this axis here."
        )
    return (
        f"Prediction relies on {closure_id} beyond its validated {var} bound "
        f"({var} {bound_txt}); {var} {_OBS_PHRASE[Observability.PARTIAL]}. {tail}"
    )


def render_baseline(*, baseline_fired_names: Sequence[str], all_quiet: bool) -> str:
    """OBSERVABLE / corpus-quiet narrative: the verdict defers to the statistical
    baselines (the corpus is redundant on observable axes — never double-counted)."""
    if all_quiet:
        return ("All statistical baselines are quiet and no physics bound is "
                "violated on an unobservable axis; prediction is trustworthy.")
    fired = ", ".join(sorted(baseline_fired_names)) or "(none)"
    return (f"Statistical baseline(s) fired ({fired}); the physics signal is "
            f"redundant here (observable axis) and is deferred to the baselines, "
            f"not double-counted.")
