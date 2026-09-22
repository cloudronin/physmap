"""Public typed surface for the physmap CredibilityGuardrail.

Everything categorical is an enum — no magic strings for any fixed choice.
Continuous params (thresholds, counts) are plain numbers; only the developer's
own data-column names stay strings (validated, not enumerated).
"""

from __future__ import annotations

from enum import Enum


# ── Developer's fixed choices ─────────────────────────────────────────────────
class Regime(Enum):
    INTERNAL_FORCED_CONVECTION_PIPE = "internal_forced_convection_pipe"
    INTERNAL_FORCED_CONVECTION_RECT_CHANNEL = "internal_forced_convection_rect_channel"
    ENTRANCE_REGION_PIPE = "entrance_region_pipe"
    EXTERNAL_FLAT_PLATE_FORCED = "external_flat_plate_forced"
    MIXED_CONVECTION_HORIZONTAL_TUBE = "mixed_convection_horizontal_tube"
    MIXED_CONVECTION_VERTICAL_TUBE = "mixed_convection_vertical_tube"          # Jin (sCO2 buoyancy, Liu Bu)
    INTERNAL_FORCED_CONVECTION_PROPERTY_VARIATION = "internal_forced_convection_property_variation"
    HYPERSONIC_TRANSITION_DISTURBANCE = "hypersonic_transition_disturbance"   # Casper (freestream noise)
    HYPERSONIC_TRANSITION_ENTROPY = "hypersonic_transition_entropy"           # Marineau (bluntness/entropy)
    UNLISTED = "unlisted"                          # → statistical-only mode


class DetectorKind(Enum):
    DISTANCE_TO_TRAINING = "distance_to_training"
    GP_VARIANCE = "gp_variance"
    NOVELTY_DENSITY = "novelty_density"
    CLOSURE_VALIDITY = "closure_validity"
    CONFORMAL_RESIDUAL = "conformal_residual"   # observable-pole conformal statistical mode


class DensityMethod(Enum):
    GMM = "gmm"
    PCE = "pce"                                    # deferred (raises NotImplementedError)


class AggregatorKind(Enum):
    OBSERVABILITY_WEIGHTED = "observability_weighted"   # default
    ANY_FIRED = "any_fired"
    CORPUS_GATED = "corpus_gated"


class Device(Enum):
    CPU = "cpu"
    CUDA = "cuda"                                   # wired; CPU implemented (CUDA → NotImplementedError)


# ── Typed outputs ─────────────────────────────────────────────────────────────
class Observability(Enum):
    OBSERVABLE = "observable"
    PARTIAL = "partial"
    UNOBSERVABLE = "unobservable"


class Verdict(Enum):
    TRUSTWORTHY = "trustworthy"
    WARN = "warn"
    REJECT = "reject"
    UNCERTAIN = "uncertain"


class Disposition(Enum):
    CHARACTERIZE_REGION = "characterize_region"
    RESTRICT_COU = "restrict_cou"
    ACCEPT_RESIDUAL_RISK = "accept_residual_risk"
    REVIEW = "review"
