"""VehicleConfig — the YAML-backed data shape that drives `build_substrate(...)`.

Per the v0.2 architecture refactor (Part 1): everything a vehicle needs is data,
not code. One YAML per vehicle under `physmap/vehicles/`, parsed into an
immutable `VehicleConfig`. The substrate engine reads the config + the closure
registry + the calibration corpus and emits `(rows, reference, meta)` with no
vehicle-specific Python.

VALIDATION LAYERS (fail fast on misconfiguration):

  1. Schema validation — every YAML key is recognized; unknown keys raise.
  2. Geometry vocab check — `geometry.class_` must be in
     `physmap.closures.geometry_classes.ALL_GEOMETRY_CLASSES`.
  3. Registry reference check — `matched_closure_id` and every
     `reference_closure_ids` entry must exist in
     `physmap.closures.REGISTRY`.
  4. Mismatch escape-hatch check — `expect_mismatch=True` requires a
     non-empty `mismatch_rationale`; the geometry-match invariant lives
     in the substrate engine (build-time), not here, because it needs
     to compare the closure's geometry_class to the vehicle's class.

Reserved keys per schema (rejected if anything else appears):
  vehicle_id, domain, geometry, matched_closure_id, reference_closure_ids,
  cell_bands, data_source, fluid, expect_mismatch, mismatch_rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from physmap.closures import REGISTRY
from physmap.closures.geometry_classes import assert_known_geometry


# ── exceptions ──────────────────────────────────────────────────────────────

class VehicleConfigError(ValueError):
    """Raised on any structural / vocab / reference problem in a VehicleConfig."""


# ── reserved top-level keys ─────────────────────────────────────────────────

_TOP_LEVEL_KEYS = frozenset({
    "vehicle_id", "domain",
    "geometry", "matched_closure_id", "reference_closure_ids",
    "cell_bands", "data_source", "fluid",
    "expect_mismatch", "mismatch_rationale",
    "benchmark",
})

_GEOMETRY_KEYS = frozenset({"class", "dims"})
_DATA_SOURCE_KEYS = frozenset({"loader", "path", "dir", "options"})
_FLUID_KEYS = frozenset({"name", "pr_range"})
_BENCHMARK_KEYS = frozenset({
    "include", "domain", "surrogate_inputs", "regime", "failure_driver",
    "expected_observability_class", "threshold_calibration", "architecture_axis", "caveat",
})
_OBSERVABILITY_CLASSES = frozenset({"OBSERVABLE", "PARTIAL", "UNOBSERVABLE"})
_CELL_BANDS_TYPES = frozenset({
    "re_bands",                # Forrest — single Re cutoffs
    "dh_roughness_bands",      # Mudhafar — Dh + roughness flag
    "x_over_d_bands",          # NACA — entrance-region cells
    "richardson_bands",        # buoyancy middle vehicles (Testi-Grassi) — Ri cutoffs
    "buoyancy_parameter_bands",# Jin sCO2 vertical tube — Liu Bu buoyancy (benign/deploy by split_role)
    "property_variation_bands",# Velazquez sCO2 — property-variation (pseudo-critical) cells
    "freestream_disturbance_bands",        # Casper — quiet-vs-noisy hypersonic transition
    "entropy_layer_shock_interaction_bands",  # Marineau — bluntness (S_T/X_SW) transition
    "continuous",              # Lance & Smith — no bins
    "custom",                  # escape hatch for vehicle-specific logic
})


# ── dataclasses ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GeometryConfig:
    """Geometry block of a VehicleConfig.

    `class_` (trailing underscore to avoid Python keyword collision) is the
    geometry-vocab string compared by the invariant. `dims` is free-form
    (each vehicle records what its physics needs); the substrate engine
    surfaces it into `SubstrateMeta` but does not interpret it directly.
    """
    class_: str
    dims: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        assert_known_geometry(self.class_)


@dataclass(frozen=True)
class CellBandsConfig:
    """Cell-bands block. `type` selects the band-assignment strategy used by
    `substrate_engine.assign_cells(...)`. `bands` is type-specific shape;
    `continuous` carries no bands at all.
    """
    type: str
    bands: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.type not in _CELL_BANDS_TYPES:
            raise VehicleConfigError(
                f"cell_bands.type={self.type!r} not in {sorted(_CELL_BANDS_TYPES)}. "
                f"Add the new type to vehicle_config._CELL_BANDS_TYPES and teach "
                f"substrate_engine.assign_cells about it."
            )
        if self.type == "continuous" and self.bands:
            raise VehicleConfigError(
                "cell_bands.type='continuous' must not carry a `bands` list "
                "(the substrate is continuous in its operating point)."
            )
        if self.type != "continuous" and not self.bands:
            raise VehicleConfigError(
                f"cell_bands.type={self.type!r} requires a non-empty `bands` list."
            )
        # Each band entry must have a name
        for i, b in enumerate(self.bands):
            if not isinstance(b, dict) or "name" not in b:
                raise VehicleConfigError(
                    f"cell_bands.bands[{i}] missing 'name' field: {b!r}"
                )


@dataclass(frozen=True)
class DataSourceConfig:
    """Data-source block — which loader the substrate engine should call to
    materialize raw data into row dicts. `path` (file) and `dir` (directory)
    are alternatives — exactly one must be set unless `options` carries
    something loader-specific.
    """
    loader: str
    path: str | None = None
    dir: str | None = None
    options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.loader:
            raise VehicleConfigError("data_source.loader is required.")
        if self.path is None and self.dir is None and not self.options:
            raise VehicleConfigError(
                f"data_source.loader={self.loader!r} must specify one of "
                f"`path`, `dir`, or `options.*` so the loader knows what to read."
            )


@dataclass(frozen=True)
class FluidConfig:
    """Fluid metadata. Surfaced into row meta for the validity detectors;
    `pr_range` is the working envelope, not the per-row Pr value."""
    name: str
    pr_range: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise VehicleConfigError("fluid.name is required.")
        if self.pr_range is not None:
            lo, hi = self.pr_range
            if not (lo <= hi):
                raise VehicleConfigError(
                    f"fluid.pr_range invalid: {self.pr_range!r} (lo must be <= hi)."
                )


@dataclass(frozen=True)
class BenchmarkConfig:
    """Declarative benchmark-registry classification. Presence with `include=true`
    puts the vehicle in the benchmark matrix; absence means the vehicle is loadable
    but not benchmarked. Declares INTENT (`expected_observability_class`) + the few
    facts the runner can't infer (regime, surrogate_inputs, failure_driver) — and
    NEVER an outcome label (the cell outcome is computed from raw signals, never
    declared, so a vehicle can't assert its own win)."""
    include: bool
    domain: str
    surrogate_inputs: tuple[str, ...]
    regime: str
    failure_driver: str
    expected_observability_class: str
    threshold_calibration: tuple[float, float] | None = None
    architecture_axis: bool = False
    caveat: str = ""

    def __post_init__(self) -> None:
        for name, val in (("domain", self.domain), ("regime", self.regime),
                          ("failure_driver", self.failure_driver)):
            if not val:
                raise VehicleConfigError(f"benchmark.{name} is required (non-empty).")
        if not self.surrogate_inputs:
            raise VehicleConfigError("benchmark.surrogate_inputs must be non-empty.")
        if self.expected_observability_class not in _OBSERVABILITY_CLASSES:
            raise VehicleConfigError(
                f"benchmark.expected_observability_class="
                f"{self.expected_observability_class!r} not in "
                f"{sorted(_OBSERVABILITY_CLASSES)}."
            )
        if self.threshold_calibration is not None and len(self.threshold_calibration) != 2:
            raise VehicleConfigError(
                f"benchmark.threshold_calibration must be [paper_pct, dig_pct], "
                f"got {self.threshold_calibration!r}."
            )


@dataclass(frozen=True)
class VehicleConfig:
    """The full, validated VehicleConfig. Built only via `load_vehicle_config`
    (which feeds through `from_dict` to enforce schema). Immutable; the
    substrate engine treats it as read-only data.
    """
    vehicle_id: str
    domain: str
    geometry: GeometryConfig
    matched_closure_id: str
    reference_closure_ids: tuple[str, ...]
    cell_bands: CellBandsConfig
    data_source: DataSourceConfig
    fluid: FluidConfig
    expect_mismatch: bool = False
    mismatch_rationale: str = ""
    benchmark: BenchmarkConfig | None = None

    def __post_init__(self) -> None:
        if not self.vehicle_id:
            raise VehicleConfigError("vehicle_id is required.")
        if not self.domain:
            raise VehicleConfigError("domain is required.")
        if self.matched_closure_id not in REGISTRY:
            raise VehicleConfigError(
                f"matched_closure_id={self.matched_closure_id!r} not in REGISTRY. "
                f"Known: {sorted(REGISTRY.keys())}."
            )
        unknown_refs = [c for c in self.reference_closure_ids if c not in REGISTRY]
        if unknown_refs:
            raise VehicleConfigError(
                f"reference_closure_ids contain unknown entries: {unknown_refs}. "
                f"Known: {sorted(REGISTRY.keys())}."
            )
        # mismatch override discipline
        if self.expect_mismatch and not self.mismatch_rationale.strip():
            raise VehicleConfigError(
                f"vehicle_id={self.vehicle_id!r}: expect_mismatch=true requires a "
                f"non-empty mismatch_rationale (the rationale surfaces in meta and "
                f"is the audit trail for the override)."
            )
        if not self.expect_mismatch and self.mismatch_rationale.strip():
            raise VehicleConfigError(
                f"vehicle_id={self.vehicle_id!r}: mismatch_rationale is set but "
                f"expect_mismatch is false. Either set expect_mismatch=true or "
                f"remove the rationale (a rationale without the override is dead text)."
            )


# ── loader ──────────────────────────────────────────────────────────────────

def _ensure_known_keys(name: str, payload: dict, allowed: frozenset[str]) -> None:
    """Reject any keys outside the allowed set. Catches YAML typos that would
    otherwise silently parse and produce a misconfigured vehicle."""
    unknown = set(payload.keys()) - allowed
    if unknown:
        raise VehicleConfigError(
            f"{name}: unknown keys {sorted(unknown)} (allowed: {sorted(allowed)}). "
            f"Either add them to the schema or fix the typo."
        )


def from_dict(payload: dict) -> VehicleConfig:
    """Build a VehicleConfig from a parsed YAML dict. Validates the schema."""
    if not isinstance(payload, dict):
        raise VehicleConfigError(
            f"VehicleConfig payload must be a dict, got {type(payload).__name__}."
        )
    _ensure_known_keys("VehicleConfig", payload, _TOP_LEVEL_KEYS)

    # Required top-level keys
    for required in ("vehicle_id", "domain", "geometry",
                     "matched_closure_id", "cell_bands",
                     "data_source", "fluid"):
        if required not in payload:
            raise VehicleConfigError(f"VehicleConfig: missing required key {required!r}.")

    geom_raw = payload["geometry"]
    if not isinstance(geom_raw, dict):
        raise VehicleConfigError("geometry must be a mapping.")
    _ensure_known_keys("geometry", geom_raw, _GEOMETRY_KEYS)
    geom = GeometryConfig(
        class_=geom_raw["class"],          # YAML key is "class"; dataclass uses "class_"
        dims=dict(geom_raw.get("dims") or {}),
    )

    cell_raw = payload["cell_bands"]
    if not isinstance(cell_raw, dict):
        raise VehicleConfigError("cell_bands must be a mapping.")
    bands_raw = cell_raw.get("bands", [])
    if bands_raw and not isinstance(bands_raw, list):
        raise VehicleConfigError("cell_bands.bands must be a list when present.")
    cells = CellBandsConfig(
        type=cell_raw["type"],
        bands=tuple(dict(b) for b in bands_raw),
    )

    ds_raw = payload["data_source"]
    if not isinstance(ds_raw, dict):
        raise VehicleConfigError("data_source must be a mapping.")
    _ensure_known_keys("data_source", ds_raw, _DATA_SOURCE_KEYS)
    ds = DataSourceConfig(
        loader=ds_raw["loader"],
        path=ds_raw.get("path"),
        dir=ds_raw.get("dir"),
        options=dict(ds_raw.get("options") or {}),
    )

    fluid_raw = payload["fluid"]
    if not isinstance(fluid_raw, dict):
        raise VehicleConfigError("fluid must be a mapping.")
    _ensure_known_keys("fluid", fluid_raw, _FLUID_KEYS)
    pr_range_raw = fluid_raw.get("pr_range")
    pr_range: tuple[float, float] | None = None
    if pr_range_raw is not None:
        if not (isinstance(pr_range_raw, (list, tuple)) and len(pr_range_raw) == 2):
            raise VehicleConfigError(
                f"fluid.pr_range must be a 2-element list [lo, hi], got {pr_range_raw!r}."
            )
        pr_range = (float(pr_range_raw[0]), float(pr_range_raw[1]))
    fluid = FluidConfig(name=fluid_raw["name"], pr_range=pr_range)

    refs = payload.get("reference_closure_ids", []) or []
    if not isinstance(refs, list):
        raise VehicleConfigError("reference_closure_ids must be a list.")

    bench_raw = payload.get("benchmark")
    benchmark: BenchmarkConfig | None = None
    if bench_raw is not None:
        if not isinstance(bench_raw, dict):
            raise VehicleConfigError("benchmark must be a mapping.")
        _ensure_known_keys("benchmark", bench_raw, _BENCHMARK_KEYS)
        for req in ("include", "domain", "surrogate_inputs", "regime",
                    "failure_driver", "expected_observability_class"):
            if req not in bench_raw:
                raise VehicleConfigError(f"benchmark: missing required key {req!r}.")
        si_raw = bench_raw["surrogate_inputs"]
        if not (isinstance(si_raw, (list, tuple)) and si_raw):
            raise VehicleConfigError("benchmark.surrogate_inputs must be a non-empty list.")
        tc_raw = bench_raw.get("threshold_calibration")
        tc: tuple[float, float] | None = None
        if tc_raw is not None:
            if not (isinstance(tc_raw, (list, tuple)) and len(tc_raw) == 2):
                raise VehicleConfigError(
                    f"benchmark.threshold_calibration must be [paper_pct, dig_pct], "
                    f"got {tc_raw!r}.")
            tc = (float(tc_raw[0]), float(tc_raw[1]))
        benchmark = BenchmarkConfig(
            include=bool(bench_raw["include"]),
            domain=str(bench_raw["domain"]),
            surrogate_inputs=tuple(str(s) for s in si_raw),
            regime=str(bench_raw["regime"]),
            failure_driver=str(bench_raw["failure_driver"]),
            expected_observability_class=str(bench_raw["expected_observability_class"]),
            threshold_calibration=tc,
            architecture_axis=bool(bench_raw.get("architecture_axis", False)),
            caveat=str(bench_raw.get("caveat", "")),
        )

    return VehicleConfig(
        vehicle_id=payload["vehicle_id"],
        domain=payload["domain"],
        geometry=geom,
        matched_closure_id=payload["matched_closure_id"],
        reference_closure_ids=tuple(refs),
        cell_bands=cells,
        data_source=ds,
        fluid=fluid,
        expect_mismatch=bool(payload.get("expect_mismatch", False)),
        mismatch_rationale=str(payload.get("mismatch_rationale", "")),
        benchmark=benchmark,
    )


def load_vehicle_config(path: str | Path) -> VehicleConfig:
    """Parse a vehicle YAML at `path` into a validated VehicleConfig."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"VehicleConfig file not found: {path}")
    try:
        with path.open("r") as fh:
            payload = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise VehicleConfigError(f"YAML parse error in {path}: {exc}") from exc
    if payload is None:
        raise VehicleConfigError(f"VehicleConfig {path}: file is empty.")
    return from_dict(payload)


# Vehicle YAMLs are checkout data, not package data: they name CSV paths that only
# exist in a clone. Resolved lazily so importing this module never depends on where
# it was installed from.
def _vehicles_dir() -> Path:
    from physmap._paths import checkout_path

    return checkout_path("data", "vehicles", what="the benchmark vehicle specs")


def load_named_vehicle(vehicle_id: str) -> VehicleConfig:
    """Convenience loader: `vehicle_config.load_named_vehicle('forrest')` ->
    `VehicleConfig` parsed from `physmap/vehicles/forrest.yaml`."""
    return load_vehicle_config(_vehicles_dir() / f"{vehicle_id}.yaml")
