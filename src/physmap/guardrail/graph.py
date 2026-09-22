"""Public Assessment → v0.6 SHACL-valid JSON-LD subgraph.

Thin reuse of pipeline.assessment_v06: rebuild a core Assessment from the public
one and run assessment_to_v06_subgraph with the DefeasibleAdjudicator (which emits
an action_class in the 5 SHACL classes). The graph is conformant by construction,
and the public 4-way Disposition (incl. REVIEW) never reaches the graph as a
literal — the adjudicator's SHACL action_class is used directly.
"""

from __future__ import annotations

from physmap.guardrail.configs import Assessment as PublicAssessment
from physmap.guardrail.enums import DetectorKind
from physmap.pipeline.assessment_v06 import assessment_to_v06_subgraph
from physmap.pipeline.core import Assessment as CoreAssessment
from physmap.pipeline.core import DetectorResult as CoreDetectorResult
from physmap.pipeline.defeasible_aggregator import DefeasibleAdjudicator


# Public DetectorKind ↔ the core detector_name strings the v0.6 mapper keys on.
NAME_BY_KIND = {
    DetectorKind.DISTANCE_TO_TRAINING: "distance",
    DetectorKind.GP_VARIANCE: "gp_variance",
    DetectorKind.NOVELTY_DENSITY: "novelty_density",
    DetectorKind.CLOSURE_VALIDITY: "closure_validity",
    DetectorKind.CONFORMAL_RESIDUAL: "conformal_residual",
}
KIND_BY_NAME = {v: k for k, v in NAME_BY_KIND.items()}


def _to_core_signals(signals: dict) -> dict[str, CoreDetectorResult]:
    out: dict[str, CoreDetectorResult] = {}
    for kind, r in signals.items():
        name = NAME_BY_KIND.get(kind, getattr(kind, "value", str(kind)))
        out[name] = CoreDetectorResult(
            detector_name=name, score=r.score, fired=r.fired,
            threshold=r.threshold, rationale=r.rationale, role="decision",
        )
    return out


def assessment_to_graph(a: PublicAssessment) -> dict:
    """Render one public Assessment as a v0.6 JSON-LD doc (@context + @graph)."""
    if a.solver_truth is None:
        raise ValueError(
            "to_graph() requires solver_truth — the v0.6 Discrepancy shape pins "
            "exactly one solverTruth. A deployment without truth still yields a "
            "flat Assessment, but cannot produce a SHACL graph. Supply truth "
            "(a Path with a truth column, or graph=True over data that carries it)."
        )
    if a.surrogate_prediction is None:
        raise ValueError(
            "to_graph() requires surrogate_prediction (the Discrepancy needs the "
            "surrogate-vs-truth pair). Supply predictions via the surrogate "
            "callable, a prediction column, or test_pred."
        )
    core_signals = _to_core_signals(a.signals)
    label = "fire" if any(r.fired for r in core_signals.values()) else "quiet"
    core = CoreAssessment(
        operating_point=a.operating_point,
        verdict=label,
        decision_signals=core_signals,
        justification_signals={},
        rationale=a.rationale,
    )
    sub = assessment_to_v06_subgraph(
        core,
        surrogate_prediction=float(a.surrogate_prediction),
        solver_truth=float(a.solver_truth),
        discrepancy_region=a.region,
        adjudicator=DefeasibleAdjudicator(),
    )
    return sub.to_jsonld()
