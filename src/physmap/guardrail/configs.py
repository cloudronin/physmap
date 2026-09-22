"""Detector config dataclasses, the ColumnMap data contract, and the public
result types (DetectorResult, Assessment) for the CredibilityGuardrail.

A detector is specified by a bare DetectorKind (no params) OR a frozen config
object (params). Continuous params are numbers; categorical params are enums.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from physmap.guardrail.enums import (
    DensityMethod,
    DetectorKind,
    Device,
    Disposition,
    Observability,
    Verdict,
)


# ── Detector specs (bare enum if no params; config object if params) ──────────
@dataclass(frozen=True)
class NoveltyDetectorConfig:
    kind: DetectorKind = DetectorKind.NOVELTY_DENSITY
    method: DensityMethod = DensityMethod.GMM
    components: int = 1
    warn_pct: float = 99.0
    reject_pct: float = 99.9
    device: Device = Device.CPU


@dataclass(frozen=True)
class DistanceDetectorConfig:
    kind: DetectorKind = DetectorKind.DISTANCE_TO_TRAINING
    k: int = 3
    device: Device = Device.CPU


@dataclass(frozen=True)
class GPVarianceDetectorConfig:
    kind: DetectorKind = DetectorKind.GP_VARIANCE
    kernel: str = "matern52"
    device: Device = Device.CPU


@dataclass(frozen=True)
class ClosureValidityDetectorConfig:
    kind: DetectorKind = DetectorKind.CLOSURE_VALIDITY
    graded: bool = True              # continuous distance-past-bound; False = binary
    status_weighting: bool = True    # weight signal by bound status (confirmed > … > claimed)


@dataclass(frozen=True)
class ConformalResidualDetectorConfig:
    """The observable-pole conformal statistical mode (spec v0.1, action #4). Opt-in —
    NOT in the default detector set, so it is strictly additive."""
    kind: DetectorKind = DetectorKind.CONFORMAL_RESIDUAL
    alpha: float = 0.1               # target miscoverage / in-distribution false-alarm rate
    calib_frac: float = 0.3          # fraction of train held out for the conformal calibration split
    random_state: int = 20260605     # locked seed (matches the GP emulator)
    device: Device = Device.CPU


DetectorSpec = Union[
    DetectorKind,
    NoveltyDetectorConfig,
    DistanceDetectorConfig,
    GPVarianceDetectorConfig,
    ClosureValidityDetectorConfig,
    ConformalResidualDetectorConfig,
]


@dataclass(frozen=True)
class ColumnMap:
    """Column schema for the Path / named-array branches.

    `inputs` is the FULL assessment-coordinate set the data carries — a SUPERSET
    of surrogate_inputs that MUST include the bound variables the closure-validity
    detector reads (e.g. x_over_D even when the surrogate only sees Re, Pr).
    """
    inputs: list[str]
    truth: str = "truth"
    prediction: str = "prediction"


# ── Results ───────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class DetectorResult:
    detector: DetectorKind
    score: float
    fired: bool
    threshold: float | None
    rationale: str


@dataclass(frozen=True)
class Assessment:
    verdict: Verdict
    disposition: Disposition
    rationale: str
    signals: dict[DetectorKind, DetectorResult]
    observability: Observability | None
    fired_bound_variable: str | None
    # Context needed to render the v0.6 SHACL subgraph (to_graph). Not part of the
    # narrative surface, but the Discrepancy/Disposition nodes require it. truth is
    # optional: a deployment without truth still yields a flat Assessment, but
    # to_graph() then raises (the Discrepancy shape pins exactly-one solverTruth).
    surrogate_prediction: float | None = None
    solver_truth: float | None = None
    operating_point: tuple = ()
    closure_id: str | None = None
    region: str = ""              # human-readable coords, e.g. "Re=55570, x_over_D=1.42"

    def to_graph(self) -> dict:
        """v0.6-conformant, SHACL-valid JSON-LD subgraph (reuses assessment_v06)."""
        from physmap.guardrail.graph import assessment_to_graph
        return assessment_to_graph(self)
