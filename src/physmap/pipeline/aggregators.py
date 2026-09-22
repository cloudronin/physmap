"""Phase-1 aggregators — Aggregator implementations for the D3 pipeline.

Per the v0.2 architecture refactor (Part 2): the aggregator consumes ONLY
decision signals and reduces them to a `Verdict`. Three Phase-1 aggregators:

  * `AnyFired`    — union of detector fires. The locked ensemble metric
                    (per [[physmap-ensemble-claim-definition]]):
                        ensemble := steelman_baseline ∪ corpus_validity_signal
                    success iff Pareto dominance (≥ everywhere, > somewhere).
  * `CorpusGated` — corpus acts on points the baselines pass. Useful for
                    diagnosing whether the corpus signal adds catches on
                    operating points the baselines incorrectly stay quiet on.
  * `WeightedVote` — sum of (fired × weight) > threshold. Phase-1 stub for
                     future calibration experiments; not used in the locked
                     ensemble metric.

Phase-2 plugs in the DEFEASIBLE-ADJUDICATION reasoner (offset / agreement /
threshold-distance modulation → Disposition). NOT built — gated on NACA result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from physmap.pipeline.core import (
    Aggregator,
    DetectorResult,
    SignalRole,
    Verdict,
)


# ── AnyFired (the locked ensemble metric) ───────────────────────────────────

@dataclass
class AnyFired:
    """Union of all decision-signal fires.

    Reduces decision signals to fire iff at least one fired. The rationale
    cites every detector that fired (so audit trails always name names);
    on quiet, the rationale states all detectors were quiet.

    This is the LOCKED ensemble metric per
    `[[physmap-ensemble-claim-definition]]`:
        ensemble := steelman_baseline ∪ corpus_validity_signal
    The aggregator IS the ensemble — building the union as an Aggregator
    makes the ensemble metric fall out of the pipeline naturally.
    """
    name: str = "any_fired"

    def combine(self, decision_signals: dict[str, DetectorResult]) -> Verdict:
        if not decision_signals:
            raise ValueError(
                "AnyFired.combine received no decision signals; nothing to "
                "weigh. The pipeline should not call the aggregator on empty "
                "input."
            )
        fired = [r for r in decision_signals.values() if r.fired]
        if fired:
            rationale = "; ".join(r.rationale for r in fired)
            return Verdict(label="fire", rationale=rationale)
        rationale = "all detectors quiet: " + "; ".join(
            r.rationale for r in decision_signals.values()
        )
        return Verdict(label="quiet", rationale=rationale)


# ── CorpusGated ─────────────────────────────────────────────────────────────

@dataclass
class CorpusGated:
    """Fire iff (baselines all quiet) AND (corpus-validity fires).

    Surfaces the "corpus catches what baselines miss" cell — the diagnostic
    operating point where corpus's structural property (literature-only,
    no training dependence) buys actual lift. If baselines fire on a point,
    this aggregator stays quiet (already covered).

    `baseline_names` lists which detectors count as "baselines"; the
    remaining detector(s) act as the corpus arm. The corpus arm must
    include AT LEAST one signal with `threshold is None` (the literature-
    only validity detector) — otherwise CorpusGated degenerates into
    "all baselines quiet" with no corpus voice.
    """
    baseline_names: tuple[str, ...]
    corpus_names: tuple[str, ...] = ("closure_validity",)
    name: str = "corpus_gated"

    def combine(self, decision_signals: dict[str, DetectorResult]) -> Verdict:
        missing_b = [n for n in self.baseline_names if n not in decision_signals]
        missing_c = [n for n in self.corpus_names if n not in decision_signals]
        if missing_b or missing_c:
            raise KeyError(
                f"CorpusGated.combine missing required detectors: "
                f"baselines={missing_b}, corpus={missing_c}. "
                f"Got detectors: {sorted(decision_signals.keys())}."
            )
        baseline_fired = any(decision_signals[n].fired for n in self.baseline_names)
        corpus_fired = any(decision_signals[n].fired for n in self.corpus_names)

        if (not baseline_fired) and corpus_fired:
            corpus_rationales = "; ".join(
                decision_signals[n].rationale for n in self.corpus_names
                if decision_signals[n].fired
            )
            return Verdict(
                label="fire",
                rationale=(
                    f"corpus_gated: baselines all quiet AND corpus fires -> "
                    f"corpus catches what baselines missed. {corpus_rationales}"
                ),
            )
        if baseline_fired and corpus_fired:
            return Verdict(
                label="quiet",
                rationale=(
                    "corpus_gated: both baselines and corpus fired; "
                    "this aggregator surfaces ONLY the baselines-miss / "
                    "corpus-catch operating point, so quiet here."
                ),
            )
        if baseline_fired and not corpus_fired:
            return Verdict(
                label="quiet",
                rationale=(
                    "corpus_gated: baseline fired, corpus quiet. Not a "
                    "corpus-catch point; verdict is quiet."
                ),
            )
        return Verdict(
            label="quiet",
            rationale="corpus_gated: all detectors quiet.",
        )


# ── WeightedVote (Phase-1 stub for calibration experiments) ─────────────────

@dataclass
class WeightedVote:
    """Fire iff sum(weight_i for detector_i in fired) >= vote_threshold.

    A future calibration knob — not used in the locked ensemble metric.
    `weights` maps detector_name -> weight; missing detectors default to
    0.0 (silent abstention). `vote_threshold` is the sum-of-weights cutoff
    (default 1.0; with unit weights this degenerates to AnyFired).

    Phase-1 ships this as a stub so the strategy axis is real (Aggregator
    is a true plug point), but NACA's gate metric is AnyFired.
    """
    weights: dict[str, float]
    vote_threshold: float = 1.0
    name: str = "weighted_vote"

    def __post_init__(self) -> None:
        if not self.weights:
            raise ValueError(
                "WeightedVote requires a non-empty weights dict; otherwise "
                "no detector can contribute to the vote."
            )
        if any(w < 0 for w in self.weights.values()):
            raise ValueError(
                f"WeightedVote.weights cannot be negative: {self.weights}. "
                f"A negative weight would mean 'fired -> reduce verdict'; "
                f"that's not voting, that's defeasibility (Phase 2)."
            )
        if self.vote_threshold <= 0:
            raise ValueError(
                f"WeightedVote.vote_threshold must be > 0; got "
                f"{self.vote_threshold}."
            )

    def combine(self, decision_signals: dict[str, DetectorResult]) -> Verdict:
        total = 0.0
        contributors: list[str] = []
        for name, weight in self.weights.items():
            r = decision_signals.get(name)
            if r is not None and r.fired:
                total += weight
                contributors.append(f"{name}(w={weight:g})")
        if total >= self.vote_threshold:
            return Verdict(
                label="fire",
                rationale=(
                    f"weighted_vote: total={total:g} >= threshold="
                    f"{self.vote_threshold:g} from {contributors}"
                ),
            )
        return Verdict(
            label="quiet",
            rationale=(
                f"weighted_vote: total={total:g} < threshold="
                f"{self.vote_threshold:g} "
                f"(fired contributors: {contributors or '(none)'})"
            ),
        )


__all__ = ["AnyFired", "CorpusGated", "WeightedVote"]
