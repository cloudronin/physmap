"""Per-vehicle parameterization shared by the observability score (D1) and the
Stage-1 ensemble sweep (D2).

The failure-region split, the surrogate-input + validity feature spaces, the
closure_id, and the failure-driving variable are ALL derived here from the
VehicleConfig (chiefly `cell_bands.type`). D1 computes the observability score
over the failure region; D2 evaluates the sweep over the same region. Defining
the region ONCE here is what keeps them from drifting apart — if they diverged,
the Stage-3 axis plot would pair a score over one region with a verdict over
another (a silent correctness bug).

Step-scope: the NACA (`x_over_d_bands`) row is wired now. Forrest (`re_bands`)
is added with the observability work (Step 1); Mudhafar (`dh_roughness_bands`)
and Testi-Grassi (`richardson_bands`) with the scaffolding (Step 4). Unwired
band types raise a clear NotImplementedError naming the step that wires them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from physmap.substrate.vehicle_config import VehicleConfig


# Failure-driving variable per cell-bands type — the meta key whose
# recoverability from the surrogate inputs IS the observability score.
# None = the vehicle has no single failure axis (caller must pass failure_var).
FAILURE_VAR_BY_CELL_BANDS_TYPE: dict[str, str | None] = {
    "x_over_d_bands": "x_over_D",     # NACA — entrance region
    "re_bands": "Re",                 # Forrest — sub-critical Re
    "dh_roughness_bands": "Dh_um",    # Mudhafar — hydraulic diameter
    "richardson_bands": "Ri",         # buoyancy middle vehicles (Testi-Grassi)
    "buoyancy_parameter_bands": "Bu", # Jin sCO2 vertical tube — Liu buoyancy parameter
    "property_variation_bands": "ratio_mu_w_b",  # Velazquez sCO2 — wall/bulk viscosity ratio
    "freestream_disturbance_bands": "freestream_noise_pct",   # Casper — tunnel freestream noise
    "entropy_layer_shock_interaction_bands": "st_xsw_ratio",  # Marineau — S_T/X_SW (bluntness)
    "continuous": None,
    "custom": None,
}

# NACA entrance-region locked boundary: x/D >= 10 trains (fully developed);
# x/D < 10 is the failure region. Mirrors phase1_gate.X_OVER_D_CUTOFF.
NACA_X_OVER_D_CUTOFF = 10.0


@dataclass(frozen=True)
class SplitSpec:
    """How the failure region is carved from a vehicle's operating points.

    `train_predicate` / `test_predicate` operate on a row's `.meta` dict. The
    failure region (test) is where the surrogate is deployed beyond the regime
    its closure was validated on; train is the in-distribution complement.
    """
    kind: str
    train_predicate: Callable[[dict], bool]
    test_predicate: Callable[[dict], bool]


@dataclass(frozen=True)
class VehicleSpec:
    """Everything the observability score + Stage-1 sweep need that is not in
    the bare VehicleConfig: the two feature spaces, the closure for the
    validity detector, the failure-driving variable, and the failure-region
    split."""
    vehicle_id: str
    baseline_feature_names: tuple[str, ...]
    validity_feature_names: tuple[str, ...]
    closure_id: str
    failure_var: str
    split: SplitSpec


def vehicle_spec(cfg: VehicleConfig) -> VehicleSpec:
    """Derive the VehicleSpec from a VehicleConfig, keyed on `cell_bands.type`."""
    bands_type = cfg.cell_bands.type
    closure_id = cfg.matched_closure_id

    if bands_type == "x_over_d_bands":
        # NACA: baselines see (log10_Re, Pr); the validity detector also sees
        # x/D (the omitted failure axis). Locked cutoff x/D = 10. These feature
        # spaces + closure reproduce phase1_gate's constants exactly, so the
        # sweep's NACA arm is byte-identical to the locked gate.
        cutoff = NACA_X_OVER_D_CUTOFF
        return VehicleSpec(
            vehicle_id=cfg.vehicle_id,
            baseline_feature_names=("log10_Re", "Pr"),
            validity_feature_names=("log10_Re", "Pr", "x_over_D"),
            closure_id=closure_id,
            failure_var="x_over_D",
            split=SplitSpec(
                kind="x_over_d_threshold",
                train_predicate=lambda m, c=cutoff: m["x_over_D"] >= c,
                test_predicate=lambda m, c=cutoff: m["x_over_D"] < c,
            ),
        )

    if bands_type == "re_bands":
        # Forrest: failure axis is Reynolds number, which IS a surrogate input
        # (log10_Re) — the high-observability pole. The validity space carries
        # no extra coord (Sparrow-Cur's validated range is (Re, Pr) only).
        # Failure region = lowest Re band (sub-critical); train = top catch-all
        # band (benign turbulent); the transition band is excluded from both
        # (indeterminate, per forrest_resolvability).
        bands = cfg.cell_bands.bands
        sub_critical_cut = float(bands[0]["re_lt"])     # e.g. 4000 (sub-critical < this)
        benign_lo = float(bands[-2]["re_lt"])           # e.g. 10000 (benign >= this)
        return VehicleSpec(
            vehicle_id=cfg.vehicle_id,
            baseline_feature_names=("log10_Re", "Pr"),
            validity_feature_names=("log10_Re", "Pr"),
            closure_id=closure_id,
            failure_var="Re",
            split=SplitSpec(
                kind="re_bands",
                train_predicate=lambda m, lo=benign_lo: m["Re"] >= lo,
                test_predicate=lambda m, c=sub_critical_cut: m["Re"] < c,
            ),
        )

    if bands_type == "dh_roughness_bands":
        # Mudhafar (out-of-envelope control): the steelman baseline is the
        # cross-substrate feature space, which INCLUDES geometry (log10_Dh_mm).
        # So the failure axis Dh IS a baseline input → high-observability /
        # baseline-sufficient pole (the spec's prediction). Failure region =
        # small-diameter OR rough cells; train = standard smooth.
        bands = cfg.cell_bands.bands
        dh_min = next((float(b["dh_um_min"]) for b in bands if "dh_um_min" in b), 200.0)
        cross = ("log10_Re", "Pr", "log10_Dh_mm", "alpha_star",
                 "heating_pattern_indicator", "roughness_relative")
        return VehicleSpec(
            vehicle_id=cfg.vehicle_id,
            baseline_feature_names=cross,
            validity_feature_names=cross,
            closure_id=closure_id,
            failure_var="Dh_um",
            split=SplitSpec(
                kind="dh_roughness",
                train_predicate=lambda m, lo=dh_min: (
                    float(m.get("Dh_um", 0.0)) >= lo and not m.get("rough", False)),
                test_predicate=lambda m, lo=dh_min: (
                    float(m.get("Dh_um", 1e18)) < lo or bool(m.get("rough", False))),
            ),
        )

    if bands_type == "richardson_bands":
        # Buoyancy middle vehicle (Testi-Grassi): the surrogate is a
        # forced-convection (Re, Pr) closure with the buoyancy variable
        # (Richardson number) OMITTED. Ri is NOT a baseline input but is
        # partially correlated with Re/heat flux → MIDDLE observability by
        # construction. Failure region = where buoyancy matters (Ri >= the
        # forced-dominated cutoff); train = forced-dominated (low Ri).
        #
        # The corpus Ri-bound IS wired (Dirker/Meyer/Reid water vehicle): the
        # MATCHED closure aung-worku-mixed-convection-1986 carries the
        # richardson_number ceiling (corpus.jsonl); detectors.extract_features
        # supports "Ri"/"log10_Ri", and validity_feature_names is ("Ri",) below.
        # NOTE: aung-worku bounds ONLY richardson_number, so the public
        # CredibilityGuardrail's derived (log10_Re, Pr, Ri) validity space is
        # behaviorally IDENTICAL to this ("Ri",) — Re/Pr have no aung-worku bound
        # and contribute zero distance (verified). The dedicated mixed-convection
        # closure (NOT the shared gnielinski) keeps the Ri bound off NACA/Forrest.
        # baseline_feature_names keeps (log10_Re, Pr) — buoyancy omission from the
        # surrogate inputs IS the failure mechanism.
        bands = cfg.cell_bands.bands
        ri_forced_cut = float(bands[0].get("ri_lt", 0.1))
        return VehicleSpec(
            vehicle_id=cfg.vehicle_id,
            baseline_feature_names=("log10_Re", "Pr"),
            validity_feature_names=("Ri",),
            closure_id=closure_id,
            failure_var="Ri",
            split=SplitSpec(
                kind="richardson_bands",
                train_predicate=lambda m, c=ri_forced_cut: float(m["Ri"]) < c,
                test_predicate=lambda m, c=ri_forced_cut: float(m["Ri"]) >= c,
            ),
        )

    if bands_type == "buoyancy_parameter_bands":
        # Jin sCO2 vertical-tube buoyancy vehicle: the surrogate is a CONSTANT-PROPERTY,
        # direction-OMITTING Dittus-Boelter (Re, Pr) closure; the omitted failure driver is the Liu
        # buoyancy parameter Bu (wall-aware), absent from the (Re, Pr) inputs and only PARTIALLY
        # recoverable from them (it carries the wall-temperature/HTD signal) -> MIDDLE observability,
        # MEASURED via cv_r2_knn. The matched closure dittus-boelter-buoyancy-sco2 carries the corpus
        # Bu <= 1.3e-5 bound (REGIME_TO_CLOSURES[MIXED_CONVECTION_VERTICAL_TUBE]); validity_feature_names
        # adds "Bu", so the corpus detector fires in the upward-HTD deploy while the (Re, Pr) baseline
        # stays quiet (the matched up/down inputs are identical — the A6(ii) toggle). The benign/deploy
        # split is the physical regime label `split_role` (benign = downward / high-G / low-q NHT;
        # deploy = upward HTD), precomputed offline — NOT a Bu threshold (downward q=43.9 has Bu>1.3e-5
        # from buoyancy ENHANCEMENT yet is benign NHT). baseline keeps (log10_Re, Pr): buoyancy
        # omission from the surrogate inputs IS the failure mechanism.
        return VehicleSpec(
            vehicle_id=cfg.vehicle_id,
            baseline_feature_names=("log10_Re", "Pr"),
            validity_feature_names=("log10_Re", "Pr", "Bu"),
            closure_id=closure_id,
            failure_var="Bu",
            split=SplitSpec(
                kind="buoyancy_parameter_bands",
                train_predicate=lambda m: str(m["split_role"]) == "benign",
                test_predicate=lambda m: str(m["split_role"]) == "deploy",
            ),
        )

    if bands_type == "property_variation_bands":
        # Velazquez sCO2 property-variation middle vehicle: the surrogate is a
        # CONSTANT-PROPERTY (Re, Pr) closure (Gnielinski); the wall/bulk viscosity
        # ratio mu_w/mu_b is OMITTED and drives the failure near the pseudo-critical
        # point. mu_w/mu_b is NOT a baseline input but is partially correlated with
        # Pr (which rises toward pseudo-critical) -> MIDDLE observability, to be
        # MEASURED (could land nearer the observable pole; that is the open question).
        # Buoyancy confound isolated by pressure: only p >= p_min_mpa, where the paper
        # (Fig. 11) shows buoyancy negligible (>= 15 MPa). Failure region = near
        # pseudo-critical (|T_b - T_pc| < abs_dt_pc_lt); train = far from it (benign
        # property variation), same pressure subset.
        bands = cfg.cell_bands.bands
        b0 = bands[0]
        p_min = float(b0.get("p_min_mpa", 15.0))
        dt_cut = float(b0.get("abs_dt_pc_lt", 10.0))
        return VehicleSpec(
            vehicle_id=cfg.vehicle_id,
            baseline_feature_names=("log10_Re", "Pr"),
            validity_feature_names=("log10_Re", "Pr", "ratio_mu_w_b"),
            closure_id=closure_id,
            failure_var="ratio_mu_w_b",
            split=SplitSpec(
                kind="property_variation_bands",
                train_predicate=lambda m, p=p_min, c=dt_cut: (
                    float(m["p_MPa"]) >= p and float(m["abs_dT_pc"]) >= c),
                test_predicate=lambda m, p=p_min, c=dt_cut: (
                    float(m["p_MPa"]) >= p and float(m["abs_dT_pc"]) < c),
            ),
        )

    if bands_type == "freestream_disturbance_bands":
        # Casper hypersonic transition (aerospace PHYSMAP_WINS). The surrogate
        # sees (Mach, unit Reynolds, axial x); the omitted driver is the tunnel
        # freestream disturbance (freestream_noise_pct), a distinct flow-
        # environment axis NOT recoverable from the inputs -> UNOBSERVABLE. The
        # validity space adds freestream_noise_pct, and the corpus Pate-Stainback
        # bound fires on the QUIET deploy while the baseline stays silent (quiet
        # deploy is interior in the Mach-spanned training). Train = noisy
        # (fs >= cut), deploy = quiet (fs < cut); band[0].fs_lt is the 0.5% edge.
        fs_cut = float(cfg.cell_bands.bands[0].get("fs_lt", 0.5))
        return VehicleSpec(
            vehicle_id=cfg.vehicle_id,
            baseline_feature_names=("M", "Re_per_m_e6", "x_m"),
            validity_feature_names=("M", "Re_per_m_e6", "x_m", "freestream_noise_pct"),
            closure_id=closure_id,
            failure_var="freestream_noise_pct",
            split=SplitSpec(
                kind="freestream_disturbance_bands",
                train_predicate=lambda m, c=fs_cut: float(m["freestream_noise_pct"]) >= c,
                test_predicate=lambda m, c=fs_cut: float(m["freestream_noise_pct"]) < c,
            ),
        )

    if bands_type == "entropy_layer_shock_interaction_bands":
        # Marineau bluntness transition (aerospace NEGATIVE CONTROL). The
        # surrogate sees (unit Reynolds, nose radius). The failure driver
        # S_T/X_SW (st_xsw_ratio) is a deterministic function of nose radius (a
        # surrogate input) at fixed Mach -> OBSERVABLE; the steelman baseline
        # fires on the large-bluntness deploy (exterior in Rn). The validity
        # space adds st_xsw_ratio and the corpus bound fires there too, but the
        # baseline is NOT quiet -> no clean lift (the discrimination control).
        # Train = benign (S_T/X_SW >= cut), deploy = failure (< cut).
        st_cut = float(cfg.cell_bands.bands[0].get("st_xsw_lt", 0.1))
        return VehicleSpec(
            vehicle_id=cfg.vehicle_id,
            baseline_feature_names=("Re_per_m", "Rn_mm"),
            validity_feature_names=("Re_per_m", "Rn_mm", "st_xsw_ratio"),
            closure_id=closure_id,
            failure_var="st_xsw_ratio",
            split=SplitSpec(
                kind="entropy_layer_shock_interaction_bands",
                train_predicate=lambda m, c=st_cut: float(m["st_xsw_ratio"]) >= c,
                test_predicate=lambda m, c=st_cut: float(m["st_xsw_ratio"]) < c,
            ),
        )

    raise NotImplementedError(
        f"vehicle_spec: cell_bands.type={bands_type!r} not wired. "
        f"Supported: x_over_d_bands, re_bands, dh_roughness_bands, richardson_bands, "
        f"buoyancy_parameter_bands, property_variation_bands, freestream_disturbance_bands, "
        f"entropy_layer_shock_interaction_bands."
    )
