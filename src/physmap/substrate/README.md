# `physmap.substrate` — engine + configs + per-vehicle adapters

The architecture refactor's substrate side: take a `VehicleConfig` (YAML data,
no code), run it through `build_substrate(...)`, get back stage-1 `Row` objects
with closure predictions computed from the registry.

The engine enforces the **geometry-match invariant** — the Sparrow-Cur lesson
encoded as code. A closure's `geometry_class` must match the vehicle's
`geometry.class`, else `GeometryMismatchError`. The `expect_mismatch: true`
escape hatch (Mudhafar's intentional positive-control case) requires a non-empty
`mismatch_rationale`.

## Modules

| Module | Role |
|---|---|
| [`vehicle_config.py`](vehicle_config.py) | `VehicleConfig` + nested `GeometryConfig` / `CellBandsConfig` / `DataSourceConfig` / `FluidConfig` dataclasses. Strict-schema YAML loader. Rejects unknown keys, unknown geometry strings, unknown closure IDs, and "dead" mismatch overrides at load time. |
| [`engine.py`](engine.py) | `build_substrate(config) -> (rows, reference, meta)`. Enforces the geometry-match invariant, dispatches to a registered loader, annotates `meta.extra` with engine-provenance keys (`vehicle_id`, `matched_closure_id`, `geometry_class`, `expect_mismatch`, `mismatch_rationale`, …). |
| [`loaders.py`](loaders.py) | `LOADERS` dispatch registry: one adapter per `data_source.loader` string. Adapters reuse CSV-I/O helpers from the per-vehicle modules + compute predictions via the closure registry. Four adapters: `lance_smith_lfs`, `forrest_visual_estimates`, `mudhafar_wpd`, `naca_wpd`. |
| [`stage1_ingest.py`](stage1_ingest.py) | `Row` + `Mechanism` dataclasses (the canonical per-point shape) + `load_rows` independence guard (refuses `truth_source == "same-closure"`). |
| [`corpus_real.py`](corpus_real.py) | `SubstrateMeta` dataclass + per-row physics-coords helper. Used by the engine to assemble meta. |
| [`forrest.py`](forrest.py) | Forrest mini-channel — geometry constants + `cell_assignment` (Re-band classifier) + Table-4 reference MAE dicts. Post-Cleanup 5 part 2: closure functions + `forrest_to_rows` + `ForrestRow` retired. |
| [`lance_smith.py`](lance_smith.py) | Lance & Smith transient — CSV-I/O helpers (`read_srq_heatflux`, `read_bc_*`, `_refuse_forbidden_sources`) + `lance_smith_to_rows` shim that forwards to the engine. Post-Cleanup 5 part 1: closure functions + module constants retired. |
| [`naca_tn1451.py`](naca_tn1451.py) | NACA TN-1451 — `NACARow` dataclass + `from_synthetic_shape` generator + `cell_assignment` (x/D bands). Still used by `analysis.naca_synthetic_verification` and the WPD loader. |
| [`naca_wpd_loader.py`](naca_wpd_loader.py) | WPD CSV loader — enforces `source='wpd-csv'` discipline + the Fig-21 Re=26,100 asymptote-not-reached exclusion. Called by `loaders.naca_wpd`. |

## How to use

```python
from physmap.substrate import build_substrate
from physmap.substrate.vehicle_config import load_named_vehicle

cfg = load_named_vehicle("naca_tn1451")
rows, reference, meta = build_substrate(cfg)

print(len(rows))                              # 76 for the default WPD Fig 10
print(meta.extra["matched_closure_id"])       # "gnielinski-1976"
print(meta.extra["geometry_class"])           # "circular_pipe_entrance_region"
print(meta.extra["expect_mismatch"])          # True (intentional v0.3 mismatch)
print(rows[0].surrogate_prediction)           # Gnielinski Nu, computed via registry
print(rows[0].cfd_truth)                      # measured Nu_meas from the CSV
```

## The geometry-match invariant

```python
matched = registry[config.matched_closure_id]
if matched.geometry_class != config.geometry.class_:
    if not config.expect_mismatch:
        raise GeometryMismatchError(...)  # the Sparrow-Cur trap
    if not config.mismatch_rationale.strip():
        raise ValueError("expect_mismatch=true requires a rationale")
```

Two defenses-in-depth: a config that flags `expect_mismatch=true` but whose
classes actually MATCH also raises (catches config rot where geometry was edited
but the flag wasn't removed).

## Adding a new vehicle

1. Write `physmap/vehicles/<name>.yaml` per the `VehicleConfig` schema.
2. Pick the `matched_closure_id` from `closures.REGISTRY` — confirm its
   `geometry_class` matches your vehicle's `geometry.class`, or set
   `expect_mismatch: true` + `mismatch_rationale`.
3. Register a loader adapter in `loaders.py` if your data shape needs one
   (the existing four cover most patterns).
4. Run `build_substrate(load_named_vehicle("<name>"))` to confirm.

## Tests pinning the substrate

`tests/test_substrate_engine.py` — 19 tests including the geometry invariant
(positive + negative cases), the `expect_mismatch` escape-hatch discipline,
the L&S structural-equality gate over 276 real rows, and per-vehicle
"engine actually uses the registry" sentinel-swap tests.
