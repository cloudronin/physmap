# Slide sequence

Seventeen main slides, about twenty minutes, then the backup inventory. The talk is built on
two things PhysMAP does: **applicability assurance** (slide 4, NACA x/D) and **causal
materiality** (slides 6–12, Lewis 35A, the main controlled demonstration). Slides 13–14 are
supporting evidence from the seven-vehicle benchmark, led by Casper. Figures are in
[`figures/`](figures/README.md); notes for each technical figure are in
[`speaker-notes.md`](speaker-notes.md). The live demo — when to start `physmap benchmark run`,
what to do if it breaks — is in [`../talk-runbook.md`](../talk-runbook.md).

## Main sequence

| # | Slide title | On the slide | The point | Time |
|---|---|---|---|---|
| 1 | PhysMAP: a causal, materiality-weighted in-calibration check for AI surrogates | Title, author, NAFEMS Multiphysics 2026 | — | 0:30 |
| 2 | What an input-based guardrail asks | Text: "Do this prediction's inputs look like the training inputs?" Distance to training; GP variance | A good question, about inputs only | 1:30 |
| 3 | What PhysMAP asks | Text: "Does the physics the model relies on still apply here? Does a mechanism the model left out materially change the answer?" Two boxes: applicability assurance · causal materiality. It keeps the OOD detectors | Two questions an input-based detector cannot ask | 1:15 |
| 4 | Applicability assurance: the x/D entrance region | `bench_1_naca_entrance` | Gnielinski within the numerical-error threshold on 40 of 40 home points; exceeds it on 9 of 45 entrance points; PhysMAP places all 45 outside the closure's supported region — the other 36 are numerically acceptable but not physically supported; input-based detectors 0 | 1:30 |
| 5 | What changed since the abstract | Text only — see below | The abstract's numbers are named and explained, not replaced | 1:15 |
| 6 | Causal materiality: does an omitted mechanism matter? | Text: "Is an applicable mechanism outside calibration — and does it materially change the answer?" Materiality = 1 − QoI(mechanism off) / QoI(mechanism on), by matched ablation. Two boxes: applicability (`examples/naca_entrance_region.py`) · causal materiality (`physmap stress-test lewis-reuse`) | Different question, different evidence; neither is evidence for the other | 1:15 |
| 7 | Lewis 35A: a controlled model-reuse stress test | The framing and the claim, word for word; "One run. Its stations are not cases." | What the test is, and what it is not | 0:45 |
| 8 | The input contract | `lewis_1_input_contract` | Same three inputs; gravity is not one; every deployment input is a training input | 1:15 |
| 9 | Same inputs, two physical states | `lewis_2_control_vs_gravity_on` | Control within 0.06 %; measurement 17–18 % off; OOD unchanged; materiality up to 0.195 | 1:45 |
| 10 | The OOD scores do not move | `lewis_3_ood_identical` | Largest difference 0 — the detector doing its job | 0:45 |
| 11 | Materiality is continuous | `lewis_4_materiality` | The headline needs no θ; 0.10 is illustrative only | 1:15 |
| 12 | In one table | `lewis_5_control_table` | "Same inputs, same OOD scores. Different physics, different materiality." | 0:30 |
| 13 | Supporting evidence: Casper, across three model types | Text: a table — Gaussian process, DeepONet, gradient-boosted trees; each passes the same home-accuracy check; each leaves 4 of 8 deployment errors only PhysMAP flags. Home: 6 of 159 wrong, held out; deployed: 8 of 8 | The result does not depend on the kind of surrogate, where it can be tested | 1:15 |
| 14 | Seven datasets, with their limitations | `bench_4_home_baseline` | Every dataset stays on the slide. Casper and Dirker have a home baseline, and NACA is slide 4's case; Jin and Velazquez are wrong almost everywhere; Marineau adds nothing; Forrest is untested | 1:45 |
| 15 | What this shows — and what it does not | Two columns, from part 5 of [`narrative.md`](narrative.md) — see below | Applicability and materiality shown; the benchmark supports; one causal run, no rates | 1:30 |
| 16 | Rerun it | `git clone …`, `pip install -e .`, `physmap benchmark run`, `physmap stress-test lewis-reuse`; commit and exit status from [`reproduction/`](reproduction/README.md); "does not rerun OpenFOAM" | Anyone can check it | 0:45 |
| 17 | Close | "OOD asks whether inputs look familiar. PhysMAP asks whether the model's physics remains applicable, and whether an omitted mechanism materially changes the quantity of interest. NACA demonstrates applicability assurance; Lewis demonstrates causal materiality; Casper shows supporting evidence across surrogate architectures." | — | 0:30 |

**Slide 5, the text on it:**

> **The abstract reports** precision 1.00, recall 0.65, F1 0.79 (θ ≈ tol = 0.10).
>
> **Rebuilding the study showed:** the truth was a fitted correlation, not measurements · the
> construction ties the flag to the label · the original inputs no longer exist.
>
> **So:** not presented as experimental validation. What follows is a controlled test on one
> real experiment, with a smaller claim.

Say the thirty-second version in
[`historical-reconciliation.md`](historical-reconciliation.md). Do not put any new number on
this slide.

**Slide 15, the text on it:**

| Shown | Not shown |
|---|---|
| Applicability: all 45 NACA entrance predictions are outside the closure's supported region; 9 exceed the threshold, 36 are numerically acceptable | That numerical agreement alone makes a prediction credible |
| Materiality: identical OOD output with identical inputs; 0 with gravity off, up to 0.195 with gravity on | Any detection rate for the causal check — one run, no precision, recall or F1 |
| Lewis: control within 0.06 %; 17–18 % off the measurement downstream | A θ — it is unlocked |
| The measurement sides with the gravity-on CFD downstream | That materiality predicts error in general — here it is partly built in |
| Casper: three model types, each 4 of 8 that only PhysMAP flags; Dirker a second home baseline | That every benchmark count shows a failure deployment created — Jin and Velazquez are wrong almost everywhere |
| All of it reruns from a clean clone | That PhysMAP beats OOD detection in general; a pooled rate; anything about NVIDIA PhysicsNeMo |

## Backup inventory

Separate from the main deck. Each is ready to pull up for a question.

| # | Backup slide | Content and source | Answers |
|---|---|---|---|
| B1 | Specificity: the operating point between training runs | Designs A and A3: the detector warns at all 9 comparable stations, gravity off and on alike; materiality unchanged. Facts sheet §5; the command's SECONDARY block | "Isn't the OOD detector just quiet because you put 35A in training?" |
| B2 | The lower operating percentiles | Sweep p50 6/9 … p99 0/9, identical in both states; in-sample alarm rates; why p75 fires downstream. Facts sheet §5; `design_M_low_pct_mechanism.json` | Hostile question 13 |
| B3 | How the surrogate's error splits | Missing buoyancy × base-model gap × fit error, per station. Facts sheet §6 | Hostile questions 10 and 14 |
| B4 | Which results depend on a threshold | The command's THRESHOLDS section, as printed | Hostile question 12 |
| B5 | Pre-declared | The three criteria and the commit that preceded the results. `PREDECLARE_design_M_matched.md` | Hostile question 19 |
| B6 | The physical case and the CFD model | Lewis 35A geometry, flux, properties, Nu reduction; variable-property OpenFOAM, 2.5 d unheated entry. Facts sheet §2 | "What exactly did you simulate?" |
| B7 | Mesh, iterations, energy closure | Grid pair; the recorded iteration check; the two energy references; the two extraction paths. Facts sheet §7–8 | Hostile question 14 |
| B8 | The training runs | 13 runs: Re, Pr, iterations, energy closure, residual. Facts sheet §8 | "How good is the training data?" |
| B9 | The surrogate and the detector | GP recipe; leave-one-run-out; the benchmark's detector, unchanged; percentiles. `docs/findings/lewis-ood-head-to-head.md` | Hostile questions 3 and 19 |
| B10 | What "matched" means | Only `constant/g` differs; recursive diff; 3000 iterations each. The command's MATCHED ABLATION block | Hostile question 7 |
| B11 | Why 35A, and why not the other Lewis runs | Only run printed as numbers; no independent eligibility rule. `protocols/protocol.json`; `data/lewis1992/flow_regime_eligibility.json` | Hostile questions 16 and 20 |
| B12 | The reconstruction, in detail | Correlation-referenced truth; E = d − m(1 + d) + ε; the known-results declaration. [`historical-reconciliation.md`](historical-reconciliation.md) | Hostile question 11 |
| B13 | The seven vehicles, in full | `bench_2_seven_vehicles`: rows, licence basis, data quality, outcome labels. Facts sheet §9 | Hostile questions 18 and 22; licences |
| B19 | The detector counts, per dataset | `bench_3_what_physmap_adds`: wrong predictions only PhysMAP flags, and accurate ones it flags anyway, at percentile 99 | "How many did it catch?" — per dataset, never pooled |
| B20 | The NACA data correction | Bank v0.4.1: the original NACA row came from an automated read found invalid; replaced by the two-reader read; the original kept for audit. [`data/naca/CORRECTION_v0_4_1.md`](../../data/naca/CORRECTION_v0_4_1.md) | Hostile question 28 |
| B14 | The reproduction record | Commit, environment, exit status, bank comparison. [`reproduction/README.md`](reproduction/README.md) | Hostile question 21 |
| B15 | The two screened-out cases | Conjugate heat transfer, blood pump: `physmap screen …` returns NOT APPLICABLE, marked declarative — stated preconditions, not measured results | "What about the negatives in the abstract?" |
| B16 | The stations Lewis disowns | x/D 0.31 and 0.85 (axial wall conduction), 159.33 (suspect); shown hollow, left out of every summary | "What is the +63.0 %?" |
| B18 | The kind of model | `physmap benchmark architectures --banked`: per vehicle, which model types pass the home-accuracy check, and what each leaves for PhysMAP | "Does it work with any model?" — [claims ledger B9](claims-ledger.md) |
| B17 | How the guardrail combines its checks | At setup, each bounded variable is classed visible, partly visible or hidden from the surrogate's inputs. Closure check fires on a hidden one → reject; partly visible → calibrated blend or uncertain; otherwise the OOD detectors decide. The README's "Using the guardrail" | Hostile questions 23 and 24 |
