"""Causal materiality by ablation counterfactual.

    materiality(m, x, q) = 1 - q_ablated / q_full

How much of the quantity of interest `q` at operating point `x` goes away when mechanism
`m` is removed. Both numbers come from outside this module, and both are persisted on the
result, because a materiality whose inputs you cannot see is a number you cannot check.

WHY THIS IS A REWRITE AND NOT A PORT
------------------------------------
The monorepo computes a contribution FRACTION: each mechanism's declared contribution
divided by the sum over all mechanisms. For exactly two mechanisms whose contributions
are (q_ablated, q_full - q_ablated), that fraction happens to equal 1 - q_ablated/q_full.
The arithmetic agrees; the meaning does not.

A fraction of declared contributions is a bookkeeping identity -- it sums to one by
construction, no matter what the mechanisms are or whether the decomposition is real. A
counterfactual is a claim about what the world does when you remove something, and it can
be wrong, checked, and refused. Only the second is evidence.

The practical consequence is the one that matters. Under the fraction, a mechanism with
no recorded contribution gets 0.0 and is silently judged immaterial. Under the
counterfactual, a missing input yields INSUFFICIENT_EVIDENCE and no verdict at all. An
inferred zero is the failure mode this whole project is about: an absence of evidence
rendered as evidence of absence, in a number that looks just like a real one.

REFUSED PROVENANCE
------------------
An ablation is only a counterfactual if the ablated run is otherwise the same run. A
flat-plate correlation evaluated for a pipe is not an ablation of anything; it is a
different formula for a different geometry. It is refused by name rather than merely
discouraged, because it is cheap, available, and gives plausible-looking numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from physmap.core.mechanism import Mechanism
from physmap.core.signals import Signal, SignalKind
from physmap.release import EvidenceState

__all__ = [
    "AblationProvenance",
    "REFUSED_PROVENANCE",
    "MaterialityStatus",
    "AblationInputs",
    "MaterialityResult",
    "estimate_materiality",
    "materiality_signal",
]


class AblationProvenance(str, Enum):
    """Where the ablated value came from. Not a label -- a gate."""

    #: Same mesh, same boundary conditions, mechanism switched off. The real thing.
    MATCHED_ABLATION = "matched_ablation"
    #: A correlation for THIS geometry with the mechanism absent. Weaker, admissible.
    GEOMETRY_MATCHED_CORRELATION = "geometry_matched_correlation"
    #: A correlation for a DIFFERENT geometry. Refused; see the module docstring.
    FLAT_PLATE_CORRELATION = "flat_plate_correlation"


REFUSED_PROVENANCE: frozenset[AblationProvenance] = frozenset(
    {AblationProvenance.FLAT_PLATE_CORRELATION}
)


class MaterialityStatus(str, Enum):
    ESTIMATED = "estimated"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REFUSED_PROVENANCE = "refused_provenance"


@dataclass(frozen=True)
class AblationInputs:
    """The two numbers the estimate is made of, kept so a reader can redo the division."""

    qoi_full: float | None = None
    qoi_ablated: float | None = None
    provenance: AblationProvenance | None = None

    def complete(self) -> bool:
        return (
            self.qoi_full is not None
            and self.qoi_ablated is not None
            and self.provenance is not None
        )

    def missing(self) -> list[str]:
        return [
            name
            for name, v in (
                ("qoi_full", self.qoi_full),
                ("qoi_ablated", self.qoi_ablated),
                ("provenance", self.provenance),
            )
            if v is None
        ]


@dataclass(frozen=True)
class MaterialityResult:
    """An estimate, or a stated reason there is none.

    `value` is None unless `status` is ESTIMATED. There is no zero-valued failure: a
    materiality of 0.0 means the ablation genuinely changed nothing.
    """

    mechanism_id: str
    qoi: str
    status: MaterialityStatus
    inputs: AblationInputs
    evidence_state: EvidenceState
    reason: str
    value: float | None = None

    def __post_init__(self) -> None:
        if self.status is MaterialityStatus.ESTIMATED and self.value is None:
            raise ValueError("an ESTIMATED materiality must carry a value")
        if self.status is not MaterialityStatus.ESTIMATED and self.value is not None:
            raise ValueError(
                f"materiality status {self.status.value} must not carry a value; "
                f"got {self.value!r}. A failed estimate has no number, not a zero."
            )

    def is_usable(self) -> bool:
        return self.status is MaterialityStatus.ESTIMATED


def estimate_materiality(
    mechanism: Mechanism,
    qoi: str,
    inputs: AblationInputs,
    *,
    evidence_state: EvidenceState,
) -> MaterialityResult:
    """Compute 1 - q_ablated/q_full, or say why not."""

    def _fail(status: MaterialityStatus, reason: str) -> MaterialityResult:
        return MaterialityResult(
            mechanism_id=mechanism.mechanism_id, qoi=qoi, status=status,
            inputs=inputs, evidence_state=evidence_state, reason=reason, value=None,
        )

    if inputs.provenance in REFUSED_PROVENANCE:
        return _fail(
            MaterialityStatus.REFUSED_PROVENANCE,
            f"ablation provenance {inputs.provenance.value!r} is refused: it is a "
            f"correlation for a different geometry, not an ablation of this case.",
        )

    if not inputs.complete():
        return _fail(
            MaterialityStatus.INSUFFICIENT_EVIDENCE,
            f"missing ablation input(s): {', '.join(inputs.missing())}. No materiality "
            f"is inferred; an absent input is not a zero.",
        )

    if inputs.qoi_full == 0.0:
        return _fail(
            MaterialityStatus.INSUFFICIENT_EVIDENCE,
            "qoi_full is zero, so the materiality fraction is undefined.",
        )

    value = 1.0 - (inputs.qoi_ablated / inputs.qoi_full)
    return MaterialityResult(
        mechanism_id=mechanism.mechanism_id, qoi=qoi,
        status=MaterialityStatus.ESTIMATED, inputs=inputs,
        evidence_state=evidence_state,
        reason=(
            f"1 - {inputs.qoi_ablated:g}/{inputs.qoi_full:g} = {value:.4g} "
            f"({inputs.provenance.value})"
        ),
        value=value,
    )


def materiality_signal(
    mechanism: Mechanism,
    result: MaterialityResult,
    *,
    theta: float,
) -> Signal:
    """The flag rule: fire iff the mechanism is OUTSIDE its calibration window AND its
    materiality reaches theta.

    Both halves are required. Out-of-range alone is the naive box check, which fires on
    every excursion however irrelevant. Material alone says nothing is wrong -- a
    mechanism can dominate the QoI and be perfectly well calibrated.

    An unusable materiality cannot fire. It also cannot clear: the honest output is a
    quiet signal whose rationale states that the question was not answered.
    """
    outside = mechanism.outside_calibration()
    window = mechanism.window.describe()

    if not result.is_usable():
        return Signal(
            kind=SignalKind.CAUSAL_MATERIALITY, fired=False, value=None, threshold=theta,
            rationale=(
                f"causal_materiality: NOT ASSESSED for {mechanism.name} "
                f"({result.status.value}) -- {result.reason} "
                f"The mechanism is {'outside' if outside else 'inside'} {window}, but "
                f"without a materiality this is not a causal verdict either way."
            ),
        )

    material = result.value >= theta
    if outside and material:
        rationale = (
            f"causal_materiality: FIRED. {mechanism.name} is outside {window} "
            f"(operating value {mechanism.operating_value:g}) and carries materiality "
            f"{result.value:.3g} >= theta={theta:g} for {result.qoi}. {result.reason}"
        )
    elif outside:
        rationale = (
            f"causal_materiality: quiet. {mechanism.name} is outside {window} but its "
            f"materiality {result.value:.3g} < theta={theta:g} for {result.qoi}, so the "
            f"excursion does not reach the quantity of interest. {result.reason}"
        )
    else:
        rationale = (
            f"causal_materiality: quiet. {mechanism.name} is within {window}; "
            f"materiality {result.value:.3g} is not a defect on its own."
        )

    return Signal(
        kind=SignalKind.CAUSAL_MATERIALITY,
        fired=bool(outside and material),
        value=result.value, threshold=theta, rationale=rationale,
    )


def with_inputs(result: MaterialityResult, **kwargs) -> MaterialityResult:
    """Return a copy with replaced ablation inputs. Used by fixtures and tests."""
    return replace(result, inputs=replace(result.inputs, **kwargs))
