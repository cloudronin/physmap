"""PhysMAP D3 — NACA TN-1451 entrance-region vehicle substrate.

Source paper: Boelter, L.M.K., Young, G., Iversen, H.W. (1948).
"An Investigation of Aircraft Heaters XXVII — Distribution of Heat-Transfer
Rate in the Entrance Section of a Circular Tube." NACA Technical Note 1451,
July 1948. UC Berkeley. NTRS ID 19930082084. Public domain.

What this substrate is for (one sentence): a steady-state internal-flow
heat-transfer vehicle where MEASUREMENTS span both fully-developed
(x/D > 10) and developing (x/D < 5) regions at the SAME (Re, Pr), providing
the orthogonal-axis decoupling Forrest could not provide — surrogate inputs
on aggregate (Re, Pr) coords look in-distribution to baselines at any test
x/D, while the closure-validity literature knows x/D < 10 is outside the
fully-developed regime where Gnielinski / Dittus-Boelter apply.

D3 role (per locked design v0.2 + entrance-region recon v0.1 + v0.2 steelman):
  The differentiator test substrate. Replaces the locked v0.2 Forrest+Mudhafar
  scenario (which failed the on-axis decoupling). Per the v0.2 steelman, the
  test cell is:
    - Train: fully-developed measurements (x/D > 10), surrogate inputs =
      (log10_Re, Pr) only. Per the v0.2 steelman, x/D is OMITTED from
      surrogate inputs (the aggregate HE use-case).
    - Test_A: developing-region measurements (x/D < 5) at the SAME (Re, Pr)
      conditions as training. Surrogate inputs identical to training; closure
      is invalid because flow isn't developed; truth is the measured Nu
      which is ~1.5-2x the closure prediction (Hausen-factor regime).
    - Test_B: held-out fully-developed measurements. Surrogate inputs in
      training distribution; closure works to within ~5% MAE.

Expected D3 signals:
  - Baselines (distance, GP variance) on (log10_Re, Pr) inputs: cannot fire
    on test_A vs test_B because the inputs are LITERALLY identical (same
    Re, same Pr, same geometry). |Cohen d| approximately 0 by construction.
  - Validity-range-distance signal: fires on test_A (x/D < 10 is outside
    Gnielinski's new validated range [10, infinity]); quiet on test_B
    (x/D > 10 is inside). Large positive Cohen d.

Steelman framing (v0.2 ENSEMBLE, NOT structural-blindness):
  Not "no competent practitioner includes x/D." Rather: across the ensemble
  of competent practitioners building aggregate HE surrogates, a non-trivial
  fraction omit x/D, omit the Hausen correction, or use bare Gnielinski
  beyond L/D > 10. PhysMAP's corpus adds REAL LIFT to those practitioners'
  workflows by catching the literature-derived validity boundary their
  surrogate inputs can't represent. The result claim is "adds lift," NOT
  "is the unique mechanism" — practitioners who already apply Hausen don't
  need the corpus, but the ensemble of omitters is the value-add target.

Data-acquisition status:
  - NACA TN-1451 PDF in hand at /tmp/naca_tn1451.pdf (downloaded from NTRS).
  - Per-x/D Nu measurements are in Figures 10-25 of the report (16 entering-
    air conditions x multiple x/D positions). Apply same triage discipline
    as Forrest Fig 5: visual-estimate rows tagged separately from any
    future WPD-digitized rows.

Per-paper facts (from paper text):
  - 0.93-inch ID circular tube (smooth wall).
  - 16 entering-air conditions tested.
  - x/D positions reported include 1.03, 4.41, 5.25, 15.40, 16.50 and others.
  - Air only (Pr ≈ 0.71 at typical conditions).
  - Quantified uncertainty: ±5% total experimental error; ±3% reproducibility.
  - Paper finding: "experimental values appreciably higher than equations
    derived from over-all data taken on long pipes" — the entrance-region
    divergence, central to the paper.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

from physmap.substrate.stage1_ingest import Mechanism, Row, load_rows
from physmap.substrate.corpus_real import SubstrateMeta
from physmap.closures import REGISTRY
from physmap.closures.formulas import (
    dittus_boelter_nu,
    gnielinski_nu,
    petukhov_nu,
)


# Calibration ranges sourced from the closure registry (Cleanup 5 part 2).
GNIELINSKI_RE_LO, GNIELINSKI_RE_HI = REGISTRY["gnielinski-1976"].re_range
DITTUS_BOELTER_RE_LO, DITTUS_BOELTER_RE_HI = REGISTRY["dittus-boelter-1930"].re_range


# ── geometry + fluid (per NACA TN-1451 paper) ───────────────────────────────
# Tube ID from paper line 233: "highly polished seamless steel tube 32 inches
# long having a 2-inch outside diameter (1.785 in. I.D.)". Earlier prereg
# draft had 0.93 in — that was wrong (confused with Mudhafar). Corrected here.
TUBE_ID_INCH = 1.785
TUBE_ID_MM = TUBE_ID_INCH * 25.4   # 45.34 mm
TUBE_ID_FT = TUBE_ID_INCH / 12.0   # 0.14875 ft (used to convert fc → Nu)
FLUID = "air"
PR_AIR_NOMINAL = 0.71               # air at typical heater operating temps
ALPHA_STAR_CIRCULAR = 1.0
HEATING_PATTERN = "all_walls_steam_jacketed"   # uniform circumferential


# ── cell definitions (per Hausen factor + textbook L/D > 10 rule) ────────────
# Cells defined by x/D position. The orthogonal-axis differentiator depends
# on this cell structure:
#   - developing: x/D < 5  (Hausen factor > ~1.34, divergence > 30%)
#   - shoulder:   5 ≤ x/D < 10  (Hausen factor 1.22-1.34, divergence 20-30%)
#   - fully_developed: x/D ≥ 10  (Hausen factor < 1.22, divergence < 20%
#     and approaching textbook MAE of ~5-10%)

Cell = Literal["developing", "shoulder", "fully_developed"]

DEVELOPING_X_OVER_D_HI = 5.0
SHOULDER_X_OVER_D_HI = 10.0


def cell_assignment(x_over_D: float) -> Cell:
    """Per-row cell label by x/D band."""
    if x_over_D < DEVELOPING_X_OVER_D_HI:
        return "developing"
    if x_over_D < SHOULDER_X_OVER_D_HI:
        return "shoulder"
    return "fully_developed"


# Hausen entrance-correction factor (textbook approximation):
#   F(x/D) = 1 + (D/x)^(2/3)
# At x/D = 1: F = 2.0; x/D = 2: F = 1.63; x/D = 5: F = 1.34; x/D = 10: F = 1.22
def hausen_factor(x_over_D: np.ndarray | float) -> np.ndarray:
    """Hausen entrance-correction multiplier for fully-developed Nu."""
    x_over_D = np.asarray(x_over_D, dtype=float)
    return 1.0 + (1.0 / np.maximum(x_over_D, 1e-3)) ** (2.0 / 3.0)


# ── schema ───────────────────────────────────────────────────────────────────

@dataclass
class NACARow:
    """One measured local-Nu point on the NACA TN-1451 substrate.

    Re, Pr, Nu_meas, x_over_D, Nu_unc are load-bearing.
    """
    Re: float
    Pr: float
    Nu_meas: float
    x_over_D: float
    Nu_unc: float = None                # absolute Nu units; if None, use 5% of Nu_meas
    # Provenance
    entering_condition: str = "bellmouth"   # e.g. "bellmouth", "long_calming", "sharp_edge_orifice"
    figure: str = ""                         # which Fig (10-25) the point came from
    source: str = "naca_tn1451"
    digitization_uncertainty: float | None = None

    def __post_init__(self):
        if self.Nu_unc is None:
            self.Nu_unc = 0.05 * self.Nu_meas   # paper-reported ±5% default

    def cell(self) -> Cell:
        return cell_assignment(self.x_over_D)


# ── loader ───────────────────────────────────────────────────────────────────

def naca_to_rows(data_table: list[NACARow]) -> tuple[list[Row], dict, SubstrateMeta]:
    """Convert NACA measurement points into Stage-1 Rows.

    Each Row carries:
      operating_point = (Re, Pr) - the SURROGATE inputs per v0.2 steelman
      surrogate_prediction = Gnielinski Nu (the closure the practitioner uses)
      cfd_truth = measured Nu (the actual measurement)
      meta = full physical context INCLUDING x_over_D, so detectors that
             use the physical context (validity signal) can access x/D
             while detectors that use surrogate inputs (baselines) don't
             extract x_over_D.
    """
    rows: list[Row] = []
    for r in data_table:
        Re = float(r.Re)
        Pr = float(r.Pr)
        Nu_meas = float(r.Nu_meas)
        Nu_unc = float(r.Nu_unc)
        x_over_D = float(r.x_over_D)
        if Nu_meas <= 0:
            continue

        Nu_g  = float(gnielinski_nu(Re=np.array([Re]), Pr=np.array([Pr]))[0])
        Nu_db = float(dittus_boelter_nu(Re=np.array([Re]), Pr=np.array([Pr]))[0])
        Nu_pk = float(petukhov_nu(Re=np.array([Re]), Pr=np.array([Pr]))[0])

        if r.digitization_uncertainty is not None and r.digitization_uncertainty > 0:
            total_unc = float(np.sqrt(Nu_unc ** 2 + r.digitization_uncertainty ** 2))
        else:
            total_unc = Nu_unc

        # The surrogate is Gnielinski (the standard industrial choice for HE).
        # Per the v0.2 steelman: this closure is applied with surrogate
        # inputs = (Re, Pr) only, omitting x/D. The corpus now encodes
        # x_over_D > 10 as Gnielinski's validated range.
        mechanisms = [
            Mechanism(
                name="forced_internal_pipe_gnielinski_aggregate_use",
                closure_id="gnielinski-1976",
                operating_value=Re,
                calib_lo=GNIELINSKI_RE_LO,
                calib_hi=GNIELINSKI_RE_HI,
                contribution=Nu_g,
            ),
            Mechanism(
                name="forced_internal_pipe_dittus_boelter_reference",
                closure_id="dittus-boelter-1930",
                operating_value=Re,
                calib_lo=DITTUS_BOELTER_RE_LO,
                calib_hi=DITTUS_BOELTER_RE_HI,
                contribution=Nu_db,
            ),
        ]

        rows.append(Row(
            operating_point=(round(Re, 1), round(Pr, 4)),
            surrogate_prediction=Nu_g,           # Gnielinski (the practitioner's surrogate)
            cfd_truth=Nu_meas,
            truth_source="experimental",
            cfd_uncertainty=total_unc,
            guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
            mechanisms=mechanisms,
            meta={
                "Re": Re, "Pr": Pr,
                "Nu_meas": Nu_meas, "Nu_unc_reported": Nu_unc,
                "Nu_unc_total_propagated": total_unc,
                "Nu_pred_gnielinski": Nu_g,
                "Nu_pred_dittus_boelter": Nu_db,
                "Nu_pred_petukhov": Nu_pk,
                "x_over_D": x_over_D,             # PHYSICAL CONTEXT (validity uses this)
                "x_over_D_log10": float(np.log10(x_over_D)),
                "hausen_factor_expected": float(hausen_factor(x_over_D)),
                "cell": r.cell(),
                "Dh_mm": TUBE_ID_MM,
                "alpha_star": ALPHA_STAR_CIRCULAR,
                "heating_pattern_indicator": 1.0,
                "roughness_relative": 0.0,
                "fluid": FLUID,
                "entering_condition": r.entering_condition,
                "figure": r.figure,
                "source": r.source,
                "digitization_uncertainty": r.digitization_uncertainty,
            },
        ))

    rows = load_rows(rows)

    reference = {"ood": [0.0], "residual": [0.0], "variance": [0.0]}
    meta = SubstrateMeta(
        name="naca-tn1451-entrance-region",
        divergent_truth_substrate=True,
        reason=(
            "Independent experimental truth: measured local Nu via "
            "steam-condensation calorimetry per section in a 0.93-in ID "
            "circular tube. Per NACA TN-1451 (Boelter, Young, Iversen 1948; "
            "NTRS ID 19930082084; public domain). 16 entering-air conditions "
            "tested across multiple x/D positions; the per-x/D variation IS "
            "the central paper finding. Steady-state — no temporal "
            "autocorrelation. Per D3 v0.2 steelman, this substrate provides "
            "the orthogonal-axis decoupling: x/D failure axis is NOT in the "
            "aggregate-HE surrogate's inputs (Re, Pr), so baselines see "
            "test_A (developing) and test_B (fully-developed) as identical "
            "inputs, while the corpus literature knows x/D < 10 is outside "
            "Gnielinski's validated range."
        ),
        norm_strategy="per_row_truth",
        bound_for_pde=None,
        magnitude_bridge_ok=True,
        extra={
            "geometry": (
                f"Circular tube ID = {TUBE_ID_INCH} inch = {TUBE_ID_MM:.2f} mm, "
                f"smooth wall, steam-jacketed (uniform circumferential heating), "
                f"variable length (~30 inches total); per-section local Nu "
                f"measured via condensation rate per individual jacket section."
            ),
            "fluid": FLUID,
            "Pr_nominal": PR_AIR_NOMINAL,
            "Re_range_paper": [1000, 100000],   # approximate; 16 conditions
            "x_over_D_range_paper": [1.03, ~30],  # explicit positions in text
            "cell_bands": {
                "developing": {
                    "range": f"x/D < {DEVELOPING_X_OVER_D_HI}",
                    "role": "D3 differentiator test cell — closure invalid (Hausen factor > 1.34)",
                    "expected_validity_signal": "FIRES (x/D below corpus validated range [10, inf])",
                    "expected_baseline_signal": (
                        "QUIET if surrogate inputs exclude x/D (per v0.2 steelman). "
                        "Test_A and Test_B have identical surrogate inputs by construction."
                    ),
                },
                "shoulder": {
                    "range": f"{DEVELOPING_X_OVER_D_HI} <= x/D < {SHOULDER_X_OVER_D_HI}",
                    "role": "transition shoulder — borderline (Hausen factor 1.22-1.34)",
                    "use": "excluded from primary differentiator test; reserved for sensitivity check",
                },
                "fully_developed": {
                    "range": f"x/D >= {SHOULDER_X_OVER_D_HI}",
                    "role": "training set + Test_B control",
                    "expected_validity_signal": "quiet (x/D in corpus validated range)",
                    "expected_baseline_signal": "quiet (training distribution)",
                },
            },
            "n_entering_conditions": 16,
            "uncertainty_quantified": {
                "max_total_error_pct": 5.0,
                "reproducibility_pct": 3.0,
                "source": "NACA TN-1451 paper text (line 329 of pdftotext extract)",
            },
            "d3_role": (
                "DIFFERENTIATOR vehicle. Replaces the locked v0.2 Forrest+Mudhafar "
                "scenario after the Forrest on-axis structural finding. Provides "
                "the orthogonal-axis decoupling needed to genuinely test the "
                "literature-validity signal against quiet baselines."
            ),
            "data_source_note": (
                "Per-row Nu measurements pending digitization of NACA Figs 10-25. "
                "Apply Forrest-style triage discipline: visual-estimate rows "
                "tagged 'visual-estimate-rendered-pdf-naca' separated from any "
                "future WPD-digitized rows."
            ),
        },
    )
    return rows, reference, meta


# ── data-acquisition path stubs (NotImplementedError until digitization) ─────

def from_wpd_csv(path: Path) -> list[NACARow]:
    raise NotImplementedError(
        "NACA Figs 10-25 WPD digitization pending. Recommended sequence: "
        "Fig 10 (bellmouth, full Re range) first as a starting target; then "
        "Figs 11-25 for the other entering conditions. Export CSV with "
        "(Re, x_over_D, Nu_meas) columns; entering_condition encoded in filename."
    )


def from_visual_estimate_csv(path: Path) -> list[NACARow]:
    raise NotImplementedError("Visual-estimate digitization not yet performed.")


def from_synthetic_shape(n_re_conditions: int = 16,
                          x_over_D_positions: tuple = (1, 2, 3, 5, 10, 15, 20, 30, 50),
                          re_min: float = 3000.0,
                          re_max: float = 100000.0,
                          seed: int = 20260605) -> list[NACARow]:
    """SYNTHETIC data matching NACA TN-1451's experimental shape.

    Used for the synthetic-shape verification of the differentiator design
    BEFORE digitization lands. The synthesis uses:
      - n_re_conditions Re values sampled log-uniformly in [re_min, re_max].
        Default [3000, 100000] keeps Re strictly inside Gnielinski's
        validated Re lower bound (3000) so the synthetic test isolates the
        x/D axis as the cause of any corpus firing — any benign FA on a
        synthetic point would necessarily be a true positive on Re axis
        otherwise (Gnielinski's validated range Re=[3000, 5e6]).
      - x/D positions covering both developing and fully-developed.
      - Nu_truth = Gnielinski(Re, Pr) * Hausen_factor(x/D) + noise
      - 5% measurement noise per the paper.

    Honest about being synthetic: marks source='synthetic-naca-shape' so
    these rows are clearly distinguished from any future real-data rows.
    """
    rng = np.random.default_rng(seed)
    Re_values = np.logspace(np.log10(re_min), np.log10(re_max), n_re_conditions)
    rows = []
    for Re in Re_values:
        # Synthesize Nu using Gnielinski + Hausen factor + noise
        Nu_gnielinski = float(gnielinski_nu(np.array([Re]), np.array([PR_AIR_NOMINAL]))[0])
        for xd in x_over_D_positions:
            F = float(hausen_factor(xd))
            Nu_truth = Nu_gnielinski * F * (1.0 + rng.normal(0, 0.05))
            rows.append(NACARow(
                Re=float(Re), Pr=PR_AIR_NOMINAL, Nu_meas=float(Nu_truth),
                x_over_D=float(xd),
                entering_condition="synthetic_bellmouth",
                source="synthetic-naca-shape",
            ))
    return rows
