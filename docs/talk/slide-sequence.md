# Slide sequence

Sixteen main slides, about eighteen minutes, then the backup inventory. Figures are in
[`figures/`](figures/README.md); notes for each technical figure are in
[`speaker-notes.md`](speaker-notes.md). The live demo — when to start `physmap benchmark run`,
what to do if it breaks — is in [`../talk-runbook.md`](../talk-runbook.md).

## Main sequence

| # | Slide title | On the slide | The point | Time |
|---|---|---|---|---|
| 1 | PhysMAP: a causal, materiality-weighted in-calibration check for AI surrogates | Title, author, NAFEMS Multiphysics 2026 | — | 0:30 |
| 2 | What an input-based guardrail asks | Text: "Do this prediction's inputs look like the training inputs?" Distance to training; GP variance | A good question, about inputs only | 1:30 |
| 3 | What PhysMAP asks | Text: "Is an applicable mechanism outside calibration — and does it materially change the answer?" Materiality = 1 − QoI(mechanism off) / QoI(mechanism on), by matched ablation | A different question; complementary, not a replacement | 1:30 |
| 4 | Two results, kept apart | Two boxes: observability (`physmap benchmark run`) · causal materiality (`physmap stress-test lewis-reuse`) | Neither is evidence for the other | 0:45 |
| 5 | The x/D entrance region | `bench_1_naca_entrance` | Closure check 45 of 45; input-based detectors 0 | 1:30 |
| 6 | Seven vehicles, one question | `bench_2_seven_vehicles` | Observability classes, not rates; Forrest shown as weak | 1:30 |
| 7 | What changed since the abstract | Text only — see below | The abstract's numbers are named and explained, not replaced | 1:30 |
| 8 | Lewis 35A: a controlled model-reuse stress test | The framing and the claim, word for word; "One run. Its stations are not cases." | What the test is, and what it is not | 1:00 |
| 9 | The input contract | `lewis_1_input_contract` | Same three inputs; gravity is not one; every deployment input is a training input | 1:30 |
| 10 | Same inputs, two physical states | `lewis_2_control_vs_gravity_on` | Control within 0.06 %; measurement 17–18 % off; OOD unchanged; materiality up to 0.195 | 2:00 |
| 11 | The OOD scores do not move | `lewis_3_ood_identical` | Largest difference 0 — the detector doing its job | 1:00 |
| 12 | Materiality is continuous | `lewis_4_materiality` | The headline needs no θ; 0.10 is illustrative only | 1:30 |
| 13 | In one table | `lewis_5_control_table` | "Same inputs, same OOD scores. Different physics, different materiality." | 0:45 |
| 14 | What this shows — and what it does not | Two columns, from part 5 of [`narrative.md`](narrative.md) | One run; no rates; coupling disclosed; generality unproven | 1:30 |
| 15 | Rerun it | `git clone …`, `pip install -e .`, `physmap stress-test lewis-reuse`; commit and exit status from [`reproduction/`](reproduction/README.md); "does not rerun OpenFOAM" | Anyone can check it | 0:45 |
| 16 | Close | "A mixed-convection surrogate built correctly should include Ri, Gr or an equivalent. PhysMAP asks whether a mechanism the model never saw has become material." | — | 0:30 |

**Slide 7, the text on it:**

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

**Slide 14, the text on it:**

| Shown, for this construction | Not shown |
|---|---|
| Identical OOD output with identical inputs | Any detection rate — one run, no precision, recall or F1 |
| Materiality 0 with gravity off, up to 0.195 with gravity on | A θ — it is unlocked |
| Control within 0.06 %; 17–18 % off the measurement downstream | That materiality predicts error in general — here it is partly built in |
| The measurement sides with the gravity-on CFD downstream | That PhysMAP sees every error — not the base-model ones |
| x/D: closure check 45 of 45, input-based detectors 0 | Generality — one run, one geometry, one mechanism |
| All of it reruns from a clean clone | Anything about NVIDIA PhysicsNeMo |

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
| B13 | The seven vehicles, in full | Rows, licence basis, data quality, outcome definitions. Facts sheet §9 | Hostile question 18; licences |
| B14 | The reproduction record | Commit, environment, exit status, bank comparison. [`reproduction/README.md`](reproduction/README.md) | Hostile question 21 |
| B15 | The two screened-out cases | Conjugate heat transfer, blood pump: `physmap screen …` returns NOT APPLICABLE, marked declarative — stated preconditions, not measured results | "What about the negatives in the abstract?" |
| B16 | The stations Lewis disowns | x/D 0.31 and 0.85 (axial wall conduction), 159.33 (suspect); shown hollow, left out of every summary | "What is the +63.0 %?" |
