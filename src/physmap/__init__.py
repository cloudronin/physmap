"""PhysMAP — physics-aware credibility checks for AI surrogates.

Two distinct methods live here, and they are deliberately kept apart:

**Closure validity and surrogate observability.** A surrogate trained on (Re, Pr) is
blind to x/D, so it fails silently in a pipe entrance region -- and so do input-space
novelty detectors, because they see only (Re, Pr) too. This path reads the bound
variable from the test coordinates, checks it against the closure's validated range,
and knows at fit time whether that variable is structurally observable to the
surrogate. Where it is observable, the guard defers to the statistical baselines.

**Causal materiality.** A mechanism outside its calibration range only matters if it
materially reaches the requested quantity of interest. This path flags a prediction
only when a mechanism is both out of range AND material to that QoI.

These are different claims with different evidence. Nothing in this package attributes
the results of one to the other. See `physmap.release` for what this build may claim.

No LLM is in any path. Explanations are deterministic rendered templates.
"""

from __future__ import annotations

from physmap.release import (
    CURRENT_RELEASE_STATE,
    EvidenceState,
    ReleaseState,
)

__version__ = "0.2.0"


# The CredibilityGuardrail public surface is re-exported LAZILY (PEP 562). A bare
# `import physmap` must stay free of numpy, sklearn, scipy and joblib -- a test
# asserts it -- while `from physmap import CredibilityGuardrail` pulls the
# guardrail and its scientific stack, which is fair because you are about to use
# the guard. Adding an eager import here breaks that guarantee silently.
_GUARDRAIL_EXPORTS = frozenset({
    "CredibilityGuardrail",
    "Regime", "DetectorKind", "DensityMethod", "AggregatorKind", "Device",
    "Observability", "Verdict", "Disposition",
    "NoveltyDetectorConfig", "DistanceDetectorConfig", "GPVarianceDetectorConfig",
    "ClosureValidityDetectorConfig", "ColumnMap", "DetectorResult", "Assessment",
})

_RELEASE_EXPORTS = frozenset({
    "CURRENT_RELEASE_STATE", "ReleaseState", "EvidenceState",
})

__all__ = ["__version__", *sorted(_RELEASE_EXPORTS), *sorted(_GUARDRAIL_EXPORTS)]


def __getattr__(name: str):
    if name in _GUARDRAIL_EXPORTS:
        import physmap.guardrail as _g
        return getattr(_g, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | _GUARDRAIL_EXPORTS)
