# Changelog

## 0.1.0 — first public release

PhysMAP lifted out of a private monorepo into its own repository, with fresh history.

### What works

- **Closure validity and surrogate observability.** The pipe-entrance case runs from a
  clean clone: 45 entrance points, every one rejected, every one firing on `x/D`, with the
  statistical baselines silent because they cannot observe the variable that broke the
  surrogate. `examples/naca_entrance_region.py`.
- **The seven-vehicle v0.4 benchmark.** `physmap benchmark run` recomputes all seven from
  the checkout and diffs every field against the committed matrix. Verified from a clean
  public clone on a different Python and numpy than it was developed on.
- **The causal-materiality API**, as method only: ablation counterfactual, applicability
  screen, truth-independence guard, deterministic explanations. Synthetic and declarative
  fixtures. No performance claim anywhere.

### What this release does not claim

It reports **no precision, recall or F1**, and the causal-materiality results in the
NAFEMS Multiphysics 2026 abstract are **not reproduced here**. The original study's inputs
are gone and the basis for its experimental truth is unresolved. A reconstruction is under
way under a locked protocol; because its grid, truth source and counterfactual all differ,
the best outcome available to it is independent corroboration, not reproduction. See
`protocols/`.

The benchmark is **not** evidence for the causal result. It measures closure validity and
observability. `jin_sco2_buoyancy` is a mixed-convection vertical tube and is the nearest
vehicle to the causal case; it still only asks whether its buoyancy parameter is
observable. Every explanation says so in its header.

### Licensing

Code is MIT. The corpus is CC BY 4.0. Digitised third-party measurements are under
neither — those measurements were not made here, so no copyright in them is claimed.

**Five of the seven benchmark datasets ship without a licence**, four of them against
express publisher terms. Numbers only: no paper, figure or PDF. Removed on objection. The
basis for each, including the arguments against, is in `data/REDISTRIBUTION.md` and
`NOTICE`.

### Known limitations

- **`forrest` is published but not benchmark-grade.** Its own header calls the values
  triage-only, and its cell is degenerate — one training row, no detector fit — so its
  `DO_NO_HARM` outcome is short-circuited rather than earned. Re-digitise Fig 5 properly
  before treating it as evidence.
- Reproduction requires an **editable install from a checkout**. Benchmark data lives in
  the repository, outside the package, deliberately. A wheel gives you the library and the
  seed corpus; it cannot run the benchmark.
- The calibration corpus is **open-core**: 15 seed closures ship with bounds, alongside a
  verdict-free index of 201. The full 53-closure corpus is not published.
- Float comparison against the banked matrix uses a `1e-9` relative tolerance. Outcomes,
  verdicts and every count are compared exactly.
