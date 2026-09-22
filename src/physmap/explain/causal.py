"""Deterministic explanations for causal assessments.

Rendered templates. No LLM, no sampling, no model call anywhere in this path -- the same
inputs give byte-identical output, which is what makes an explanation checkable rather
than merely fluent.

Every rendering states its evidence state and its release state, so an explanation can
never be quoted as a performance claim that this build does not make.
"""

from __future__ import annotations

from physmap.applicability.screen import Applicability, ScreenResult
from physmap.core.signals import Signal
from physmap.materiality.estimator import MaterialityResult, MaterialityStatus
from physmap.release import CURRENT_RELEASE_STATE, EvidenceState

__all__ = ["render_screen", "render_materiality", "render_signal"]

_EVIDENCE_NOTE = {
    EvidenceState.SYNTHETIC_FIXTURE:
        "Synthetic fixture: inputs are constructed, not measured. No claim about any "
        "real case follows from this result.",
    EvidenceState.DECLARATIVE:
        "Declarative: the preconditions are asserted from the case description, not read "
        "from data. This demonstrates refusal logic; it is not an evidence-backed case.",
    EvidenceState.MEASURED:
        "Measured: inputs come from recorded data with stated provenance.",
}


def _footer(evidence_state: EvidenceState) -> str:
    return (
        f"  evidence: {evidence_state.value} -- {_EVIDENCE_NOTE[evidence_state]}\n"
        f"  release:  {CURRENT_RELEASE_STATE.value} -- this build reports no precision, "
        f"recall or F1."
    )


def render_screen(result: ScreenResult) -> str:
    verdict = {
        Applicability.APPLICABLE: "APPLICABLE",
        Applicability.NOT_APPLICABLE: "NOT APPLICABLE",
        Applicability.INSUFFICIENT_EVIDENCE: "INSUFFICIENT EVIDENCE",
    }[result.applicability]
    lines = [
        f"{result.case_id}  [{verdict}]",
        f"  quantity of interest: {result.qoi}",
        f"  reason code:          {result.reason_code.value}",
        f"  why:                  {result.rationale}",
    ]
    lines.extend(f"  note:                 {n}" for n in result.notes)
    lines.append(_footer(result.evidence_state))
    return "\n".join(lines)


def render_materiality(result: MaterialityResult) -> str:
    head = (
        f"{result.mechanism_id} -> {result.qoi}  "
        f"[{'materiality ' + format(result.value, '.4g') if result.is_usable() else result.status.value.upper()}]"
    )
    lines = [head, f"  why: {result.reason}"]
    if result.status is MaterialityStatus.ESTIMATED:
        i = result.inputs
        lines.append(
            f"  inputs: qoi_full={i.qoi_full:g}  qoi_ablated={i.qoi_ablated:g}  "
            f"provenance={i.provenance.value}"
        )
    else:
        lines.append("  inputs: incomplete -- no value is inferred, and none is a zero.")
    lines.append(_footer(result.evidence_state))
    return "\n".join(lines)


def render_signal(signal: Signal) -> str:
    state = "FIRED" if signal.fired else "quiet"
    value = "n/a" if signal.value is None else format(signal.value, ".4g")
    thresh = "n/a" if signal.threshold is None else format(signal.threshold, ".4g")
    return (
        f"{signal.kind.value}  [{state}]  value={value}  threshold={thresh}\n"
        f"  {signal.rationale}"
    )
