"""D3 detection + adjudication pipeline — the architecture refactor's
detection-side surface.

Module layout (renamed during R4 reorg — d3_ prefix dropped):
  core                  (was d3_pipeline)          Pipeline + DetectorAdapter + protocols
  aggregators           (was d3_aggregators)       Phase-1 aggregators (AnyFired, ...)
  defeasible_aggregator (was d3_defeasible_aggregator) Phase-2 reasoner
  detectors             (was d3_detectors)         Inner detector classes
  validity_signal       (was d3_validity_signal)   Literature-distance detector
  surrogate             (was d3_surrogate)         GP surrogate + thresholds
  phase1_gate           (was d3_phase1_gate)       Phase-1 NACA gate runner
  phase2_gate           (was d3_phase2_gate)       Phase-2 NACA gate runner
  assessment_v06                                   Phase-1 -> v0.6 subgraph mapper
  evidence_stage                                   Claim-centric JustificationStage

Common entrypoints re-exported so consumers can write
`from physmap.pipeline import Pipeline, AnyFired, ...`:
"""

from physmap.pipeline.aggregators import AnyFired, CorpusGated, WeightedVote
from physmap.pipeline.core import (
    Assessment,
    Detector,
    DetectorAdapter,
    DetectorResult,
    JustificationStage,
    Pipeline,
    Verdict,
    make_closure_validity_adapter,
    make_distance_adapter,
    make_ensemble_variance_adapter,
    make_gp_variance_adapter,
)
from physmap.pipeline.defeasible_aggregator import (
    AdjudicationResult,
    DefeasibleAdjudicator,
    OffsetRule,
)

__all__ = [
    "Assessment",
    "Detector",
    "DetectorAdapter",
    "DetectorResult",
    "JustificationStage",
    "Pipeline",
    "Verdict",
    "AnyFired",
    "CorpusGated",
    "WeightedVote",
    "AdjudicationResult",
    "DefeasibleAdjudicator",
    "OffsetRule",
    "make_closure_validity_adapter",
    "make_distance_adapter",
    "make_ensemble_variance_adapter",
    "make_gp_variance_adapter",
]
