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
    Redistribution,
    banked_only_ids,
    licensed_ids,
    rerunnable_ids,
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

    out: list[str] = [
        matrix["benchmark"],
        "",
        f"All seven vehicles are reported. {len(rerunnable_ids())} of 7 are recomputed "
        f"in this checkout; {len(banked_only_ids())} are read from the banked matrix "
        f"because their source data is not redistributable.",
        "",
        "THIS COMMAND DOES NOT REPRODUCE ALL SEVEN VEHICLES.",
        "",
    ]

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
        out.append(
            "  Shipping is not licensing. Those three rest on the position that measured"
        )
        out.append(
            "  values are facts, and two of them are published against an express"
        )
        out.append(
            "  publisher term rather than under one. Only the numbers are redistributed;"
        )
        out.append(
            "  no paper, figure or PDF. They are removed on objection -- see NOTICE."
        )
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
        out.append(f"    basis       {v.redistribution_reason}")
        out.append("")

    out.append(coverage_note())
    out.append("")
    out.append("Full determinations: data/REDISTRIBUTION.md")
    return "\n".join(out)
