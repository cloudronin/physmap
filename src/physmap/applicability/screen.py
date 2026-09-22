"""The applicability screen: is the causal method even the right tool here?

Cheap, and deliberately run first. The causal method needs three things to be true of a
case: the quantity of interest must decompose, the mechanism must be separable enough to
remove on its own, and an ablation must be obtainable. Where any of those fails, the right
answer is a refusal with a reason code -- not a confident number produced by machinery
operating outside the conditions it assumes.

A refusal here is a result. It is also the cheapest honest output the method has.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from physmap.release import EvidenceState

__all__ = ["Applicability", "ReasonCode", "ScreenResult", "screen_case"]


class Applicability(str, Enum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ReasonCode(str, Enum):
    #: The QoI is not a sum or blend over mechanisms, so removing one is undefined.
    QOI_DOES_NOT_DECOMPOSE = "qoi_does_not_decompose"
    #: The mechanisms are coupled: you cannot switch one off and hold the rest fixed.
    MECHANISMS_NOT_SEPARABLE = "mechanisms_not_separable"
    #: No calibration window is recorded, so "outside calibration" has no meaning.
    NO_CALIBRATION_WINDOW = "no_calibration_window"
    #: No matched ablation is obtainable for this case.
    NO_ABLATION_AVAILABLE = "no_ablation_available"
    #: Everything needed is present.
    SATISFIED = "satisfied"


@dataclass(frozen=True)
class ScreenResult:
    case_id: str
    qoi: str
    applicability: Applicability
    reason_code: ReasonCode
    rationale: str
    evidence_state: EvidenceState
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_declarative(self) -> bool:
        return self.evidence_state is EvidenceState.DECLARATIVE


def screen_case(
    case_id: str,
    qoi: str,
    *,
    qoi_decomposes: bool | None,
    mechanisms_separable: bool | None,
    has_calibration_window: bool | None,
    ablation_available: bool | None,
    evidence_state: EvidenceState,
    notes: tuple[str, ...] = (),
) -> ScreenResult:
    """Screen a case. `None` for any precondition means "not established", which is
    INSUFFICIENT_EVIDENCE -- distinct from establishing that it is false."""

    def _r(app: Applicability, code: ReasonCode, why: str) -> ScreenResult:
        return ScreenResult(
            case_id=case_id, qoi=qoi, applicability=app, reason_code=code,
            rationale=why, evidence_state=evidence_state, notes=tuple(notes),
        )

    checks = (
        (qoi_decomposes, ReasonCode.QOI_DOES_NOT_DECOMPOSE,
         f"the quantity of interest ({qoi}) does not decompose over mechanisms, so "
         f"removing one is not defined"),
        (mechanisms_separable, ReasonCode.MECHANISMS_NOT_SEPARABLE,
         "the mechanisms are coupled: one cannot be switched off while the others are "
         "held fixed, so an ablation would change more than the mechanism under test"),
        (has_calibration_window, ReasonCode.NO_CALIBRATION_WINDOW,
         "no calibration window is recorded, so 'outside calibration' has no meaning "
         "for this case"),
        (ablation_available, ReasonCode.NO_ABLATION_AVAILABLE,
         "no matched ablation is obtainable, so the counterfactual cannot be formed"),
    )

    for value, code, why in checks:
        if value is None:
            return _r(Applicability.INSUFFICIENT_EVIDENCE, code,
                      f"not established whether {why.split(',')[0]}")
        if value is False:
            return _r(Applicability.NOT_APPLICABLE, code, why)

    return _r(Applicability.APPLICABLE, ReasonCode.SATISFIED,
              "quantity of interest decomposes, mechanisms are separable, a calibration "
              "window is recorded, and a matched ablation is obtainable")
