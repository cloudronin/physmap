"""Generic config-driven substrate engine.

Per the v0.2 architecture refactor (Part 1): one `build_substrate(config, ...)`
function replaces the per-vehicle hand-coded substrate loaders. Vehicle-specific
data (geometry, closures, cell bands, raw-data loader) lives in YAML configs
under `physmap/vehicles/`; the engine reads the config, enforces the
geometry-match invariant, dispatches to a registered loader adapter, and
annotates the returned SubstrateMeta with engine-level provenance.

THE GEOMETRY-MATCH INVARIANT (the Sparrow-Cur / Lance & Smith lesson encoded
as code):

    assert matched_closure.geometry_class == config.geometry.class_, REFUSE

The check has a single escape hatch: `expect_mismatch=True` paired with a
non-empty `mismatch_rationale` in the VehicleConfig. This is the explicit
override used by positive-control vehicles (Mudhafar) whose mismatch is the
experiment. The override surfaces in the returned meta's `extra` dict so
downstream auditors can see why the invariant was bypassed.

Phase-1 staging: loader adapters in `substrate_loaders.py` are THIN wrappers
around the existing hand-coded substrate loaders (`lance_smith_to_rows()`,
etc.). The engine's job in Step 4 is the invariant + dispatch + meta
annotation, not row-level computation. In Step 9 (per-vehicle migration),
each loader is decomposed into a raw-data reader; the engine then computes
matched + reference predictions via the closure registry, and the
structural-equality gate becomes non-trivial.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Callable

from physmap.closures import REGISTRY, ClosureEntry
from physmap.substrate.corpus_real import SubstrateMeta
from physmap.substrate.stage1_ingest import Row
from physmap.substrate.vehicle_config import (
    VehicleConfig,
    VehicleConfigError,
    load_vehicle_config,
)


# ── exceptions ──────────────────────────────────────────────────────────────

class GeometryMismatchError(ValueError):
    """The matched closure's geometry_class does not equal the vehicle's
    geometry class, and `expect_mismatch=True` was not set. Refused at
    build time — the substrate engine guards itself against the trap that
    bit Lance & Smith and almost bit Forrest."""


# Loader signature: takes the validated VehicleConfig and the closure registry,
# returns (rows, reference, meta) compatible with the existing pipeline.
LoaderFn = Callable[[VehicleConfig, dict[str, ClosureEntry]],
                    tuple[list[Row], dict, SubstrateMeta]]


# ── LOADERS registry ────────────────────────────────────────────────────────
# Populated by `substrate_loaders` at import time. Kept as a plain dict so
# tests can monkey-patch entries for the byte-equality gate.

LOADERS: dict[str, LoaderFn] = {}


def register_loader(name: str, fn: LoaderFn) -> None:
    """Register a data-source loader adapter. Raises if the name is taken
    (silent override would mask refactor bugs)."""
    if name in LOADERS:
        raise ValueError(
            f"LOADERS already has entry {name!r}; refusing silent override. "
            f"If you intend to swap implementations, delete the entry first."
        )
    LOADERS[name] = fn


# ── the engine ──────────────────────────────────────────────────────────────

def build_substrate(
    config: VehicleConfig | str | Path,
    *,
    registry: dict[str, ClosureEntry] | None = None,
    corpus_path: str | Path | None = None,
) -> tuple[list[Row], dict, SubstrateMeta]:
    """Build a substrate from a VehicleConfig.

    Args:
        config: a `VehicleConfig` instance, or a path/string to a YAML file
            (auto-loaded via `vehicle_config.load_vehicle_config`).
        registry: closure registry; defaults to the global `REGISTRY`. Tests
            inject a custom registry to exercise edge cases.
        corpus_path: optional calibration-corpus path; accepted for forward
            compatibility but unused in Phase 1 (the closure registry caches
            ranges; the ClosureValidityDetector reads corpus.jsonl directly).

    Returns:
        (rows, reference, meta) — the same tuple shape every existing
        substrate loader returns. `meta.extra` is augmented with engine-level
        provenance keys: `substrate_engine_version`, `vehicle_id`,
        `geometry_class`, `matched_closure_id`, `matched_closure_geometry_class`,
        `matched_closure_status`, `expect_mismatch`, `mismatch_rationale` (only
        if expect_mismatch is set), `reference_closure_ids`, `cell_bands_type`.

    Raises:
        GeometryMismatchError: matched-closure geometry != vehicle geometry
            and expect_mismatch is not set.
        ValueError: expect_mismatch is set but geometries actually agree
            (dead override; either fix the YAML or drop the flag).
        KeyError: unknown loader name in `data_source.loader`.
    """
    # Step 1 — coerce path to VehicleConfig
    if isinstance(config, (str, Path)):
        config = load_vehicle_config(config)
    elif not isinstance(config, VehicleConfig):
        raise TypeError(
            f"build_substrate(config): expected VehicleConfig or path, got "
            f"{type(config).__name__}."
        )

    reg = registry if registry is not None else REGISTRY

    # Step 2 — registry lookup (KeyError already produced by VehicleConfig
    # validation, but defensively re-check here so test-injected registries
    # surface the error from the engine, not from dataclass construction).
    if config.matched_closure_id not in reg:
        raise KeyError(
            f"matched_closure_id={config.matched_closure_id!r} not in the "
            f"provided registry. Known: {sorted(reg.keys())}."
        )
    matched: ClosureEntry = reg[config.matched_closure_id]

    # Step 3 — geometry-match invariant (THE Sparrow-Cur lesson)
    geom_match = (matched.geometry_class == config.geometry.class_)

    if not geom_match and not config.expect_mismatch:
        raise GeometryMismatchError(
            f"VehicleConfig {config.vehicle_id!r}: matched_closure_id "
            f"{config.matched_closure_id!r} has geometry_class="
            f"{matched.geometry_class!r} but vehicle geometry.class="
            f"{config.geometry.class_!r}. This is the Sparrow-Cur / "
            f"Lance & Smith trap; refused at build time. If this mismatch is "
            f"INTENTIONAL (positive control), set `expect_mismatch: true` "
            f"and supply a non-empty `mismatch_rationale` in the YAML."
        )
    if geom_match and config.expect_mismatch:
        raise ValueError(
            f"VehicleConfig {config.vehicle_id!r}: expect_mismatch=true but "
            f"geometries actually match (both are "
            f"{matched.geometry_class!r}). Either remove expect_mismatch / "
            f"mismatch_rationale (override is dead), or correct the geometry "
            f"class. Refusing to silently treat a matching configuration as "
            f"a positive control."
        )

    # Step 4 — verify all reference closures resolve in the registry
    # (VehicleConfig already checks against the GLOBAL REGISTRY; if a custom
    # registry is injected, re-check.)
    if registry is not None:
        unknown_refs = [c for c in config.reference_closure_ids if c not in reg]
        if unknown_refs:
            raise KeyError(
                f"reference_closure_ids unknown to provided registry: "
                f"{unknown_refs}. Known: {sorted(reg.keys())}."
            )

    # Step 5 — loader dispatch
    loader_name = config.data_source.loader
    if loader_name not in LOADERS:
        raise KeyError(
            f"Unknown data-source loader {loader_name!r}. Registered: "
            f"{sorted(LOADERS.keys())}. To add a new loader, call "
            f"substrate_engine.register_loader(...) at import time."
        )
    loader = LOADERS[loader_name]

    rows, reference, meta = loader(config, reg)

    # Step 6 — annotate meta with engine-level provenance
    extra = dict(meta.extra)
    extra.update({
        "substrate_engine_version": "v0.2-phase1",
        "vehicle_id": config.vehicle_id,
        "domain": config.domain,
        "geometry_class": config.geometry.class_,
        "geometry_dims": dict(config.geometry.dims),
        "matched_closure_id": config.matched_closure_id,
        "matched_closure_geometry_class": matched.geometry_class,
        "matched_closure_status": matched.status,
        "reference_closure_ids": list(config.reference_closure_ids),
        "cell_bands_type": config.cell_bands.type,
        "expect_mismatch": bool(config.expect_mismatch),
    })
    if config.expect_mismatch:
        extra["mismatch_rationale"] = config.mismatch_rationale

    annotated = dataclasses.replace(meta, extra=extra)
    return rows, reference, annotated


# Bootstrap: register the loader adapters at engine-import time. Importing
# substrate_loaders also imports the existing legacy substrate modules (which
# is fine — we want them available during the Phase-1 wrapper period).
def _register_default_loaders() -> None:
    from physmap.substrate import loaders as substrate_loaders   # noqa: F401  (side-effect import)


_register_default_loaders()
