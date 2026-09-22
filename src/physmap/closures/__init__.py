"""Closure registry — the executable bridge between corpus entries and Nu formulas.

Per the v0.2 architecture refactor (Part 1): closure formulas live in `formulas.py`;
the keyed registry of `{closure_id -> ClosureEntry}` lives in `registry.py`; the
controlled geometry-class vocabulary lives in `geometry_classes.py`.

The registry is queried by `substrate_engine.build_substrate(...)` to look up both
the executable formula AND the geometry_class used in the geometry-match invariant.
Ranges and status mirror the calibration table (`results/calibration_corpus/corpus.jsonl`);
the registry caches them for fast invariant checks, but corpus.jsonl remains the
source of truth.
"""

from physmap.closures.geometry_classes import (
    GeometryClass,
    NARROW_RECT_CHANNEL_ONE_SIDED,
    CIRCULAR_PIPE,
    CIRCULAR_MICRO_TUBE_SMOOTH,
    CIRCULAR_PIPE_ROUGH,
    FLAT_PLATE_EXTERNAL_FORCED,
    VERTICAL_PLATE_EXTERNAL_NATURAL,
    FLAT_PLATE_EXTERNAL_MIXED,
    CIRCULAR_PIPE_ENTRANCE_REGION,
    ALL_GEOMETRY_CLASSES,
)
from physmap.closures.registry import (
    ClosureEntry,
    REGISTRY,
    get_closure,
    closure_ids_for_geometry,
)

__all__ = [
    "ClosureEntry",
    "REGISTRY",
    "get_closure",
    "closure_ids_for_geometry",
    "GeometryClass",
    "NARROW_RECT_CHANNEL_ONE_SIDED",
    "CIRCULAR_PIPE",
    "CIRCULAR_MICRO_TUBE_SMOOTH",
    "CIRCULAR_PIPE_ROUGH",
    "FLAT_PLATE_EXTERNAL_FORCED",
    "VERTICAL_PLATE_EXTERNAL_NATURAL",
    "FLAT_PLATE_EXTERNAL_MIXED",
    "CIRCULAR_PIPE_ENTRANCE_REGION",
    "ALL_GEOMETRY_CLASSES",
]
