# Jin sCO₂-Buoyancy Vehicle — Provenance

## Source (the measured truth)
Jin, Y., Zhao, P., Wan, T., Chen, Z., Liu, K., Wang, X., Li, Y. & Wan, Y. (2023). "Experimental investigation of
buoyancy effects on the heat transfer of supercritical carbon dioxide in a vertical tube." *Annals of Nuclear
Energy* 188: 109825. DOI 10.1016/j.anucene.2023.109825.

- **Measured:** local wall temperature (29 K-type thermocouples), local HTC, local Nu along a d=7.74 mm vertical
  tube; supercritical CO₂; upward and downward flow. Ranges: P 7.8–10 MPa, G 138.3–512.1 kg/m²s, q 29–60.3 kW/m²,
  T_in 14–33 °C (T_pc ≈ 33.5 °C @ 7.8 MPa). Stated measurement uncertainty: Nu ±9.27%, HTC ±9.16%, wall-T ±0.5 °C.
- **Properties:** NIST REFPROP 9.0 (used by the authors; will be recomputed locally for the surrogate via the
  property library, cf. the Velázquez `compute_properties.py` pattern). REFPROP/CoolProp are property evaluation,
  not truth.
- **Comparison closures (NOT truth):** Dittus-Boelter, Gupta 2013, Jackson 2013, Zhu 2020, Kim & Kim 2010, and the
  paper's own Eq. 22 — these are the closures being validity-bounded.

## Acquisition status (the G1 gate) — COMPLETE
- **Per-point data is figure-only in the PDF;** author raw data is **not forthcoming**, so figure-digitization is the
  **final data** (the project's accepted standard, as for Casper/Velázquez). `AUTHOR_DATA_REQUEST.md` is retired.
- **Truth used:** NACA-grade two-reader figure-digitization (per-point uncertainty preserved). The A6(ii) cell
  (Fig 17b up/down) is **human-confirmed** (`jin_fig17_htc_reconciled.csv`); the q/G family extremes are
  reader-2-verified (`jin_fig7_10_families_htc_corrected.csv`). Derived Bo\*/Bu are **recomputed** (Jin Eqs. 20–21 +
  CoolProp) and cross-checked vs the paper's Fig 8/10 — not digitized as truth.
- **State:** **G1 complete for the differentiator → G2–G7 all PASS → `BUILT_DIFFERENTIATOR` (digitization-tier)**
  (`DATA_STATUS.md`, `GATES_DRY_RUN.md`). Final at figure-read precision; the banked Claim stays bound-only/`claimed`.

## Banked artifacts elsewhere
- Evidence-corpus bound (banked, main @02880b7): `jin-2023-correct-dittus-boelter-buoyancy-bound` (role=correct,
  bound-only — the buoyancy validity-limit; the quantitative magnitude is produced HERE).
- Triage: `docs/findings/PhysMAP_BuoyancyEntrance_A6ii_Triage_v0_1.md`.
- Construction spec: `docs/specs/PhysMAP_sCO2Buoyancy_Construction_Spec_v0_1.md`.

## Dual role
Beyond the standalone differentiator, the up/down matched pair isolates buoyancy from property-variation (same
property field, opposite buoyancy), which sharpens the property-variation observability axis — the separation the
Velázquez sCO₂ middle could not make. Build sequencing should extract that isolation even if the full differentiator
construction is later deferred.
