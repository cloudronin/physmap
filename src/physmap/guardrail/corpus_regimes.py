"""Corpus prerequisites for the structural-observability layer.

Four additive pieces the CredibilityGuardrail needs that the shipped corpus
does not yet provide. They live here — NOT by mutating corpus/calibration.py or
corpus.jsonl — so the locked calibration validator + SHACL + phase tests stay
untouched. The classifier reads the existing corpus via the existing accessors
(load_corpus / index_by_id / get_validated_range) and joins to these maps.

  1. REGIME_TO_CLOSURES  — a structured Regime → closure_ids map. The corpus only
     carries `regime_context` as prose; this is authored from closures/registry.py
     geometry groupings ∩ the corpus closure_ids. ENTRANCE_REGION_PIPE →
     gnielinski-1976 is what carries the x/D bound the locked NACA case fires on.
  2. observability_class  — a (closure_id, coord) → tag, defaulting to
     "structural-binary"; only buoyancy/property-ratio/roughness coords are
     "known-partial". Drives the PARTIAL routing.
  3. partial_degree       — the graded-partial DEGREE (Layer 2c) for known-partial
     coords: empirical, regime-specific, and EMPTY until a middle vehicle calibrates
     it. Leaving it empty is the honest state — an uncalibrated degree that drove a
     weight would be a fabricated empirical claim.
  4. corpus_fingerprint   — version + content hash for the save/load manifest.

These maps are the authoritative source the regime→observability mapping artifact
(physmap/guardrail/regime_observability.py) is GENERATED from; the artifact is a
validated, version-tagged projection, never a second runtime source of truth.

TODO: the canonical home for observability_class is a field on CoordinateBound,
once a buoyancy vehicle lands and the corpus owner re-blesses the validator.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from physmap.corpus.calibration import (
    DEFAULT_PATH as CALIBRATION_CORPUS_PATH,
    active_tier,
    resolve_corpus_path,
)
from physmap.guardrail.enums import Regime


# Regime → the corpus closure_ids whose validity bounds define that regime.
# Closure_ids verified present in results/calibration_corpus/corpus.jsonl.
REGIME_TO_CLOSURES: dict[Regime, tuple[str, ...]] = {
    Regime.ENTRANCE_REGION_PIPE: ("gnielinski-1976",),
    Regime.INTERNAL_FORCED_CONVECTION_PIPE: (
        "gnielinski-1976",
        "dittus-boelter-1930",
        "sieder-tate-1936",
        "petukhov-1970",
    ),
    Regime.INTERNAL_FORCED_CONVECTION_RECT_CHANNEL: (
        "modified-sparrow-cur-asym-narrow-rect-channel-2014",
    ),
    Regime.EXTERNAL_FLAT_PLATE_FORCED: (
        "blasius-pohlhausen-flat-plate-forced-1921",
    ),
    Regime.MIXED_CONVECTION_HORIZONTAL_TUBE: (
        "aung-worku-mixed-convection-1986",   # carries the richardson_number bound
    ),
    Regime.MIXED_CONVECTION_VERTICAL_TUBE: (
        "dittus-boelter-buoyancy-sco2",       # carries the liu_buoyancy_parameter (Bu) bound (Jin sCO2)
    ),
    Regime.INTERNAL_FORCED_CONVECTION_PROPERTY_VARIATION: (
        "gnielinski-constprop-sco2",          # carries the viscosity_ratio_wall_bulk bound
    ),
    Regime.HYPERSONIC_TRANSITION_DISTURBANCE: (
        "pate-stainback-freestream-noise-hypersonic-1980",   # freestream-noise validity bound (Casper)
    ),
    Regime.HYPERSONIC_TRANSITION_ENTROPY: (
        "marineau-entropy-layer-shock-interaction-2014",     # S_T/X_SW validity bound (Marineau)
    ),
    Regime.UNLISTED: (),                       # statistical-only; physics layer inactive
}

# TODO (handbook-harvest rounds 1+2, corpus v0.2.3) — closures present in the corpus but NOT yet
# wired to a Regime above. They are INERT: discoverable via load_default_corpus_index(), but they
# do NOT fire in the guardrail until mapped here. Each needs a human physics decision on which
# Regime it defines (+ a known-partial override in OBSERVABILITY_CLASS_OVERRIDES below if its coord
# is absent-but-correlated rather than a clean structural-binary miss).
#
#   ⚠ CONSISTENCY OBLIGATION — viscosity_ratio_wall_bulk is KNOWN_PARTIAL on the mapped
#     gnielinski-constprop-sco2, and a variable's class is one value everywhere it appears, so BOTH
#     inert closures that reuse it (whitaker-sphere-external-forced-1972, sieder-tate-laminar-
#     combined-entry-1936) MUST get a known-partial override here AT THE MOMENT THEY ARE WIRED, or
#     the mapping class-consistency gate fails. Harmless while inert: build_mapping() omits unmapped
#     closures, so the conflict is latent until one is wired.
#
#   Round 1 (still inert):
#     * swanson-catton-opposing-mixed-convection-1987       (grashof_number)              — opposing mixed convection
#     * mack-second-mode-transition-1969                    (mach_number)                 — compressible 2nd-mode transition
#     * perfect-gas-constant-cp-compressible-bl-1989        (mach_number)                 — compressible boundary layer
#     * blasius-pohlhausen-horizontal-plate-forced-1921     (gr_over_re2p5, gr_xl1p5_*)   — horizontal-plate mixed convection
#     * campbell-perkins-triangular-duct-air-1968           (temperature_ratio_wall_bulk) — triangular-duct gas property variation
#     * sieder-tate-laminar-combined-entry-1936             (viscosity_ratio_wall_bulk)   — laminar combined-entry μ/μ_s  [known-partial WHEN WIRED]
#   Round 2 (promoted v0.2.3, all inert):
#     * whitaker-sphere-external-forced-1972                (viscosity_ratio_wall_bulk)   — sphere μ/μ_s moat  [known-partial WHEN WIRED]
#     * cheng-curved-square-duct-nusselt-1975               (dean_number)                 — curved square duct; De is hydraulic-diameter-normalized
#     * depew-august-horizontal-tube-mixed-convection-1971  (rayleigh_number)             — horizontal-tube mixed convection (isothermal wall)
#     * marcos-bergles-horizontal-tube-mixed-convection-1975 (rayleigh_number)            — horizontal-tube mixed convection (uniform heat flux)
#     * eckert-reference-temperature-compressible-1972      (mach_number)                 — compressible reference-temperature property method
#     * herwig-perturbation-variable-property-bl-1985       (mach_number)                 — compressible variable-property BL skin friction
#     * goertler-concave-wall-transition-1940               (goertler_number)             — concave-wall centrifugal transition (momentum-thickness G)
#     * millikan-log-law-of-the-wall-1938                   (wall_y_plus)                 — log-law overlap onset; may JOIN the wall-function closures
#     * rotta-constant-turbulent-prandtl-number-1964        (prandtl_number)              — bound on MOLECULAR Pr (not Pr_t) → OBSERVABLE / low-moat
#     * laminar-fully-developed-tube-isothermal-nu366       (reynolds_number)             — Nu=3.66 analytical backbone → OBSERVABLE / low-moat
#     * laminar-fully-developed-tube-uniform-flux-nu436     (reynolds_number)             — Nu=4.36 analytical backbone → OBSERVABLE / low-moat


# Observability class for a bound coordinate. Cleanly-in/out axes (Re, Pr, x/D)
# are "structural-binary": the surrogate either consumes the axis or it does not.
# Absent-but-correlated axes (buoyancy, property-ratio, roughness) are
# "known-partial" — a surrogate may carry correlated information even without the
# axis itself, so set-membership can't cleanly weight them yet.
DEFAULT_OBSERVABILITY_CLASS = "structural-binary"
KNOWN_PARTIAL = "known-partial"

OBSERVABILITY_CLASS_OVERRIDES: dict[tuple[str, str], str] = {
    ("aung-worku-mixed-convection-1986", "richardson_number"): KNOWN_PARTIAL,
    # Wall/bulk property ratio: absent from (Re, Pr) inputs but correlated with them
    # through the property field near the pseudo-critical point — set-membership sees
    # it absent, so it routes PARTIAL (not a clean structural-binary miss).
    ("gnielinski-constprop-sco2", "viscosity_ratio_wall_bulk"): KNOWN_PARTIAL,
    # NOTE (Jin sCO2 vertical-tube, liu_buoyancy_parameter Bu): NOT overridden -> defaults to
    # structural-binary -> routes UNOBSERVABLE. This is the MEASURED result, not a guess: the Liu Bu
    # (and even the bulk-only Jackson Bo*) recoverability from the (Re, Pr) surrogate inputs over the
    # deploy region is cv_r2_knn ~ 0 (corr ~ -0.2), because Bu carries the wall-temperature/HTD signal
    # the DIRECTION toggle drives — orthogonal to the bulk inputs, the SAME structure as Casper's
    # freestream noise (a flow-environment binary), NOT the Velazquez property-ratio middle. So Jin
    # plots at the unobservable pole (a thermal-fluids PHYSMAP_WINS + the buoyancy/property-variation
    # confound-isolation case), not the partial band. (Distinct group from richardson_number Gr/Re^2.)
    # Sparrow-Gregg forced-convection buoyancy-validity bound (Gr/Re^2 <= 0.225, Rohsenow §4.9).
    # richardson_number is the SAME physical quantity already classed known-partial above, and the
    # per-variable class-consistency invariant requires one class everywhere it appears — so it is
    # known-partial here too (Ri absent from a forced (Re,Pr) surrogate, correlated through Re).
    ("blasius-pohlhausen-flat-plate-forced-1921", "richardson_number"): KNOWN_PARTIAL,
}


def observability_class_for(closure_id: str, coord: str) -> str:
    """Return "structural-binary" (default) or "known-partial" (override table)."""
    return OBSERVABILITY_CLASS_OVERRIDES.get((closure_id, coord), DEFAULT_OBSERVABILITY_CLASS)


# Graded-partial DEGREE (Layer 2c). For a known-partial coord, HOW partial it is —
# the correlation between the absent axis and the surrogate's inputs in a given
# operating regime. Empirical and regime-specific, so keyed (closure_id, coord) →
# {"partial_degree": {regime_value: degree}, "calibrated_by": [middle_vehicle_ids]}.
# A cell is populated ONLY by a middle vehicle that passes the digitization protocol
# + the stability gate; an uncalibrated cell stays absent here (the classifier then
# defers: PARTIAL → UNCERTAIN/REVIEW). Honesty discipline: an uncalibrated degree that
# drives a weight is a fabricated empirical claim — never invent a cell, and never key
# one to a regime the calibrating vehicle did not actually operate in.
PARTIAL_DEGREE_CALIBRATIONS: dict[tuple[str, str], dict] = {
    # Velázquez sCO2 (property-variation middle): cv_r2_knn = 0.575, stability-confirmed
    # (provisional=false, subsampling std 0.139 < 0.15 gate). Measured value banked in
    # results/velazquez_sco2_digitization/observability_result.json; this cell consumes
    # that score, it does not recompute it. Keyed to the regime the vehicle operates in.
    ("gnielinski-constprop-sco2", "viscosity_ratio_wall_bulk"): {
        "partial_degree": {"internal_forced_convection_property_variation": 0.575},
        "calibrated_by": ["velazquez_sco2"],
    },
}


def partial_degree_for(
    closure_id: str, coord: str,
) -> tuple[dict[str, float] | None, str, list[str]]:
    """Return (partial_degree, degree_status, calibrated_by) for a bound coordinate.

    Three states, mirroring the spec's `degree_status` vocabulary:
      * structural-binary           → (None, "n/a", [])
      * known-partial, uncalibrated → (None, "uncalibrated", [])
      * known-partial, calibrated   → ({regime_value: degree}, "calibrated", [ids])
    """
    if observability_class_for(closure_id, coord) != KNOWN_PARTIAL:
        return None, "n/a", []
    cal = PARTIAL_DEGREE_CALIBRATIONS.get((closure_id, coord))
    if not cal:
        return None, "uncalibrated", []
    return cal["partial_degree"], "calibrated", list(cal.get("calibrated_by", []))


# Bumped by hand when the calibration corpus changes in a way that affects
# guardrail bounds. The content hash catches silent drift a semver alone misses.
CALIBRATION_CORPUS_VERSION = "0.2.4"   # 0.2.4: +dittus-boelter-buoyancy-sco2 (corpus 52->53) — NEW coordinate liu_buoyancy_parameter (Liu et al. 2017 Bu, wall-aware; DISTINCT from richardson_number Gr/Re^2, same-name trap avoided), validated_range Bu<=1.3e-5 (a-priori, banked jin-2023-correct Claim). WIRED into REGIME_TO_CLOSURES[MIXED_CONVECTION_VERTICAL_TUBE] + KNOWN_PARTIAL (Bu partial-recoverable) — FIRES for the Jin sCO2-buoyancy benchmark cell, INERT for the other six (they carry no Bu coordinate, so their cells stay byte-identical). MAPPING regenerated (Jin regime/closure now in the projection). 0.2.3: handbook-harvest round 2 — 11 INERT new closures promoted (corpus 41->52), all claimed, none wired. MAPPING_VERSION intentionally stays 0.2.2: every promoted closure is inert (not in REGIME_TO_CLOSURES), so build_mapping()'s projection is byte-identical and the drift-guard is green WITHOUT regen. New: Incropera whitaker-sphere-external-forced-1972 (viscosity_ratio_wall_bulk [1.0,3.2] sphere μ/μ_s moat; known-partial WHEN WIRED) + laminar-fully-developed-tube nu366/nu436 (reynolds_number<=2300 analytical backbone, OBSERVABLE); Rohsenow cheng-curved-square-duct-nusselt-1975 (dean_number [20,705], D_h-normalized) + depew-august/marcos-bergles horizontal-tube mixed-conv (rayleigh_number); VDI eckert-reference-temperature-compressible-1972 (mach_number<=20); Schlichting millikan-log-law (wall_y_plus>=70) + goertler-concave-wall-transition (goertler_number>=7, momentum-thickness) + herwig-variable-property-bl (mach_number<=3) + rotta-constant-turbulent-prandtl (prandtl_number>=0.5 MOLECULAR-Pr, OBSERVABLE). dean_number & goertler_number are new vocabulary coords (conventions pinned in SCHEMA.md). 0.2.2: handbook-harvest batch — VDI gnielinski-1976 property-variation (prandtl_ratio_bulk_wall [0.1,10] + temperature_ratio_bulk_wall [0.5,1.0], FIRE) + swanson-catton-opposing-mixed-convection-1987 grashof_number (inert); Schlichting mach_number closures mack-second-mode-transition-1969 (>=2.2) + perfect-gas-constant-cp-compressible-bl-1989 (<=5.0) (inert); Rohsenow blasius-pohlhausen-horizontal-plate-forced-1921 (3 buoyancy-grouping coords) + campbell-perkins-triangular-duct-air-1968 (temperature_ratio_wall_bulk [1.10,2.11] gas T-ratio) (both inert); all new coords structural-binary/UNOBSERVABLE, additive. 0.2.1: +Sparrow-Gregg Ri<=0.225 on blasius-pohlhausen (fires) + sieder-tate-laminar (inert)


def corpus_fingerprint(path: str | Path | None = None) -> dict:
    """{'version', 'sha256', 'n_entries', 'tier'} for the save/load manifest.

    The hash is over the SORTED non-empty JSONL lines, so reordering closures
    does not change it (the corpus is a set of closures, not an ordered list).
    path=None fingerprints the ACTIVE corpus (env → premium → bundled seed); the
    'tier' field lets load() distinguish a seed-fitted guard from a premium one
    (different content → different hash already, but tier makes the drift message
    explicit). Seed and premium therefore carry distinct fingerprints by design.
    """
    p = Path(path) if path is not None else resolve_corpus_path()
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    digest = hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()
    return {
        "version": CALIBRATION_CORPUS_VERSION,
        "sha256": digest,
        "n_entries": len(lines),
        "tier": active_tier(p),
    }
