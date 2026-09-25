# Slide sequence

Sixteen main slides plus 5b, about twenty minutes, then the backup inventory. Slides 3–5b are the
point of PhysMAP and what sets it apart; slides 7–13 are the separate, causal question.
Figures are in [`figures/`](figures/README.md); notes for each technical figure are in
[`speaker-notes.md`](speaker-notes.md). The live demo — when to start `physmap benchmark run`,
what to do if it breaks — is in [`../talk-runbook.md`](../talk-runbook.md).

## Main sequence

| # | Slide title | On the slide | The point | Time |
|---|---|---|---|---|
| 1 | PhysMAP: a causal, materiality-weighted in-calibration check for AI surrogates | Title, author, NAFEMS Multiphysics 2026 | — | 0:30 |
| 2 | What an input-based guardrail asks | Text: "Do this prediction's inputs look like the training inputs?" Distance to training; GP variance | A good question, about inputs only | 1:30 |
| 3 | What PhysMAP adds | Text: "It reads the variables the surrogate never saw, tests the physics relation behind it against its validated range, and knows which of those variables the OOD detectors can see." It keeps the OOD detectors, and overrides them only where they are blind | The check an input-based detector cannot make | 1:15 |
| 4 | The x/D entrance region | `bench_1_naca_entrance` | Closure check 45 of 45; input-based detectors 0. The correlation is right at home (0 of 40) and fails near the inlet (9 of 45), so 36 flags land on right predictions | 1:15 |
| 5 | What PhysMAP adds, across seven datasets | `bench_3_what_physmap_adds` | Where the cause is hidden from the inputs, it flags wrong predictions the OOD detectors miss; where the cause is an input, it adds nothing; the cost is false alarms | 2:00 |
| 5b | Is the surrogate right at home? | `bench_4_home_baseline` | A count shows a blind spot deployment created only where the surrogate was right at home: yes for Casper and Dirker; not for NACA, Jin or Velazquez, whose counts stand as counts | 1:15 |
| 6 | What changed since the abstract | Text only — see below | The abstract's numbers are named and explained, not replaced | 1:15 |
| 7 | A separate question: does an unseen mechanism matter? | Text: "Is an applicable mechanism outside calibration — and does it materially change the answer?" Materiality = 1 − QoI(mechanism off) / QoI(mechanism on), by matched ablation. Two boxes: the benchmark (`physmap benchmark run`) · causal materiality (`physmap stress-test lewis-reuse`) | Different question, different evidence; neither is evidence for the other | 1:15 |
| 8 | Lewis 35A: a controlled model-reuse stress test | The framing and the claim, word for word; "One run. Its stations are not cases." | What the test is, and what it is not | 0:45 |
| 9 | The input contract | `lewis_1_input_contract` | Same three inputs; gravity is not one; every deployment input is a training input | 1:15 |
| 10 | Same inputs, two physical states | `lewis_2_control_vs_gravity_on` | Control within 0.06 %; measurement 17–18 % off; OOD unchanged; materiality up to 0.195 | 1:45 |
| 11 | The OOD scores do not move | `lewis_3_ood_identical` | Largest difference 0 — the detector doing its job | 0:45 |
| 12 | Materiality is continuous | `lewis_4_materiality` | The headline needs no θ; 0.10 is illustrative only | 1:15 |
| 13 | In one table | `lewis_5_control_table` | "Same inputs, same OOD scores. Different physics, different materiality." | 0:30 |
| 14 | What this shows — and what it does not | Two columns, from part 4 of [`narrative.md`](narrative.md) — see below | Where it helps and what it costs; one causal run, no rates | 1:30 |
| 15 | Rerun it | `git clone …`, `pip install -e .`, `physmap benchmark run`, `physmap stress-test lewis-reuse`; commit and exit status from [`reproduction/`](reproduction/README.md); "does not rerun OpenFOAM" | Anyone can check it | 0:45 |
| 16 | Close | "An input-based OOD detector tells you whether the inputs are familiar. PhysMAP tells you when the physics behind a surrogate has left its tested range in a variable the surrogate never saw — and, separately, whether an unseen mechanism has become material." | — | 0:30 |

**Slide 6, the text on it:**

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

| Shown | Not shown |
|---|---|
| Where the cause is hidden from the inputs, PhysMAP catches what the OOD detectors miss — 20 of 20 at the pipe entrance | That PhysMAP beats OOD detection in general — it adds nothing when the cause is an input |
| The cost: false alarms — 24 for NACA, 16 for Dirker | A rate pooled across datasets |
| Lewis: identical OOD output with identical inputs; materiality 0 with gravity off, up to 0.195 with gravity on | Any detection rate for the causal check — one run, no precision, recall or F1 |
| Lewis: control within 0.06 %; 17–18 % off the measurement downstream | A θ — it is unlocked |
| The measurement sides with the gravity-on CFD downstream | That materiality predicts error in general — here it is partly built in |
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
| B13 | The seven vehicles, in full | `bench_2_seven_vehicles`: rows, licence basis, data quality, outcome labels. Facts sheet §9 | Hostile questions 18 and 22; licences |
| B14 | The reproduction record | Commit, environment, exit status, bank comparison. [`reproduction/README.md`](reproduction/README.md) | Hostile question 21 |
| B15 | The two screened-out cases | Conjugate heat transfer, blood pump: `physmap screen …` returns NOT APPLICABLE, marked declarative — stated preconditions, not measured results | "What about the negatives in the abstract?" |
| B16 | The stations Lewis disowns | x/D 0.31 and 0.85 (axial wall conduction), 159.33 (suspect); shown hollow, left out of every summary | "What is the +63.0 %?" |
| B18 | The kind of model | `physmap benchmark architectures --banked`: Casper, three model types pass the gate, each 4 of 8; NACA, Jin, Velazquez, none passes | "Does it work with any model?" — [claims ledger B9](claims-ledger.md) |
| B17 | How the guardrail combines its checks | At setup, each bounded variable is classed visible, partly visible or hidden from the surrogate's inputs. Closure check fires on a hidden one → reject; partly visible → calibrated blend or uncertain; otherwise the OOD detectors decide. The README's "Using the guardrail" | Hostile questions 23 and 24 |
