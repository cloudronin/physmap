"""PhysMAP Forrest mini-channel vehicle — D3 differentiator substrate.

Build the substrate for the D3 differentiator experiment. Source paper:
Forrest, Hu, Buongiorno, McKrell (2014), "Convective Heat Transfer in a High
Aspect Ratio Mini-Channel Heated on One Side," J. Heat Transfer 138(2):021704,
DOI: 10.1115/1.4031646 / OSTI 1295764 / SAND2014-18834J. Geometry confirmed
against the 2012 RERTR predecessor paper (Forrest, Buongiorno, McKrell, Hu).

What this substrate is for (one sentence): a steady-state internal-flow
heat-transfer vehicle with three cells defined by Re band — BENIGN
(10k≤Re≤70k, geometry-MATCHED Modified Sparrow-Cur MAE 6.1%, paper Table 4),
TRANSITION (4k≤Re<10k, textbook turbulent closures not validated; paper's
semi-analytic Eq. 24 covers it at MAE 4.6%), and SUB_CRITICAL_LAMINAR
(Re<4k, critical Re between 3500-4000 per Eq. 18; turbulent closures
overpredict by ~40% at Pr=5.4 per paper body p.7) — suitable for testing
whether PhysMAP's corpus-error signal catches divergence that
input-distribution novelty detectors miss or weakly signal.

Geometry-matched primary closure (resolves the Lance & Smith trap):
  The primary closure tested on this substrate is Modified Sparrow-Cur
  (Forrest 2014 Eq. 7, corpus entry
  `modified-sparrow-cur-asym-narrow-rect-channel-2014`), which IS designed
  for one-sided heated narrow rectangular channels. Circular-pipe closures
  (Gnielinski, Dittus-Boelter, Petukhov, Sieder-Tate) are computed for
  cross-comparison against Forrest's Table 4 MAEs but are NOT the primary
  test target. Testing the differentiator on the geometry-mismatched
  circular-pipe closures would contaminate the result with geometry
  mismatch — exactly the trap that produced the Lance & Smith
  confined-geometry finding. By using the matched closure, the
  divergence at Re<4k and the transition is cleanly attributable to
  closure validity-edge failure (Re below the closure's validated lower
  bound 10000), not to geometry incompatibility.

Build discipline (mirrors D1 / Lance & Smith):
  - Truth column = measured Nu ONLY. Refuse fitted-correlation truth
    (Eq. 19 and Eq. 24 are the AUTHORS' own fits; cannot serve as truth —
    independence guard).
  - Steady-state → no temporal-autocorrelation discount on effective n.
    Each (Re, Pr) operating point is a genuinely independent sample.
  - Inspect before blessing (D1 done-gate discipline).

Two corrections wired in from the build directive:

  Correction 1 — baseline-invisibility is the MEASURED OUTCOME of D3,
  NOT passed by reading the paper. D3 measures the SIGNAL-GAP between
  both baseline detectors (distance-to-training AND prediction-variance/
  ensemble) and the corpus signal at the transition cell. Both detectors
  must be quiet simultaneously at the transition for the truly-invisible
  bar; gap-against-threshold is the weaker bar. Which bar counts as a win
  is pre-registered BEFORE the experiment runs.

  Correction 2 — Mudhafar (canonical smooth pipe, separate substrate) is
  the baseline positive control. Built deliberately, not as an
  afterthought. Mudhafar's divergent cells (small d, rough surface) are
  baseline-VISIBLE by design. Same detectors that fire on Mudhafar's
  divergence should stay quiet/weak on Forrest's transition — the
  contrast that makes the differentiator result interpretable.

Data-acquisition status:
  - OSTI 1295764 / 2014 paper read in full; confirms NO supplementary data
    tables. Table 2 (geometry) + Table 4 (cell-level MAE summary) are the
    only tables. Per-point Nu values are in Figures 5, 6, 7, 9.
  - Hybrid path: cell-level analysis from Table 4 + Eq. 24 model for the
    benign cell (no digitization); figure digitization of Fig. 5 for the
    transition+sub-critical cells where the differentiator signal lives.
    Author-data request as long-tail clean path.

The raw-data ingest function (forrest_to_rows) is parameterized by a
caller-supplied data table; the three ingest stubs below
(from_thesis_table / from_digitization / from_author_csv) raise
NotImplementedError until the data-acquisition decision lands.

Entry (post-data-acquisition): python -m physmap.forrest_inspect
"""

from __future__ import annotations

from typing import Literal


# Cleanup 5 part 2: the Forrest legacy closure functions, calibration-range
# constants, ForrestRow dataclass, forrest_to_rows loader, and the three
# data-acquisition stubs have all been retired. Their canonical homes:
#   - closures/formulas.py        (Pohlhausen, McAdams, Churchill,
#                                   Sparrow-Cur, Gnielinski, Dittus-Boelter,
#                                   Petukhov, Sieder-Tate formulas)
#   - closures/registry.py        (re_range, pr_range, geometry_class,
#                                   status)
#   - vehicles/forrest.yaml       (geometry + data_source)
#   - substrate_loaders.py        (engine-driven row build)
#
# This module retains ONLY:
#   - geometry constants (CHANNEL_*) documenting the rig dimensions
#   - the Cell Literal type + cell_assignment helper (still imported by
#     forrest_resolvability)
#   - the Re-band thresholds + Forrest Table-4 reference MAE dicts
#     (descriptive constants used by reports + analysis scripts)


# ── geometry + fluid properties ──────────────────────────────────────────────
# From the Forrest et al. predecessor paper (2012 RERTR conference paper),
# Table 1, confirmed in SAND2014-18834J / OSTI 1295764:
#   - High-aspect-ratio rectangular channel, α* = gap/width = 0.035 (≈29:1
#     width:gap convention).
#   - Hydraulic diameter Dh = 3.78 mm (Table 1, explicit). The 2*gap = 3.92 mm
#     value is the parallel-plates asymptote; the actual finite-width
#     rectangular-channel Dh = 4·A_flow / P_w gives 3.78. The paper uses Dh
#     as the characteristic length in its Re and Nu definitions.
#   - One-sided heating (asymmetric); the heated wall is one of the long
#     faces (51 mm × 305 mm heated). The Nu is the channel-averaged for the
#     heated wall.
#   - Working fluid: water. Pr range 2.2 – 5.4 (corresponds to bulk
#     temperatures of roughly 60-95°C; lower Pr = higher temperature).

# Geometry per Forrest, Buongiorno, McKrell, Hu (2012 RERTR conference paper),
# Table 1 — the predecessor publication to the 2014 J. Heat Transfer paper.
# Same experimental rig; the 2012 paper's Table 1 gives the dimensions
# explicitly. (The 2014 paper extends the dataset to more Pr values and
# higher Re, but uses the same rig.)
CHANNEL_GAP_MM = 1.96
CHANNEL_WIDTH_MM = 56.0
CHANNEL_LENGTH_MM = 483.0
CHANNEL_HEATED_LENGTH_MM = 305.0
CHANNEL_HEATED_WIDTH_MM = 51.0
CHANNEL_ASPECT_RATIO_ALPHA_STAR = CHANNEL_GAP_MM / CHANNEL_WIDTH_MM  # = 0.035, per Table 1
CHANNEL_ASPECT_RATIO_INVERSE = CHANNEL_WIDTH_MM / CHANNEL_GAP_MM     # = 28.6, the
                                                                     # "high aspect ratio"
                                                                     # convention (~29:1)
CHANNEL_HYDRAULIC_DIAMETER_MM = 3.79   # Forrest 2014 Table 2 explicit value
                                       # (2012 RERTR paper Table 1 had 3.78;
                                       # 2014 paper supersedes with 3.79).
                                       # NOT 2*gap=3.92: the 2*gap limit is the
                                       # parallel-plates asymptote; the actual
                                       # rectangular-channel Dh = 4·A_flow/P_w
                                       # accounts for finite width.

# Closure-bound calib ranges per the Track C corpus entries.
#
# PRIMARY (geometry-matched) closure for this substrate:
#   Modified Sparrow-Cur (Forrest 2014 Eq. 7) — Nu = 0.036·Re^0.76·Pr^(1/3).
#   Corpus entry: modified-sparrow-cur-asym-narrow-rect-channel-2014.
#   This is the ONLY corpus closure with explicit one-sided-heating geometry
#   dependence and is the right closure for Forrest's narrow rectangular
#   mini-channel. Its validity range is what should drive the
#   benign/transition/laminar cell-validity gates.
#
# COMPARISON (geometry-mismatched, circular-pipe) closures:
#   Gnielinski, Dittus-Boelter, Petukhov, Sieder-Tate. These are computed
#   alongside Sparrow-Cur for cross-comparison against Forrest 2014 Table 4
#   MAEs, but the closure-validity test runs on Sparrow-Cur (the matched
#   closure). Testing the differentiator on Gnielinski would contaminate
#   the result with geometry mismatch (the same trap that produced the
#   Lance & Smith confined-geometry finding), so the matched closure is
#   the primary; circular-pipe closures are reported for reference only.



# ── cell definitions ─────────────────────────────────────────────────────────
# Cell-band thresholds match Forrest 2014 paper's EXPLICIT characterizations
# (revised after reading the full paper; the prior recon-memory had four
# cells with wrong boundaries).
#
#   - Re < 4,000:       SUB_CRITICAL / LAMINAR. Critical Re between 3,500
#                       and 4,000 (Eq. 18). At Re < 4,000 the flow is
#                       likely still laminar. Paper body, p.7: the
#                       Gnielinski correlation for Pr = 5.4 (top curve in
#                       Fig. 6) overpredicts the Nusselt number by about
#                       40%, indicating the closure is being applied
#                       below its validity. Modified Sparrow-Cur (turbulent
#                       form, Re^0.76) would similarly over-predict here.
#
#   - 4,000 ≤ Re < 10,000: TRANSITION. Flow becomes fully turbulent at
#                          Re ≈ 7,000 per the friction-factor data (paper
#                          p.5). Textbook turbulent closures are not
#                          validated here — Forrest's Table 4 MAEs are
#                          reported only for Re ≥ 10,000. The paper's
#                          semi-analytic Eq. (24) covers 4k–70k at MAE
#                          4.6%.
#
#   - 10,000 ≤ Re ≤ 70,000: BENIGN (turbulent). Textbook closures applicable
#                            here with MAE 6.1-15.2% (Table 4). NO sub-cell
#                            structure within this range — Gnielinski's
#                            8.4% MAE is reported uniformly across this
#                            interval, not split by sub-range.
#
# This is THREE cells, not four. The prior `divergent_high_re` (Re > 35k)
# was a misreading of Eq. (19)'s 10k–35k validity (the authors' OWN power
# law fit, limited to the range where a simple power law is adequate);
# it is NOT a textbook-closure divergence cell.

Cell = Literal[
    "benign_turbulent",                # do-no-harm cell: closures perform per Table 4
    "transition_excluded_indeterminate", # excluded: closure-divergence signal within measurement floor
    "sub_critical_laminar",            # divergent test cell: ~50-80% closure over-prediction
]

BENIGN_RE_LO = 10000.0          # paper Table 4 lower bound for all textbook closures
BENIGN_RE_HI = 70000.0          # paper Table 4 upper bound for all textbook closures
TRANSITION_RE_LO = 4000.0       # paper p.7 / Fig. 5 region — EXCLUDED, not benign
TRANSITION_RE_HI = 10000.0
SUB_CRITICAL_RE_HI = 4000.0     # paper Eq. 18: Re_crit between 3500-4000


def cell_assignment(Re: float) -> Cell:
    """Per-row cell label by Re band. Bands READ FROM the Forrest 2014 paper
    (Table 4 + Eq. 18 + p.7 cell-by-cell discussion), NOT derived from the
    data (which would be a leak).

    Cell roles in the D3 differentiator (per the build directive):
      - `sub_critical_laminar`: the ONLY divergent test cell. Visible n=2
        in Fig 5 at Re ~ 3800, Pr=5.4. Both Sparrow-Cur and Gnielinski
        over-predict by ~50-80% (resolvable: |gap|/unc > 3).
      - `transition_excluded_indeterminate`: excluded from the test cell
        set. Resolvability triage on visual estimates from Fig 5 (n=12)
        shows median |gap|/unc ~ 0.4-0.5 — within the measurement-
        uncertainty floor. Paper text calls the transition "conservative
        estimate" territory, which is a safety statement not a validity
        statement, so the cell is indeterminate (NOT benign-relabeled).
      - `benign_turbulent`: do-no-harm cell. Closures perform per Table 4
        (Sparrow-Cur MAE 6.1%, Gnielinski 8.4%, etc.). The corpus signal
        is expected to be quiet here.
    """
    if Re < SUB_CRITICAL_RE_HI:
        return "sub_critical_laminar"
    if Re < TRANSITION_RE_HI:
        return "transition_excluded_indeterminate"
    return "benign_turbulent"   # 10000 ≤ Re; covers full validated turbulent range


# Paper Table 4 reference MAE numbers (2.2 ≤ Pr ≤ 5.4, Re per cell)
# Used for cell-level comparison against corpus signal predictions.
# Recorded here as ground-truth references; the live closure-vs-truth
# comparison still runs row-by-row on measured Nu when data is in hand.
TABLE_4_MAES_BENIGN = {
    "modified-sparrow-cur-asym-narrow-rect-channel-2014": 0.061,   # 6.1% — GEOMETRY-MATCHED, lowest
    "dittus-boelter-1930":     0.064,   # 6.4%
    "modified-colburn":        0.073,   # 7.3% (not in corpus)
    "gnielinski-1976":         0.084,   # 8.4%
    "petukhov-1970":           0.114,   # 11.4% (not currently in corpus)
    "sieder-tate-1936":        0.152,   # 15.2%
    "barrow-one-sided":        0.204,   # 20.4% (worst — not in corpus)
}
TABLE_4_FORREST_FITS = {
    "Empirical fit Eq.(19) [10000-35000]":  0.038,   # 3.8%
    "Semi-analytic Eq.(24) [4000-70000]":   0.046,   # 4.6%
}



