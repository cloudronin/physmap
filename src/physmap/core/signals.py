"""Signal kinds. The no-conflation rule, made structural.

Four different questions get asked about a prediction, and they rest on different
evidence. Mixing them up is the failure this project exists to prevent, so a signal
cannot be constructed without saying which kind it is, and nothing aggregates two
kinds into a single number.

  closure_validity      Is a closure being used outside its calibrated range?
  observability         Can the surrogate's inputs represent the governing variable?
  causal_materiality    Is the out-of-range mechanism big enough to matter for the QoI?
  statistical_baseline  Does an input-space novelty detector fire?

Each carries its own threshold and its own rationale. A `causal_materiality` signal is
never evidence for an `observability` claim, and the reverse is equally false.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = ["SignalKind", "Signal"]


class SignalKind(str, Enum):
    CLOSURE_VALIDITY = "closure_validity"
    OBSERVABILITY = "observability"
    CAUSAL_MATERIALITY = "causal_materiality"
    STATISTICAL_BASELINE = "statistical_baseline"


@dataclass(frozen=True)
class Signal:
    """One signal of one kind. `value` and `threshold` are None when the signal could
    not be computed -- which is different from computing it and getting zero."""

    kind: SignalKind
    fired: bool
    rationale: str
    value: float | None = None
    threshold: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, SignalKind):
            raise TypeError(f"kind must be a SignalKind, got {type(self.kind).__name__}")
        if self.fired and self.value is None:
            raise ValueError(
                f"{self.kind.value} signal claims to have fired with no value. A signal "
                f"that could not be computed must not fire."
            )
