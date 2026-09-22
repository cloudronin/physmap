"""The observability-weighted aggregator — where the physics signal is trusted
precisely on the axes the statistical baselines are structurally blind to.

This is NOT a pipeline.core.Aggregator (that returns the internal fire/quiet
Verdict and sees only decision_signals); it needs the observability dict + the
governing fired bound, so it has its own combine(). Three branches, keyed on the
FIRED BOUND's observability, not baseline silence:

  UNOBSERVABLE → REJECT          baselines blind → their silence is expected, not
                                 reassuring → trust the corpus. THE product value.
  PARTIAL      → UNCERTAIN/REVIEW honest interim; defer, do not over-fire.
  OBSERVABLE / → baseline verdict corpus redundant → defer to baselines, never
   corpus quiet                  double-count (do-no-harm).

The Disposition reuses the shipped DefeasibleAdjudicator (action_class ∈ the 5
SHACL classes), mapped to the public 4-way Disposition enum. Verdict is the public
4-way enum (distinct from the internal fire/quiet core.Verdict).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from physmap.guardrail.enums import Disposition, Observability, Regime, Verdict
from physmap.guardrail.weighting_heuristic import (
    LEAN_BASELINE_TRUST,
    LEAN_CORPUS_TRUST,
    WEIGHT_GRADED,
    graded_lean,
    resolve_partial,
)
from physmap.pipeline.assessment_v06 import (
    _PATTERN_ID_BY_DETECTOR,
    WeakenerAnnotationNode,
)
from physmap.pipeline.core import DetectorResult
from physmap.pipeline.defeasible_aggregator import DefeasibleAdjudicator
from physmap.pipeline.validity_signal import PerBoundMargin


CORPUS_NAME = "closure_validity"

# SHACL action_class → public Disposition. The public enum (spec-locked at 4) is
# narrower than the 5 SHACL classes: acquire-validation maps to REVIEW, and
# change-cou folds into RESTRICT_COU (both narrow/alter the context of use).
_DISPOSITION_FROM_ACTION = {
    "characterize-region": Disposition.CHARACTERIZE_REGION,
    "restrict-cou": Disposition.RESTRICT_COU,
    "accept-residual-risk": Disposition.ACCEPT_RESIDUAL_RISK,
    "acquire-validation": Disposition.REVIEW,
    "change-cou": Disposition.RESTRICT_COU,
}


@dataclass(frozen=True)
class AggregateOutcome:
    verdict: Verdict
    disposition: Disposition
    action_class: str        # the SHACL action_class (kept for graph/audit consistency)
    rule: str                # which branch fired (debug / rationale seed)


def _build_weakeners(decision_signals: dict[str, DetectorResult]) -> list[WeakenerAnnotationNode]:
    """One WeakenerAnnotation per FIRED detector — the adjudicator's input. Mirrors
    assessment_v06's construction but needs no truth/Discrepancy (placeholder ids)."""
    return [
        WeakenerAnnotationNode(
            id_=f"weakener:guardrail/{name}",
            pattern_id=_PATTERN_ID_BY_DETECTOR.get(name, name),
            affected_node="discrepancy:guardrail",
            justification=r.rationale,
        )
        for name, r in decision_signals.items()
        if r.fired
    ]


@dataclass
class ObservabilityWeightedAggregator:
    """The default aggregator. status_weighting is informational here (the
    governing bound is chosen upstream in the detector); kept for parity."""

    status_weighting: bool = True
    _adjudicator: DefeasibleAdjudicator = field(default_factory=DefeasibleAdjudicator, repr=False)

    def combine(
        self,
        *,
        decision_signals: dict[str, DetectorResult],
        observability: dict[str, Observability],
        fired_bound: PerBoundMargin | None,
        severities: dict[str, str | None],
        fired_closure_id: str | None = None,
        regime: Regime | None = None,
    ) -> AggregateOutcome:
        coord = fired_bound.coord if fired_bound is not None else None
        obs = observability.get(coord) if coord is not None else None

        if fired_bound is not None and obs is Observability.UNOBSERVABLE:
            # Corpus fired on a bound the baselines are STRUCTURALLY BLIND to.
            # Trust it. Disposition from the adjudicator over ALL fired weakeners.
            action = self._adjudicate(decision_signals)
            return AggregateOutcome(
                Verdict.REJECT, _DISPOSITION_FROM_ACTION[action], action,
                "unobservable-corpus-trusted",
            )

        if fired_bound is not None and obs is Observability.PARTIAL:
            return self._partial_outcome(
                decision_signals, severities, coord, fired_closure_id, regime,
            )

        # OBSERVABLE (corpus redundant) or corpus quiet → baseline verdict.
        return self._baseline_outcome(decision_signals, severities)

    def _partial_outcome(
        self,
        decision_signals: dict[str, DetectorResult],
        severities: dict[str, str | None],
        coord: str,
        closure_id: str | None,
        regime: Regime | None,
    ) -> AggregateOutcome:
        """The PARTIAL middle. Uncalibrated → DEFER (honest UNCERTAIN), exactly as
        before. Calibrated (a real vehicle has set this regime+variable's Layer-2c
        degree) → the continuous-blend graded weight: corpus-trust near the unobservable
        pole, baseline verdict near the observable pole (corpus redundant), else a
        calibrated WARN soft-flag. No rule change at graduation — we just read the
        richer corpus value."""
        regime_value = regime.value if regime is not None else None
        decision = (
            resolve_partial(closure_id, coord, regime_value=regime_value)
            if closure_id else None
        )
        if decision is None or decision.weight_target != WEIGHT_GRADED:
            # Uncalibrated, or a labeled lean — set membership can't weight it; defer.
            return AggregateOutcome(
                Verdict.UNCERTAIN, Disposition.REVIEW, "acquire-validation",
                "partial-defer",
            )

        lean = graded_lean(decision.partial_degree)
        if lean == LEAN_CORPUS_TRUST:
            # Calibrated near the unobservable pole → trust the corpus fire.
            action = self._adjudicate(decision_signals)
            return AggregateOutcome(
                Verdict.REJECT, _DISPOSITION_FROM_ACTION[action], action,
                "partial-graded-corpus-trust",
            )
        if lean == LEAN_BASELINE_TRUST:
            # Calibrated near the observable pole → corpus redundant; defer to baselines.
            return self._baseline_outcome(decision_signals, severities)
        # Mid-axis → calibrated soft-flag: warn + characterize the partial-driver region.
        return AggregateOutcome(
            Verdict.WARN, Disposition.CHARACTERIZE_REGION, "characterize-region",
            "partial-graded-softflag",
        )

    def _baseline_outcome(
        self,
        decision_signals: dict[str, DetectorResult],
        severities: dict[str, str | None],
    ) -> AggregateOutcome:
        # Exclude the corpus detector entirely — never double-count on observable
        # axes; this is what makes OBSERVABLE equivalent to statistical-only.
        baselines = {n: r for n, r in decision_signals.items() if n != CORPUS_NAME}
        fired = {n: r for n, r in baselines.items() if r.fired}
        action = self._adjudicate(baselines)            # adjudicate over fired baselines only

        if not fired:
            verdict = Verdict.TRUSTWORTHY
        elif any(severities.get(n) == "reject" for n in fired):
            verdict = Verdict.REJECT
        else:
            verdict = Verdict.WARN
        return AggregateOutcome(
            verdict, _DISPOSITION_FROM_ACTION[action], action, "baseline-verdict",
        )

    def _adjudicate(self, decision_signals: dict[str, DetectorResult]) -> str:
        weakeners = _build_weakeners(decision_signals)
        result = self._adjudicator.adjudicate(
            weakeners=weakeners,
            decision_signals=decision_signals,
            discrepancy_id="discrepancy:guardrail",
        )
        return result.action_class
