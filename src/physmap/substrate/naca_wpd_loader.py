"""PhysMAP D3 — NACA TN-1451 WPD CSV loader.

Loads WebPlotDigitizer-produced CSVs in the schema locked at
physmap/results/naca_digitization/WPD_DIGITIZATION_SPEC.md.

Per prereg v0.3 non-negotiable #5: source='wpd-csv' is the BANKED tag;
visual-estimate-rendered-pdf-naca rows are NOT banked.

Per user 2026-06-05 directive on Fig 21:
  The Re=26,100 curve in Fig 21 (right-angle bend) is still descending at
  x/D=17 (hasn't reached asymptote within plotted range). Those rows are:
    - EXCLUDED from both verdict cells (not in subcrit, not in benign)
    - TAGGED 'asymptote_not_reached' in meta
    - RETAINED as recorded observation for the alignment analysis
  This loader enforces the exclusion automatically when figure='Fig21' AND
  Re=26100 AND x_over_D>=10.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from physmap.substrate.naca_tn1451 import NACARow


REQUIRED_COLUMNS = (
    "row", "Re", "Pr", "x_over_D", "fc_Btu_hr_ft2_F", "fc_unc_wpd",
    "Nu_meas", "Nu_unc_paper_pct", "Nu_unc_digitization_abs",
    "source", "figure", "entering_condition", "note",
)

# Fig 21 Re=26,100 asymptote_not_reached rule (locked per user 2026-06-05)
FIG21_EXCLUDED_FIGURE = "Fig21"
FIG21_EXCLUDED_RE = 26100.0
FIG21_EXCLUDED_X_OVER_D_MIN = 10.0
ASYMPTOTE_NOT_REACHED_TAG = "asymptote_not_reached"


@dataclass
class LoadedWPDData:
    """Output of load_wpd_csv: rows usable in the verdict + the alignment-only
    rows + per-figure metadata."""
    rows_for_verdict: list[NACARow]
    rows_alignment_only: list[NACARow]       # asymptote_not_reached etc.
    figure_metadata: dict[str, dict]
    n_total_loaded: int


def _validate_header(header: Sequence[str], path: Path) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise ValueError(
            f"WPD CSV {path} missing required columns: {missing}. "
            f"See physmap/results/naca_digitization/WPD_DIGITIZATION_SPEC.md "
            f"for the canonical schema."
        )


def _is_fig21_re26100_asymptote(figure: str, Re: float, x_over_D: float) -> bool:
    return (
        figure == FIG21_EXCLUDED_FIGURE
        and abs(Re - FIG21_EXCLUDED_RE) < 50.0  # tolerance for digitization noise on Re
        and x_over_D >= FIG21_EXCLUDED_X_OVER_D_MIN
    )


def load_wpd_csv(path: Path) -> LoadedWPDData:
    """Load a single WPD CSV and produce LoadedWPDData with the Fig 21
    exclusion rule applied."""
    path = Path(path)
    rows_for_verdict: list[NACARow] = []
    rows_alignment_only: list[NACARow] = []

    with open(path) as f:
        # Strip lines starting with '#' (comment headers WPD/user may add)
        reader = csv.DictReader(
            (line for line in f if not line.lstrip().startswith("#"))
        )
        _validate_header(reader.fieldnames or [], path)
        for r in reader:
            source = r["source"].strip()
            if source != "wpd-csv":
                raise ValueError(
                    f"WPD CSV {path} row {r['row']} has source='{source}'; "
                    f"only 'wpd-csv' is banked. Use a separate file with "
                    f"source='visual-estimate-...' if needed."
                )
            figure = r["figure"].strip()
            Re = float(r["Re"])
            Pr = float(r["Pr"])
            x_over_D = float(r["x_over_D"])
            Nu_meas = float(r["Nu_meas"])
            Nu_unc_dig = float(r["Nu_unc_digitization_abs"])
            # Paper unc = 3% per prereg (line-text). Stored as fraction.
            Nu_unc_paper_pct_frac = float(r["Nu_unc_paper_pct"])
            paper_unc_abs = Nu_meas * Nu_unc_paper_pct_frac
            # Combined unc: quadrature of paper (absolute) + digitization (absolute)
            total_unc = float((paper_unc_abs ** 2 + Nu_unc_dig ** 2) ** 0.5)

            # Build NACARow
            note = r.get("note", "").strip()
            if _is_fig21_re26100_asymptote(figure, Re, x_over_D):
                note = (
                    f"{note}; {ASYMPTOTE_NOT_REACHED_TAG}: Fig 21 Re=26,100 "
                    f"curve still descending at x/D=17; excluded from verdict "
                    f"cells; retained for alignment analysis."
                ).strip("; ")

            nrow = NACARow(
                Re=Re,
                Pr=Pr,
                Nu_meas=Nu_meas,
                x_over_D=x_over_D,
                Nu_unc=total_unc,
                entering_condition=r["entering_condition"].strip(),
                figure=figure,
                source=source,
                digitization_uncertainty=Nu_unc_dig,
            )
            # Attach the note as an attribute (NACARow doesn't have a note field
            # by default; mutate __dict__ for forward-compatibility with the
            # alignment / verdict reporting):
            nrow.__dict__["wpd_note"] = note

            if _is_fig21_re26100_asymptote(figure, Re, x_over_D):
                rows_alignment_only.append(nrow)
            else:
                rows_for_verdict.append(nrow)

    fig_meta = {}
    n_loaded = len(rows_for_verdict) + len(rows_alignment_only)
    for r in rows_for_verdict + rows_alignment_only:
        figure_id = r.figure
        if figure_id not in fig_meta:
            fig_meta[figure_id] = {
                "n_total": 0, "n_verdict": 0, "n_alignment_only": 0,
                "Re_values": set(), "entering_condition": r.entering_condition,
            }
        fig_meta[figure_id]["n_total"] += 1
        fig_meta[figure_id]["Re_values"].add(round(r.Re, 0))
    for r in rows_for_verdict:
        fig_meta[r.figure]["n_verdict"] += 1
    for r in rows_alignment_only:
        fig_meta[r.figure]["n_alignment_only"] += 1
    for fid in fig_meta:
        fig_meta[fid]["Re_values"] = sorted(fig_meta[fid]["Re_values"])

    return LoadedWPDData(
        rows_for_verdict=rows_for_verdict,
        rows_alignment_only=rows_alignment_only,
        figure_metadata=fig_meta,
        n_total_loaded=n_loaded,
    )


def load_wpd_directory(dir_path: Path, glob_pattern: str = "wpd_fig*.csv"
                       ) -> LoadedWPDData:
    """Load all WPD CSVs matching the pattern in a directory, merge into one
    LoadedWPDData. Per-figure metadata accumulates across files."""
    dir_path = Path(dir_path)
    files = sorted(dir_path.glob(glob_pattern))
    if not files:
        raise FileNotFoundError(
            f"No WPD CSVs found in {dir_path} matching '{glob_pattern}'. "
            f"Expected files like wpd_fig10.csv, wpd_fig15.csv, etc."
        )

    all_verdict: list[NACARow] = []
    all_alignment: list[NACARow] = []
    merged_meta: dict[str, dict] = {}
    n_total = 0
    for f in files:
        result = load_wpd_csv(f)
        all_verdict.extend(result.rows_for_verdict)
        all_alignment.extend(result.rows_alignment_only)
        n_total += result.n_total_loaded
        merged_meta.update(result.figure_metadata)

    return LoadedWPDData(
        rows_for_verdict=all_verdict,
        rows_alignment_only=all_alignment,
        figure_metadata=merged_meta,
        n_total_loaded=n_total,
    )
