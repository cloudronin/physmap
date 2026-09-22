"""Phase-2 Assessment as a v0.6-conformant UofA subgraph.

Per the v0.2 architecture refactor spec, Part 4: the Phase-1 flat Assessment
becomes a focused subgraph conforming to the v0.6 vocab
(`https://uofa.net/vocab#`). The mapping is mechanical from the Phase-1
field names (chosen as Phase-2 seeds during Steps 5–6):

  Assessment.operating_point     -> Discrepancy.id_ + discrepancyRegion
  Assessment.verdict             -> Disposition.actionClass (via adjudicator)
  Assessment.decision_signals[*] -> CredibilityFactor (always)
                                    + WeakenerAnnotation (when fired)
  DetectorResult.rationale       -> WeakenerAnnotation.justification
  Assessment.rationale           -> Disposition.actionParameters

Phase-2 scope (per the spec): the ~8 IN-SCOPE node types
  * Discrepancy           — the surrogate point under review
  * CredibilityFactor     — one per detector (status: fired/quiet)
  * WeakenerAnnotation    — one per FIRED detector
  * OffsetRationale       — emitted by the defeasible adjudicator (Phase 2C)
  * Disposition           — actionClass from the v0.6 controlled vocab
  * hasEvidence/hasJustification — link edges (carried as `affectedNode`
                                    and the v0.6 `justification` property)

OUT-OF-SCOPE per point (these belong to the enclosing UnitOfAssurance
case, not the per-point assessment): VerificationActivity, ModelConfiguration,
SensitivityAnalysis, ProcessAttestation, DeploymentRecord, InputPedigreeLink,
ReviewActivity, full UnitOfAssurance lifecycle.

This module ships the dataclasses + the Phase-1 → v0.6 mapper. The
defeasible-adjudication aggregator (Phase 2C) plugs into
`_choose_action_class` and `_build_offset_rationales` so this layer
stays a pure structural mapping; Phase 2C reasons over it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from physmap.pipeline.core import Assessment, DetectorResult


# Path the v0.6 @context is loaded from — relative to package root.
# Mirrors evidence_corpus.py's pattern (commit 2897392).
V06_CONTEXT_REF = "physmap/fixtures/context/v0.6.jsonld"

# Disposition controlled vocabulary (locked by uofa's disposition_shapes.ttl;
# any string outside this set fails SHACL).
DISPOSITION_ACTION_CLASSES = (
    "restrict-cou",            # narrow the context of use to avoid the failure
    "acquire-validation",      # get more validation data
    "characterize-region",     # describe where the failure occurs
    "accept-residual-risk",    # accept the failure with justification
    "change-cou",              # alter the context of use (model swap, etc.)
)


# ── factor / pattern dictionaries (Phase-1 -> v0.6 controlled-ish terms) ────
#
# These maps make the per-detector mapping mechanical. They are not fixed
# vocab (v0.6 doesn't pin factorType / patternId controlled strings the way
# it pins actionClass), but they ARE the names the EvidenceEnrichmentStage
# from Step 7 already uses for its provenance keys — preserving them lets
# Phase-1 + Phase-2 outputs line up without renames.

_FACTOR_TYPE_BY_DETECTOR = {
    "distance":             "input-distribution-novelty",
    "gp_variance":          "surrogate-prediction-variance",
    "ensemble_variance":    "ensemble-prediction-variance",
    "corpus":               "training-set-corpus-error",
    "closure_validity":     "literature-validity-distance",
    "novelty_density":      "input-distribution-novelty",   # physmap GMM density baseline
}
# Note: EvidenceEnrichmentStage (in evidence_stage.py, Cleanup 6) attaches
# claim-centric provenance to justification_signals when the
# closure_validity gating signal fires. The justification payload's
# `claim_type` / `source` fields map to v0.6's hasEvidence and
# wasDerivedFrom edges in the Phase-2 graph.

_PATTERN_ID_BY_DETECTOR = {
    "distance":             "InputOutOfTrainingDistribution",
    "gp_variance":          "SurrogateVarianceExceedsThreshold",
    "ensemble_variance":    "EnsembleDisagreement",
    "corpus":               "CorpusErrorMagnitudeAboveThreshold",
    "closure_validity":     "OutOfValidatedRange",
    # physmap GMM density baseline → an input-distribution novelty pattern (already
    # in defeasible_aggregator.NOVELTY_PATTERNS), so a fired GMM adjudicates as novelty.
    "novelty_density":      "InputOutOfTrainingDistribution",
    # observable-pole conformal statistical mode → a surrogate-variance-family weakener
    # (a baseline-side credibility signal, never the corpus), so it adjudicates like gp_variance.
    "conformal_residual":   "SurrogateVarianceExceedsThreshold",
}


# ── v0.6 node dataclasses ───────────────────────────────────────────────────

# DiscrepancyShape pins measureType to this 2-entry vocab.
DISCREPANCY_MEASURE_TYPES = ("point", "aggregate")


@dataclass(frozen=True)
class DiscrepancyNode:
    """uofa:Discrepancy — the surrogate point under review. Measured FACT;
    carries surrogate-vs-truth + region/measure metadata. SHACL pins
    surrogatePrediction, solverTruth, discrepancyMagnitude as xsd:double
    (exactly one each) and `measureType ∈ {"point", "aggregate"}`."""
    id_: str
    surrogate_prediction: float
    solver_truth: float
    discrepancy_magnitude: float
    discrepancy_region: str = ""
    measure_type: str = "point"   # one row = one operating-point measurement

    def __post_init__(self) -> None:
        if self.measure_type not in DISCREPANCY_MEASURE_TYPES:
            raise ValueError(
                f"Discrepancy.measure_type={self.measure_type!r} not in v0.6 "
                f"controlled vocab {DISCREPANCY_MEASURE_TYPES}. SHACL "
                f"DiscrepancyShape will reject this; refuse at construction."
            )


@dataclass(frozen=True)
class CredibilityFactorNode:
    """uofa:CredibilityFactor — one per detector. `factor_type` names the
    detector family; `factor_status` is "fired" or "quiet"; `factor_standard`
    cites the literature standard backing the detector (e.g., the closure_id
    a validity-range detector queries)."""
    id_: str
    factor_type: str
    factor_status: str        # "fired" | "quiet"
    factor_standard: str = ""


@dataclass(frozen=True)
class WeakenerAnnotationNode:
    """uofa:WeakenerAnnotation — emitted for EVERY fired detector. patternId
    names the failure pattern; affectedNode points at the Discrepancy; the
    `justification` text is the DetectorResult.rationale verbatim
    (preserves the audit trail Phase-1 already built)."""
    id_: str
    pattern_id: str
    affected_node: str
    justification: str
    severity: str | None = None


@dataclass(frozen=True)
class OffsetRationaleNode:
    """uofa:OffsetRationale — emitted by the defeasible adjudicator (Phase 2C)
    to say "this CredibilityFactor's fire is OFFSET by other evidence; do
    not weigh it as a defeater." Phase 2A doesn't emit these; the dataclass
    is defined here so the Phase 2C aggregator can construct them without
    introducing new types later."""
    id_: str
    refers_to_factor: str
    justification: str
    offsetting_evidence: str = ""


@dataclass(frozen=True)
class DispositionNode:
    """uofa:Disposition — the action taken in response to the assessment.
    SHACL pins actionClass to the 5-entry controlled vocab
    (DISPOSITION_ACTION_CLASSES). `actionParameters` is optional free text;
    `confidenceLevel` is optional High/Medium/Low or numeric;
    `residual_risk_justification` is required when actionClass is
    'accept-residual-risk'."""
    id_: str
    action_class: str
    action_parameters: str = ""
    confidence_level: str | None = None
    residual_risk_justification: str = ""

    def __post_init__(self) -> None:
        if self.action_class not in DISPOSITION_ACTION_CLASSES:
            raise ValueError(
                f"Disposition.action_class={self.action_class!r} not in v0.6 "
                f"controlled vocab {DISPOSITION_ACTION_CLASSES}. SHACL will "
                f"reject this; refuse at construction."
            )


@dataclass
class V06AssessmentSubgraph:
    """The full per-point Phase-2 subgraph: one Discrepancy + N
    CredibilityFactors + M WeakenerAnnotations + 0-K OffsetRationales +
    one Disposition."""
    discrepancy: DiscrepancyNode
    credibility_factors: list[CredibilityFactorNode]
    weakener_annotations: list[WeakenerAnnotationNode]
    offset_rationales: list[OffsetRationaleNode]
    disposition: DispositionNode
    operating_point: tuple

    def to_jsonld(self, *, context_ref: str = V06_CONTEXT_REF) -> dict:
        """Serialize as a v0.6 JSON-LD doc with @context + @graph."""
        graph: list[dict] = []
        graph.append(_discrepancy_to_jsonld(self.discrepancy))
        for f in self.credibility_factors:
            graph.append(_credibility_factor_to_jsonld(f))
        for w in self.weakener_annotations:
            graph.append(_weakener_annotation_to_jsonld(w))
        for o in self.offset_rationales:
            graph.append(_offset_rationale_to_jsonld(o))
        graph.append(_disposition_to_jsonld(self.disposition))
        return {"@context": context_ref, "@graph": graph}


# ── JSON-LD serializers (each emits one @graph entry) ───────────────────────

def _discrepancy_to_jsonld(d: DiscrepancyNode) -> dict:
    payload: dict[str, Any] = {
        "@type": "Discrepancy",
        "id": d.id_,
        # SHACL pins these as xsd:double; the @context coerces JSON numbers
        # to xsd:double automatically.
        "surrogatePrediction": float(d.surrogate_prediction),
        "solverTruth":         float(d.solver_truth),
        "discrepancyMagnitude": float(d.discrepancy_magnitude),
    }
    if d.discrepancy_region:
        payload["discrepancyRegion"] = d.discrepancy_region
    if d.measure_type:
        payload["measureType"] = d.measure_type
    return payload


def _credibility_factor_to_jsonld(f: CredibilityFactorNode) -> dict:
    payload: dict[str, Any] = {
        "@type": "CredibilityFactor",
        "id": f.id_,
        "factorType": f.factor_type,
        "factorStatus": f.factor_status,
    }
    if f.factor_standard:
        payload["factorStandard"] = f.factor_standard
    return payload


def _weakener_annotation_to_jsonld(w: WeakenerAnnotationNode) -> dict:
    payload: dict[str, Any] = {
        "@type": "WeakenerAnnotation",
        "id": w.id_,
        "patternId": w.pattern_id,
        "affectedNode": w.affected_node,
        "justification": w.justification,
    }
    if w.severity is not None:
        payload["severity"] = w.severity
    return payload


def _offset_rationale_to_jsonld(o: OffsetRationaleNode) -> dict:
    payload: dict[str, Any] = {
        "@type": "OffsetRationale",
        "id": o.id_,
        "refersToFactor": o.refers_to_factor,
        "justification": o.justification,
    }
    if o.offsetting_evidence:
        payload["offsettingEvidence"] = o.offsetting_evidence
    return payload


def _disposition_to_jsonld(d: DispositionNode) -> dict:
    payload: dict[str, Any] = {
        "@type": "Disposition",
        "id": d.id_,
        "actionClass": d.action_class,
    }
    if d.action_parameters:
        payload["actionParameters"] = d.action_parameters
    if d.confidence_level is not None:
        payload["confidenceLevel"] = d.confidence_level
    if d.residual_risk_justification:
        payload["residualRiskJustification"] = d.residual_risk_justification
    return payload


# ── Phase-1 → v0.6 mapper ───────────────────────────────────────────────────

# Match a closure_id inside a rationale string. ValidityRangeDistanceDetector
# rationales surface 'gnielinski-1976' / 'modified-sparrow-cur-...' in single
# quotes; pull them out to populate factorStandard.
_CLOSURE_ID_RE = re.compile(r"'([a-z][a-z0-9-]+(?:-[a-z0-9]+)*-\d{4})'")


def _factor_standard_from_rationale(result: DetectorResult) -> str:
    """Extract a literature-standard string from a DetectorResult rationale.
    Today only the closure_validity rationale carries a closure_id; other
    detectors leave the field blank.
    """
    if result.detector_name != "closure_validity":
        return ""
    match = _CLOSURE_ID_RE.search(result.rationale)
    return match.group(1) if match else ""


def _default_action_class_for_verdict(verdict: str,
                                       weakeners: list[WeakenerAnnotationNode],
                                       ) -> tuple[str, str]:
    """Phase-2A default action-class chooser. The Phase 2C defeasible
    aggregator replaces this with proper offset/agreement/threshold-distance
    reasoning. Defaults:
        verdict='quiet'  AND no weakeners   -> accept-residual-risk
        verdict='fire'   AND >=1 weakener   -> characterize-region

    Returns (action_class, residual_risk_justification).
    """
    if verdict == "quiet":
        return ("accept-residual-risk",
                "No decision-signal weakeners fired; accepting with residual risk.")
    # verdict == "fire"
    weakener_patterns = sorted({w.pattern_id for w in weakeners})
    return ("characterize-region",
            f"Weakeners fired on patterns {weakener_patterns}; downstream "
            f"reasoning must characterize the affected region before deploying. "
            f"(Phase-2A default; Phase-2C adjudicator may upgrade/downgrade.)")


def _op_to_id_suffix(operating_point: tuple) -> str:
    """Make a stable id-safe slug from an operating-point tuple. Avoids
    collisions across vehicles by including the structure verbatim."""
    parts = ["%g" % float(p) if isinstance(p, (int, float)) else str(p)
             for p in operating_point]
    raw = "x".join(parts)
    return re.sub(r"[^A-Za-z0-9._-]", "_", raw)


def assessment_to_v06_subgraph(
    phase1: Assessment,
    *,
    surrogate_prediction: float,
    solver_truth: float,
    point_id_prefix: str = "p1pt",
    discrepancy_region: str = "",
    measure_type: str = "point",
    confidence_level: str | None = None,
    action_class_chooser=None,
    adjudicator=None,
) -> V06AssessmentSubgraph:
    """Map a Phase-1 Assessment + the underlying surrogate/truth pair into a
    v0.6-conformant subgraph.

    Args:
        phase1: the Phase-1 Assessment from Pipeline.run / phase1_gate.
        surrogate_prediction: scalar — the row's surrogate_prediction (often
            the matched-closure prediction the engine populated).
        solver_truth: scalar — the row's cfd_truth (measured Nu).
        point_id_prefix: id prefix for the generated nodes (so multiple
            subgraphs can coexist in one document without colliding).
        discrepancy_region: free-text region descriptor surfaced into
            Discrepancy.discrepancyRegion (e.g., "x_over_D=2.5, Re=55570").
        measure_type: what the discrepancy is in (default "Nu").
        confidence_level: optional override for Disposition.confidenceLevel.
        action_class_chooser: optional callable
            (verdict, weakeners) -> (action_class, residual_risk_justification).
            Defaults to `_default_action_class_for_verdict`. The defeasible
            adjudicator (Phase 2C) plugs in here.

    Returns:
        A V06AssessmentSubgraph carrying the typed nodes. Serialize to
        JSON-LD via `.to_jsonld()`.
    """
    suffix = _op_to_id_suffix(phase1.operating_point)
    base = f"{point_id_prefix}/{suffix}"

    discrepancy = DiscrepancyNode(
        id_=f"discrepancy:{base}",
        surrogate_prediction=float(surrogate_prediction),
        solver_truth=float(solver_truth),
        discrepancy_magnitude=abs(float(surrogate_prediction) - float(solver_truth)),
        discrepancy_region=discrepancy_region,
        measure_type=measure_type,
    )

    factors: list[CredibilityFactorNode] = []
    weakeners: list[WeakenerAnnotationNode] = []
    for name, det_result in phase1.decision_signals.items():
        f = CredibilityFactorNode(
            id_=f"factor:{base}/{name}",
            factor_type=_FACTOR_TYPE_BY_DETECTOR.get(name, name),
            factor_status="fired" if det_result.fired else "quiet",
            factor_standard=_factor_standard_from_rationale(det_result),
        )
        factors.append(f)
        if det_result.fired:
            weakeners.append(WeakenerAnnotationNode(
                id_=f"weakener:{base}/{name}",
                pattern_id=_PATTERN_ID_BY_DETECTOR.get(name, name),
                affected_node=discrepancy.id_,
                justification=det_result.rationale,
                # The DetectorResult doesn't carry a separate "severity"
                # term; leave None so SHACL/audit can see absence.
                severity=None,
            ))

    # Adjudicator overrides chooser when set (Phase-2C path). Otherwise
    # fall through to the Phase-2A default chooser.
    offset_rationales: list[OffsetRationaleNode] = []
    if adjudicator is not None:
        result = adjudicator.adjudicate(
            weakeners=weakeners,
            decision_signals=phase1.decision_signals,
            discrepancy_id=discrepancy.id_,
        )
        action_class = result.action_class
        residual_just = result.residual_risk_justification
        offset_rationales = list(result.offset_rationales)
    else:
        chooser = action_class_chooser or _default_action_class_for_verdict
        action_class, residual_just = chooser(phase1.verdict, weakeners)

    disposition = DispositionNode(
        id_=f"disposition:{base}",
        action_class=action_class,
        action_parameters=phase1.rationale,
        confidence_level=confidence_level,
        residual_risk_justification=(
            residual_just if action_class == "accept-residual-risk" else ""
        ),
    )

    return V06AssessmentSubgraph(
        discrepancy=discrepancy,
        credibility_factors=factors,
        weakener_annotations=weakeners,
        offset_rationales=offset_rationales,
        disposition=disposition,
        operating_point=phase1.operating_point,
    )


def assessments_to_v06_document(
    phase1_assessments: Sequence[Assessment],
    *,
    surrogates: Sequence[float],
    truths: Sequence[float],
    regions: Sequence[str] | None = None,
    point_id_prefix: str = "naca-p1pt",
    measure_type: str = "point",
    action_class_chooser=None,
    adjudicator=None,
) -> dict:
    """Map a sequence of Phase-1 Assessments into a single v0.6 JSON-LD
    document with one shared @context and a flat @graph of all nodes
    across all points. The id_prefix keeps points cleanly addressable.

    Args:
        phase1_assessments: list of Phase-1 Assessments (e.g. from phase1_gate).
        surrogates, truths: parallel arrays of per-point surrogate/truth pairs.
        regions: optional parallel array of free-text region descriptors.
        point_id_prefix: id prefix used per subgraph.
        action_class_chooser: defeasible adjudicator (Phase 2C). If None,
            defaults to the Phase-2A heuristic.
    """
    n = len(phase1_assessments)
    if len(surrogates) != n or len(truths) != n:
        raise ValueError(
            f"surrogates ({len(surrogates)}) and truths ({len(truths)}) must "
            f"match the assessment count ({n})."
        )
    if regions is None:
        regions = [""] * n
    elif len(regions) != n:
        raise ValueError(
            f"regions ({len(regions)}) must match assessment count ({n})."
        )

    graph: list[dict] = []
    for i, assess in enumerate(phase1_assessments):
        sub = assessment_to_v06_subgraph(
            assess,
            surrogate_prediction=float(surrogates[i]),
            solver_truth=float(truths[i]),
            point_id_prefix=point_id_prefix,
            discrepancy_region=regions[i],
            measure_type=measure_type,
            action_class_chooser=action_class_chooser,
            adjudicator=adjudicator,
        )
        graph.append(_discrepancy_to_jsonld(sub.discrepancy))
        for f in sub.credibility_factors:
            graph.append(_credibility_factor_to_jsonld(f))
        for w in sub.weakener_annotations:
            graph.append(_weakener_annotation_to_jsonld(w))
        for o in sub.offset_rationales:
            graph.append(_offset_rationale_to_jsonld(o))
        graph.append(_disposition_to_jsonld(sub.disposition))

    return {"@context": V06_CONTEXT_REF, "@graph": graph}


__all__ = [
    "DISPOSITION_ACTION_CLASSES",
    "DISCREPANCY_MEASURE_TYPES",
    "V06_CONTEXT_REF",
    "DiscrepancyNode",
    "CredibilityFactorNode",
    "WeakenerAnnotationNode",
    "OffsetRationaleNode",
    "DispositionNode",
    "V06AssessmentSubgraph",
    "assessment_to_v06_subgraph",
    "assessments_to_v06_document",
]
