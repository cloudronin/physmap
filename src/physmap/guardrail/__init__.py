"""Public API for the physmap CredibilityGuardrail.

Importing this package pulls numpy + sklearn (via the pipeline detectors) but
never torch or an LLM SDK — the no-heavy-imports guard stays green. Bare
`import physmap` does NOT import this package; it is loaded lazily on first
access to a guardrail symbol (see physmap/__init__.py).
"""

from physmap.guardrail.configs import (
    Assessment,
    ClosureValidityDetectorConfig,
    ColumnMap,
    DetectorResult,
    DistanceDetectorConfig,
    GPVarianceDetectorConfig,
    NoveltyDetectorConfig,
)
from physmap.guardrail.enums import (
    AggregatorKind,
    DensityMethod,
    Device,
    DetectorKind,
    Disposition,
    Observability,
    Regime,
    Verdict,
)
from physmap.guardrail.guardrail import CredibilityGuardrail

__all__ = [
    "CredibilityGuardrail",
    # enums
    "Regime", "DetectorKind", "DensityMethod", "AggregatorKind", "Device",
    "Observability", "Verdict", "Disposition",
    # configs / data contracts
    "NoveltyDetectorConfig", "DistanceDetectorConfig", "GPVarianceDetectorConfig",
    "ClosureValidityDetectorConfig", "ColumnMap", "DetectorResult", "Assessment",
]
