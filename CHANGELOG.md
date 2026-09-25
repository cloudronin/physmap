# Changelog

## 0.2.5 — two functions, and a corrected NACA bank

### Changed: how PhysMAP is presented

- **Two functions, each on its own evidence.** The README and the NAFEMS talk package are
  reorganised around them. *Applicability assurance* — is the physics a prediction relies on
  still applicable? — shown on NACA TN-1451's pipe entrance region. *Causal materiality* — does
  a mechanism the model left out materially change the quantity of interest? — shown in the
  Lewis 35A controlled model-reuse stress test, the main controlled demonstration. The
  seven-vehicle benchmark is supporting evidence, led by Casper.
- **The x/D example is applicability assurance, not a count of caught errors.** It now scores
  the Gnielinski correlation against the measurement and says so: within the numerical-error
  threshold on 40 of 40 fully developed points; over it on 9 of 45 entrance points, all near
  the inlet; all 45 entrance predictions outside the closure's supported region — the other 36
  numerically acceptable but not physically supported.

### Corrected: the benchmark's NACA source data (bank v0.4.1)

- The original bank's NACA row came from an automated read of NACA TN-1451 Fig 10 that does
  not represent the figure: its axis calibration was wrong, and its points sat on gridline
  crossings and legend text. Verified against the figure and two independent human reads. The
  NACA vehicle now reads the two-reader record of the same figure. Only that cell changed:
  wrong predictions flagged only by PhysMAP 20 of 20 → 9 of 9 (the "20 of 20" is withdrawn);
  accurate predictions flagged anyway 24 → 19. Record: `data/naca/CORRECTION_v0_4_1.md`.
- The current bank is `data/benchmarks/v0_4_1/`; `physmap benchmark report` names it and says
  why. The original `data/benchmarks/v0_4/` and `data/naca/wpd_fig10.csv` are kept unchanged
  for audit — history, not evidence — and their fingerprints are pinned by a test.

### New: the home baseline beside every count

- A wrong deployment prediction that only PhysMAP flags shows a failure deployment created only
  if the surrogate was accurate at home. `physmap benchmark report`, the README and the talk
  now show, per dataset: how the home error was obtained (in-sample fit error with a
  leave-one-out refit beside it, or a published correlation never fitted to the rows), home and
  deployment counts and rates at the benchmark's own threshold, and a written interpretation.
- **No gate decides a dataset's reading.** A one-sided Fisher exact test is reported only as
  exploratory analysis: it was chosen after the counts were seen, and it decides nothing. Each
  interpretation is prose reviewed against the exact counts it quotes; a test fails if a
  recomputation moves them.
- Casper and Dirker have a home baseline from which deployment fails, and NACA is the
  applicability case; Jin and Velazquez are wrong almost everywhere, at home too; Marineau's
  nine home rows are too few; Forrest has one. Every count stays; no row is removed.

### New: the architecture axis

- `physmap benchmark architectures` trains a Gaussian process, a DeepONet and gradient-boosted
  trees on each flagged vehicle, gates each on its held-out home error, and compares with the
  bank (PyTorch via `physmap[architectures]`, about 20 minutes; `--banked` reads the bank). On
  Casper all three pass and each leaves 4 of 8 deployment errors only PhysMAP flags. On NACA
  all three pass too, but its home reads repeat — 40 rows, 5 distinct values — so the check
  says little there, and the output says so. On Jin and Velazquez none passes.

### Also

- 234 tests ported from the research tree: they covered public code and had stayed behind.
- The stress-test report names itself as the causal-materiality check.

## 0.2.4 — the DOI on the PyPI page

- **The README carries the Zenodo DOI**: a badge at the top, and a line in the Citing section.
  `CITATION.cff` carries it too. `10.5281/zenodo.22950742` always resolves to the latest
  version; 0.2.3 has its own, `10.5281/zenodo.22950743`. This release exists so that the PyPI
  project page shows the same.
- No code changes.

## 0.2.3 — archived on Zenodo, with a DOI

- **Every release is now archived on Zenodo.** Once a version is on PyPI, the release workflow
  creates its GitHub release, with the version's changelog entry as the notes. Zenodo archives
  that release and gives the version a DOI, so the software can be cited. `.zenodo.json` holds
  the archive's metadata. This is the first archived release.
- **NOTICE and `data/REDISTRIBUTION.md` now say what removal on objection can reach.** It
  reaches the repository and every later release. It cannot reach a version already archived
  on Zenodo; only Zenodo can withdraw one. The packages on PyPI do not include `data/`.
- No code changes.

## 0.2.2 — what PhysMAP adds, up front

- **The README leads with what PhysMAP adds to input-based OOD detection.** A chart and a
  table show, per dataset at the default setting, the wrong predictions the closure check caught
  that the OOD detectors missed, and the right predictions it flagged anyway. Where the cause of
  failure is hidden from the surrogate's inputs, it catches what the detectors cannot — all 20 at
  the pipe entrance. Where the cause is an input, it adds nothing. It costs false alarms: 24 and
  16 in two datasets. Counts per dataset, never pooled into a rate.
- **`physmap benchmark report` prints those counts** under its table, so every number in the
  README can be checked against the command.
- The talk package leads with the same result, and presents the Lewis stress test as a separate,
  causal question.
- A slow test no longer demands a bit-identical benchmark match: on another numpy build one
  float can differ in its last bit, and the command then reports a match within 1e-9, which
  passes.

## 0.2.1 — the README says what is published

- The README's corpus section drops the "open-core" framing and says what is true: the code is
  MIT and the corpus data CC BY 4.0; the published seed is 15 closures with their bounds plus
  an index of 201; a larger 53-closure corpus exists and is not published, and nothing in the
  repository needs it. This release exists so that the PyPI project page shows the same text.
- No code changes.

## 0.2.0 — on PyPI, and a controlled model-reuse stress test

### New

- **`pip install physmap`.** The first release published to PyPI, built and published by
  `.github/workflows/workflow.yml` through PyPI trusted publishing — no token is stored. The
  wheel carries the library, the `physmap` command and the seed corpus. The benchmark, the
  stress test and the examples need a clone: their data lives in the repository by design.
- **`physmap stress-test lewis-reuse`.** A controlled model-reuse stress test on Lewis (1992)
  Test 35A: a surrogate trained for forced convection, reused in vertical heated flow where
  buoyancy is material. Every visible deployment input is a training input. The input-based
  OOD detector's scores are identical with gravity off and on; PhysMAP's materiality is 0 with
  gravity off and rises to 0.195 with gravity on. It recomputes from committed CFD-derived
  profiles — it does not rerun OpenFOAM — asserts the input overlap and the identical OOD
  scores, and checks itself against a committed record. Pre-declared before it was run:
  `results/lewis35A_head_to_head/`.
- **CFD for Lewis 35A** (`cfd/`): a variable-property OpenFOAM case using Lewis's own property
  polynomials, geometry and Nusselt definition, with a matched gravity-on/off ablation and
  recorded grid, iteration and energy-balance checks. Regenerating it needs Docker.
- **The NAFEMS talk package** (`docs/talk/`): figures generated from committed records, a
  facts sheet, a claims ledger, and `tools/talk_package.py check`, which fails if any displayed
  number drifts from the evidence.

### Changed

- From a pip-installed wheel, commands that need checkout-only data — `benchmark`,
  `explain <vehicle>`, `stress-test` — now refuse in one sentence instead of a traceback.
- The stress test compares against its record at a per-field tolerance — 1e-4 relative, and
  0.001 percentage points for error percentages — because its Gaussian-process fit moves
  slightly between machines. Flags, counts and labels are still compared exactly. The
  benchmark keeps its 1e-9.
- The reconstruction protocol records Lewis runs 13A, 16A and 35A as spent development
  evidence, barred from any scored figure, and fixes how results are shown while the
  materiality threshold θ is unlocked.

### Still not claimed

- **No precision, recall or F1.** The Lewis stress test is one run; its stations are not
  independent cases. The NAFEMS abstract's figures are not reproduced here and are not
  presented as experimental validation: `docs/talk/historical-reconciliation.md` explains why.
- OOD detectors do not fail in general; a mixed-convection surrogate built correctly should
  include Richardson number, Grashof number or equivalent; nothing is claimed about NVIDIA
  PhysicsNeMo.

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
