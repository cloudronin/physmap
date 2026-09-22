"""The truth-independence guard. Refuses before any metric is computed.

The whole value of a performance claim here is that the truth label is independent of the
closure the causal method checks. If the "truth" a prediction is scored against was
produced by that same closure, then closure-versus-truth measures closure-versus-itself,
every disagreement is definitionally zero, and any reported lift is an artifact of the
setup rather than a finding about the world.

This guard raises. It does not warn, and it does not return a lower confidence, because a
circular comparison has no degraded-but-usable form -- there is nothing to salvage from
it. The refusal happens at load time, before precision, recall or F1 exist, so a circular
run cannot produce a number that someone later quotes.

The open question this guards is live, not hypothetical. The prior implementation marked
the mixed-convection pipe substrate as non-divergent on exactly these grounds: its truth
column was a closure-style correlation rather than a measurement. The abstract describes
that truth as experimental. Until that is resolved, the guard is what stands between the
two readings.
"""

from __future__ import annotations

from enum import Enum

__all__ = [
    "TruthIndependence",
    "INDEPENDENT_SOURCES",
    "CircularTruthError",
    "require_independent_truth",
    "may_report_performance",
]


class TruthIndependence(str, Enum):
    #: Measured. The only source the abstract's phrasing would justify.
    EXPERIMENTAL = "experimental"
    #: A high-fidelity model that does not share the closure under test.
    INDEPENDENT_HIGH_FIDELITY = "independent_high_fidelity"
    #: Declared by a fixture. Exercises the machinery; backs no performance claim.
    FIXTURE = "fixture"
    #: Produced by the closure under test. Circular. Always refused.
    SAME_CLOSURE = "same_closure"
    #: Provenance not established. Refused, because unknown is not innocent.
    UNKNOWN = "unknown"


#: The only sources that may back a reported performance metric.
INDEPENDENT_SOURCES: frozenset[TruthIndependence] = frozenset(
    {TruthIndependence.EXPERIMENTAL, TruthIndependence.INDEPENDENT_HIGH_FIDELITY}
)


class CircularTruthError(ValueError):
    """Raised when truth is not independent of the closure being checked."""


def require_independent_truth(source: TruthIndependence | str) -> TruthIndependence:
    """Raise unless `source` can back a performance claim. Returns it otherwise."""
    try:
        s = TruthIndependence(source)
    except ValueError as e:
        raise CircularTruthError(
            f"unknown truth source {source!r}; allowed: "
            f"{sorted(t.value for t in TruthIndependence)}"
        ) from e

    if s is TruthIndependence.SAME_CLOSURE:
        raise CircularTruthError(
            "truth_source is 'same_closure': the truth was produced by the closure under "
            "test, so any comparison measures the closure against itself. Refused before "
            "any metric is computed."
        )
    if s is TruthIndependence.UNKNOWN:
        raise CircularTruthError(
            "truth_source is 'unknown': independence has not been established. Unknown "
            "provenance is refused rather than assumed innocent."
        )
    if s is TruthIndependence.FIXTURE:
        raise CircularTruthError(
            "truth_source is 'fixture': a declared value exercises the machinery but "
            "cannot back a performance claim. Use may_report_performance() to branch on "
            "this instead of calling the guard."
        )
    return s


def may_report_performance(source: TruthIndependence | str) -> bool:
    """Non-raising form, for deciding whether to compute metrics at all."""
    try:
        return TruthIndependence(source) in INDEPENDENT_SOURCES
    except ValueError:
        return False
