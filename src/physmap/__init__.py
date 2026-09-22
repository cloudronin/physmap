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

__version__ = "0.1.0"

__all__ = ["__version__", "CURRENT_RELEASE_STATE", "ReleaseState", "EvidenceState"]
