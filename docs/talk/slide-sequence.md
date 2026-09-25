# Slide sequence

Thirteen main slides, about twenty minutes, then the backup inventory. The talk is built on two
things PhysMAP does: **applicability assurance** (slide 4, NACA x/D) and **causal materiality**
(slides 5–9, Lewis 35A, the main controlled demonstration). Slides 10–11 are supporting evidence
from the seven-vehicle benchmark, led by Casper. Nothing depends on a live computation: slide 13
shows the public commands and their captured, verified output. The live-demo runbook,
[`../talk-runbook.md`](../talk-runbook.md), is contingency only. Figures are in
[`figures/`](figures/README.md); notes for each slide are in [`speaker-notes.md`](speaker-notes.md).

## Main sequence

| # | Slide title | On the slide | The point | Time |
|---|---|---|---|---|
| 1 | PhysMAP: a causal, materiality-weighted in-calibration check for AI surrogates | The accepted title, with a plain-language subtitle: "Physics-aware guardrails: checking whether a surrogate's physics still applies — not only whether its inputs look familiar." Author, NAFEMS Multiphysics 2026 | — | 0:30 |
| 2 | What input-based OOD asks | Text: "Do this prediction's inputs look like the training inputs?" Distance to training; GP variance | A good question, about inputs only. Say the abstract sentence here, once — see the notes | 1:30 |
| 3 | What PhysMAP adds | Two boxes. **Applicability assurance:** does the physics the model relies on still apply here? **Causal materiality:** does a mechanism the model left out materially change the answer? It keeps the OOD detectors | Two questions an input-based detector cannot ask | 1:15 |
| 4 | Applicability assurance: the NACA entrance region | `bench_1_naca_entrance` | Gnielinski within the numerical-error threshold on 40 of 40 home points; exceeds it on 9 of 45 entrance points; PhysMAP places all 45 outside the closure's supported region. The other 36 are numerically close, but that agreement is not supported by validation evidence for this region. Input-based detectors: 0 | 1:45 |
| 5 | Causal materiality and matched ablation | Text: "Is an applicable mechanism outside calibration — and does it materially change the quantity of interest?" Materiality = 1 − QoI(mechanism off) / QoI(mechanism on), by matched ablation: same mesh, same conditions, the one mechanism removed | A different question from applicability, with different evidence | 1:15 |
| 6 | Lewis 35A: a controlled model-reuse stress test | The framing and the claim, word for word; "One run, nominally laminar, buoyancy aiding. Its stations are not cases." "It replaces the earlier metrics as the main causal demonstration." | What the test is, and what it is not | 1:00 |
| 7 | The input contract | `lewis_1_input_contract` | Same three inputs; gravity is not one; every deployment input is a training input | 1:15 |
| 8 | Same inputs, two physical states | `lewis_2_control_vs_gravity_on` | Control within 0.06 %; the surrogate is 17–18 % below the measurement downstream. The OOD scores are identical with gravity on and off because the visible inputs are identical — quiet in both at the reference percentile, 99. Materiality 0 with gravity off, up to 0.195 with gravity on | 2:15 |
| 9 | Materiality is continuous | `lewis_4_materiality` | The headline needs no θ. θ = 0.10 is labelled illustrative, and unnecessary for the headline | 1:15 |
| 10 | Supporting evidence: Casper, across three model architectures | Text: a small table — Gaussian process, DeepONet, gradient-boosted trees; each passes the same home-accuracy check; each leaves 4 of 8 deployment errors only PhysMAP flags. Home: 6 of 159 wrong, held out; deployed: 8 of 8 | The result does not depend on the kind of surrogate, where that can be tested | 1:15 |
| 11 | Seven datasets: the supporting-evidence portfolio | `bench_4_home_baseline`, with its short annotations: Casper — strongest support across three model types; Dirker — additional support; NACA — the applicability case, not separate evidence; Jin, Velazquez — no credible home baseline; Marineau — cause visible to the surrogate; PhysMAP adds nothing; Forrest — triage-only | Every dataset on one chart, with which ones have credible home baselines. The dense seven-row table is backup B21 | 1:45 |
| 12 | What the evidence shows — and what it does not | Three rows, Shown and Boundary — see below | Restraint: what each result shows, and where it stops. The complete limitations table is backup B25 | 1:30 |
| 13 | Reproduce it — and the close | The public commands, the repository link, the captured output's key lines from [`reproduction/`](reproduction/README.md) (commit, exit status, bank comparison); then the final line | Anyone can check it; the conclusion | 1:15 |

**Slide 12, the text on it:**

| Shown | Boundary |
|---|---|
| NACA: applicability outside the supported region | Numerical agreement alone does not establish credibility |
| Lewis: identical OOD scores, different materiality and error | One run; no detection rate or fixed θ |
| Casper and Dirker: supporting benchmark evidence | No general superiority or pooled performance claim |

One line under the table: "The accepted abstract's precision, recall and F1 are not presented
as experimental validation." No numbers on the slide.

**Slide 13, the final line, word for word:**

> OOD asks whether inputs look familiar. PhysMAP asks whether the model's physics remains
> applicable, and whether an omitted mechanism materially changes the quantity of interest.
> NACA demonstrates applicability assurance; Lewis demonstrates causal materiality; Casper shows
> supporting evidence across surrogate architectures.

The historical metrics appear on no main slide. The complete reconciliation — the original
numbers and why their interpretation is withdrawn — is backup B22.

## Backup inventory

Separate from the main deck. Each is ready to pull up for a question.

| # | Backup slide | Content and source | Answers |
|---|---|---|---|
| B1 | Specificity: the operating point between training runs | Designs A and A3: the detector warns at all 9 comparable stations, gravity off and on alike; materiality unchanged. Facts sheet §5; the command's SECONDARY block | "Isn't the OOD detector just quiet at 99 because you put 35A in training?" |
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
| B21 | The full seven-row table | The supporting-evidence table: detector counts, home provenance, home and deployment error rates, and each dataset's limitation. [`narrative.md`](narrative.md) part 4 | "Show me the numbers behind the chart" |
| B22 | What changed since the abstract | The accepted abstract reports precision 1.00, recall 0.65, F1 0.79 (θ ≈ tol = 0.10). Rebuilding the study showed: the truth was a fitted correlation, not measurements · the construction ties the flag to the label · the original inputs no longer exist. So: not presented as experimental validation. [`historical-reconciliation.md`](historical-reconciliation.md) | Hostile questions 11 and 20; "What happened to the abstract's numbers?" |
| B23 | The OOD scores are identical | `lewis_3_ood_identical`: each score, gravity off against gravity on, every station, on the diagonal; largest difference 0 | "Show me the OOD scores" |
| B24 | In one table | `lewis_5_control_table`: "Same inputs, same OOD scores. Different physics, different materiality." | A one-table recap, if time allows |
| B25 | The complete limitations table | Applicability: all 45 NACA entrance predictions are outside the closure's supported region; 9 exceed the threshold; the 36 numerically close ones lack validation evidence for this region — not shown: That numerical agreement alone makes a prediction credible · Materiality: the OOD scores are identical in both states because the inputs are identical; materiality 0 with gravity off, up to 0.195 with gravity on — not shown: Any detection rate for the causal check — one run, no rates · Lewis: control within 0.06 %; the surrogate 17–18 % below the measurement downstream — not shown: A θ — it is unlocked · The measurement sides with the gravity-on CFD downstream — not shown: That materiality predicts error in general — here it is partly built in · Casper: three model types, each 4 of 8 that only PhysMAP flags; Dirker adds support — not shown: That every benchmark dataset shows a failure deployment created · All of it reproduces from a public clean clone — not shown: The accepted abstract's precision, recall and F1 — they are not presented as experimental validation. Nor general superiority over OOD detection, a pooled rate, or anything about NVIDIA PhysicsNeMo | "What exactly are you not claiming?" |
