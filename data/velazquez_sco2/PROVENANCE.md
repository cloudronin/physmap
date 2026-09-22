# Velázquez et al. 2026 — supercritical CO₂ microtube (local heat-transfer data)

**Source.** I. Velázquez, D.A. Cantero, F. Demeyer, M. Reyes, *"Experimental investigation on heat transfer to
supercritical CO₂ in a microtube up to 30 MPa for application in the NET Power cycle,"* Applied Thermal
Engineering **285** (2026) 129206. DOI [10.1016/j.applthermaleng.2025.129206](https://doi.org/10.1016/j.applthermaleng.2025.129206).
Open access (CC BY 4.0).

**Data provenance — EXACT extraction, NOT figure-digitized.** Values are taken verbatim from the article's
Supplementary Material **mmc1.docx**
(`https://ars.els-cdn.com/content/image/1-s2.0-S1359431125037986-mmc1.docx`), **Appendix D — "Experimental data
points and uncertainties"** (Tables D1–D28). These are the authors' reduced data points plus their stated
per-point uncertainties, so there is **no digitization uncertainty**. (The article's "Data availability: data will
be made available on request" refers to raw data; the reduced points are published in Appendix D.) Extraction
method: Python stdlib (`zipfile` + `xml.etree`) parse of the docx nested tables. Verified against the paper:
**28 tests × 20 thermocouple stations = 560 points**; pressures **10/15/20/25/30 MPa**; α range **328–8057 W m⁻²K⁻¹**;
T_b range **20.3–97.9 °C** — consistent with Figs 8–10 and the stated ranges.

**File:** `velazquez_sco2_local_alpha.csv` (561 rows incl. header).

| Column | Meaning |
|---|---|
| `test`, `station` | test id T1–T28; thermocouple station 1–20 along the 1600 mm heated length (76.2 mm spacing). **x/Dᵢ is implicit** in station order — recover from Fig. 4 geometry if a per-point x/Dᵢ is needed. |
| `p_MPa, G_kg_m2s, U_V, I_A, qw_kW_m2, Tin_C, dp_bar` | per-test conditions (constant within a test): pressure, mass flux, voltage, current, applied heat flux, inlet temperature, pressure drop. |
| `Two_C, Twi_C` | measured outer / derived inner wall temperature. |
| `hb_kJ_kg, Tb_C` | local bulk enthalpy / bulk temperature. |
| `alpha_W_m2K` | **local heat-transfer coefficient** (the truth). |
| `unc_qw_W_m2, unc_Two_C (=0.50), unc_hb_J_kg, unc_alpha_W_m2K` | the paper's per-point uncertainties; `unc_alpha` ≈ 6 % of α. |

**Not tabulated — compute in Phase C** (needs a CO₂ property library, e.g. CoolProp/REFPROP, from G, Dᵢ=0.88 mm,
p, T_b, T_wi): `Re_b` (paper range 4099.9–23847.4), `Pr_b`, `Nu = α·Dᵢ/λ_b`, wall/bulk property ratios
(ρ_w/ρ_b, μ_w/μ_b, λ_w/λ_b), and the buoyancy criteria (Richardson Eq. 14 / Petukhov Gr_q/Gr_th Eq. 15 / Jackson
Ja Eq. 16). Tube: 316L, Dᵢ = 0.88 mm, heated length 1600 mm, horizontal.

**Build notes** (see `docs/findings/PhysMAP_Vehicle_Search_Coverage_v0_1.md` §6.1). Property-variation middle-vehicle
candidate; the failure driver is the **wall/bulk property ratio**, omitted from a constant-property Nu(Re_b, Pr_b)
surrogate. **Pressure-subset construction decision:** 10 MPa = strongest property-variation failure but buoyancy
is non-negligible (paper Fig. 11: Ri > 10⁻³ and Gr_q/Gr_th > 1 *only* at 10 MPa); 15–30 MPa = buoyancy negligible
(clean property-variation) but milder failure. Observability (genuine middle vs near-observable pole) must be
**measured in Phase E**. Encouraging early sign (see Phase-C below): at these ≥10 MPa pressures Pr_b only
ranges 1.21–4.41 (no dramatic pseudo-critical spike), so the failure region is *not* screaming-OOD in Pr — the
genuinely-hidden driver is the property ratio (μ_w/μ_b down to 0.55), which a (Re_b, Pr_b) baseline does not see.
That milder-Mudhafar-trap picture favours a real middle, but it must still be measured.

## Phase-C computed properties (CoolProp, offline)

- **Script:** `compute_properties.py` (banked here; requires CoolProp, run offline; NOT a pipeline/runtime dependency).
- **Output:** `velazquez_sco2_local_alpha_with_properties.csv` — the raw 18 columns plus 19 computed: bulk & wall
  ρ/μ/λ, c_p,b, **Pr_b**, **Re_b = G·Dᵢ/μ_b**, **Nu_meas = α·Dᵢ/λ_b**, property ratios **ρ_w/ρ_b, μ_w/μ_b,
  λ_w/λ_b**, **T_pc(p)** (= argmax_T c_p), **dT_b_to_pc**, `near_pc`, and the `h_b` cross-check.
- **Validation:** CoolProp ≡ REFPROP for CO₂ (pseudo-critical enthalpy match < 0.2 kJ/kg at all five pressures);
  bulk states validated (`h_b` residual < 0.23 kJ/kg over all 560 points); Re_b 5021–23468 (paper 4100–23847 —
  the *min* extreme differs ~22%, a single coldest/most-viscous point, not load-bearing); Pr_b 1.21–4.41;
  Nu_meas 3.3–83.6; property ratios μ_w/μ_b 0.55–1.02, ρ_w/ρ_b 0.58–0.99 (strong variation = the failure driver).
  Constant-property **Gnielinski(Re_b,Pr_b) MAPE = 245 %** → confirms the surrogate failure is *massive*
  (Phase-D2 "measurably wrong" is amply satisfied; the paper's Table 3 reports 148 % with their exact
  entrance-term Gnielinski form — the discrepancy is the entrance term + x/Dᵢ, not load-bearing here).
- **Buoyancy isolation — NOT recomputed.** For a property-variation vehicle Ri is a *confound*, not the driver.
  Velázquez Fig. 11 already settles it ("for pressures above 10 MPa, buoyancy effects can be neglected"), so the
  vehicle isolates the confound by **pressure**: use the **15–30 MPa subset** for the clean property-variation
  claim. (An earlier from-memory Gr/Ri recompute failed the Fig.-11 sanity-check and was dropped — pressure-based
  isolation per the paper is the authoritative, citable approach.)
