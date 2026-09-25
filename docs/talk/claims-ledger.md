# Claims ledger

Every sentence the talk might say as a headline, with the exact wording, the command and
artifact behind it, the evidence, its scope and limits, and where it may be used:
**main** (a main slide or its voice-over), **backup** (backup slide or an answer), or
**do not say**.

Commands run from a clone of the public repository. "The bank" is
`results/lewis35A_head_to_head/stress_test_lewis_reuse.json`, which
`physmap stress-test lewis-reuse` recomputes and checks itself against. Numbers are in
[`facts-sheet.md`](facts-sheet.md).

---

## Main talk

Two functions, each with its own evidence. **Applicability assurance** (MA, M9): is the physics
the model relies on still applicable? **Causal materiality** (M1–M8, Lewis 35A, the main
controlled demonstration): does an omitted mechanism materially change the answer? The
seven-vehicle benchmark (M0, M0d, M0b, M0c, M10) is supporting evidence, led by Casper.

### MA — the two questions

> "OOD asks whether inputs look familiar. PhysMAP asks whether the model's physics remains
> applicable, and whether an omitted mechanism materially changes the quantity of interest."

- **Command and artifact:** the two demonstrations below — M9 (applicability) and M1–M8
  (causal materiality).
- **Scope and limits:** it names two functions; each is shown once, on its own evidence.
  Neither is evidence for the other, and neither is a detection rate.
- **Use:** main — slides 3 and 13.

### M9 — applicability assurance: the x/D entrance region

> "In the pipe's entrance region, Gnielinski is within the numerical-error threshold on 40 of 40
> fully developed points and exceeds it on 9 of 45 entrance points. PhysMAP identifies all 45
> entrance predictions as outside the closure's supported region. The other 36 are numerically
> acceptable, but not physically supported by that closure."

- **Command and artifact:** `python examples/naca_entrance_region.py` prints the counts and
  asserts the clean home baseline; captured in `reproduction/naca_example.txt`. Figure:
  `bench_1_naca_entrance`.
- **Evidence:** NACA TN-1451, Fig 10, two-reader digitisation: 9 positions on each of 5
  Reynolds-number curves; the closure's validated range starts at x/D = 10; the threshold
  (17.5 %) is the benchmark's own NACA threshold. The input-based detectors fire on 0.
- **Scope and limits:** applicability, not materiality. The 9 exceedances are all at x/D ≤ 5.
  It shows that a numerically acceptable prediction can still rest on physics outside its
  supported region — not that each of the 45 is wrong.
- **Use:** main — slide 4, the first of the two functions. Say the 36 unprompted: numerically
  close, but not supported by validation evidence for this region — never "by luck".

### M1 — what an input-based detector can see

> "An input-based OOD detector tells you whether the inputs are familiar. It cannot report a
> change that is not in its inputs."

- **Command and artifact:** `physmap stress-test lewis-reuse` prints "The OOD columns are the
  SAME with gravity off and on -- every score, every percentile: YES", and asserts it. The bank:
  `headline_design_M.ood.identical_between_gravity_states`. Figure: `lewis_3_ood_identical`.
- **Evidence:** for all 12 stations, both detector scores and all six operating percentiles, the
  largest difference between gravity off and gravity on is 0.
- **Scope and limits:** the first sentence describes what the detector is designed to do. The
  second is a logical property — identical inputs give identical scores — demonstrated here with
  the seven-vehicle benchmark's own detector, unchanged, on one run.
- **Use:** main.

### M1b — the threshold-independent headline

> "The OOD scores are identical with gravity on and off because the visible inputs are
> identical."

- **Command and artifact:** as M1. Figure: `lewis_2_control_vs_gravity_on` (bottom left);
  `lewis_3_ood_identical` in backup.
- **Scope and limits:** this needs no threshold. Whether the detector *fires* does: at the
  benchmark's reference percentile, 99, it is quiet in both states; at lower percentiles it
  fires — in both states alike (B4). Never say "quiet" without "at the reference percentile,
  99".
- **Use:** main — slide 8.

### M2 — the claim

> "PhysMAP detects when model reuse activates a physically relevant mechanism outside the
> surrogate's observable input space. An input-only OOD detector cannot identify a change
> absent from its input contract."

- **Command and artifact:** printed as the command's `Claim:`; the bank's `claim` field.
- **Evidence:** M1, M3, M6.
- **Scope and limits:** demonstrated once — one run, one mechanism (buoyancy), in a reuse
  scenario built on purpose. "Detects" means the materiality separates the two states; there is
  no detection rate. Say "shown in one controlled stress test" alongside it.
- **Use:** main.

### M3 — the input contract

> "The surrogate and the OOD detector both receive Re, Pr and x/D. Neither receives gravity,
> Ri, Gr or heat flux. Every visible deployment input exactly matches a training input."

- **Command and artifact:** the command's `INPUT CONTRACT` block, ending "every visible
  deployment input exactly matches a training input (design M): YES", asserted by the command.
  The bank: `input_contract`. Figure: `lewis_1_input_contract`.
- **Evidence:** exact set membership of (Re, Pr, x/D) for all 12 deployment stations in the
  532 training rows.
- **Scope and limits:** exact because the matched training run is labelled with 35A's reported
  Re 1143.4 and Pr 8.46. Its own inlet values differ by -0.062 % and +0.141 %. That labelling
  was pre-declared (`results/lewis35A_head_to_head/PREDECLARE_design_M_matched.md`).
- **Use:** main.

### M4 — the control is accurate

> "On the gravity-off control, the surrogate is within 0.06 %."

- **Command and artifact:** the `control` column of the command's headline table. Figure:
  `lewis_2_control_vs_gravity_on`.
- **Evidence:** the largest control error over the 9 comparable stations.
- **Scope and limits:** against gravity-off CFD, not the experiment. It shows the surrogate
  reproduces the physics it was trained on — not that the physics is right.
- **Use:** main.

### M5 — the reused model is wrong

> "With gravity on, the surrogate is 17–18 % off Lewis's measurement at x/D 67.55, 101.69 and
> 135.84."

- **Command and artifact:** the `experiment` column. Figure: `lewis_2_control_vs_gravity_on`.
- **Evidence:** -17.0 %, -16.8 %, -18.0 % at those three stations.
- **Scope and limits:** one run. The source reports no combined per-point uncertainty. These are
  three positions in one experiment, not three cases.
- **Use:** main.

### M6 — materiality separates the states

> "PhysMAP's materiality is 0 with gravity off and rises down the tube to 0.195 with gravity
> on."

- **Command and artifact:** the materiality columns; the bank's `threshold_dependence`.
  Figures: `lewis_2_control_vs_gravity_on`, `lewis_4_materiality`.
- **Evidence:** 0.006 to 0.195 at the comparable stations with gravity on; 0 at every station
  with gravity off.
- **Scope and limits:** materiality comes from the matched CFD pair, not from the measurement.
  Zero with gravity off is by construction — there is no buoyancy to remove. The finding is the
  gravity-on profile, and that the OOD output does not change while it does.
- **Use:** main.

### M7 — the line to land

> "Same inputs, same OOD scores. Different physics, different materiality — and where
> materiality is largest, the surrogate is 17–18 % off."

- **Command and artifact:** M1, M5 and M6 together. Figure: `lewis_5_control_table`.
- **Scope and limits:** "where materiality is largest" means the three downstream comparable
  stations. It does not claim materiality predicts error in general (see B8), or that every
  error carries materiality (see B7).
- **Use:** main. It replaces the earlier "and the materiality is where the error is" — see D9.

### M8 — thresholds

> "θ is not locked, and the headline needs none. At the illustrative θ = 0.10 — the original
> study's value — three comparable stations would flag. At 0.05, five. At 0.20, none. With
> gravity off, none at any θ."

- **Command and artifact:** the command's `THRESHOLDS` section; the bank's
  `threshold_dependence`; `protocols/protocol.json` (`threshold_presentation`). Figure:
  `lewis_4_materiality`.
- **Evidence:** materiality values; at least one flag for any θ ≤ 0.195.
- **Scope and limits:** θ = 0.10 is shown because it is the historical value, recorded before
  any Lewis work, not because it is endorsed. The OOD detector's fired-or-quiet also depends on a
  threshold: its operating percentile, reference 99, fixed in code before this work.
- **Use:** main.

### M0 — supporting evidence: Casper, across three model types

> "In the hypersonic case the surrogate is accurate at home — 6 of 159 wrong, held out — and
> wrong on 8 of 8 deployed. Three model types, a Gaussian process, a DeepONet and
> gradient-boosted trees, each pass the same home-accuracy check, and each leaves 4 of 8
> deployment errors that only PhysMAP flags."

- **Command and artifact:** `physmap benchmark architectures --banked` (the bank
  `data/benchmarks/v0_4_1/architecture_axis.json`); `physmap benchmark report` for the home
  baseline and the detector counts; the matrix `data/benchmarks/v0_4_1/matrix_full_seven.json`.
- **Evidence:** a count needs the closure check fired, both input-based detectors
  (distance-to-training and GP variance) quiet, and the prediction wrong. The detectors never
  see a prediction, so their flags are the same for every model type.
- **Scope and limits:** one dataset; rows are not independent cases; values digitised from a
  publication. Supporting evidence, not the headline.
- **Use:** main — slide 10.

### M0d — the full matrix, with its limitations

> "Every dataset stays on the slide. Casper and Dirker have a home baseline from which
> deployment fails; NACA is the applicability case. Jin and Velazquez are wrong almost
> everywhere, at home too, so their counts cannot show that deployment created the failure."

- **Command and artifact:** `physmap benchmark report`, "Home baseline"; bank:
  `data/benchmarks/v0_4_1/home_baseline.json`, beside the matrix. Figure:
  `bench_4_home_baseline`.
- **Evidence:** home error is labelled by how it was obtained — in-sample fit error where the
  surrogate was fitted to the home rows, with a leave-one-out refit beside it; held-out home
  error where it is a published correlation. "Wrong" is each dataset's own threshold. Casper
  6 of 159 at home, 8 of 8 deployed; Dirker 0 of 31, 11 of 60; NACA 0 of 40, 9 of 45; Jin
  17 of 17, 26 of 27; Velazquez 386 of 393, 67 of 67; Marineau 5 of 9, 6 of 6; Forrest 0 of 1.
- **Scope and limits:** no gate decides a dataset's reading — the counts and rates are the
  evidence, and the reading is written prose. A Fisher test was run after the counts were seen;
  it is labelled exploratory and decides nothing. No row is removed.
- **Use:** main — slide 11, as the chart with its short annotations; the dense table is
  backup B21.

### M0b — where it adds nothing

> "Where the cause is one of the surrogate's inputs, the OOD detectors already see it, and
> PhysMAP adds nothing — 0 of 6 in the control."

- **Command and artifact:** as M0; the `marineau_hypersonic_transition` row.
- **Scope and limits:** one control dataset; `forrest`, the other visible-cause dataset, has one
  training row and was not tested.
- **Use:** main. Say it unprompted — it is what makes M0 believable.

### M0c — accurate predictions flagged anyway

> "PhysMAP flags every prediction outside a closure's supported region, accurate or not — 19 at
> the pipe entrance, 16 for Dirker. As detection those are false alarms; as applicability
> assurance, they are predictions the closure does not support."

- **Command and artifact:** as M0; the "right: flagged anyway" column of
  `physmap benchmark report`.
- **Scope and limits:** at percentile 99. "Accurate" is within the benchmark's accuracy
  threshold; between it and the "wrong" threshold is a dead band, which is why NACA's 19 and the
  x/D example's 36 differ. Whether materiality weighting cuts these is the purpose of the causal
  work, and is not shown yet.
- **Use:** main. Say it unprompted.

### M10 — the seven vehicles, in full

> "Across seven published datasets, the benchmark asks whether the variable that breaks each
> surrogate is visible to an input-based detector. In three it is invisible, and the closure
> check flagged wrong rows the baseline missed; two of those three have a home baseline from
> which deployment fails. Two are partial. One is a negative control, where
> the baseline sees it. Forrest is triage-grade, and its result is not earned."

- **Command and artifact:** `physmap benchmark run` recomputes all seven and diffs against
  `data/benchmarks/v0_4/matrix_full_seven.json`; `physmap benchmark report` prints the table
  (captured in `reproduction/benchmark_report.txt`). Figure: `bench_2_seven_vehicles`.
- **Scope and limits:** the outcome labels are observability classes; the counts are in M0–M0c.
  Not evidence for causal materiality. Row counts are data rows, not cases. Five of the seven
  datasets ship without a licence.
- **Use:** backup — the chart in M0 carries the main slide.

### M11 — building it right

> "A mixed-convection surrogate built correctly should include Richardson number, Grashof
> number, or equivalent physical information."

- **Command and artifact:** the command's framing paragraph; `not_claimed` in the bank.
- **Use:** main. Say it before anyone asks.

### M12 — what Lewis is

> "This is one run. Its twelve stations are positions along one tube, not twelve cases. There
> is no precision, recall or F1."

- **Command and artifact:** the command's status line: "Development demonstration. One run
  (Lewis 35A), already inspected during development."
- **Use:** main. It must be said.

### M13 — reproduction

> "Anyone can rerun this analysis with one command from a clean clone. It reproduces the
> committed record — exactly on the recorded machine, and elsewhere to within a tolerance far
> below any printed digit. It does not rerun OpenFOAM."

- **Command and artifact:** [`reproduction/README.md`](reproduction/README.md): a clean public
  clone of the 0.2.5 release commit, exit status 0, the record matching the bank within the
  command's stated tolerance; the benchmark and the x/D example from the same clone.
- **Scope and limits:** reproduces the analysis from committed CFD-derived profiles.
  Regenerating the CFD needs Docker and the case generator; the manifest says how. Between
  machines and library versions the surrogate's last few digits move slightly; the command
  allows for that at a stated tolerance and still compares every flag, count and label
  exactly.
- **Use:** main — slide 13, as the commands and their captured, verified output. No live run.

### M14 — the abstract's numbers

> "The abstract reports precision 1.00 and recall 0.65. We are not presenting them as
> experimental validation. They were scored against a fitted correlation, not measurements,
> and the construction ties the flag to the label."

- **Artifact:** `protocols/known-results-declaration.md`;
  `docs/findings/surrogate-and-truth-provenance.md`;
  [`historical-reconciliation.md`](historical-reconciliation.md).
- **Use:** backup only (B22), with the numbers. In the main talk: once, early, without numbers
  (MB); at Lewis, that it replaces the earlier metrics as the main causal demonstration; and on
  slide 12, that the abstract's precision, recall and F1 are not presented as experimental
  validation.

### MB — the accepted abstract, said once

> "The accepted abstract reported an earlier correlation-referenced study. Rebuilding it
> changed what I am willing to claim, so today I will show the reconstructed open evidence."

- **Artifact:** [`historical-reconciliation.md`](historical-reconciliation.md).
- **Use:** main — slide 2, once. Do not repeat the historical metrics on any main slide.

---

## Backup

### B1 — specificity (designs A and A3)

> "When 35A's operating point sat between training runs, the OOD detector warned at all 9
> comparable stations — with gravity off, where the surrogate is right, and with gravity on,
> identically. PhysMAP's materiality did not change."

- **Command and artifact:** the command's `SECONDARY` block; the bank's `secondary_design_A3`.
- **Evidence:** distance 0.60–0.68 against a threshold of 0.473; control within 0.07 %.
- **Scope and limits:** the detector is right that the inputs are unfamiliar. It cannot say
  whether buoyancy caused an error. Specificity, not detection failure.
- **Use:** backup.

### B2 — pre-declared

> "Design M and its three success criteria were committed before any of its output existed.
> All three were met — the second at the illustrative θ."

- **Artifact:** `results/lewis35A_head_to_head/PREDECLARE_design_M_matched.md`;
  `design_M_matched.json` (`predeclared_criteria`).
- **Scope and limits:** 35A itself had been inspected during development. Pre-declaration
  fixes the analysis, not the data's history.
- **Use:** backup, or a sentence in the main talk.

### B3 — the buoyancy is real

> "Downstream, the measurement agrees with the gravity-on CFD within 1.6–6.6 %. The buoyancy
> effect the materiality measures is in the experiment."

- **Artifact:** facts sheet §6, computed from `cfd_profiles.json` and the bank.
- **Scope and limits:** one run; development evidence; the CFD was built while 35A was being
  inspected.
- **Use:** backup, or an answer.

### B4 — lower percentiles

> "At the reference percentile 99 the detector is quiet everywhere. At 75 it fires on 3 of 9
> comparable stations — identically with gravity off — because at that setting it fires on
> 97 % of its own training rows at x/D 50–100."

- **Artifact:** the command's sweep line; `design_M_low_pct_mechanism.json`.
- **Use:** backup. Volunteer it if a slide shows the sweep.

### B5 — numerics

> "The downstream stations are grid-converged: between the 20×300 and 30×400 meshes they move
> by at most 0.94 %. Energy closes within 0.35 % in every training run."

- **Artifact:** `results/lewis35A_vp/grid_pair.json`; `cfd_profiles.json`; facts sheet §7–8.
- **Scope and limits:** numerical stability, not validation. The entrance stations are
  sensitive to mesh and to how Nu is read off the wall. No separate grid study was run for
  gravity off.
- **Use:** backup.

### B6 — what "matched" means

> "The two CFD cases differ in one file, `constant/g`. Mesh, properties, boundary conditions,
> iterations and extraction are identical."

- **Artifact:** the bank's `matched_ablation.only_difference`, checked by a recursive diff
  when the inputs were banked.
- **Use:** backup, or an answer.

### B7 — what PhysMAP does not see

> "At x/D 2.45 and 16.32 the surrogate is off because the base CFD differs from the
> experiment there, not because of buoyancy. PhysMAP checks one mechanism."

- **Artifact:** facts sheet §6 (base-model gap +10.6 % and -9.8 %).
- **Use:** backup. Volunteer it.

### B8 — the coupling, stated

> "The surrogate's error splits exactly into missing buoyancy times the base model's gap times
> the fit error. The surrogate and the materiality share the gravity-off CFD, so their agreement
> is partly built in. That is one reason no rate is computed."

- **Artifact:** facts sheet §6; the same coupling is described for the original study in
  `docs/findings/surrogate-and-truth-provenance.md`.
- **Use:** backup. Say it if anyone asks whether materiality is just the error.

---

### B9 — the kind of model

> "On the hypersonic case, three model types — a Gaussian process, a DeepONet and
> gradient-boosted trees — each pass the same home-accuracy check, and each leaves 4 of 8
> deployment errors that only PhysMAP flags. At the pipe entrance all three pass too, but its
> home reads repeat — 40 rows, 5 distinct values — so the check says little there. On Jin and
> Velazquez no model type passes."

- **Command and artifact:** `physmap benchmark architectures` (PyTorch, about 20 minutes;
  `--banked` reads the bank); bank: `data/benchmarks/v0_4_1/architecture_axis.json`.
- **Evidence:** the detectors never see a prediction, so their flags are the same for every
  model; the axis shows which flagged rows each model gets wrong. Casper, Jin and Velazquez
  rerun bit-identical to the research bank on a second machine; NACA changed with its corrected
  data.
- **Scope and limits:** Casper is the one vehicle where the home check is informative and two
  or more model types pass it. These are trained models, not the benchmark's own surrogates;
  they do not change any home-baseline reading.
- **Use:** backup; Casper's line is main (M0).

---

## Do not say

| # | Do not say | Why | Say instead |
|---|---|---|---|
| D1 | "OOD detectors fail." / "OOD detection doesn't work." | Not shown, and not true: the detector did its job | M1 |
| D2 | "Engineers should leave gravity out." | The opposite of the lesson | M11 |
| D3 | "NVIDIA PhysicsNeMo fails." / "PhysicsNeMo would miss this." | Neither of its checks was run, and its OOD and physics checks are distinct | "We make no claim about PhysicsNeMo." |
| D4 | "PhysMAP achieves precision 1.00, recall 0.65, F1 0.79." | Correlation-referenced and coupled; not validation | M14 |
| D5 | "PhysMAP flagged three stations." (as a verdict) | θ is unlocked | M8 |
| D6 | "Lewis gives us twelve (or nine) test cases." | One run | M12 |
| D7 | "PhysMAP outperforms OOD detection." / any general superiority | It adds nothing when the cause is an input, and flags accurate predictions too | M0, M0b, M0c — say all three together |
| D8 | "Materiality predicts surrogate error." | Partly built in here; not shown in general | B8 |
| D9 | "The materiality is where the error is." | At x/D 2.45 and 16.32 there is error without materiality | M7 |
| D10 | "The CFD is validated." | Development evidence; convergence is not validation | B5 |
| D11 | Any rate across vehicles, such as "wins three of seven" or a pooled catch rate | The datasets differ in physics and size; rows are not independent; Forrest is not evidence | M0, per dataset |
| D18 | The catches without the flags on accurate predictions | They are part of the result | M0c |
| D12 | "The OOD detector was starved of inputs." | It got every input the surrogate gets | M3 |
| D13 | "The OOD detector caught the downstream stations." (citing percentile 75) | It fires there on its own training data, identically with gravity off | B4 |
| D14 | "The seven-vehicle benchmark shows the causal method works." | It measures closure validity and observability — supporting evidence, a separate question | M0, and part 3 of the narrative |
| D15 | "This reproduces the abstract." / "This reruns the CFD." | It reproduces the Lewis analysis from committed profiles | M13 |
| D16 | "PhysMAP catches every surrogate error." | Not the base-model errors | B7 |
| D17 | "We chose θ = 0.10." | It is the original study's value, shown for illustration | M8 |
| D19 | "PhysMAP catches all 20 failures at the pipe entrance." / any benchmark count read as a failure deployment created, for Jin or Velazquez | The 20 is withdrawn — it came from an invalid read; Jin and Velazquez are wrong almost everywhere, at home too | M9, M0d |
| D20 | "PhysMAP works with any model." | Informatively tested on one vehicle, with three model types | B9 |
| D21 | "The surrogate fails confidently across the entrance region." | It exceeds the threshold on 9 of 45 entrance points, near the inlet | M9 |
| D22 | "PhysMAP caught 45 prediction errors." | 9 exceed the threshold; all 45 are outside the closure's supported region, and 36 are numerically acceptable | M9 |
| D23 | "The difference is statistically significant." (as a verdict on a dataset) | The Fisher test was chosen after the counts were seen; it is exploratory and decides nothing | M0d |
| D24 | "The 36 are close by luck." / "right by chance" | Outside a validated range means unsupported; it does not prove an agreement is accidental | M9 |
| D25 | "The OOD detector is quiet." (for Lewis, unqualified) | It is quiet at the reference percentile, 99; at lower percentiles it fires in both states | M1b |
| D26 | "Test 35A is laminar." | Nominally laminar; the CFD models it as laminar; laminar flow throughout has not been independently established | M12 |
