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

### M9 — the x/D example

> "In the entrance region, PhysMAP's closure check fires on 45 of 45 points. Both input-based
> detectors fire on 0."

- **Command and artifact:** `python examples/naca_entrance_region.py` prints "input-based OOD
  detectors fired on 0 of 45 entrance points" and asserts it. Captured in
  `reproduction/naca_example.txt`. Figure: `bench_1_naca_entrance`.
- **Evidence:** NACA TN-1451, Fig 10: 9 positions on each of 5 Reynolds-number curves; the
  closure's validated range starts at x/D = 10.
- **Scope and limits:** observability, not materiality. The detectors are silent because x/D
  is not their input, not because they were tuned.
- **Use:** main.

### M10 — the seven vehicles

> "Across seven published datasets, the benchmark asks whether the variable that breaks each
> surrogate is visible to an input-based detector. In three it is invisible, and the closure
> check caught wrong rows the baseline missed. Two are partial. One is a negative control, where
> the baseline sees it. Forrest is triage-grade, and its result is not earned."

- **Command and artifact:** `physmap benchmark run` recomputes all seven and diffs against
  `data/benchmarks/v0_4/matrix_full_seven.json`; `physmap benchmark report` prints the table
  (captured in `reproduction/benchmark_report.txt`). Figure: `bench_2_seven_vehicles`.
- **Scope and limits:** observability classes, not rates. Not evidence for causal materiality.
  Row counts are data rows, not cases. Five of the seven datasets ship without a licence.
- **Use:** main.

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

- **Command and artifact:** [`reproduction/README.md`](reproduction/README.md): clean public
  clone, exit status 0, "The record matches the banked record exactly."
- **Scope and limits:** reproduces the analysis from committed CFD-derived profiles.
  Regenerating the CFD needs Docker and the case generator; the manifest says how. Between
  machines and library versions the surrogate's last few digits move slightly; the command
  allows for that at a stated tolerance and still compares every flag, count and label
  exactly.
- **Use:** main.

### M14 — the abstract's numbers

> "The abstract reports precision 1.00 and recall 0.65. We are not presenting them as
> experimental validation. They were scored against a fitted correlation, not measurements,
> and the construction ties the flag to the label."

- **Artifact:** `protocols/known-results-declaration.md`;
  `docs/findings/surrogate-and-truth-provenance.md`;
  [`historical-reconciliation.md`](historical-reconciliation.md).
- **Use:** main — one slide, before Lewis.

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

## Do not say

| # | Do not say | Why | Say instead |
|---|---|---|---|
| D1 | "OOD detectors fail." / "OOD detection doesn't work." | Not shown, and not true: the detector did its job | M1 |
| D2 | "Engineers should leave gravity out." | The opposite of the lesson | M11 |
| D3 | "NVIDIA PhysicsNeMo fails." / "PhysicsNeMo would miss this." | Neither of its checks was run, and its OOD and physics checks are distinct | "We make no claim about PhysicsNeMo." |
| D4 | "PhysMAP achieves precision 1.00, recall 0.65, F1 0.79." | Correlation-referenced and coupled; not validation | M14 |
| D5 | "PhysMAP flagged three stations." (as a verdict) | θ is unlocked | M8 |
| D6 | "Lewis gives us twelve (or nine) test cases." | One run | M12 |
| D7 | "PhysMAP outperforms OOD detection." / any general superiority | They answer different questions; one run cannot rank them | "They answer different questions." |
| D8 | "Materiality predicts surrogate error." | Partly built in here; not shown in general | B8 |
| D9 | "The materiality is where the error is." | At x/D 2.45 and 16.32 there is error without materiality | M7 |
| D10 | "The CFD is validated." | Development evidence; convergence is not validation | B5 |
| D11 | Any rate across vehicles, such as "wins three of seven" | Outcomes are classes; Forrest is not evidence | M10 |
| D12 | "The OOD detector was starved of inputs." | It got every input the surrogate gets | M3 |
| D13 | "The OOD detector caught the downstream stations." (citing percentile 75) | It fires there on its own training data, identically with gravity off | B4 |
| D14 | "The seven-vehicle benchmark shows the causal method works." | It is an observability benchmark | M10 |
| D15 | "This reproduces the abstract." / "This reruns the CFD." | It reproduces the Lewis analysis from committed profiles | M13 |
| D16 | "PhysMAP catches every surrogate error." | Not the base-model errors | B7 |
| D17 | "We chose θ = 0.10." | It is the original study's value, shown for illustration | M8 |
