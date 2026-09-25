"""Data-source loader adapters — the LOADERS registry entries.

Each adapter takes a validated `VehicleConfig` plus the closure registry and
returns `(rows, reference, meta)` in the existing pipeline shape.

LOADER OWNERSHIP MIGRATION STATUS (per the Step-9 plan):
  lance_smith_lfs    — ENGINE-DRIVEN (Step 9a). Reuses CSV helpers from
                       `lance_smith_substrate.py` but computes all closure
                       predictions VIA THE REGISTRY. Byte-equal output to
                       the legacy `lance_smith_to_rows()`; the structural-
                       equality gate in test_substrate_engine pins this.
  forrest_visual_estimates - placeholder (Step 9b).
  mudhafar_wpd       - placeholder (Step 9c, awaiting WPD CSVs).
  naca_wpd           - placeholder (Step 9d, locked-last per gate decision).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from physmap.closures import ClosureEntry
from physmap.substrate.corpus_real import SubstrateMeta
from physmap.substrate.stage1_ingest import Mechanism, Row, load_rows
from physmap.substrate.engine import register_loader
from physmap.substrate.vehicle_config import VehicleConfig


# Benchmark substrate CSVs live in the CHECKOUT, not in the installed package --
# they are deliberately outside the wheel. YAML paths look like
# "data/naca/wpd_fig10.csv" and resolve against the repository root.
#
# This raises rather than returning a wrong path. A silently mis-resolved CSV
# surfaces as an empty or short substrate, which the engine happily runs on and
# reports an outcome for.
def _repo_root() -> Path:
    from physmap._paths import CheckoutRequired, repo_root

    root = repo_root()
    if root is None:
        raise CheckoutRequired("the benchmark substrate data")
    return root


def _resolve(relative: str | None) -> Path | None:
    if relative is None:
        return None
    p = Path(relative)
    return p if p.is_absolute() else (_repo_root() / p)


# ── lance_smith_lfs (engine-driven, Step 9a) ────────────────────────────────

# The reason string in SubstrateMeta is preserved byte-equal to the legacy
# `lance_smith_to_rows()` so the structural-equality gate stays strict.
_LANCE_SMITH_REASON = (
    "Independent experimental truth: SRQ-HeatFlux measured q\" at 3 "
    "plate locations × 92 timesteps × {q\",B,S,U} = 276 measurements "
    "per Lance & Smith ASME J. VVUQ 2016 (OSTI 1263650/1257801; USU "
    "DigitalCommons engineering_datasets/2). Truth is measured q\" "
    "with B/S/U uncertainty, NOT Eq-13 and NOT the theoretical Ri "
    "grid (the two vehicle-3 disqualifiers, refused by the loader)."
)


def lance_smith_lfs(config: VehicleConfig,
                    registry: dict[str, ClosureEntry]) -> tuple[list[Row], dict, SubstrateMeta]:
    """Engine-driven Lance & Smith loader.

    Reads raw measurements via the I/O helpers in `lance_smith_substrate.py`
    (CSV parsers, time-base alignment, forbidden-source guard), then computes
    all per-row closure predictions VIA THE CLOSURE REGISTRY:

        Nu_forced  := REGISTRY["blasius-pohlhausen-..."].fn(Re=Re_x, Pr=pr)
        Nu_natural := REGISTRY["mcadams-vertical-..."].fn(Ra=Ra_x)
        Nu_blend   := REGISTRY["churchill-mixed-..."].fn(
                          Nu_forced=Nu_forced, Nu_natural=Nu_natural, n=n)

    Physical constants (g, ν_air, k_air, Pr_air, Churchill blend exponent)
    come from `config.data_source.options` — NOT from module-level constants
    in `lance_smith_substrate.py`. This is the substantive Step-9a change:
    the registry is the source of truth for closure formulas; the YAML is
    the source of truth for vehicle-specific physical constants.

    Byte-equality with the legacy loader is the gate. See
    `tests/test_substrate_engine.py::test_lance_smith_engine_matches_direct_loader_call`.
    """
    # I/O helpers stay in lance_smith_substrate for now (vehicle-specific
    # CSV plumbing — moved out of scope for Step 9a). The closures DO move.
    from physmap.substrate.lance_smith import (
        BC_HEATED_WALL_NAME,
        BC_INLET_TEMP_NAME,
        BC_INLET_VEL_NAME,
        SRQ_HEATFLUX_NAME,
        _refuse_forbidden_sources,
        read_bc_freestream_timeseries,
        read_bc_mean_timeseries,
        read_srq_heatflux,
        read_wall_temp_local_at_X,
    )

    data_dir_in = _resolve(config.data_source.dir)
    if data_dir_in is None:
        raise ValueError(
            f"VehicleConfig {config.vehicle_id!r}: data_source.dir is required "
            f"for the lance_smith_lfs loader."
        )
    data_dir = data_dir_in.resolve()
    _refuse_forbidden_sources(data_dir)

    # ── physical constants from the YAML (data_source.options) ──────────────
    opts = config.data_source.options
    pr = float(opts.get("Pr_air", 0.71))
    g_gravity = float(opts.get("g_gravity", 9.81))
    nu_air = float(opts.get("nu_air_m2_s", 1.86e-5))
    k_air = float(opts.get("k_air_w_mk", 0.0265))
    churchill_n = float(opts.get("churchill_blend_n", 3.0))
    time_subrange: tuple[float, float] | None = None
    raw_subrange = opts.get("time_subrange_s")
    if raw_subrange is not None:
        time_subrange = (float(raw_subrange[0]), float(raw_subrange[1]))

    # ── raw I/O ─────────────────────────────────────────────────────────────
    srq = read_srq_heatflux(data_dir / SRQ_HEATFLUX_NAME)
    t_seconds = srq["time_s"]
    n_t = len(t_seconds)
    X_m = srq["X_m"]
    n_loc = len(X_m)

    t_w, T_wall_local = read_wall_temp_local_at_X(
        data_dir / BC_HEATED_WALL_NAME, X_m,
    )
    t_i, T_inlet_mean = read_bc_mean_timeseries(
        data_dir / BC_INLET_TEMP_NAME, "T(K)",
    )
    t_u, u_inlet_freestream = read_bc_freestream_timeseries(
        data_dir / BC_INLET_VEL_NAME, "u(m/s)", percentile=90.0,
    )

    # Time-base sanity check (mirrors the legacy guard).
    for label, t_arr in (("wall", t_w), ("inlet_T", t_i), ("inlet_u", t_u)):
        if not np.allclose(t_arr, t_seconds, atol=1e-6):
            raise RuntimeError(
                f"time-base mismatch: {label} times {t_arr[:3]}... vs SRQ "
                f"{t_seconds[:3]}... — re-check BC file headers"
            )

    # ΔT(X, t) is per-location-per-timestep — the heated wall has substantial
    # X-variation (cool at leading edge, hot in developed region).
    delta_T = T_wall_local - T_inlet_mean[np.newaxis, :]
    T_film = 0.5 * (T_wall_local + T_inlet_mean[np.newaxis, :])
    beta = 1.0 / T_film

    # ── closure registry lookups (THE ENGINE-DRIVEN PIECE) ──────────────────
    matched = registry[config.matched_closure_id]    # Churchill blend
    forced_id = "blasius-pohlhausen-flat-plate-forced-1921"
    natural_id = "mcadams-vertical-plate-natural-1954"
    forced = registry[forced_id]
    natural = registry[natural_id]

    # Pin the geometry-class linkage so a future registry edit that loses the
    # right Pohlhausen/McAdams entries surfaces here, not as a silent
    # numerical drift.
    if forced_id not in config.reference_closure_ids:
        raise RuntimeError(
            f"Lance & Smith engine path requires {forced_id!r} in "
            f"reference_closure_ids; got {config.reference_closure_ids}."
        )
    if natural_id not in config.reference_closure_ids:
        raise RuntimeError(
            f"Lance & Smith engine path requires {natural_id!r} in "
            f"reference_closure_ids; got {config.reference_closure_ids}."
        )

    # ── per-row build ───────────────────────────────────────────────────────
    rows: list[Row] = []
    for i_loc, x in enumerate(X_m):
        x_f = float(x)
        for i_t, t_s in enumerate(t_seconds):
            t_s_f = float(t_s)
            if time_subrange is not None:
                t_lo, t_hi = time_subrange
                if not (t_lo <= t_s_f <= t_hi):
                    continue

            u = float(u_inlet_freestream[i_t])
            T_wall = float(T_wall_local[i_loc, i_t])
            T_inlet = float(T_inlet_mean[i_t])
            dT = float(delta_T[i_loc, i_t])
            beta_i = float(beta[i_loc, i_t])
            q_meas = float(srq["q"][i_loc, i_t])
            u_q = float(srq["U"][i_loc, i_t])

            # Local non-dimensional groups (positive ΔT for assisting/heated)
            Re_x = max(u * x_f / nu_air, 1e-12)
            Gr_x = (
                g_gravity * beta_i * max(dT, 0.0) * (x_f ** 3) / (nu_air ** 2)
            )
            Ra_x = Gr_x * pr
            Ri_x = Gr_x / (Re_x ** 2)

            # ─── REGISTRY-DRIVEN CLOSURE EVALUATION ─────────────────────────
            # The legacy code called nu_forced_pohlhausen_local, etc.,
            # imported directly from lance_smith_substrate.py. Here we go
            # through the registry — same math (closure formulas are
            # byte-equal copies; pinned by test_closures_registry), but the
            # registry is the source of truth.
            Nu_F = float(forced.fn(Re=np.array([Re_x]), Pr=pr)[0])
            Nu_N = float(natural.fn(Ra=np.array([Ra_x]))[0])
            Nu_M_blend = float(
                matched.fn(
                    Nu_forced=np.array([Nu_F]),
                    Nu_natural=np.array([Nu_N]),
                    n=churchill_n,
                )[0]
            )

            # Measured Nu_x from measured q":  Nu_x = q" · x / (k · ΔT)
            if dT > 0 and x_f > 0:
                nu_meas = q_meas * x_f / (k_air * dT)
                nu_unc = u_q * x_f / (k_air * dT)
            else:
                nu_meas = float("nan")
                nu_unc = float("nan")

            # Mechanism calib_lo/hi come from the REGISTRY ranges; this
            # replaces the BLASIUS_RE_LO/HI + MCADAMS_RA_LO/HI module
            # constants in lance_smith_substrate.py.
            if forced.re_range is None:
                raise RuntimeError(
                    f"{forced_id!r} has no re_range; cannot construct "
                    f"forced-mechanism calibration bounds."
                )
            if natural.ra_range is None:
                raise RuntimeError(
                    f"{natural_id!r} has no ra_range; cannot construct "
                    f"natural-mechanism calibration bounds."
                )

            mechanisms = [
                Mechanism(
                    name="forced",
                    closure_id=forced_id,
                    operating_value=Re_x,
                    calib_lo=forced.re_range[0],
                    calib_hi=forced.re_range[1],
                    contribution=Nu_F ** churchill_n,
                ),
                Mechanism(
                    name="natural",
                    closure_id=natural_id,
                    operating_value=Ra_x,
                    calib_lo=natural.ra_range[0],
                    calib_hi=natural.ra_range[1],
                    contribution=Nu_N ** churchill_n,
                ),
            ]

            rows.append(Row(
                operating_point=(round(x_f, 4), round(t_s_f, 2)),
                surrogate_prediction=Nu_M_blend,
                cfd_truth=nu_meas,
                truth_source="experimental",
                cfd_uncertainty=nu_unc,
                guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
                mechanisms=mechanisms,
                meta={
                    "time_index": int(i_t),
                    "time_s": float(t_s),
                    "location_index": int(i_loc),
                    "X_m": float(x),
                    "u_inlet_m_per_s": float(u),
                    "T_wall_K": float(T_wall),
                    "T_inlet_K": float(T_inlet),
                    "delta_T_K": float(dT),
                    "Re_x": float(Re_x),
                    "Gr_x": float(Gr_x),
                    "Ra_x": float(Ra_x),
                    "Ri_x": float(Ri_x),
                    "Nu_F_local": float(Nu_F),
                    "Nu_N_local": float(Nu_N),
                    "Nu_blend_churchill": float(Nu_M_blend),
                    "q_meas_W_per_m2": float(q_meas),
                    "q_uncertainty_W_per_m2": float(u_q),
                    "Nu_meas": float(nu_meas),
                    "Nu_meas_uncertainty": float(nu_unc),
                },
            ))

    # Independence guard runs the per-row shape validation.
    rows = load_rows(rows)

    plate_length_m = float(
        config.geometry.dims.get("plate_length_m", 1.926)
    )

    reference = {"ood": [0.0], "residual": [0.0], "variance": [0.0]}
    meta = SubstrateMeta(
        name="lance-smith-vehicle3",
        divergent_truth_substrate=True,
        reason=_LANCE_SMITH_REASON,
        norm_strategy="per_row_truth",
        bound_for_pde=None,
        magnitude_bridge_ok=True,
        extra={
            "data_dir": str(data_dir),
            "n_timesteps": int(n_t),
            "n_locations": int(n_loc),
            "n_rows_pre_subrange": int(n_t * n_loc),
            "n_rows_post_subrange": int(len(rows)),
            "time_subrange_s": list(time_subrange) if time_subrange else None,
            "plate_length_m": plate_length_m,
            "X_positions_m": X_m.tolist(),
            "time_range_s": [float(t_seconds[0]), float(t_seconds[-1])],
            "fluid": "air at ~87 kPa, T_film ~305 K",
            "air_properties": {
                "nu_m2_per_s": nu_air,
                "k_W_per_mK": k_air,
                "Pr": pr,
                "note": "ν pressure-corrected for ambient 87 kPa",
            },
            "closures": {
                "forced": (
                    f"{forced_id} "
                    f"(Nu_x = 0.332·Re_x^(1/2)·Pr^(1/3))"
                ),
                "natural": (
                    f"{natural_id} "
                    f"(Nu_x = 0.59·Ra_x^(1/4))"
                ),
                "blend": f"Churchill assisting, n={churchill_n}",
            },
        },
    )
    return rows, reference, meta


# ── forrest_visual_estimates (engine-driven, Step 9b) ───────────────────────

# Identical to the legacy `forrest_substrate.SubstrateMeta.reason` so the
# structural-equality gate stays strict.
_FORREST_REASON = (
    "Independent experimental truth: measured Nu via thermocouples + "
    "RTDs + heat flux sensors on a high-aspect-ratio mini-channel "
    "with asymmetric one-sided heating, per Forrest, Hu, Buongiorno, "
    "McKrell (2014, SAND2014-18834J / OSTI 1295764). Nu uncertainty "
    "at 95% CI ~±10%. Truth is measured q\" → measured Nu, NOT a "
    "fitted correlation. Steady-state — no temporal autocorrelation "
    "discount; each (Re, Pr) operating point is an independent draw."
)


def _load_forrest_visual_estimate_rows(csv_path: Path,
                                       cell_assignment_fn,
                                       ) -> list[dict]:
    """Read the visual-estimate CSV into per-point dicts (raw measurements +
    propagated total uncertainty). Comment lines beginning with '#' are
    skipped; rows with non-positive Nu_meas are skipped (mirrors the
    legacy `forrest_to_rows` filter).

    Returns dicts in INSERTION ORDER (matches the CSV's row-id order) so
    the structural-equality gate aligns row-for-row.
    """
    import csv as _csv
    import numpy as np

    rows: list[dict] = []
    with csv_path.open("r", newline="") as fh:
        reader = _csv.DictReader(
            (line for line in fh if not line.lstrip().startswith("#")),
        )
        for r in reader:
            try:
                Re = float(r["Re"])
                Pr = float(r["Pr"])
                Nu_meas = float(r["Nu_meas"])
            except (TypeError, ValueError, KeyError):
                continue
            if Nu_meas <= 0:
                continue
            # Paper-reported uncertainty is FRACTIONAL (e.g. 0.10 = 10%);
            # digitization uncertainty is ABSOLUTE Nu units. Both go into
            # the ForrestRow shape the legacy expects.
            nu_unc_paper_pct = float(r.get("Nu_unc_paper_pct", 0.0) or 0.0)
            nu_unc_dig_abs_raw = r.get("Nu_unc_digitization_abs", "")
            nu_unc_dig_abs = (
                float(nu_unc_dig_abs_raw) if str(nu_unc_dig_abs_raw).strip() else 0.0
            )
            Nu_unc_reported = Nu_meas * nu_unc_paper_pct
            # legacy propagation: sqrt(reported^2 + digitization^2)
            if nu_unc_dig_abs > 0:
                total_unc = float(
                    np.sqrt(Nu_unc_reported ** 2 + nu_unc_dig_abs ** 2)
                )
            else:
                total_unc = Nu_unc_reported
            rows.append({
                "Re": Re,
                "Pr": Pr,
                "Nu_meas": Nu_meas,
                "Nu_unc_reported": Nu_unc_reported,
                "Nu_unc_total_propagated": total_unc,
                "digitization_uncertainty": nu_unc_dig_abs if nu_unc_dig_abs > 0 else None,
                "source": str(r.get("source") or "forrest"),
                "figure_or_table": str(r.get("figure") or ""),
                "T_bulk_K": None,
                "T_wall_K": None,
                "mass_flow_kg_s": None,
                "cell": cell_assignment_fn(Re),
            })
    return rows


def _forrest_cell_assignment_from_config(config: VehicleConfig):
    """Return a function `Re -> cell_name` derived from the YAML's re_bands.
    Mirrors `forrest_substrate.cell_assignment` semantics: the first band
    whose `re_lt` exceeds Re wins; the last band is the catch-all."""
    if config.cell_bands.type != "re_bands":
        raise ValueError(
            f"Forrest engine path expects cell_bands.type='re_bands'; "
            f"got {config.cell_bands.type!r}."
        )
    bands = list(config.cell_bands.bands)
    if not bands:
        raise ValueError("Forrest cell_bands has no bands.")

    def assign(re_val: float) -> str:
        for band in bands:
            re_lt = float(band["re_lt"])
            if re_val < re_lt:
                return str(band["name"])
        return str(bands[-1]["name"])
    return assign


def forrest_visual_estimates(config: VehicleConfig,
                             registry: dict[str, ClosureEntry]) -> tuple[list[Row], dict, SubstrateMeta]:
    """Engine-driven Forrest loader (Step 9b).

    Reads the visual-estimate CSV at `config.data_source.path` and emits
    Row objects whose `surrogate_prediction` is the matched closure
    (Modified Sparrow-Cur) computed VIA THE REGISTRY. Reference
    closures (Gnielinski, Dittus-Boelter, Petukhov, Sieder-Tate) are
    also computed via the registry and surfaced in meta + as Mechanism
    entries.

    The geometry-match invariant is exercised on its HAPPY path here:
    Forrest's matched_closure_id is `modified-sparrow-cur-...` whose
    registry `geometry_class` is `narrow_rect_channel_one_sided`, which
    matches the vehicle YAML's `geometry.class`. No `expect_mismatch`
    override needed.

    Status caveat: today the only CSV available is the visual-estimate
    triage file (~n=15, sub-critical + transition + boundary rows).
    `cfd_truth` from this source is NOT bankable as a true verdict; the
    `source` field is `visual-estimate-rendered-pdf-fig5` so downstream
    callers can filter. The loader still RUNS so the substrate engine
    is exercised end-to-end on Forrest before banked digitization lands.
    """
    import csv as _csv
    import numpy as np

    if config.data_source.path is None:
        raise ValueError(
            f"VehicleConfig {config.vehicle_id!r}: data_source.path is "
            f"required for the forrest_visual_estimates loader."
        )
    csv_path = _resolve(config.data_source.path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Forrest visual-estimate CSV not found: {csv_path}"
        )

    # Registry lookups (matched + 4 references).
    matched = registry[config.matched_closure_id]
    forced_id = config.matched_closure_id   # alias for readability below
    refs: dict[str, ClosureEntry] = {
        cid: registry[cid] for cid in config.reference_closure_ids
    }

    # Pin the legacy-expected reference set so a future YAML edit that
    # drops one (or reorders) surfaces here, not as silent meta drift.
    expected_refs = {
        "gnielinski-1976",
        "dittus-boelter-1930",
        "sieder-tate-1936",
        "petukhov-1970",
    }
    missing = expected_refs - set(refs)
    if missing:
        raise RuntimeError(
            f"Forrest engine path expects reference_closure_ids superset "
            f"of {sorted(expected_refs)}; missing: {sorted(missing)}."
        )

    assign_cell = _forrest_cell_assignment_from_config(config)
    raw_rows = _load_forrest_visual_estimate_rows(csv_path, assign_cell)

    # Build Row objects with predictions through the registry.
    rows: list[Row] = []
    for raw in raw_rows:
        Re = raw["Re"]
        Pr = raw["Pr"]
        Re_arr = np.array([Re])
        Pr_arr = np.array([Pr])
        # MATCHED: Modified Sparrow-Cur. Geometry-matched primary closure.
        Nu_sc = float(matched.fn(Re=Re_arr, Pr=Pr_arr)[0])
        # References (geometry-mismatched circular-pipe closures, reported
        # for Table-4 cross-comparison).
        Nu_g = float(refs["gnielinski-1976"].fn(Re=Re_arr, Pr=Pr_arr)[0])
        Nu_db = float(refs["dittus-boelter-1930"].fn(Re=Re_arr, Pr=Pr_arr)[0])
        Nu_pk = float(refs["petukhov-1970"].fn(Re=Re_arr, Pr=Pr_arr)[0])
        Nu_st = float(refs["sieder-tate-1936"].fn(Re=Re_arr, Pr=Pr_arr)[0])

        # Mechanism calib_lo/hi come from the REGISTRY ranges; this
        # replaces the SPARROW_CUR_RE_LO/HI + GNIELINSKI_RE_LO/HI +
        # DITTUS_BOELTER_RE_LO/HI module constants in forrest_substrate.
        if matched.re_range is None:
            raise RuntimeError(
                f"{config.matched_closure_id!r} has no re_range; cannot "
                f"build matched mechanism."
            )
        for ref_id in ("gnielinski-1976", "dittus-boelter-1930"):
            if refs[ref_id].re_range is None:
                raise RuntimeError(
                    f"{ref_id!r} has no re_range; cannot build reference "
                    f"mechanism."
                )

        mechanisms = [
            Mechanism(
                name="forced_one_sided_narrow_rect_sparrow_cur_modified",
                closure_id=config.matched_closure_id,
                operating_value=Re,
                calib_lo=matched.re_range[0],
                calib_hi=matched.re_range[1],
                contribution=Nu_sc,
            ),
            Mechanism(
                name="forced_internal_flow_gnielinski_reference",
                closure_id="gnielinski-1976",
                operating_value=Re,
                calib_lo=refs["gnielinski-1976"].re_range[0],
                calib_hi=refs["gnielinski-1976"].re_range[1],
                contribution=Nu_g,
            ),
            Mechanism(
                name="forced_internal_flow_dittus_boelter_reference",
                closure_id="dittus-boelter-1930",
                operating_value=Re,
                calib_lo=refs["dittus-boelter-1930"].re_range[0],
                calib_hi=refs["dittus-boelter-1930"].re_range[1],
                contribution=Nu_db,
            ),
        ]

        rows.append(Row(
            operating_point=(round(Re, 1), round(Pr, 4)),
            surrogate_prediction=Nu_sc,
            cfd_truth=raw["Nu_meas"],
            truth_source="experimental",
            cfd_uncertainty=raw["Nu_unc_total_propagated"],
            guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
            mechanisms=mechanisms,
            meta={
                "Re": Re,
                "Pr": Pr,
                "Nu_meas": raw["Nu_meas"],
                "Nu_unc_reported": raw["Nu_unc_reported"],
                "Nu_unc_total_propagated": raw["Nu_unc_total_propagated"],
                "Nu_pred_modified_sparrow_cur": Nu_sc,
                "Nu_pred_gnielinski": Nu_g,
                "Nu_pred_dittus_boelter": Nu_db,
                "Nu_pred_petukhov": Nu_pk,
                "Nu_pred_sieder_tate": Nu_st,
                "cell": raw["cell"],
                "T_bulk_K": raw["T_bulk_K"],
                "T_wall_K": raw["T_wall_K"],
                "mass_flow_kg_s": raw["mass_flow_kg_s"],
                "source": raw["source"],
                "figure_or_table": raw["figure_or_table"],
                "digitization_uncertainty": raw["digitization_uncertainty"],
            },
        ))

    rows = load_rows(rows)

    # Geometry / fluid context (from YAML).
    dims = config.geometry.dims
    alpha_star = float(dims.get("aspect_ratio_alpha_star", 0.0))
    inverse = float(dims.get("aspect_ratio_inverse", 0.0))
    gap_mm = float(dims.get("gap_mm", 0.0))
    width_mm = float(dims.get("width_mm", 0.0))
    length_mm = float(dims.get("length_mm", 0.0))
    heated_length_mm = float(dims.get("heated_length_mm", 0.0))
    heated_width_mm = float(dims.get("heated_width_mm", 0.0))
    Dh_mm = float(dims.get("Dh_mm", 0.0))

    geometry_text = (
        f"high aspect ratio mini-channel, α*={alpha_star:.3f} "
        f"(~{inverse:.0f}:1 width:gap), gap "
        f"{gap_mm} mm, width {width_mm} mm, channel length "
        f"{length_mm} mm, heated length {heated_length_mm} mm × "
        f"width {heated_width_mm} mm, one-sided uniform-heat-flux "
        f"asymmetric heating (other walls insulated/adiabatic)"
    )

    reference = {"ood": [0.0], "residual": [0.0], "variance": [0.0]}
    meta = SubstrateMeta(
        name="forrest-mini-channel",
        divergent_truth_substrate=True,
        reason=_FORREST_REASON,
        norm_strategy="per_row_truth",
        bound_for_pde=None,
        magnitude_bridge_ok=True,
        extra={
            "geometry": geometry_text,
            "hydraulic_diameter_mm": Dh_mm,
            "fluid": config.fluid.name,
            "Pr_range_paper_design": [1.77, 9.44],
            "Re_range_paper_design": [2200, 93000],
            "Pr_range_paper_table4": list(config.fluid.pr_range) if config.fluid.pr_range else [2.2, 5.4],
            "Re_range_paper_table4_textbook_closures": [10000, 70000],
            "Pr_range_2012_conference": [3.9, 4.0],
            "Re_range_2012_conference": [5000, 32000],
            "critical_Re": [3500, 4000],
            "n_rows": len(rows),
            "data_source_path": str(csv_path),
            "closures": {
                "primary_geometry_matched": (
                    f"{config.matched_closure_id} "
                    f"(corpus {matched.status}; ONLY corpus closure with "
                    "explicit one-sided-heating geometry dependence)"
                ),
                "reference_circular_pipe": [
                    f"{cid} (corpus {refs[cid].status}; geometry-mismatched)"
                    for cid in config.reference_closure_ids
                ],
                "matched_closure_rationale": (
                    "Sparrow-Cur-modified is the geometry-matched closure for "
                    "Forrest's one-sided heated narrow rectangular channel. "
                    "Forrest 2014 Table 4 reports MAE 6.1% — lowest of any "
                    "standard closure on this geometry. Testing the "
                    "differentiator on circular-pipe closures would "
                    "contaminate divergence with geometry mismatch (the Lance "
                    "& Smith confined-geometry trap)."
                ),
            },
        },
    )
    return rows, reference, meta


# ── mudhafar_wpd (engine-driven scaffold, Step 9c) ──────────────────────────

# Mudhafar substrate-meta `reason` field. Kept in this module so the
# engine-driven path is self-contained; the meta text stays close to
# the loader logic.
_MUDHAFAR_REASON = (
    "Independent experimental truth: measured Nu via thermocouples on "
    "circular micro-tubes (50-950 μm inner diameter, smooth + rough "
    "variants) for air and CO2, per Mudhafar, M. A. H. (2023), 'The "
    "measurement of friction factors and heat transfer Nusselt numbers "
    "for the flow of air and CO2 through micro tubes', Heat and Mass "
    "Transfer 59:989-1004 (DOI 10.1007/s00231-022-03315-x). D3 positive-"
    "control vehicle — INTENTIONAL geometry mismatch with the matched "
    "closure (Modified Sparrow-Cur, narrow_rect_channel_one_sided) so "
    "baseline + corpus signals are both expected to fire across the "
    "small-d and rough cells."
)


# Expected WPD CSV schema, mirroring the Forrest visual-estimate shape but
# with two added geometry columns. Source figures: Figs 7-11 of Mudhafar
# 2023 (Heat and Mass Transfer 59:989-1004).
_MUDHAFAR_EXPECTED_CSV_COLUMNS = (
    "row", "Re", "Pr", "Nu_meas",
    "Nu_unc_paper_pct", "Nu_unc_digitization_abs",
    "Dh_um", "rough",
    "source", "figure", "note",
)


def _mudhafar_cell_assignment_from_config(config: VehicleConfig):
    """Build a `(Dh_um, rough) -> cell_name` mapper from the YAML's
    dh_roughness_bands. The locked Mudhafar cell-assignment policy:
       if rough → 'rough'
       elif Dh_um < dh_um_max → 'small_d_smooth'
       else → 'standard_smooth'
    """
    if config.cell_bands.type != "dh_roughness_bands":
        raise ValueError(
            f"Mudhafar engine path expects cell_bands.type="
            f"'dh_roughness_bands'; got {config.cell_bands.type!r}."
        )
    bands = list(config.cell_bands.bands)
    if not bands:
        raise ValueError("Mudhafar cell_bands has no bands.")

    # Build lookup tables from the YAML so the assignment is data, not code.
    rough_band: dict | None = None
    small_d_band: dict | None = None
    standard_band: dict | None = None
    for band in bands:
        if band.get("rough") is True:
            rough_band = band
        elif "dh_um_max" in band:
            small_d_band = band
        else:
            standard_band = band
    if rough_band is None or small_d_band is None or standard_band is None:
        raise ValueError(
            f"Mudhafar dh_roughness_bands must include one rough, one "
            f"dh_um_max-bounded smooth, and one standard band; got "
            f"{bands!r}."
        )
    dh_threshold = float(small_d_band["dh_um_max"])

    def assign(dh_um: float, rough: bool) -> str:
        if rough:
            return str(rough_band["name"])
        if dh_um < dh_threshold:
            return str(small_d_band["name"])
        return str(standard_band["name"])
    return assign


def _load_mudhafar_wpd_rows(csv_path: Path,
                            cell_assignment_fn) -> list[dict]:
    """Read the Mudhafar WPD CSV into per-point dicts (raw measurements +
    propagated total uncertainty). Mirrors the Forrest visual-estimate
    reader; expected schema is documented at module scope.

    Comment lines (starting with '#') are skipped; rows with non-positive
    Nu_meas are skipped.
    """
    import csv as _csv
    import numpy as np

    rows: list[dict] = []
    with csv_path.open("r", newline="") as fh:
        reader = _csv.DictReader(
            (line for line in fh if not line.lstrip().startswith("#")),
        )
        for r in reader:
            try:
                Re = float(r["Re"])
                Pr = float(r["Pr"])
                Nu_meas = float(r["Nu_meas"])
                Dh_um = float(r["Dh_um"])
            except (TypeError, ValueError, KeyError):
                continue
            if Nu_meas <= 0:
                continue
            rough_str = str(r.get("rough", "")).strip().lower()
            rough = rough_str in ("1", "true", "yes", "y")
            nu_unc_paper_pct = float(r.get("Nu_unc_paper_pct", 0.0) or 0.0)
            nu_unc_dig_raw = r.get("Nu_unc_digitization_abs", "")
            nu_unc_dig_abs = (
                float(nu_unc_dig_raw) if str(nu_unc_dig_raw).strip() else 0.0
            )
            Nu_unc_reported = Nu_meas * nu_unc_paper_pct
            if nu_unc_dig_abs > 0:
                total_unc = float(
                    np.sqrt(Nu_unc_reported ** 2 + nu_unc_dig_abs ** 2)
                )
            else:
                total_unc = Nu_unc_reported
            rows.append({
                "Re": Re,
                "Pr": Pr,
                "Nu_meas": Nu_meas,
                "Nu_unc_reported": Nu_unc_reported,
                "Nu_unc_total_propagated": total_unc,
                "digitization_uncertainty": nu_unc_dig_abs if nu_unc_dig_abs > 0 else None,
                "Dh_um": Dh_um,
                "rough": rough,
                "source": str(r.get("source") or "mudhafar"),
                "figure_or_table": str(r.get("figure") or ""),
                "cell": cell_assignment_fn(Dh_um, rough),
            })
    return rows


def mudhafar_wpd(config: VehicleConfig,
                 registry: dict[str, ClosureEntry]) -> tuple[list[Row], dict, SubstrateMeta]:
    """Engine-driven Mudhafar loader (Step 9c).

    Reads a WPD-digitized CSV at `config.data_source.path` (when banked)
    and emits Rows whose `surrogate_prediction` is the INTENTIONALLY
    geometry-mismatched matched closure (Modified Sparrow-Cur applied to
    circular micro-tubes) computed via the registry.

    The geometry-match invariant is intentionally OVERRIDDEN by the
    Mudhafar YAML's `expect_mismatch: true` + `mismatch_rationale`. The
    substrate engine surfaces `mismatch_rationale` into `meta.extra` for
    audit.

    DATA STATE: the WPD CSVs from Figs 7-11 of Mudhafar 2023 are not yet
    banked. Until they are, this loader raises NotImplementedError unless
    `data_source.path` points at an existing CSV with the documented
    schema. A synthetic-CSV test exercises the engine path end-to-end so
    the wiring is known-good before real data lands.

    Expected CSV columns (per `_MUDHAFAR_EXPECTED_CSV_COLUMNS`):
        row, Re, Pr, Nu_meas, Nu_unc_paper_pct, Nu_unc_digitization_abs,
        Dh_um, rough (truthy/falsy), source, figure, note
    """
    import numpy as np

    if config.data_source.path is None:
        raise NotImplementedError(
            "mudhafar_wpd loader: VehicleConfig.data_source.path is unset. "
            "The Mudhafar WPD CSV from Figs 7-11 of Mudhafar 2023 must be "
            "banked at `results/mudhafar_digitization/wpd_fig*.csv` (or "
            "equivalent) and the YAML's `data_source.path` pointed at it. "
            f"Expected columns: {_MUDHAFAR_EXPECTED_CSV_COLUMNS}."
        )
    csv_path = _resolve(config.data_source.path)
    if not csv_path.exists():
        raise NotImplementedError(
            f"mudhafar_wpd loader: data_source.path resolves to {csv_path} "
            f"which does not exist. The Mudhafar WPD CSV from Figs 7-11 of "
            f"Mudhafar 2023 must be banked before this loader produces rows. "
            f"Expected columns: {_MUDHAFAR_EXPECTED_CSV_COLUMNS}."
        )

    matched = registry[config.matched_closure_id]
    # Mudhafar references are circular-pipe closures (Gnielinski, D-B,
    # Petukhov). Pin the expected set so a YAML edit that drops one
    # surfaces here.
    refs: dict[str, ClosureEntry] = {
        cid: registry[cid] for cid in config.reference_closure_ids
    }
    expected_refs = {"gnielinski-1976", "dittus-boelter-1930", "petukhov-1970"}
    missing = expected_refs - set(refs)
    if missing:
        raise RuntimeError(
            f"Mudhafar engine path expects reference_closure_ids superset "
            f"of {sorted(expected_refs)}; missing: {sorted(missing)}."
        )

    assign_cell = _mudhafar_cell_assignment_from_config(config)
    raw_rows = _load_mudhafar_wpd_rows(csv_path, assign_cell)

    if matched.re_range is None:
        raise RuntimeError(
            f"{config.matched_closure_id!r} has no re_range; cannot build "
            f"matched mechanism."
        )

    rows: list[Row] = []
    for raw in raw_rows:
        Re = raw["Re"]
        Pr = raw["Pr"]
        Re_arr = np.array([Re])
        Pr_arr = np.array([Pr])
        Nu_sc = float(matched.fn(Re=Re_arr, Pr=Pr_arr)[0])
        Nu_g = float(refs["gnielinski-1976"].fn(Re=Re_arr, Pr=Pr_arr)[0])
        Nu_db = float(refs["dittus-boelter-1930"].fn(Re=Re_arr, Pr=Pr_arr)[0])
        Nu_pk = float(refs["petukhov-1970"].fn(Re=Re_arr, Pr=Pr_arr)[0])

        mechanisms = [
            Mechanism(
                name="forced_circular_micro_tube_sparrow_cur_mismatched",
                closure_id=config.matched_closure_id,
                operating_value=Re,
                calib_lo=matched.re_range[0],
                calib_hi=matched.re_range[1],
                contribution=Nu_sc,
            ),
            Mechanism(
                name="forced_internal_flow_gnielinski_reference",
                closure_id="gnielinski-1976",
                operating_value=Re,
                calib_lo=refs["gnielinski-1976"].re_range[0],
                calib_hi=refs["gnielinski-1976"].re_range[1],
                contribution=Nu_g,
            ),
            Mechanism(
                name="forced_internal_flow_dittus_boelter_reference",
                closure_id="dittus-boelter-1930",
                operating_value=Re,
                calib_lo=refs["dittus-boelter-1930"].re_range[0],
                calib_hi=refs["dittus-boelter-1930"].re_range[1],
                contribution=Nu_db,
            ),
        ]

        rows.append(Row(
            operating_point=(round(Re, 1), round(Pr, 4), round(raw["Dh_um"], 2)),
            surrogate_prediction=Nu_sc,
            cfd_truth=raw["Nu_meas"],
            truth_source="experimental",
            cfd_uncertainty=raw["Nu_unc_total_propagated"],
            guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
            mechanisms=mechanisms,
            meta={
                "Re": Re,
                "Pr": Pr,
                "Dh_um": raw["Dh_um"],
                "rough": raw["rough"],
                "Nu_meas": raw["Nu_meas"],
                "Nu_unc_reported": raw["Nu_unc_reported"],
                "Nu_unc_total_propagated": raw["Nu_unc_total_propagated"],
                "Nu_pred_modified_sparrow_cur": Nu_sc,
                "Nu_pred_gnielinski": Nu_g,
                "Nu_pred_dittus_boelter": Nu_db,
                "Nu_pred_petukhov": Nu_pk,
                "cell": raw["cell"],
                "source": raw["source"],
                "figure_or_table": raw["figure_or_table"],
                "digitization_uncertainty": raw["digitization_uncertainty"],
            },
        ))

    rows = load_rows(rows)

    reference = {"ood": [0.0], "residual": [0.0], "variance": [0.0]}
    meta = SubstrateMeta(
        name="mudhafar-micro-tubes",
        divergent_truth_substrate=True,
        reason=_MUDHAFAR_REASON,
        norm_strategy="per_row_truth",
        bound_for_pde=None,
        magnitude_bridge_ok=True,
        extra={
            "geometry": (
                f"circular micro-tubes; inner diameters "
                f"{config.geometry.dims.get('smooth_diameters_um')} μm "
                f"smooth + roughness levels "
                f"{config.geometry.dims.get('rough_roughness_um')} μm Ra"
            ),
            "fluid": config.fluid.name,
            "Pr_range": list(config.fluid.pr_range) if config.fluid.pr_range else None,
            "n_rows": len(rows),
            "data_source_path": str(csv_path),
            "closures": {
                "primary_matched_INTENTIONAL_MISMATCH": (
                    f"{config.matched_closure_id} "
                    f"(corpus {matched.status}; INTENDED geometry mismatch — "
                    f"narrow_rect_channel_one_sided closure applied to "
                    f"circular_micro_tube_smooth geometry; positive-control "
                    f"design)"
                ),
                "reference_circular_pipe": [
                    f"{cid} (corpus {refs[cid].status}; geometry-aligned to "
                    f"circular micro-tubes)"
                    for cid in config.reference_closure_ids
                ],
                "positive_control_rationale": (
                    "Sparrow-Cur is the Forrest-matched closure. Applying it "
                    "to circular micro-tubes is the INTENDED experimental "
                    "mismatch. Baselines and corpus validity signal both "
                    "expected to fire across out-of-envelope cells "
                    "(small_d_smooth and rough)."
                ),
            },
        },
    )
    return rows, reference, meta


# ── naca_wpd (engine-driven, Step 9d) ───────────────────────────────────────

_NACA_REASON = (
    "Independent experimental truth: measured Nu_x from heat-transfer "
    "coefficients on a steam-jacketed circular tube (1.785\" ID), air "
    "flow with Pr ≈ 0.71, per NACA TN-1451 (Boelter, Young, Iversen 1948). "
    "Entrance-region heat-transfer coefficient varies strongly with x/D "
    "below x/D ≈ 10; aggregate (Re, Pr) surrogates that omit x/D from "
    "inputs cannot see this failure. The corpus's x/D ≥ 10 validity "
    "boundary catches it — the differentiator on three figures (10, 15, "
    "19) per docs/findings/PhysMAP_D3_NACA_EntranceRegion_Findings_v0_1.md."
)

# Two CSV schemas are accepted (both used by the NACA workflow):
#   * WPD-banked  (wpd_fig*.csv): uses `Nu_unc_digitization_abs` (absolute Nu).
#     Routed through the strict `naca_wpd_loader.load_wpd_csv` which enforces
#     source='wpd-csv' and the Fig-21 asymptote-not-reached exclusion.
#   * Cross-validated visual (cross_validated_fig*.csv): uses
#     `Nu_unc_digitization_pct` (percent). No strict source discipline; the
#     visual-precision development runs use these.
_NACA_WPD_SCHEMA_DIG_COLUMN = "Nu_unc_digitization_abs"
_NACA_VISUAL_SCHEMA_DIG_COLUMN = "Nu_unc_digitization_pct"


def _naca_cell_assignment_from_config(config: VehicleConfig):
    """Return `x_over_D -> cell_name` from the YAML's x_over_d_bands.
    Mirrors `naca_tn1451_substrate.cell_assignment`: first band whose
    `x_over_d_lt` exceeds x/D wins."""
    if config.cell_bands.type != "x_over_d_bands":
        raise ValueError(
            f"NACA engine path expects cell_bands.type='x_over_d_bands'; "
            f"got {config.cell_bands.type!r}."
        )
    bands = list(config.cell_bands.bands)
    if not bands:
        raise ValueError("NACA cell_bands has no bands.")

    def assign(x_over_D: float) -> str:
        for band in bands:
            if x_over_D < float(band["x_over_d_lt"]):
                return str(band["name"])
        return str(bands[-1]["name"])
    return assign


def _detect_naca_csv_schema(csv_path: Path) -> str:
    """Inspect the CSV header to figure out which schema variant it is.
    Returns 'wpd' if the `Nu_unc_digitization_abs` column is present, else
    'visual' if `Nu_unc_digitization_pct` is present. Raises otherwise."""
    import csv as _csv
    with csv_path.open("r", newline="") as fh:
        reader = _csv.reader(
            line for line in fh if not line.lstrip().startswith("#")
        )
        header = next(reader, [])
    cols = set(header)
    if _NACA_WPD_SCHEMA_DIG_COLUMN in cols:
        return "wpd"
    if _NACA_VISUAL_SCHEMA_DIG_COLUMN in cols:
        return "visual"
    raise ValueError(
        f"NACA CSV {csv_path} has neither {_NACA_WPD_SCHEMA_DIG_COLUMN!r} nor "
        f"{_NACA_VISUAL_SCHEMA_DIG_COLUMN!r} in its header; cannot determine "
        f"which uncertainty convention to use. Header: {sorted(cols)}."
    )


def _load_naca_raw_rows(csv_path: Path,
                        schema: str,
                        cell_assignment_fn) -> tuple[list[dict], list[dict]]:
    """Read a NACA CSV into per-point raw-row dicts.

    For schema='wpd': delegates to `naca_wpd_loader.load_wpd_csv` so the
    Fig-21 Re=26,100 asymptote-not-reached exclusion is enforced and
    source='wpd-csv' is required. Returns (verdict_rows, alignment_rows).

    For schema='visual': hand-rolled CSV reader; the digitization
    uncertainty column is in percent, so it's converted to absolute Nu
    units before propagation. Returns (verdict_rows, []).
    """
    import csv as _csv
    import numpy as np

    verdict_rows: list[dict] = []
    alignment_rows: list[dict] = []

    if schema == "wpd":
        from physmap.substrate.naca_wpd_loader import load_wpd_csv
        loaded = load_wpd_csv(csv_path)
        for naca_row, bucket in (
            [(r, "verdict") for r in loaded.rows_for_verdict]
            + [(r, "alignment") for r in loaded.rows_alignment_only]
        ):
            # NACARow → raw dict; load_wpd_csv has already combined paper +
            # digitization uncertainty into Nu_unc (absolute units).
            wpd_note = naca_row.__dict__.get("wpd_note", "")
            raw = {
                "Re": float(naca_row.Re),
                "Pr": float(naca_row.Pr),
                "x_over_D": float(naca_row.x_over_D),
                "Nu_meas": float(naca_row.Nu_meas),
                "Nu_unc_total_propagated": float(naca_row.Nu_unc),
                "digitization_uncertainty_abs": float(
                    naca_row.digitization_uncertainty or 0.0
                ),
                "source": str(naca_row.source),
                "figure": str(naca_row.figure),
                "entering_condition": str(naca_row.entering_condition),
                "note": wpd_note,
                "cell": cell_assignment_fn(float(naca_row.x_over_D)),
                "alignment_only": (bucket == "alignment"),
            }
            (alignment_rows if bucket == "alignment" else verdict_rows).append(raw)
        return verdict_rows, alignment_rows

    # schema == "visual"
    with csv_path.open("r", newline="") as fh:
        reader = _csv.DictReader(
            (line for line in fh if not line.lstrip().startswith("#")),
        )
        for r in reader:
            try:
                Re = float(r["Re"])
                Pr = float(r["Pr"])
                x_over_D = float(r["x_over_D"])
                Nu_meas = float(r["Nu_meas"])
            except (TypeError, ValueError, KeyError):
                continue
            if Nu_meas <= 0:
                continue
            paper_pct = float(r.get("Nu_unc_paper_pct", 0.0) or 0.0)
            dig_pct_raw = r.get(_NACA_VISUAL_SCHEMA_DIG_COLUMN, "")
            dig_pct = float(dig_pct_raw) if str(dig_pct_raw).strip() else 0.0
            paper_abs = Nu_meas * paper_pct
            dig_abs = Nu_meas * dig_pct
            total_unc = float(np.sqrt(paper_abs ** 2 + dig_abs ** 2))
            verdict_rows.append({
                "Re": Re,
                "Pr": Pr,
                "x_over_D": x_over_D,
                "Nu_meas": Nu_meas,
                "Nu_unc_total_propagated": total_unc,
                "digitization_uncertainty_abs": dig_abs,
                "source": str(r.get("source") or "naca"),
                "figure": str(r.get("figure") or ""),
                "entering_condition": str(r.get("entering_condition") or ""),
                "note": str(r.get("note") or ""),
                "cell": cell_assignment_fn(x_over_D),
                "alignment_only": False,
            })
    return verdict_rows, []


def naca_wpd(config: VehicleConfig,
             registry: dict[str, ClosureEntry]) -> tuple[list[Row], dict, SubstrateMeta]:
    """Engine-driven NACA TN-1451 loader (Step 9d).

    Reads the WPD-banked CSV (`wpd_fig*.csv`) at `config.data_source.path`
    and emits Rows whose `surrogate_prediction` is the INTENTIONALLY
    geometry-mismatched matched closure (Gnielinski applied to an
    entrance-region geometry) computed via the registry. Also supports
    the two-reader cross-validated visual CSVs (`cross_validated_fig*.csv`)
    when the YAML's `data_source.path` points at one — the loader
    detects the schema by column presence.

    The geometry-match invariant is OVERRIDDEN by the YAML's
    `expect_mismatch: true` + `mismatch_rationale`. v0.3 framing per the
    findings doc: practitioners use Gnielinski as an aggregate
    heat-exchanger surrogate that omits x/D; PhysMAP's corpus signal
    catches the x/D < 10 invalidity.

    Fig-21 Re=26,100 asymptote-not-reached exclusion is enforced for
    WPD-schema CSVs via `naca_wpd_loader.load_wpd_csv` (excluded rows
    appear in `meta.extra['alignment_only_rows']` for downstream
    inspection but are NOT in the returned `rows` list).

    Expected WPD CSV columns: see
        `physmap/results/naca_digitization/WPD_DIGITIZATION_SPEC.md`.
    """
    import numpy as np

    if config.data_source.path is None:
        raise ValueError(
            f"VehicleConfig {config.vehicle_id!r}: data_source.path is "
            f"required for the naca_wpd loader."
        )
    csv_path = _resolve(config.data_source.path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"NACA CSV not found at {csv_path}. Bank a WPD CSV "
            f"(wpd_fig*.csv) or point the YAML at a cross-validated "
            f"visual CSV (cross_validated_fig*.csv)."
        )

    schema = _detect_naca_csv_schema(csv_path)

    matched = registry[config.matched_closure_id]   # gnielinski-1976
    refs: dict[str, ClosureEntry] = {
        cid: registry[cid] for cid in config.reference_closure_ids
    }
    expected_refs = {"dittus-boelter-1930", "sieder-tate-1936", "petukhov-1970"}
    missing = expected_refs - set(refs)
    if missing:
        raise RuntimeError(
            f"NACA engine path expects reference_closure_ids superset "
            f"of {sorted(expected_refs)}; missing: {sorted(missing)}."
        )

    assign_cell = _naca_cell_assignment_from_config(config)
    verdict_raw, alignment_raw = _load_naca_raw_rows(
        csv_path, schema, assign_cell,
    )

    if matched.re_range is None:
        raise RuntimeError(
            f"{config.matched_closure_id!r} has no re_range; cannot build "
            f"matched mechanism."
        )

    # Pin the geometry mismatch — the v0.3 framing depends on Gnielinski
    # (circular_pipe) applied to circular_pipe_entrance_region. If the
    # registry ever changes Gnielinski's geometry_class to match the
    # entrance-region one, the v0.3 framing is lost; surface that
    # mismatch loudly here.
    if matched.geometry_class == config.geometry.class_:
        raise RuntimeError(
            f"NACA engine path: Gnielinski's geometry_class is now "
            f"{matched.geometry_class!r} which MATCHES the vehicle's "
            f"{config.geometry.class_!r}. The v0.3 framing (Gnielinski "
            f"as an aggregate-heat-exchanger surrogate applied to entrance "
            f"regions, omitting x/D from inputs) requires this mismatch. "
            f"Audit the registry edit."
        )

    rows: list[Row] = []
    for raw in verdict_raw:
        Re = raw["Re"]
        Pr = raw["Pr"]
        Re_arr = np.array([Re])
        Pr_arr = np.array([Pr])
        Nu_g = float(matched.fn(Re=Re_arr, Pr=Pr_arr)[0])
        Nu_db = float(refs["dittus-boelter-1930"].fn(Re=Re_arr, Pr=Pr_arr)[0])
        Nu_st = float(refs["sieder-tate-1936"].fn(Re=Re_arr, Pr=Pr_arr)[0])
        Nu_pk = float(refs["petukhov-1970"].fn(Re=Re_arr, Pr=Pr_arr)[0])

        mechanisms = [
            Mechanism(
                name="forced_circular_pipe_gnielinski_entrance_mismatched",
                closure_id=config.matched_closure_id,
                operating_value=Re,
                calib_lo=matched.re_range[0],
                calib_hi=matched.re_range[1],
                contribution=Nu_g,
            ),
            Mechanism(
                name="forced_internal_flow_dittus_boelter_reference",
                closure_id="dittus-boelter-1930",
                operating_value=Re,
                calib_lo=refs["dittus-boelter-1930"].re_range[0],
                calib_hi=refs["dittus-boelter-1930"].re_range[1],
                contribution=Nu_db,
            ),
            Mechanism(
                name="forced_internal_flow_sieder_tate_reference",
                closure_id="sieder-tate-1936",
                operating_value=Re,
                calib_lo=refs["sieder-tate-1936"].re_range[0],
                calib_hi=refs["sieder-tate-1936"].re_range[1],
                contribution=Nu_st,
            ),
            Mechanism(
                name="forced_internal_flow_petukhov_reference",
                closure_id="petukhov-1970",
                operating_value=Re,
                calib_lo=refs["petukhov-1970"].re_range[0],
                calib_hi=refs["petukhov-1970"].re_range[1],
                contribution=Nu_pk,
            ),
        ]

        rows.append(Row(
            operating_point=(round(Re, 1), round(raw["x_over_D"], 4)),
            surrogate_prediction=Nu_g,
            cfd_truth=raw["Nu_meas"],
            truth_source="experimental",
            cfd_uncertainty=raw["Nu_unc_total_propagated"],
            guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
            mechanisms=mechanisms,
            meta={
                "Re": Re,
                "Pr": Pr,
                # x_over_D MUST be in meta — the validity-range detector
                # reads it to compute distance to Gnielinski's x/D ≥ 10
                # bound. The surrogate/baseline detectors deliberately
                # don't see it (the v0.3 omission framing).
                "x_over_D": raw["x_over_D"],
                "Nu_meas": raw["Nu_meas"],
                "Nu_unc_total_propagated": raw["Nu_unc_total_propagated"],
                "Nu_pred_gnielinski": Nu_g,
                "Nu_pred_dittus_boelter": Nu_db,
                "Nu_pred_sieder_tate": Nu_st,
                "Nu_pred_petukhov": Nu_pk,
                "cell": raw["cell"],
                "source": raw["source"],
                "figure_or_table": raw["figure"],
                "entering_condition": raw["entering_condition"],
                "note": raw["note"],
                "digitization_uncertainty": raw["digitization_uncertainty_abs"],
            },
        ))

    rows = load_rows(rows)

    reference = {"ood": [0.0], "residual": [0.0], "variance": [0.0]}
    meta = SubstrateMeta(
        name="naca-tn1451-entrance-region",
        divergent_truth_substrate=True,
        reason=_NACA_REASON,
        norm_strategy="per_row_truth",
        bound_for_pde=None,
        magnitude_bridge_ok=True,
        extra={
            "geometry": (
                f"circular pipe ID {config.geometry.dims.get('tube_id_inch')}\" "
                f"({config.geometry.dims.get('tube_id_mm')} mm), "
                f"{config.geometry.dims.get('wall_condition')}, "
                f"{config.geometry.dims.get('surface_finish')}"
            ),
            "fluid": config.fluid.name,
            "Pr_range": list(config.fluid.pr_range) if config.fluid.pr_range else None,
            "n_rows": len(rows),
            "n_alignment_only": len(alignment_raw),
            "alignment_only_rows": alignment_raw,
            "schema_detected": schema,
            "data_source_path": str(csv_path),
            "closures": {
                "primary_matched_INTENTIONAL_MISMATCH": (
                    f"{config.matched_closure_id} (corpus {matched.status}; "
                    f"circular_pipe closure applied to "
                    f"circular_pipe_entrance_region geometry; aggregate-HE "
                    f"surrogate practice — omits x/D from inputs)"
                ),
                "reference_circular_pipe": [
                    f"{cid} (corpus {refs[cid].status}; same aggregate-HE "
                    f"family as the matched closure)"
                    for cid in config.reference_closure_ids
                ],
                "v03_framing_rationale": (
                    "Per the locked v0.3 prereg + the findings doc, the "
                    "matched closure for NACA is the bare circular-pipe "
                    "Gnielinski applied as a practitioner aggregate-HE "
                    "surrogate WITHOUT x/D in inputs. The mismatch with "
                    "the entrance-region geometry is the failure mode the "
                    "corpus catches; the surrogate + baseline detectors "
                    "can't see it because the inputs (Re, Pr only) are "
                    "in-distribution at every x/D."
                ),
            },
        },
    )
    return rows, reference, meta


# ── Testi & Grassi 2006 (FC-72 horizontal tube) — middle-vehicle loader STUB ──
#
# The first buoyancy (mixed-convection) middle vehicle. Source: Testi & Grassi
# (2006), "Mixed convection heat transfer of FC-72 in a horizontal tube",
# J. Heat Transfer, DOI 10.1115/1.2345436. Local Nu at 5 cross-sections x 8
# points, Re 3050-6800, Gr 1.3-5.0e8, FC-72.
#
# DATA STATE: the local-Nu figures are NOT yet digitized. Until banked, this
# loader raises NotImplementedError with the expected schema. See
# docs/PhysMAP_MiddleVehicle_Extraction_Protocol.md for the per-vehicle
# extraction checklist (confirm LOCAL measured Nu; digitize with two-reader
# cross-validation + per-point uncertainty; compute Ri/Gr per row; build the
# forced-convection surrogate with the buoyancy variable OMITTED + the two
# gates; pass the observability subsampling-stability gate; record the
# entrance/calming condition for the NACA geometry-dependence link).

_TESTI_GRASSI_EXPECTED_CSV_COLUMNS = (
    "row", "Re", "Pr", "Ri", "Gr", "x_over_D", "cross_section",
    "Nu_meas", "Nu_unc_paper_pct", "Nu_unc_digitization_abs",
    "entering_condition", "source", "figure", "note",
)


def testi_grassi_lfs(config: VehicleConfig,
                     registry: dict[str, ClosureEntry]) -> tuple[list[Row], dict, SubstrateMeta]:
    """Engine-driven Testi & Grassi 2006 loader (middle-vehicle STUB).

    Emits Rows whose `surrogate_prediction` is the forced-convection matched
    closure (Gnielinski, circular pipe) computed via the registry, with the
    buoyancy variable (Richardson number) OMITTED from the surrogate inputs —
    the middle-axis failure mechanism. `meta` must carry `Ri` (computed per row
    from the measured Re + heat flux) so the observability score and the
    richardson_bands split can read it.

    DATA STATE: not yet digitized — raises NotImplementedError until a CSV with
    the documented schema is banked at `config.data_source.path`.
    """
    if config.data_source.path is None:
        raise NotImplementedError(
            "testi_grassi_lfs loader: VehicleConfig.data_source.path is unset. "
            "The Testi & Grassi 2006 local-Nu figures (DOI 10.1115/1.2345436) "
            "must be digitized and banked at "
            "`results/testi_grassi_digitization/local_nu.csv`. "
            f"Expected columns: {_TESTI_GRASSI_EXPECTED_CSV_COLUMNS}."
        )
    csv_path = _resolve(config.data_source.path)
    if not csv_path.exists():
        raise NotImplementedError(
            f"testi_grassi_lfs loader: data_source.path resolves to {csv_path} "
            f"which does not exist. Digitize the Testi & Grassi 2006 local-Nu "
            f"figures (LOCAL measured Nu, NOT overall coefficients) per "
            f"docs/PhysMAP_MiddleVehicle_Extraction_Protocol.md before this "
            f"loader produces rows. "
            f"Expected columns: {_TESTI_GRASSI_EXPECTED_CSV_COLUMNS}."
        )
    raise NotImplementedError(
        "testi_grassi_lfs loader: CSV banked but the row-construction body is "
        "not implemented. Implement per the extraction protocol: compute Ri/Gr "
        "per row, set surrogate_prediction from the forced-convection closure "
        "(buoyancy omitted), populate meta['Ri'] + entering_condition."
    )


# ── dirker_water_richardson_bands (Stage-3 MIDDLE-axis vehicle) ─────────────

_DIRKER_WATER_EXPECTED_CSV_COLUMNS = (
    "row", "case", "position", "phi_deg", "angle_span_deg",
    "local_heat_flux_Wm2", "power_W", "Re", "Pr", "Ri", "Ri_unc_pct",
    "Nu_meas", "Nu_unc_paper_pct", "Nu_unc_digitization_abs",
    "entering_condition", "source", "figure", "note",
)

_DIRKER_WATER_REASON = (
    "Independent experimental truth: length-averaged Nu measured on a smooth "
    "horizontal water tube (D=27.8 mm, Pr 6-7, laminar Re 650-2600) under "
    "circumferentially non-uniform heat flux, per Dirker, J., Meyer, J.P. & "
    "Reid, W.J. (2018), 'Experimental investigation of circumferentially "
    "non-uniform heat flux ... smooth horizontal tube with buoyancy driven "
    "secondary flow', Exp. Thermal & Fluid Sci. (ScienceDirect pii "
    "S0894177718302528). Stage-3 MIDDLE-axis vehicle: the surrogate is a "
    "buoyancy/position/flux-BLIND forced-convection fit on the low-Ri "
    "(forced-collapsed) rows; the failure variable Ri=Gr/Re^2 (digitized "
    "directly from the authors' per-point Figs 18/20) is OMITTED from the "
    "(log10_Re, Pr) surrogate inputs, so it is only PARTIALLY observable -> a "
    "middle observability score by construction. Multi-flux (6631 + 4421 W/m2) "
    "supplies Ri variation at FIXED Re so the failure is corpus-detectable but "
    "baseline-quiet in the interleaved band (clean_lift), unlike a single-flux "
    "set whose Ri ~ f(Re) is baseline-sufficient (near the Forrest pole)."
)


def _richardson_cell_assignment_from_config(config: VehicleConfig):
    """Return a function `Ri -> cell_name` from the YAML's richardson_bands:
    the first band whose `ri_lt` exceeds Ri wins; the last band is the
    catch-all. Mirrors `_forrest_cell_assignment_from_config` but on the
    Richardson number instead of Re."""
    if config.cell_bands.type != "richardson_bands":
        raise ValueError(
            f"dirker_water path expects cell_bands.type='richardson_bands'; "
            f"got {config.cell_bands.type!r}."
        )
    bands = list(config.cell_bands.bands)
    if not bands:
        raise ValueError("richardson_bands has no bands.")

    def assign(ri_val: float) -> str:
        for band in bands:
            if ri_val < float(band["ri_lt"]):
                return str(band["name"])
        return str(bands[-1]["name"])
    return assign


def _load_dirker_water_rows(csv_path: Path) -> list[dict]:
    """Read the digitized CSV into per-point dicts (raw measurements +
    propagated total uncertainty). '#' comment lines are skipped; rows with
    non-positive Nu_meas or Ri are skipped."""
    import csv as _csv

    rows: list[dict] = []
    with csv_path.open("r", newline="") as fh:
        reader = _csv.DictReader(
            (line for line in fh if not line.lstrip().startswith("#")),
        )
        for r in reader:
            try:
                Re = float(r["Re"]); Pr = float(r["Pr"])
                Ri = float(r["Ri"]); Nu_meas = float(r["Nu_meas"])
            except (TypeError, ValueError, KeyError):
                continue
            if Nu_meas <= 0 or Ri <= 0:
                continue
            # Nu_unc_paper_pct is in PERCENT (e.g. 3.5); digitization is ABS Nu.
            nu_unc_paper_frac = float(r.get("Nu_unc_paper_pct", 0.0) or 0.0) / 100.0
            nu_unc_dig_abs = float(r.get("Nu_unc_digitization_abs", 0.0) or 0.0)
            Nu_unc_reported = Nu_meas * nu_unc_paper_frac
            total_unc = (
                float(np.sqrt(Nu_unc_reported ** 2 + nu_unc_dig_abs ** 2))
                if nu_unc_dig_abs > 0 else Nu_unc_reported
            )
            ri_unc_pct = float(r.get("Ri_unc_pct", 0.0) or 0.0)
            rows.append({
                "Re": Re, "Pr": Pr, "Ri": Ri, "Nu_meas": Nu_meas,
                "Ri_unc": Ri * ri_unc_pct / 100.0,
                "Nu_unc_reported": Nu_unc_reported,
                "Nu_unc_total_propagated": total_unc,
                "digitization_uncertainty": nu_unc_dig_abs if nu_unc_dig_abs > 0 else None,
                "case": str(r.get("case") or ""),
                "position": str(r.get("position") or ""),
                "phi_deg": float(r.get("phi_deg", 0.0) or 0.0),
                "local_heat_flux_Wm2": float(r.get("local_heat_flux_Wm2", 0.0) or 0.0),
                "entering_condition": str(r.get("entering_condition") or ""),
                "source": str(r.get("source") or "dirker-water"),
                "figure_or_table": str(r.get("figure") or ""),
            })
    return rows


def dirker_forced_fit(log10_re, nu) -> np.ndarray:
    """The Dirker surrogate: a degree-1 least-squares fit of Nu against log10(Re). Returns
    the coefficients (a, b) of Nu = a*log10(Re) + b, for np.polyval. Module-level so the
    home baseline can refit it without one row."""
    return np.polyfit(np.asarray(log10_re, dtype=float), np.asarray(nu, dtype=float), deg=1)


def dirker_water_richardson_bands(config: VehicleConfig,
                                  registry: dict[str, ClosureEntry]) -> tuple[list[Row], dict, SubstrateMeta]:
    """Engine-driven Dirker/Meyer/Reid (2018) MIDDLE-axis loader (Path A).

    Reads the digitized 180-degree-span CSV and emits Rows whose
    `surrogate_prediction` is a buoyancy/position/flux-BLIND forced-convection
    fit on the LOW-Ri (forced-collapsed) rows. Gnielinski (the matched closure)
    is turbulent and yields negative Nu at laminar Re, so it CANNOT be the
    surrogate-of-record here; instead a degree-1 Nu-vs-log10(Re) least-squares
    trend is fit on the rows with Ri < the forced cutoff (richardson_bands
    band[0].ri_lt) and evaluated for EVERY row. Because position and heat-flux
    are not inputs, the fit collapses the configs at low Ri (accurate -> Gate 1)
    and fails where they spread at high Ri (measurably wrong -> Gate 2). Gnielinski
    stays the corpus/validity anchor (its richardson_number ceiling fires on the
    deploy rows); `meta['Ri']` is populated on every Row for the split, the
    observability score, and the validity detector.
    """
    if config.data_source.path is None:
        raise ValueError(
            f"VehicleConfig {config.vehicle_id!r}: data_source.path is required "
            f"for the dirker_water_richardson_bands loader. Expected CSV columns: "
            f"{_DIRKER_WATER_EXPECTED_CSV_COLUMNS}."
        )
    csv_path = _resolve(config.data_source.path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"dirker_water loader: data_source.path resolves to {csv_path} "
            f"which does not exist."
        )

    assign_cell = _richardson_cell_assignment_from_config(config)
    raw = _load_dirker_water_rows(csv_path)
    if not raw:
        raise RuntimeError(f"dirker_water loader: no usable rows in {csv_path}")

    # Validate the matched closure is registered (corpus/validity anchor).
    matched = registry[config.matched_closure_id]

    # ri_forced_cut = the low-Ri (forced/train) boundary = first band's ri_lt.
    ri_forced_cut = float(config.cell_bands.bands[0]["ri_lt"])

    # PATH-A surrogate: fit the buoyancy-blind forced trend on the low-Ri rows.
    train = [d for d in raw if d["Ri"] < ri_forced_cut]
    if len(train) < 2:
        raise RuntimeError(
            f"dirker_water loader: need >= 2 low-Ri (Ri<{ri_forced_cut}) train "
            f"rows for the forced surrogate fit; got {len(train)}."
        )
    x_train = np.array([np.log10(d["Re"]) for d in train], dtype=float)
    y_train = np.array([d["Nu_meas"] for d in train], dtype=float)
    coeffs = dirker_forced_fit(x_train, y_train)          # Nu ~ a*log10(Re) + b
    surrogate_calib_lo = float(min(d["Re"] for d in train))
    surrogate_calib_hi = float(max(d["Re"] for d in train))

    rows: list[Row] = []
    for d in raw:
        Re = d["Re"]; Pr = d["Pr"]; Ri = d["Ri"]
        nu_surrogate = float(np.polyval(coeffs, np.log10(Re)))
        mech = Mechanism(
            name="forced_convection_surrogate_lowRi_fit",
            closure_id=config.matched_closure_id,
            operating_value=Re,
            calib_lo=surrogate_calib_lo,
            calib_hi=surrogate_calib_hi,
            contribution=nu_surrogate,
        )
        rows.append(Row(
            operating_point=(round(Re, 1), round(Pr, 4)),
            surrogate_prediction=nu_surrogate,
            cfd_truth=d["Nu_meas"],
            truth_source="experimental",
            cfd_uncertainty=d["Nu_unc_total_propagated"],
            guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
            mechanisms=[mech],
            meta={
                "Re": Re, "Pr": Pr, "Ri": Ri,
                "Nu_meas": d["Nu_meas"],
                "Ri_unc": d["Ri_unc"],
                "Nu_unc_reported": d["Nu_unc_reported"],
                "Nu_unc_total_propagated": d["Nu_unc_total_propagated"],
                "Nu_pred_forced_surrogate": nu_surrogate,
                "cell": assign_cell(Ri),
                "case": d["case"], "position": d["position"], "phi_deg": d["phi_deg"],
                "local_heat_flux_Wm2": d["local_heat_flux_Wm2"],
                "entering_condition": d["entering_condition"],
                "source": d["source"], "figure_or_table": d["figure_or_table"],
                "digitization_uncertainty": d["digitization_uncertainty"],
            },
        ))

    rows = load_rows(rows)

    n_train = sum(1 for d in raw if d["Ri"] < ri_forced_cut)
    dims = config.geometry.dims
    reference = {"ood": [0.0], "residual": [0.0], "variance": [0.0]}
    meta = SubstrateMeta(
        name="dirker-water-nonuniform-flux-180span",
        divergent_truth_substrate=True,
        reason=_DIRKER_WATER_REASON,
        norm_strategy="per_row_truth",
        bound_for_pde=None,
        magnitude_bridge_ok=True,
        extra={
            "geometry": (
                f"smooth horizontal circular tube, D={dims.get('tube_id_mm', 27.8)} mm, "
                f"L/D=72, 180-degree-span partial circumferential heating "
                f"(positions phi in {{0,90,135,180}} deg), laminar"
            ),
            "fluid": config.fluid.name,
            "Pr_range": list(config.fluid.pr_range) if config.fluid.pr_range else [6.0, 7.0],
            "Re_range_laminar": [650, 2600],
            "heat_flux_levels_Wm2": [4421, 6631],
            "failure_variable": "Ri = Gr/Re^2 (digitized Figs 18/20; Okafor Eq 32)",
            "ri_forced_cut": ri_forced_cut,
            "n_rows": len(rows),
            "n_train_lowRi": n_train,
            "n_deploy_highRi": len(rows) - n_train,
            "surrogate": (
                f"PATH A: deg-1 Nu-vs-log10(Re) fit on the {n_train} low-Ri "
                f"(Ri<{ri_forced_cut}) rows; buoyancy/position/flux-blind; "
                f"coeffs(a,b)=({coeffs[0]:.4f},{coeffs[1]:.4f})"
            ),
            "data_source_path": str(csv_path),
            "closures": {
                "corpus_validity_anchor": (
                    f"{config.matched_closure_id} (corpus {matched.status}; "
                    "circular-pipe geometry MATCH; carries the richardson_number "
                    "ceiling that fires on deploy rows)"
                ),
            },
        },
    )
    return rows, reference, meta


_VELAZQUEZ_REASON = (
    "Independent experimental truth: local heat-transfer coefficient of supercritical "
    "CO2 in a 0.88 mm horizontal microtube, measured by 20 axial thermocouples "
    "(Velazquez et al. 2026, ATE 285:129206; data EXACT from SI Appendix D, not "
    "digitized). The surrogate is a CONSTANT-PROPERTY (Re, Pr) closure (Gnielinski); the "
    "omitted failure driver is the wall/bulk viscosity ratio mu_w/mu_b, which blows up "
    "near the pseudo-critical point where constant-property correlations fail (Gnielinski "
    "MAPE ~245% across the set). Property-variation middle-vehicle candidate: mu_w/mu_b is "
    "absent from the surrogate inputs but partially correlated with Pr -> observability is "
    "MEASURED (middle vs near-pole is the open question). Buoyancy confound isolated by "
    "pressure (>=15 MPa clean, per paper Fig. 11). Properties precomputed via CoolProp "
    "(validated vs the paper's REFPROP); see results/velazquez_sco2_digitization/PROVENANCE.md."
)


def velazquez_sco2_lfs(config: VehicleConfig,
                       registry: dict[str, ClosureEntry]) -> tuple[list[Row], dict, SubstrateMeta]:
    """Engine-driven Velazquez sCO2 loader (property-variation middle vehicle).

    Reads the property-augmented exact-SI CSV and emits Rows whose
    `surrogate_prediction` is the constant-property matched closure
    (Gnielinski, circular pipe) computed via the registry. `meta` carries the
    failure driver `ratio_mu_w_b` (mu_w/mu_b) plus the split coordinates
    `p_MPa` and `abs_dT_pc`, so the property_variation_bands split + the
    observability score can read them.
    """
    import csv as _csv

    if config.data_source.path is None:
        raise ValueError(
            f"VehicleConfig {config.vehicle_id!r}: data_source.path is required "
            f"for the velazquez_sco2_lfs loader."
        )
    csv_path = _resolve(config.data_source.path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Velazquez sCO2 properties CSV not found: {csv_path}. Run "
            f"results/velazquez_sco2_digitization/compute_properties.py (CoolProp, "
            f"offline) to generate it from the exact SI extraction."
        )

    matched = registry[config.matched_closure_id]   # gnielinski-constprop-sco2 (constant-property)
    if matched.re_range is None:
        raise RuntimeError(
            f"{config.matched_closure_id!r} has no re_range; cannot build mechanism."
        )
    db = registry.get("dittus-boelter-1930")

    rows: list[Row] = []
    with open(csv_path, newline="") as fh:
        for raw in _csv.DictReader(fh):
            Re = float(raw["Re_b"])
            Pr = float(raw["Pr_b"])
            Nu_meas = float(raw["Nu_meas"])
            if not (Nu_meas > 0.0):
                continue
            alpha = float(raw["alpha_W_m2K"])
            unc_alpha = float(raw["unc_alpha_W_m2K"])
            Nu_unc = Nu_meas * (unc_alpha / alpha) if alpha > 0 else float("nan")
            Re_arr = np.array([Re])
            Pr_arr = np.array([Pr])
            Nu_pred = float(matched.fn(Re=Re_arr, Pr=Pr_arr)[0])
            Nu_db = float(db.fn(Re=Re_arr, Pr=Pr_arr)[0]) if db is not None else float("nan")

            mechanisms = [
                Mechanism(
                    name="constant_property_gnielinski_circular_pipe",
                    closure_id=config.matched_closure_id,
                    operating_value=Re,
                    calib_lo=matched.re_range[0],
                    calib_hi=matched.re_range[1],
                    contribution=Nu_pred,
                ),
            ]
            rows.append(Row(
                operating_point=(round(Re, 1), round(Pr, 4)),
                surrogate_prediction=Nu_pred,
                cfd_truth=Nu_meas,
                truth_source="experimental",
                cfd_uncertainty=Nu_unc,
                guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
                mechanisms=mechanisms,
                meta={
                    "Re": Re,
                    "Pr": Pr,
                    # failure driver (omitted from surrogate inputs):
                    "ratio_mu_w_b": float(raw["ratio_mu_w_b"]),
                    # split coordinates:
                    "p_MPa": float(raw["p_MPa"]),
                    "abs_dT_pc": float(raw["abs_dT_pc_K"]),
                    # context:
                    "ratio_rho_w_b": float(raw["ratio_rho_w_b"]),
                    "ratio_lam_w_b": float(raw["ratio_lam_w_b"]),
                    "dT_b_to_pc": float(raw["dT_b_to_pc_K"]),
                    "near_pc": raw["near_pc"] == "True",
                    "Nu_meas": Nu_meas,
                    "Nu_unc": Nu_unc,
                    "Nu_pred_gnielinski": Nu_pred,
                    "Nu_pred_dittus_boelter": Nu_db,
                    "test": raw["test"],
                    "station": int(raw["station"]),
                    "T_b_C": float(raw["Tb_C"]),
                    "T_wi_C": float(raw["Twi_C"]),
                    "source": "velazquez-et-al-2026-SI-appendixD-exact",
                },
            ))

    rows = load_rows(rows)

    reference = {"ood": [0.0], "residual": [0.0], "variance": [0.0]}
    meta = SubstrateMeta(
        name="velazquez-sco2-microtube",
        divergent_truth_substrate=True,
        reason=_VELAZQUEZ_REASON,
        norm_strategy="per_row_truth",
        bound_for_pde=None,
        magnitude_bridge_ok=True,
        extra={
            "geometry": "horizontal circular microtube, Di=0.88 mm, heated length 1600 mm, 316L",
            "fluid": config.fluid.name,
            "n_rows": len(rows),
            "data_source_path": str(csv_path),
            "failure_driver": "ratio_mu_w_b (wall/bulk viscosity ratio)",
            "buoyancy_isolation": "pressure >= 15 MPa (paper Fig. 11)",
            "constant_property_gnielinski_MAPE_pct": 245.0,
            "data_provenance": "exact SI Appendix D extraction; properties via CoolProp (validated vs REFPROP)",
        },
    )
    return rows, reference, meta


# ── casper_hypersonic_transition (aerospace PHYSMAP_WINS: freestream noise) ──

_CASPER_REASON = (
    "Independent experimental truth: digitized RMS wall pressure (p~/p_e) vs "
    "axial position on a sharp 7-deg cone in conventional-noisy (HWT-5, HWT-8) "
    "and flight-like-quiet (BAM6QT) hypersonic tunnels (Casper et al.; Casper "
    "PhD thesis, Purdue BAM6QT; G6 pre-registration v0.2). The surrogate is a GP "
    "transition model on (Mach, unit Reynolds, axial x) trained on the NOISY "
    "envelope (Mach 4.9-7.9, incl. HWT-8 so quiet M=6.0 is INTERIOR — the v0.2 "
    "Mach-confound fix). The omitted driver is the tunnel freestream disturbance "
    "(RMS Pitot %), baseline-invisible. On the QUIET deploy (~0.05%) transition "
    "is delayed and the noisy-trained surrogate over-predicts rms; the corpus "
    "freestream-noise validity bound (Pate-Stainback, >= ~0.5%) fires there while "
    "the steelman baseline stays silent (quiet deploy is interior in inputs)."
)

# Freestream-noise facility table (mirrors g6_differentiator_v2.py): RMS Pitot %
# vs unit Reynolds (millions) per facility; Quiet (BAM6QT laminar nozzle) is the
# flight-like ~0.05%. Source: Casper freestream-noise digitization / thesis Fig 4.30.
_CASPER_FREESTREAM_FN: dict[str, dict[float, float]] = {
    "HWT-5": {7.0: 1.8, 9.3: 1.5, 12.0: 1.35, 15.0: 1.2, 20.0: 1.0},
    "BAM6QT": {5.0: 3.3, 7.0: 2.9, 9.3: 2.549, 11.0: 2.2},
    "HWT-8": {9.3: 3.736, 12.0: 3.05, 15.0: 2.65},
}
_CASPER_QUIET_PCT = 0.05


def _casper_facility(mach: float) -> str:
    return "HWT-5" if mach < 5.3 else ("BAM6QT" if mach < 6.5 else "HWT-8")


def _casper_freestream_pct(flow: str, mach: float, re_per_m_e6: float) -> float:
    """RMS-Pitot % for a row: Quiet -> ~0.05%; Noisy -> Re-interpolated facility value."""
    if flow == "Quiet":
        return _CASPER_QUIET_PCT
    table = _CASPER_FREESTREAM_FN[_casper_facility(mach)]
    xs = sorted(table)
    return float(np.interp(re_per_m_e6, xs, [table[x] for x in xs]))


def casper_gp_fit(X, y):
    """The Casper surrogate: a GP on (Mach, unit Reynolds, axial x) with the G6 v0.2 kernel.
    Returns predict(X) on raw inputs. Module-level so the home baseline can refit it
    without one row."""
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel

    X = np.asarray(X, dtype=float)
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    gp = GaussianProcessRegressor(
        kernel=ConstantKernel(0.001, (1e-6, 1.0)) * RBF([1.0, 1.0, 1.0], (0.1, 10.0))
        + WhiteKernel(1e-5, (1e-8, 1e-2)),
        normalize_y=True, n_restarts_optimizer=4, random_state=0,
    ).fit((X - mu) / sd, np.asarray(y, dtype=float))
    return lambda Xn: gp.predict((np.asarray(Xn, dtype=float) - mu) / sd)


def casper_hypersonic_transition(config: VehicleConfig,
                                 registry: dict[str, ClosureEntry]) -> tuple[list[Row], dict, SubstrateMeta]:
    """Engine-driven Casper loader (aerospace PHYSMAP_WINS: freestream-noise transition).

    Reads the digitized RMS-pressure-vs-x CSV (unit p_rms/p_e), keeping the
    noisy/quiet source-figures named in data_source.options (defaults reproduce
    G6 v0.2: noisy Fig9a+Fig13a + HWT-8 thesis Fig4.16; quiet Fig13a). Each row is
    tagged with its tunnel freestream-noise % (the omitted driver). The surrogate
    is a GP on (Mach, unit Reynolds, axial x) fit on the NOISY rows (matching the
    G6 kernel), so it over-predicts on the quiet deploy. The matched closure
    (Pate-Stainback freestream-noise bound) is the corpus/validity anchor only.
    """
    import csv as _csv

    opts = config.data_source.options
    rms_unit = str(opts.get("rms_unit", "p_rms/p_e"))
    noisy_figs = set(opts.get("noisy_figures", ["Fig9a", "Fig13a"]))
    quiet_figs = set(opts.get("quiet_figures", ["Fig13a"]))

    if config.data_source.path is None:
        raise ValueError(
            f"VehicleConfig {config.vehicle_id!r}: data_source.path is required "
            f"for the casper_hypersonic_transition loader."
        )
    main_path = _resolve(config.data_source.path)
    if not main_path.exists():
        raise FileNotFoundError(f"Casper rms-vs-x CSV not found: {main_path}")

    def _keep(path: Path, flow_to_figs: dict[str, set]) -> list[dict]:
        out: list[dict] = []
        with open(path, newline="") as fh:
            for r in _csv.DictReader(fh):
                if r.get("unit") != rms_unit:
                    continue
                flow = r.get("flow")
                if flow not in flow_to_figs:           # this flow not requested from this file
                    continue
                figs = flow_to_figs[flow]
                if figs and r.get("source_figure") not in figs:   # empty set = all figures
                    continue
                mach = float(r["M"]); re_e6 = float(r["Re_per_m_e6"])
                x_m = float(r["x_m"]); val = float(r["value"])
                paper_pct = float(r.get("unc_paper_pct", 0.0) or 0.0)
                dig_abs = float(r.get("unc_digitization", 0.0) or 0.0)
                total_unc = float(np.sqrt((val * paper_pct / 100.0) ** 2 + dig_abs ** 2))
                out.append(dict(
                    flow=flow, M=mach, re=re_e6, x=x_m, truth=val,
                    fs=_casper_freestream_pct(flow, mach, re_e6),
                    src_fig=r.get("source_figure", ""), unc=total_unc,
                ))
        return out

    raw = _keep(main_path, {"Noisy": noisy_figs, "Quiet": quiet_figs})
    hwt8_rel = opts.get("hwt8_path")
    if hwt8_rel:
        hwt8_path = _resolve(hwt8_rel)
        if hwt8_path.exists():
            raw += _keep(hwt8_path, {"Noisy": set()})   # HWT-8: noisy, all figures
    if not raw:
        raise RuntimeError(f"casper loader: no usable {rms_unit!r} rows in {main_path}")

    noisy = [d for d in raw if d["flow"] == "Noisy"]
    if len(noisy) < 3:
        raise RuntimeError(f"casper loader: need >= 3 noisy train rows, got {len(noisy)}")

    # GP surrogate on (Mach, unit Reynolds, axial x), fit on NOISY (G6 v0.2 kernel).
    Xtr = np.array([[d["M"], d["re"], d["x"]] for d in noisy], dtype=float)
    ytr = np.array([d["truth"] for d in noisy], dtype=float)
    predict = casper_gp_fit(Xtr, ytr)

    matched = registry[config.matched_closure_id]   # corpus/validity anchor (Pate bound)
    fs_lo, fs_hi = matched.bound_range               # freestream-noise validated band (corpus mirror)

    rows: list[Row] = []
    for d in raw:
        pred = float(predict(np.array([[d["M"], d["re"], d["x"]]], dtype=float))[0])
        mech = Mechanism(
            name="casper_freestream_noise_validity_anchor",
            closure_id=config.matched_closure_id,
            operating_value=d["fs"], calib_lo=fs_lo, calib_hi=fs_hi,
            contribution=pred,
        )
        rows.append(Row(
            operating_point=(round(d["M"], 2), round(d["re"], 3), round(d["x"], 4),
                             d["flow"], d["src_fig"]),
            surrogate_prediction=pred,
            cfd_truth=d["truth"],
            truth_source="experimental",
            cfd_uncertainty=d["unc"],
            guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
            mechanisms=[mech],
            meta={
                "M": d["M"], "Re_per_m_e6": d["re"], "x_m": d["x"],
                "freestream_noise_pct": d["fs"],
                "flow": d["flow"], "source_figure": d["src_fig"],
                "rms_meas": d["truth"], "rms_pred_gp": pred, "rms_unc": d["unc"],
                "cell": "quiet_deploy" if d["fs"] < fs_lo else "noisy_train",
            },
        ))

    rows = load_rows(rows)
    n_quiet = sum(1 for d in raw if d["flow"] == "Quiet")
    reference = {"ood": [0.0], "residual": [0.0], "variance": [0.0]}
    meta = SubstrateMeta(
        name="casper-hypersonic-transition-quiet-vs-noisy",
        divergent_truth_substrate=True,
        reason=_CASPER_REASON,
        norm_strategy="per_row_truth",
        bound_for_pde=None,
        magnitude_bridge_ok=True,
        extra={
            "domain": "aerospace / hypersonic boundary-layer transition",
            "fluid": config.fluid.name,
            "n_rows": len(rows), "n_noisy_train": len(noisy), "n_quiet_deploy": n_quiet,
            "training_M_range": [float(Xtr[:, 0].min()), float(Xtr[:, 0].max())],
            "failure_variable": "freestream_noise_pct (RMS Pitot %, omitted from surrogate inputs)",
            "data_source_path": str(main_path),
            "closures": {
                "corpus_validity_anchor": (
                    f"{config.matched_closure_id} (corpus {matched.status}; "
                    "freestream-noise bound >= ~0.5% fires on the quiet deploy)"
                ),
            },
        },
    )
    return rows, reference, meta


# ── marineau_hypersonic_transition (aerospace NEGATIVE CONTROL: bluntness) ──

_MARINEAU_REASON = (
    "Independent experimental truth: transition parameters on blunt cones at "
    "Mach ~10, transcribed from Marineau et al. (2014, SAND2014-4326C) Table 3 "
    "'Transition Parameters at 0-deg AoA'. The surrogate predicts transition "
    "momentum-thickness Reynolds Re_theta,ST from (unit Reynolds, nose radius); "
    "the failure driver is the entropy-layer/shock-interaction ratio S_T/X_SW "
    "(< 0.1 -> 2nd mode absent, e^N regime breaks). NEGATIVE CONTROL: a citable "
    "validity bound exists (S_T/X_SW >= 0.1) and the corpus fires on the large-"
    "bluntness deploy, BUT nose radius IS a surrogate input, so the steelman "
    "baseline ALSO fires (deploy is exterior in Rn) -> PhysMAP correctly declines "
    "a clean differentiator."
)


def marineau_gp_fit(X, y):
    """The Marineau surrogate: a GP on (unit Reynolds, nose radius). Returns predict(X) on
    raw inputs. Module-level so the home baseline can refit it without one row."""
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel

    X = np.asarray(X, dtype=float)
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    gp = GaussianProcessRegressor(
        kernel=ConstantKernel(1.0, (1e-3, 1e3)) * RBF([1.0, 1.0], (1e-2, 1e2))
        + WhiteKernel(1.0, (1e-5, 1e2)),
        normalize_y=True, n_restarts_optimizer=4, random_state=0,
    ).fit((X - mu) / sd, np.asarray(y, dtype=float))
    return lambda Xn: gp.predict((np.asarray(Xn, dtype=float) - mu) / sd)


def marineau_hypersonic_transition(config: VehicleConfig,
                                   registry: dict[str, ClosureEntry]) -> tuple[list[Row], dict, SubstrateMeta]:
    """Engine-driven Marineau loader (aerospace NEGATIVE CONTROL: bluntness/entropy).

    Reads the Table-3 CSV (run, Rn_mm, Re_per_m, ..., ST_Xsw, RethetaST, ...).
    Split: benign/train where S_T/X_SW >= the band cutoff (e^N/2nd-mode regime),
    deploy where S_T/X_SW < cutoff (entropy-layer dominated). The surrogate is a
    GP on (unit Reynolds, nose radius) -> Re_theta,ST fit on benign. The matched
    closure (Marineau entropy-layer/shock bound) is the corpus/validity anchor.
    """
    import csv as _csv

    if config.data_source.path is None:
        raise ValueError(
            f"VehicleConfig {config.vehicle_id!r}: data_source.path is required "
            f"for the marineau_hypersonic_transition loader."
        )
    csv_path = _resolve(config.data_source.path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Marineau Table-3 CSV not found: {csv_path}")

    st_cut = float(config.cell_bands.bands[0].get("st_xsw_lt", 0.1))

    raw: list[dict] = []
    with open(csv_path, newline="") as fh:
        for r in _csv.DictReader(fh):
            try:
                raw.append(dict(
                    run=int(float(r["run"])),
                    Re_per_m=float(r["Re_per_m"]),
                    Rn_mm=float(r["Rn_mm"]),
                    st_xsw=float(r["ST_Xsw"]),
                    truth=float(r["RethetaST"]),
                ))
            except (KeyError, ValueError):
                continue
    if not raw:
        raise RuntimeError(f"marineau loader: no usable rows in {csv_path}")

    benign = [d for d in raw if d["st_xsw"] >= st_cut]
    if len(benign) < 3:
        raise RuntimeError(f"marineau loader: need >= 3 benign train rows, got {len(benign)}")

    Xtr = np.array([[d["Re_per_m"], d["Rn_mm"]] for d in benign], dtype=float)
    ytr = np.array([d["truth"] for d in benign], dtype=float)
    predict = marineau_gp_fit(Xtr, ytr)

    matched = registry[config.matched_closure_id]
    st_lo, st_hi = matched.bound_range               # S_T/X_SW validated band (corpus mirror)

    rows: list[Row] = []
    for d in raw:
        pred = float(predict(np.array([[d["Re_per_m"], d["Rn_mm"]]], dtype=float))[0])
        mech = Mechanism(
            name="marineau_entropy_layer_shock_validity_anchor",
            closure_id=config.matched_closure_id,
            operating_value=d["st_xsw"], calib_lo=st_lo, calib_hi=st_hi,
            contribution=pred,
        )
        rows.append(Row(
            operating_point=(d["run"], round(d["Rn_mm"], 3)),
            surrogate_prediction=pred,
            cfd_truth=d["truth"],
            truth_source="experimental",
            cfd_uncertainty=float("nan"),
            guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
            mechanisms=[mech],
            meta={
                "Re_per_m": d["Re_per_m"], "Rn_mm": d["Rn_mm"],
                "st_xsw_ratio": d["st_xsw"],
                "RethetaST_meas": d["truth"], "RethetaST_pred_gp": pred,
                "run": d["run"],
                "cell": "failure_2ndmode_absent" if d["st_xsw"] < st_cut else "benign_eN_valid",
            },
        ))

    rows = load_rows(rows)
    n_deploy = sum(1 for d in raw if d["st_xsw"] < st_cut)
    reference = {"ood": [0.0], "residual": [0.0], "variance": [0.0]}
    meta = SubstrateMeta(
        name="marineau-hypersonic-transition-bluntness",
        divergent_truth_substrate=True,
        reason=_MARINEAU_REASON,
        norm_strategy="per_row_truth",
        bound_for_pde=None,
        magnitude_bridge_ok=True,
        extra={
            "domain": "aerospace / hypersonic boundary-layer transition",
            "fluid": config.fluid.name,
            "n_rows": len(rows), "n_benign_train": len(benign), "n_deploy": n_deploy,
            "benign_Rn_mm_range": [float(Xtr[:, 1].min()), float(Xtr[:, 1].max())],
            "failure_variable": "st_xsw_ratio (S_T/X_SW; recoverable from Rn -> baseline-visible)",
            "data_source_path": str(csv_path),
            "closures": {
                "corpus_validity_anchor": (
                    f"{config.matched_closure_id} (corpus {matched.status}; "
                    "S_T/X_SW >= 0.1 bound fires on the large-bluntness deploy)"
                ),
            },
        },
    )
    return rows, reference, meta


_JIN_REASON = (
    "Jin et al. 2023 sCO2 vertical-tube buoyancy: measured local Nu (truth) vs the direction-OMITTING "
    "constant-property Dittus-Boelter surrogate. Failure driver = Liu buoyancy parameter Bu (omitted); the "
    "matched closure dittus-boelter-buoyancy-sco2 carries the corpus Bu<=1.3e-5 bound. Digitization-tier "
    "(Fig-17 cell human-confirmed, q/G families reader-2-verified); see results/jin_sco2_buoyancy/DATA_STATUS.md."
)


def jin_sco2_buoyancy_lfs(config: VehicleConfig,
                          registry: dict[str, ClosureEntry]) -> tuple[list[Row], dict, SubstrateMeta]:
    """Engine-driven Jin sCO2 vertical-tube buoyancy loader (buoyancy middle vehicle).

    Reads the offline-precomputed benchmark substrate CSV (make_benchmark_substrate.py: CoolProp,
    one-off) and emits Rows whose `surrogate_prediction` is the constant-property, direction-OMITTING
    Dittus-Boelter Nu(Re,Pr) (matched closure dittus-boelter-buoyancy-sco2) and whose `cfd_truth` is the
    measured local Nu. `meta` carries the failure driver `Bu` (Liu buoyancy parameter) + the `split_role`
    benign/deploy label, so the buoyancy_parameter_bands split + the observability score can read them.
    """
    import csv as _csv

    if config.data_source.path is None:
        raise ValueError(
            f"VehicleConfig {config.vehicle_id!r}: data_source.path is required for jin_sco2_buoyancy_lfs."
        )
    csv_path = _resolve(config.data_source.path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Jin sCO2 benchmark substrate CSV not found: {csv_path}. Run "
            f"results/jin_sco2_buoyancy/make_benchmark_substrate.py (CoolProp, offline) to generate it."
        )

    matched = registry[config.matched_closure_id]   # dittus-boelter-buoyancy-sco2 (constant-property D-B)
    if matched.re_range is None:
        raise RuntimeError(f"{config.matched_closure_id!r} has no re_range; cannot build mechanism.")

    rows: list[Row] = []
    with open(csv_path, newline="") as fh:
        for raw in _csv.DictReader(fh):
            Re = float(raw["Re_b"]); Pr = float(raw["Pr_b"])
            Nu_meas = float(raw["Nu_meas"])
            if not (Nu_meas > 0.0):
                continue
            Nu_unc = float(raw["Nu_unc"])
            Nu_pred = float(matched.fn(Re=np.array([Re]), Pr=np.array([Pr]))[0])
            mechanisms = [
                Mechanism(
                    name="constant_property_dittus_boelter_direction_omitted",
                    closure_id=config.matched_closure_id,
                    operating_value=Re,
                    calib_lo=matched.re_range[0],
                    calib_hi=matched.re_range[1],
                    contribution=Nu_pred,
                ),
            ]
            rows.append(Row(
                operating_point=(round(Re, 1), round(Pr, 4)),
                surrogate_prediction=Nu_pred,
                cfd_truth=Nu_meas,
                truth_source="experimental",
                cfd_uncertainty=Nu_unc,
                guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
                mechanisms=mechanisms,
                meta={
                    "Re": Re,
                    "Pr": Pr,
                    # failure driver (omitted from the surrogate inputs):
                    "Bu": float(raw["Bu"]),
                    # split coordinate (physical benign/deploy regime label):
                    "split_role": raw["split_role"],
                    # context:
                    "Bo_star": float(raw["Bo_star"]),
                    "flow_direction": raw["flow_direction"],
                    "H_b_kJ_kg": float(raw["H_b_kJ_kg"]),
                    "G_kg_m2s": float(raw["G_kg_m2s"]),
                    "q_kW_m2": float(raw["q_kW_m2"]),
                    "P_MPa": float(raw["P_MPa"]),
                    "T_b_C": float(raw["T_b_C"]),
                    "T_wi_C": float(raw["T_wi_C"]),
                    "Nu_meas": Nu_meas,
                    "Nu_unc": Nu_unc,
                    "h_meas_kW_m2K": float(raw["h_meas_kW_m2K"]),
                    "source": raw["source"],
                },
            ))

    rows = load_rows(rows)
    reference = {"ood": [0.0], "residual": [0.0], "variance": [0.0]}
    meta = SubstrateMeta(
        name="jin-sco2-vertical-tube-buoyancy",
        divergent_truth_substrate=True,
        reason=_JIN_REASON,
        norm_strategy="per_row_truth",
        bound_for_pde=None,
        magnitude_bridge_ok=True,
        extra={
            "geometry": "vertical circular tube, Di=7.74 mm, heated length 1050 mm (L/d=135), 316L",
            "fluid": config.fluid.name,
            "n_rows": len(rows),
            "data_source_path": str(csv_path),
            "failure_driver": "Bu (Liu buoyancy parameter, wall-aware)",
            "buoyancy_bound": "dittus-boelter-buoyancy-sco2: Bu <= 1.3e-5 (a-priori, banked jin-2023-correct Claim)",
            "data_tier": "digitization (Fig-17 cell human-confirmed; q/G families reader-2-verified)",
        },
    )
    return rows, reference, meta


# Register all loaders at import time.
register_loader("lance_smith_lfs", lance_smith_lfs)
register_loader("forrest_visual_estimates", forrest_visual_estimates)
register_loader("mudhafar_wpd", mudhafar_wpd)
register_loader("naca_wpd", naca_wpd)
register_loader("testi_grassi_lfs", testi_grassi_lfs)
register_loader("dirker_water_richardson_bands", dirker_water_richardson_bands)
register_loader("velazquez_sco2_lfs", velazquez_sco2_lfs)
register_loader("jin_sco2_buoyancy_lfs", jin_sco2_buoyancy_lfs)
register_loader("casper_hypersonic_transition", casper_hypersonic_transition)
register_loader("marineau_hypersonic_transition", marineau_hypersonic_transition)
