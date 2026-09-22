"""Substrate machinery — engine + configs + per-vehicle adapters.

The architecture refactor's substrate-side surface, grouped under one
subpackage. Read order for newcomers:

  vehicle_config   — VehicleConfig dataclass + strict-schema YAML loader.
  engine           — build_substrate(config, registry, corpus) with the
                      geometry-match invariant (the Sparrow-Cur lesson
                      encoded as code).
  loaders          — LOADERS dispatch registry; one adapter per vehicle.
  stage1_ingest    — Row + Mechanism dataclasses + the independence guard.
  corpus_real      — SubstrateMeta dataclass + per-row physics-coords helper.

Legacy per-vehicle modules (post-Cleanup-5; CSV helpers + thin shims to
the engine path):
  forrest          — Forrest mini-channel (cell_assignment + dims only).
  lance_smith      — L&S transient (CSV I/O helpers + lance_smith_to_rows shim).
  naca_tn1451      — NACA TN-1451 (NACARow + from_synthetic_shape).
  naca_wpd_loader  — NACA WPD CSV loader (called by the engine adapter).

Module renames during R3:
  substrate_engine.py      -> engine.py
  substrate_loaders.py     -> loaders.py
  forrest_substrate.py     -> forrest.py
  lance_smith_substrate.py -> lance_smith.py
  naca_tn1451_substrate.py -> naca_tn1451.py
  (vehicle_config, stage1_ingest, corpus_real, naca_wpd_loader keep names.)
"""
