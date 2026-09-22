"""Closure registry — the keyed `{closure_id -> ClosureEntry}` map.

Each entry binds the corpus `closure_id` (the slug used in
`results/calibration_corpus/corpus.jsonl`) to:
  - the executable formula (`fn`)
  - the inputs the formula needs (`required_inputs`) — keys the substrate
    engine populates from the row
  - the geometry class the formula was derived for (`geometry_class`) — the
    invariant compares this to `VehicleConfig.geometry.class_`
  - cached validity bounds (`re_range`, `pr_range`, `ra_range`) — mirror the
    calibration table; corpus.jsonl remains the source of truth
  - the bound status (`status`) — mirrors `bound_status` in the calibration
    table (`confirmed`, `claimed`, `extrapolated`, `confirmed-contested`),
    plus the local `not-in-corpus` sentinel for reference-only formulas
    that have no corpus entry (Petukhov, Churchill blend).

The registry is constructed at import time. Its keys MUST be a subset of
the calibration corpus closure_ids, except for entries marked
`status="not-in-corpus"`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from physmap.closures.formulas import (
    modified_sparrow_cur_nu,
    gnielinski_nu,
    dittus_boelter_nu,
    petukhov_nu,
    sieder_tate_nu,
    pohlhausen_forced_local_nu,
    mcadams_natural_local_nu,
    churchill_mixed_nu,
    aung_worku_mixed_nu,
    pate_freestream_noise_bound,
    marineau_entropy_shock_bound,
)
from physmap.closures.geometry_classes import (
    NARROW_RECT_CHANNEL_ONE_SIDED,
    CIRCULAR_PIPE,
    FLAT_PLATE_EXTERNAL_FORCED,
    VERTICAL_PLATE_EXTERNAL_NATURAL,
    FLAT_PLATE_EXTERNAL_MIXED,
    HYPERSONIC_SHARP_CONE,
    HYPERSONIC_BLUNT_CONE,
    assert_known_geometry,
)


# Bound-status vocabulary mirrors the corpus calibration table, plus one
# local sentinel for closures whose formula we ship but whose calibration
# bounds are not yet in corpus.jsonl. The ClosureValidityDetector skips
# entries with status="not-in-corpus" (no validity rectangle to test against).
ClosureStatus = str   # "confirmed" | "claimed" | "extrapolated" | "confirmed-contested" | "not-in-corpus"

# Sentinel for "this formula has no calibration entry" — kept in registry
# only so the substrate engine can compute it for reference predictions.
STATUS_NOT_IN_CORPUS = "not-in-corpus"


@dataclass(frozen=True)
class ClosureEntry:
    """One executable closure, bridged to its corpus calibration entry."""

    closure_id: str
    fn: Callable[..., object]
    required_inputs: tuple[str, ...]      # keys substrate must pass as kwargs
    geometry_class: str                   # exact string from geometry_classes.py
    status: ClosureStatus                 # mirrors corpus bound_status (or sentinel)
    re_range: tuple[float, float] | None = None     # cached from corpus calibration
    pr_range: tuple[float, float] | None = None
    ra_range: tuple[float, float] | None = None     # for natural-convection closures
    ri_range: tuple[float, float] | None = None     # for mixed-convection (richardson_number) anchors
    bound_range: tuple[float, float] | None = None  # generic validated band for a non-(Re/Pr/Ra/Ri) bound
                                                     # coord (freestream-noise %, S_T/X_SW); mirrors corpus
    note: str = ""                                  # optional human-readable rationale

    def __post_init__(self) -> None:
        assert_known_geometry(self.geometry_class)
        if not self.closure_id:
            raise ValueError("ClosureEntry.closure_id must be non-empty.")
        if not self.required_inputs:
            raise ValueError(
                f"ClosureEntry {self.closure_id!r} declared no required_inputs; "
                f"the substrate engine cannot dispatch the formula."
            )


# ── REGISTRY ─────────────────────────────────────────────────────────────────
# Keys MUST match the slug in results/calibration_corpus/corpus.jsonl, except
# for STATUS_NOT_IN_CORPUS entries (Petukhov, Churchill) which have no corpus
# row. Ranges below are CACHED from the corpus calibration table and must be
# kept in sync; the calibration table is the source of truth, the registry is
# the executable bridge.

REGISTRY: dict[str, ClosureEntry] = {

    # ── narrow_rect_channel_one_sided (Forrest matched) ──────────────────────
    "modified-sparrow-cur-asym-narrow-rect-channel-2014": ClosureEntry(
        closure_id="modified-sparrow-cur-asym-narrow-rect-channel-2014",
        fn=modified_sparrow_cur_nu,
        required_inputs=("Re", "Pr"),
        geometry_class=NARROW_RECT_CHANNEL_ONE_SIDED,
        status="extrapolated",
        re_range=(10000.0, 70000.0),
        pr_range=(2.2, 5.4),
        note="Forrest 2014 Eq. 7. Matched closure for Forrest narrow-rect mini-channel.",
    ),

    # ── circular_pipe (Gnielinski/D-B/Sieder-Tate canonical triple) ──────────
    "gnielinski-1976": ClosureEntry(
        closure_id="gnielinski-1976",
        fn=gnielinski_nu,
        required_inputs=("Re", "Pr"),
        geometry_class=CIRCULAR_PIPE,
        status="confirmed",
        re_range=(3000.0, 5.0e6),
        pr_range=(0.5, 2000.0),
        note="Gnielinski 1976. Canonical turbulent circular-pipe Nu.",
    ),
    "gnielinski-constprop-sco2": ClosureEntry(
        closure_id="gnielinski-constprop-sco2",
        fn=gnielinski_nu,
        required_inputs=("Re", "Pr"),
        geometry_class=CIRCULAR_PIPE,
        status="claimed",
        re_range=(3000.0, 5.0e6),
        pr_range=(0.5, 2000.0),
        note=("Constant-property Gnielinski applied to supercritical CO2 (SAME Nu "
              "formula as gnielinski-1976 -> identical surrogate prediction). "
              "REGIME-SPECIFIC entry so its corpus validated_range can carry a "
              "wall/bulk viscosity-ratio (property-variation) validity bound WITHOUT "
              "mutating the shared gnielinski-1976 entry used by NACA/Forrest "
              "(the dirker lesson). Velazquez sCO2 property-variation vehicle."),
    ),
    "dittus-boelter-1930": ClosureEntry(
        closure_id="dittus-boelter-1930",
        fn=dittus_boelter_nu,
        required_inputs=("Re", "Pr"),
        geometry_class=CIRCULAR_PIPE,
        status="claimed",
        re_range=(10000.0, 1.2e6),
        pr_range=(0.7, 160.0),
        note="McAdams form of Dittus-Boelter. Heating default; cooling via heating=False kwarg.",
    ),
    "dittus-boelter-buoyancy-sco2": ClosureEntry(
        closure_id="dittus-boelter-buoyancy-sco2",
        fn=dittus_boelter_nu,
        required_inputs=("Re", "Pr"),
        geometry_class=CIRCULAR_PIPE,
        status="claimed",
        re_range=(10000.0, 1.2e6),
        pr_range=(0.5, 2000.0),
        note=("Constant-property Dittus-Boelter applied to supercritical CO2 (SAME Nu formula as "
              "dittus-boelter-1930 -> identical surrogate prediction). REGIME-SPECIFIC entry so its "
              "corpus validated_range can carry the Liu buoyancy-parameter (Bu) validity bound WITHOUT "
              "mutating the shared dittus-boelter-1930 entry (the dirker/velazquez lesson). Re/Pr are the "
              "broad sCO2 turbulent envelope (Pr spikes near T_pc); the buoyancy bound Bu<=1.3e-5 is the "
              "discriminator. Jin et al. 2023 sCO2 vertical-tube buoyancy vehicle (Liu Bu, Eq. 21)."),
    ),
    "sieder-tate-1936": ClosureEntry(
        closure_id="sieder-tate-1936",
        fn=sieder_tate_nu,
        required_inputs=("Re", "Pr"),
        geometry_class=CIRCULAR_PIPE,
        status="claimed",
        re_range=(10000.0, 1.2e6),
        pr_range=(0.7, 17000.0),
        note="Includes mu_b/mu_w correction (defaults to 1.0 if not supplied).",
    ),
    "petukhov-1970": ClosureEntry(
        closure_id="petukhov-1970",
        fn=petukhov_nu,
        required_inputs=("Re", "Pr"),
        geometry_class=CIRCULAR_PIPE,
        status="claimed",
        re_range=(10000.0, 5.0e6),
        pr_range=(0.5, 2000.0),
        note=("Petukhov 1970 turbulent circular-pipe Nu. Added to corpus.jsonl "
              "as part of evidence_corpus v0.1 (commit 2897392); the registry "
              "entry was previously tagged not-in-corpus."),
    ),

    # ── circular_pipe (mixed-convection richardson_number anchor) ────────────
    # Corpus-validity anchor for the Stage-3 MIDDLE vehicle (Dirker/Meyer/Reid
    # water tube). main's regime framework maps MIXED_CONVECTION_HORIZONTAL_TUBE
    # -> this closure; it carries the richardson_number bound (Ri in [0.1, 10]).
    # No executable Nu predictor (the vehicle's surrogate is a data-driven GP);
    # registered so the geometry-match invariant + matched lookup resolve. Fills
    # the registry gap noted in the regime->observability mapping work.
    "aung-worku-mixed-convection-1986": ClosureEntry(
        closure_id="aung-worku-mixed-convection-1986",
        fn=aung_worku_mixed_nu,
        required_inputs=("Re", "Pr"),
        geometry_class=CIRCULAR_PIPE,
        status="claimed",
        ri_range=(0.1, 10.0),
        note=("Mixed forced-natural convection richardson_number anchor "
              "(Ri in [0.1, 10]); corpus-validity bound only, Nu predictor not "
              "implemented (Stage-3 dirker_water uses a GP surrogate)."),
    ),

    # ── hypersonic_sharp_cone (Casper freestream-noise transition anchor) ────
    # Corpus-validity anchor for the aerospace PHYSMAP_WINS vehicle (Casper
    # quiet-vs-noisy hypersonic transition). Carries the freestream-noise bound
    # (Pate-Stainback: conventional tunnels validated for RMS Pitot >= ~0.5%);
    # fires on the flight-like QUIET deploy (~0.05%). No executable predictor
    # (Casper uses a GP transition surrogate); registered so the geometry-match
    # invariant + matched lookup resolve.
    "pate-stainback-freestream-noise-hypersonic-1980": ClosureEntry(
        closure_id="pate-stainback-freestream-noise-hypersonic-1980",
        fn=pate_freestream_noise_bound,
        required_inputs=("freestream_noise_pct",),
        geometry_class=HYPERSONIC_SHARP_CONE,
        status="claimed",
        bound_range=(0.5, 10.0),    # freestream_noise_rms_pitot_pct band (mirrors corpus.jsonl)
        note=("Pate & Stainback freestream-disturbance transition correlation; "
              "corpus carries the freestream_noise_rms_pitot_pct bound. Corpus-"
              "validity anchor only — Casper uses a GP surrogate (loader "
              "casper_hypersonic_transition)."),
    ),

    # ── hypersonic_blunt_cone (Marineau entropy-layer/shock anchor) ──────────
    # Corpus-validity anchor for the aerospace NEGATIVE-CONTROL vehicle
    # (Marineau bluntness). Carries the entropy-layer/shock-interaction bound
    # (S_T/X_SW >= 0.1 for the e^N / 2nd-mode regime); fires on large-bluntness
    # deploy — but the steelman baseline ALSO fires (nose radius is a surrogate
    # input) so PhysMAP correctly declines. No executable predictor; registered
    # for the geometry-match invariant.
    "marineau-entropy-layer-shock-interaction-2014": ClosureEntry(
        closure_id="marineau-entropy-layer-shock-interaction-2014",
        fn=marineau_entropy_shock_bound,
        required_inputs=("st_xsw_ratio",),
        geometry_class=HYPERSONIC_BLUNT_CONE,
        status="claimed",
        bound_range=(0.1, 1.0e9),   # entropy_layer_shock_ratio band (mirrors corpus.jsonl)
        note=("Marineau et al. (2014, SAND2014-4326C) entropy-layer/shock-wave "
              "interaction transition boundary (S_T/X_SW >= 0.1); corpus carries "
              "the entropy_layer_shock_ratio bound. Corpus-validity anchor only — "
              "Marineau is the baseline-visible negative control (nose radius is "
              "a surrogate input)."),
    ),

    # ── flat_plate_external_forced (Lance & Smith Pohlhausen) ────────────────
    "blasius-pohlhausen-flat-plate-forced-1921": ClosureEntry(
        closure_id="blasius-pohlhausen-flat-plate-forced-1921",
        fn=pohlhausen_forced_local_nu,
        required_inputs=("Re", "Pr"),
        geometry_class=FLAT_PLATE_EXTERNAL_FORCED,
        status="confirmed",
        re_range=(0.0, 5.0e5),
        pr_range=(0.6, 50.0),
        note=("Local form Nu_x = 0.332 Re_x^(1/2) Pr^(1/3). Substrate engine "
              "passes Re_x as the `Re` kwarg per row."),
    ),

    # ── vertical_plate_external_natural (Lance & Smith McAdams) ──────────────
    "mcadams-vertical-plate-natural-1954": ClosureEntry(
        closure_id="mcadams-vertical-plate-natural-1954",
        fn=mcadams_natural_local_nu,
        required_inputs=("Ra",),
        geometry_class=VERTICAL_PLATE_EXTERNAL_NATURAL,
        status="confirmed",
        re_range=None,
        pr_range=(0.6, 7.0),
        ra_range=(1.0e4, 1.0e9),
        note=("Ra_x = Gr_x * Pr. Substrate engine passes per-row Ra_x as the "
              "`Ra` kwarg."),
    ),

    # ── flat_plate_external_mixed (Lance & Smith matched closure) ────────────
    # Churchill blend itself isn't in corpus; it's a Nu(Nu_F, Nu_N) combinator.
    # We register it as the matched closure for the L&S vehicle so the geometry
    # invariant has something to compare against, but flag status accordingly.
    "churchill-mixed-convection-flat-plate": ClosureEntry(
        closure_id="churchill-mixed-convection-flat-plate",
        fn=churchill_mixed_nu,
        required_inputs=("Nu_forced", "Nu_natural"),
        geometry_class=FLAT_PLATE_EXTERNAL_MIXED,
        status=STATUS_NOT_IN_CORPUS,
        re_range=None,
        pr_range=None,
        note=("Mixed-convection blend Nu_M^n = Nu_F^n + Nu_N^n (n=3, assisting). "
              "Not a primary closure in the corpus; composes Pohlhausen + McAdams. "
              "Kept as L&S matched closure so the geometry invariant works."),
    ),
}


def get_closure(closure_id: str) -> ClosureEntry:
    """Look up a closure by id; raise KeyError with a helpful message on miss."""
    try:
        return REGISTRY[closure_id]
    except KeyError as exc:
        raise KeyError(
            f"Unknown closure_id {closure_id!r}. "
            f"Known: {sorted(REGISTRY.keys())}. "
            f"If you're adding a new closure, register it in "
            f"physmap/closures/registry.py with its formula in formulas.py."
        ) from exc


def closure_ids_for_geometry(geometry_class: str) -> list[str]:
    """Return all closure_ids registered for a given geometry class.

    Used by the substrate engine and tests to confirm at least one matched
    closure exists for a vehicle's geometry, and by diagnostics.
    """
    assert_known_geometry(geometry_class)
    return sorted(cid for cid, entry in REGISTRY.items()
                  if entry.geometry_class == geometry_class)
