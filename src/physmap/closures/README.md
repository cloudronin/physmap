# `physmap.closures` — closure registry

The executable bridge between the calibration corpus (`physmap.corpus.calibration`)
and the substrate engine (`physmap.substrate.engine`).

The corpus says *"Gnielinski is valid for Re ∈ [3000, 5e6], Pr ∈ [0.5, 2000] on circular
pipes"*. The substrate engine needs to **call** that formula. The registry is what
sits in between: one entry per closure, keyed by the same `closure_id` slug the
corpus uses, carrying the Python function + the geometry class + the cached ranges.

## Modules

| Module | Role |
|---|---|
| [`formulas.py`](formulas.py) | The Nu(Re, Pr [, …]) functions. Eight closures: Modified Sparrow-Cur, Gnielinski, Dittus-Boelter, Petukhov, Sieder-Tate, Pohlhausen forced flat-plate, McAdams natural vertical-plate, Churchill mixed-convection blend. Pure NumPy; no side effects. Each function takes **keyword-only** inputs and declares what it needs (`required_inputs` in the registry entry). |
| [`registry.py`](registry.py) | The `REGISTRY` dict + `ClosureEntry` dataclass + `get_closure(id)` + `closure_ids_for_geometry(class)`. Entries cache `re_range`/`pr_range`/`ra_range` from the corpus and carry the new `geometry_class` field (NOT in `corpus.jsonl` — geometry is excluded by gate 6 of the calibration schema). |
| [`geometry_classes.py`](geometry_classes.py) | Controlled string vocabulary for `geometry_class`. The substrate engine's geometry-match invariant compares strings exactly; `assert_known_geometry()` is the typo guard. |

## Closure status

Most entries have `status` mirroring the corpus `bound_status` (`confirmed`,
`claimed`, `extrapolated`, `confirmed-contested`). Two entries (Petukhov, Churchill
blend) carry `status="not-in-corpus"` — their formulas live here for reference
predictions but no corpus row backs them; the validity detector skips them.

## How to use

```python
from physmap.closures import REGISTRY, get_closure

entry = get_closure("gnielinski-1976")
print(entry.geometry_class)   # "circular_pipe"
print(entry.re_range)         # (3000.0, 5000000.0)
Nu = entry.fn(Re=np.array([10_000.0]), Pr=np.array([1.0]))
```

The substrate engine uses the registry to compute matched + reference closure
predictions per vehicle row. The validity detector reads ranges from the corpus
directly (the registry caches them, but the corpus is source-of-truth).

## Invariants pinned by tests

* Every corpus-backed registry entry's `closure_id` is present in
  `corpus.jsonl` (`tests/test_closures_registry.py::test_every_corpus_backed_registry_entry_is_in_corpus`).
* Every registry formula is byte-equal to the legacy hand-coded version
  (pre-Cleanup) — see commit `3911162`.
* Unknown geometry strings raise (`assert_known_geometry` typo guard).

## Adding a new closure

1. Add the formula to `formulas.py` (keyword-only inputs, NumPy arrays).
2. Add the calibration entry to `physmap/results/calibration_corpus/corpus.jsonl`
   (validated_range + provenance + bound_status). Run
   `python -m physmap.corpus.calibration validate` to confirm.
3. Add the `ClosureEntry` to `REGISTRY` in `registry.py`. Set `geometry_class`
   from `geometry_classes.py`; cache the ranges; cite the function.
4. If the closure introduces a new geometry, add the class string to
   `geometry_classes.py`.
