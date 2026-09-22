"""Deterministic explanation of one benchmark cell.

Every rendering states, in the header, which KIND of claim the cell is. That is not
decoration. The seven-vehicle benchmark measures closure validity and surrogate
observability; it measures nothing about causal materiality.

**And the reason cannot be "no vehicle is close to the causal case", because one is.**
`jin_sco2_buoyancy` is a mixed-convection vertical tube whose failure driver is a
buoyancy parameter -- geometrically the nearest thing here to the NAFEMS mixed-convection
pipe. It is the cell most likely to be mistaken for causal evidence, and it is not: it
asks whether `Bu` is observable to the surrogate. It computes no ablation, no
counterfactual, no materiality and no metric. Its truth is a measured heat-transfer
coefficient, not a quantity of interest with a mechanism removed.

So the disclaimer names it rather than waving at geometry, and a test asserts that it
does. A reader who takes any cell here as support for the causal result has drawn a
conclusion the data cannot carry.

Templates only. Same cell, same bytes.
"""

from __future__ import annotations

from physmap.benchmarks.registry import DataQuality, Redistribution, get
from physmap.core.signals import SignalKind
from physmap.release import CURRENT_RELEASE_STATE

__all__ = ["BENCHMARK_MEASURES", "render_cell", "NOT_EVIDENCE_FOR",
           "NEAREST_TO_CAUSAL_CASE"]

#: What this benchmark measures. Both are closure/observability claims.
BENCHMARK_MEASURES = (SignalKind.CLOSURE_VALIDITY, SignalKind.OBSERVABILITY)

#: What it does not measure, and must never be quoted as supporting.
NOT_EVIDENCE_FOR = SignalKind.CAUSAL_MATERIALITY

#: The vehicle closest to the causal case, and therefore the one most likely to be
#: mistaken for evidence of it. Named explicitly in every rendering.
NEAREST_TO_CAUSAL_CASE = "jin_sco2_buoyancy"

_OUTCOME_MEANING = {
    "PHYSMAP_WINS": "the closure guard fired where the statistical baselines were silent",
    "PARTIAL": "the guard fired, but the baselines were not wholly silent",
    "DO_NO_HARM": "the guard stayed quiet where the baselines already saw the failure",
    "BASELINE_VISIBLE": "the baselines saw it; the guard correctly claims no credit",
}

_REDISTRIBUTION_LINE = {
    Redistribution.CLEAR: "source data ships under an affirmative licence",
    Redistribution.NO_LICENCE_FACTS_BASIS:
        "source data ships WITHOUT a licence, on a facts basis (see NOTICE)",
    Redistribution.AGAINST_PUBLISHER_TERMS:
        "source data ships AGAINST an express publisher term (see NOTICE)",
    Redistribution.EXCLUDED_BY_DECISION: "source data does not ship",
}


def render_cell(cell: dict, *, recomputed: bool = False) -> str:
    vid = cell["vehicle_id"]
    rec = get(vid)
    kinds = " + ".join(k.value for k in BENCHMARK_MEASURES)

    lines = [
        f"{vid}  [{cell['empirical_outcome']}]",
        f"  measures        {kinds}",
        f"  NOT evidence for {NOT_EVIDENCE_FOR.value} -- no cell here computes an",
        f"                  ablation, a counterfactual, a materiality or any metric.",
        f"                  Not even {NEAREST_TO_CAUSAL_CASE}, which IS a mixed-convection",
        f"                  vertical tube and is the closest vehicle to the causal case:",
        f"                  it asks whether its buoyancy parameter is observable, nothing more.",
        "",
        f"  domain          {cell['domain']}",
        f"  regime          {cell.get('regime', 'n/a')}",
        f"  failure driver  {cell['failure_var']} ({cell['failure_observability']})",
        f"  surrogate sees  {', '.join(cell.get('surrogate_inputs', []))}",
        f"  train / test    {cell.get('n_train')} / {cell.get('n_test')}",
        "",
        f"  outcome         {cell['empirical_outcome']} -- "
        f"{_OUTCOME_MEANING.get(cell['empirical_outcome'], 'see the benchmark report')}",
        f"  guard passed    {cell.get('observability_guard_passed')}",
        f"  numbers from    {'this run (recomputed)' if recomputed else 'the banked matrix'}",
    ]
    if cell.get("caveat"):
        lines.append(f"  caveat          {cell['caveat']}")
    if cell.get("rationale"):
        lines.append(f"  rationale       {cell['rationale']}")

    lines.append("")
    lines.append(f"  provenance      {rec.source}")
    lines.append(f"  values          {rec.how_values_were_produced}")
    lines.append(f"  redistribution  {_REDISTRIBUTION_LINE[rec.redistribution]}")

    if rec.quality is not DataQuality.BENCHMARK_GRADE:
        lines.append("")
        lines.append(f"  DATA QUALITY    {rec.quality.value.upper()}")
        lines.append(f"                  {rec.quality_note}")

    lines.append("")
    lines.append(f"  release         {CURRENT_RELEASE_STATE.value} -- this build reports "
                 f"no precision, recall or F1.")
    return "\n".join(lines)
