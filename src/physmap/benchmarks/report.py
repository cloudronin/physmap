"""Render the seven-vehicle benchmark, marking what was recomputed and what was not.

The report always shows all seven outcomes. Next to each it states whether that number
was recomputed in this checkout or read from the banked matrix, because a reader who
cannot tell the difference has been misled by omission.

It also states what the public subset costs in coverage. Losing five of seven vehicles is
not a uniform thinning -- it removes whole domains and whole outcome classes -- and a
report that printed two green rows without saying so would be flattering rather than
accurate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from physmap._paths import checkout_path
from physmap.benchmarks.registry import (
    VEHICLES,
    DataQuality,
    Redistribution,
    banked_only_ids,
    licensed_ids,
    rerunnable_ids,
    triage_only_ids,
    unlicensed_shipped_ids,
)

__all__ = ["load_banked_matrix", "render_report", "coverage_note"]

_MATRIX_PARTS = ("data", "benchmarks", "v0_4", "matrix_full_seven.json")

_STATUS_LABEL = {
    Redistribution.CLEAR: "ships, licensed",
    Redistribution.NO_LICENCE_FACTS_BASIS: "ships, NOT licensed (facts basis)",
    Redistribution.AGAINST_PUBLISHER_TERMS: "ships, AGAINST publisher terms",
    Redistribution.EXCLUDED_BY_DECISION: "banked only - source data excluded",
}


def load_banked_matrix() -> dict[str, Any]:
    """The committed seven-vehicle result. Counts, verdicts and our own thresholds only;
    it carries no third-party measurement values, which is why it can be published when
    five of the seven source datasets cannot."""
    p = checkout_path(*_MATRIX_PARTS, what="the banked v0.4 benchmark matrix")
    return json.loads(p.read_text("utf-8"))


def coverage_note() -> str:
    """What the public subset does and does not cover. Computed, so it cannot drift."""
    matrix = load_banked_matrix()
    cells = {c["vehicle_id"]: c for c in matrix["cells"]}
    rerun = set(rerunnable_ids())

    def _summarise(ids):
        doms = sorted({cells[i]["domain"] for i in ids if i in cells})
        outs = sorted({cells[i]["empirical_outcome"] for i in ids if i in cells})
        obs = sorted({cells[i]["failure_observability"] for i in ids if i in cells})
        return doms, outs, obs

    all_d, all_o, all_ob = _summarise(cells)
    pub_d, pub_o, pub_ob = _summarise(rerun)

    lines = [
        "What the rerunnable subset covers",
        "",
        f"  domains       full: {', '.join(all_d)}",
        f"                public: {', '.join(pub_d)}",
        f"  outcomes      full: {', '.join(all_o)}",
        f"                public: {', '.join(pub_o)}",
        f"  observability full: {', '.join(all_ob)}",
        f"                public: {', '.join(pub_ob)}",
    ]
    triage = set(triage_only_ids())
    degenerate = sorted({
        cells[i]["empirical_outcome"] for i in triage if i in cells
    })
    if degenerate:
        lines.append("")
        lines.append(
            f"  Outcome classes whose ONLY vehicle is not benchmark-grade: "
            f"{', '.join(degenerate)}."
        )
        for i in sorted(triage):
            c = cells.get(i)
            if c:
                lines.append(
                    f"    {c['empirical_outcome']} rests on {i}: "
                    f"n_train={c.get('n_train')}, n_test={c.get('n_test')} -- "
                    f"{c.get('rationale', c.get('caveat', ''))}"
                )
    lost_d = [d for d in all_d if d not in pub_d]
    lost_o = [o for o in all_o if o not in pub_o]
    if lost_d or lost_o:
        lines.append("")
        lines.append("  The subset is NOT a representative sample of the full matrix.")
        if lost_d:
            lines.append(f"  Domains absent from the rerun: {', '.join(lost_d)}")
        if lost_o:
            lines.append(f"  Outcome classes absent from the rerun: {', '.join(lost_o)}")
    return "\n".join(lines)


def render_report(rerun_results: dict[str, Any] | None = None) -> str:
    """The full seven-vehicle table.

    `rerun_results` maps vehicle_id to a freshly computed cell. Vehicles absent from it
    are reported from the bank and labelled as such.
    """
    matrix = load_banked_matrix()
    cells = {c["vehicle_id"]: c for c in matrix["cells"]}
    rerun_results = rerun_results or {}

    n = len(VEHICLES)
    ships, banked = len(rerunnable_ids()), len(banked_only_ids())
    recomputed = len([v for v in rerun_results if v in {x.vehicle_id for x in VEHICLES}])

    out: list[str] = [matrix["benchmark"], ""]

    # Computed, never hardcoded. Two different facts live here and a reader needs both:
    # how many datasets SHIP, and how many were actually RECOMPUTED in this invocation.
    # An earlier version asserted "does not reproduce all seven" as a constant; once the
    # last two datasets shipped that sentence became false, which is exactly how a
    # hardcoded honesty claim decays into a lie.
    out.append(
        f"All {n} vehicles are reported. {ships} of {n} ship their source data"
        + (f"; {banked} are banked only." if banked else " -- all of them.")
    )
    if recomputed == 0:
        out.append("")
        out.append(
            f"NOTHING WAS RECOMPUTED IN THIS RUN. Every number below is read from the "
            f"banked matrix. The substrate runner is not yet ported into this "
            f"repository."
        )
    elif recomputed < n:
        out.append("")
        out.append(
            f"THIS RUN RECOMPUTED {recomputed} OF {n} VEHICLES. The rest are read from "
            f"the banked matrix."
        )
    else:
        out.append("")
        out.append(f"All {n} vehicles were recomputed in this run.")
    out.append("")

    header = f"{'vehicle':34} {'domain':14} {'failure var':22} {'observability':14} {'outcome':17} source"
    out.append(header)
    out.append("-" * len(header))

    for v in VEHICLES:
        cell = rerun_results.get(v.vehicle_id) or cells.get(v.vehicle_id)
        if cell is None:
            out.append(f"{v.vehicle_id:34} (no banked result)")
            continue
        live = v.vehicle_id in rerun_results
        source = "RECOMPUTED" if live else _STATUS_LABEL[v.redistribution]
        out.append(
            f"{v.vehicle_id:34} {cell['domain']:14} {cell['failure_var']:22} "
            f"{cell['failure_observability']:14} {cell['empirical_outcome']:17} {source}"
        )

    out.append("")
    out.append(f"observability guards: {'all passed' if matrix['all_guards_passed'] else 'FAILED'}")
    out.append("")
    unlicensed = unlicensed_shipped_ids()
    if unlicensed:
        out.append("Redistribution basis -- read this before reusing any of this data")
        out.append("")
        out.append(
            f"  {len(licensed_ids())} of the {len(rerunnable_ids())} shipped datasets "
            f"carry affirmative permission: public domain or an open licence."
        )
        out.append(
            f"  {len(unlicensed)} ship WITHOUT a licence: {', '.join(unlicensed)}."
        )
        against = [
            v.vehicle_id for v in VEHICLES
            if v.redistribution is Redistribution.AGAINST_PUBLISHER_TERMS
        ]
        out.append(
            "  Shipping is not licensing. They rest on the position that measured values"
        )
        out.append("  are facts.")
        if against:
            out.append(
                f"  {len(against)} of them are published AGAINST an express publisher"
            )
            out.append(f"  term rather than under one: {', '.join(against)}.")
        out.append(
            "  Only the numbers are redistributed; no paper, figure or PDF. They are"
        )
        out.append("  removed on objection -- see NOTICE.")
        out.append("")
    triage = triage_only_ids()
    if triage:
        out.append("Data quality -- separate from redistribution, and not implied by it")
        out.append("")
        out.append(f"  Not benchmark-grade by their own account: {', '.join(triage)}.")
        out.append("  A dataset can be perfectly legal to publish and still be unfit to")
        out.append("  benchmark on. Their cells are reported so the weakness is")
        out.append("  inspectable, not so it can be cited.")
        out.append("")
    out.append("Provenance and redistribution basis")
    out.append("")
    for v in VEHICLES:
        out.append(f"  {v.vehicle_id}")
        out.append(f"    source      {v.source}")
        out.append(f"    values      {v.how_values_were_produced}")
        out.append(
            f"    ships       {'yes' if v.rerunnable else 'no'} ({v.redistribution.value})"
        )
        out.append(f"    licensed    {'yes' if v.licensed else 'NO'}")
        if v.quality is not DataQuality.BENCHMARK_GRADE:
            out.append(f"    QUALITY     {v.quality.value.upper()} -- {v.quality_note}")
        out.append(f"    basis       {v.redistribution_reason}")
        out.append("")

    out.append(coverage_note())
    out.append("")
    out.append("Full determinations: data/REDISTRIBUTION.md")
    return "\n".join(out)
