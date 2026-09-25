# The talk, as a story

Five parts, around two things PhysMAP does. **Applicability assurance** (part 2, NACA x/D):
is the physics the model relies on still applicable here? **Causal materiality** (part 3,
Lewis 35A, the main controlled demonstration): does a mechanism the model left out materially
change the quantity of interest? The seven-vehicle benchmark (part 4) is supporting evidence,
led by Casper. Each part says what to claim, what backs it, and which figure carries it. Every
number here is in [`facts-sheet.md`](facts-sheet.md); every headline sentence, with its limits,
is in [`claims-ledger.md`](claims-ledger.md).

---

## 1. What an input-based OOD guardrail asks — and what it cannot

A surrogate is fast because it learned from a set of runs. The usual guardrail asks one
question: **do this prediction's inputs look like the training inputs?** Distance to the
training data and Gaussian-process variance are two ways of asking it. It is a good question,
and these detectors answer it well.

But it is a question about inputs. A surrogate can be used where its inputs look ordinary and
the physics has changed — because what changed was never an input. PhysMAP asks two other
questions: **does the physics the model relies on still apply here**, and **does a mechanism
the model left out materially change the answer?**

> **Say:** "OOD asks whether the inputs look familiar. PhysMAP asks whether the model's physics
> still applies, and whether an omitted mechanism changes the answer."

---

## 2. Applicability assurance — the NACA x/D entrance region

A surrogate leans on physics relations — closures, such as a heat-transfer correlation — and
each closure is validated only over a tested range of certain variables. **PhysMAP reads those
variables from the data even when the surrogate never saw them, tests them against the
closure's validated range, and knows at setup which of them the OOD detectors can see.**

**The case** ([figure](figures/README.md#the-xd-entrance-region-closure-validity-fires-both-input-based-detectors-silent)).
The prediction comes from gnielinski-1976, a correlation for fully developed flow that uses
only Re and Pr, validated from x/D = 10. Near a pipe's inlet, x/D governs the heat transfer —
and neither the surrogate nor an input-based OOD detector sees it. On NACA TN-1451's Fig 10
(two-reader digitisation), against the measurement, at the numerical-error threshold (17.5 %):

- Gnielinski is within the threshold on 40 of 40 fully developed points.
- It exceeds the threshold on 9 of 45 entrance points, all at x/D ≤ 5, the largest 38 % at the
  inlet.
- PhysMAP identifies all 45 entrance predictions as outside the closure's supported
  applicability region. The two input-based detectors — novelty density and GP variance — fire
  on 0: they cannot see x/D.
- The other 36 are numerically acceptable, but not physically supported by that closure.

**Numerical agreement does not by itself establish that a prediction is credibly supported.**
That is what applicability assurance adds: it says when a prediction rests on physics outside
its supported region, whether or not the number happens to land close.

> **Say:** "Nine of these entrance predictions are wrong. All forty-five are outside what the
> correlation supports — and the thirty-six that happen to be close are close by luck, not by
> physics."

---

## 3. Causal materiality — Lewis 35A, a controlled model-reuse stress test

Applicability asks whether a variable has left a closure's tested range. This asks something
else, with different evidence:

> **Is a physical mechanism that applies here outside the range the surrogate was calibrated
> on — and does it change the quantity of interest by a material amount?**

- **Outside calibration.** The mechanism is named, with the dimensionless group that measures
  it. For buoyancy that is the Richardson number, Ri. The surrogate's calibrated window comes
  from its training data. This training never saw buoyancy, so the window is Ri = 0 exactly.
  Lewis Test 35A with gravity on has Ri = 0.29.
- **Material.** Materiality is measured by ablation. Run the same case with the mechanism and
  without it, change nothing else, and compare the quantity of interest:
  materiality = 1 − Nu(gravity off) / Nu(gravity on). A mechanism can be out of range and still
  not matter. Then PhysMAP stays quiet.

| Result | Question | Command |
|---|---|---|
| NACA x/D (part 2) | Is the physics the prediction relies on applicable here? | `python examples/naca_entrance_region.py` |
| Lewis 35A stress test (this part) | When a mechanism the surrogate never saw becomes active, does it matter to the answer? | `physmap stress-test lewis-reuse` |

Neither is evidence for the other.

**The framing, word for word:**

> The surrogate was trained for forced convection, where gravity did not vary and was not an
> input. It was then reused in vertical heated flow, where buoyancy became material. A
> mixed-convection surrogate designed for this regime should include Richardson number, Grashof
> number, or equivalent physical information.

**The claim, word for word:**

> PhysMAP detects when model reuse activates a physically relevant mechanism outside the
> surrogate's observable input space. An input-only OOD detector cannot identify a change absent
> from its input contract.

**The experiment.** Lewis (1992), Test 35A: water flowing up a heated vertical tube of
0.0119 m bore, heated over 1.900 m at uniform wall flux, laminar, with buoyancy aiding the flow.
It is the one run in the thesis whose local Nu is printed as numbers. **It is one run.** Its 12
thermocouple stations are positions along one tube, not 12 cases, and Lewis disowns three of
them.

**The setup** ([input contract](figures/README.md#input-contract-what-the-surrogate-and-the-ood-detector-see)).
A forced-convection surrogate — a Gaussian process on Re, Pr and x/D — trained on 13
gravity-off CFD runs, one of them at 35A's own operating point. The input-based OOD detector is
the seven-vehicle benchmark's own, unchanged, given the same three inputs. Neither sees gravity,
Ri, Gr or heat flux. **Every visible deployment input exactly matches a training input.** There
is no input gap for the detector to notice — by design.

**Two physical states, the same visible inputs**
([by position](figures/README.md#gravity-off-control-against-gravity-on-measurement-by-position),
[summary table](figures/README.md#the-control-table)):

| | surrogate error | input-based OOD detector | PhysMAP materiality |
|---|---|---|---|
| **Gravity off** — CFD, the control | within 0.06 % | quiet | 0 |
| **Gravity on** — Lewis's measurement | 17–18 % at x/D 67.55, 101.69, 135.84 | the same scores, every station, every percentile | up to 0.195, growing down the tube |

The OOD scores do not move at all
([figure](figures/README.md#the-input-based-ood-scores-are-identical-in-both-gravity-states)):
the largest difference between the two states, over every score and percentile, is 0.

> **The line to land:** "Same inputs, same OOD scores. Different physics, different
> materiality — and where materiality is largest, the surrogate is 17–18 % off."

**No threshold is needed for the headline**
([figure](figures/README.md#continuous-materiality-by-position-and-what-θ-would-change)).
Identical scores, and materiality of 0 against up to 0.195, are values. θ is unlocked. If a flag
is shown, it is at the illustrative θ = 0.10 — the original study's value — and the slide says
so. At 0.10 three comparable stations would flag; at 0.05, five; at 0.20, none.

**Backup — designs A and A3, specificity.** When 35A's operating point sits *between* training
runs instead of on one, the detector warns at all 9 comparable stations — with gravity off,
where the surrogate is right, and with gravity on, where it is wrong — identically. PhysMAP's
materiality does not change. That is specificity, not a detection failure.

**Pre-declared.** Design M and its three success criteria were committed before any of its
output existed. All three were met; the second at the illustrative θ.

**Reproducible.** `physmap stress-test lewis-reuse` recomputes it from a clean clone in a few
minutes and checks itself against the committed bank. It reproduces the analysis from committed
CFD-derived profiles. **It does not rerun OpenFOAM.**

---

## 4. Supporting evidence — seven published datasets

The seven-vehicle benchmark asks, per dataset: which wrong predictions does PhysMAP flag that
the input-based detectors (distance-to-training and GP variance) miss — and was the surrogate
accurate at home, so that deployment is what created the failure? It is supporting evidence,
not the headline: counts are rows of each dataset, not independent cases, never pooled, and
digitised from publications.

**Casper leads** ([home baseline](figures/README.md#the-home-baseline-behind-each-count)).
Hypersonic transition; the cause, freestream noise, is not a surrogate input. Its surrogate is
wrong on 6 of 159 home rows held out (4%), and on 8 of 8 deployed (100%). Three model types —
a Gaussian process, a DeepONet and gradient-boosted trees — each pass the same home-accuracy
check, and each leaves 4 of 8 deployment errors that only PhysMAP flags.

**Dirker supports it.** Water in a horizontal tube; the cause, buoyancy, is partly visible to
the inputs. Wrong on 0 of 31 home rows held out, on 11 of 60 deployed (18%); PhysMAP flags 2 of
those 11 that the detectors miss.

**The full matrix**, bank v0.4.1
([detector counts](figures/README.md#what-physmap-adds-to-input-based-ood-detection)). Home
error is labelled by how it was obtained: in-sample, then held out by refitting without each
row, where the surrogate was fitted to the home rows; held out by construction where it is a
published correlation.

| Dataset | Detectors see the cause? | Home error: how obtained | Home wrong | Deployed wrong | Wrong, flagged only by PhysMAP | Accurate, flagged anyway | Limitation |
|---|---|---|---|---|---|---|---|
| Casper · hypersonic transition | no | fitted; held out by refit (in-sample 2 of 159) | 6 of 159 (4%) | 8 of 8 (100%) | 4 of 8 | 0 | — |
| Dirker · water, horizontal tube | partly | fitted; held out by refit (in-sample 0 of 31) | 0 of 31 (0%) | 11 of 60 (18%) | 2 of 11 | 16 | the cause is partly visible |
| NACA · pipe entrance | no | published correlation; 40 of 40 inside its range | 0 of 40 (0%) | 9 of 45 (20%) | 9 of 9 | 19 | the part 2 case, same data — not separate evidence |
| Jin · sCO2, vertical tube | no | published correlation; 11 of 17 inside its range | 17 of 17 (100%) | 26 of 27 (96%) | 15 of 26 | 0 | wrong almost everywhere: no home baseline |
| Velazquez · sCO2 property variation | partly | published correlation; 197 of 393 inside its range | 386 of 393 (98%) | 67 of 67 (100%) | 18 of 67 | 0 | wrong almost everywhere: no home baseline |
| Marineau · hypersonic transition | yes | fitted; held out by refit (in-sample 0 of 9) | 5 of 9 (56%) | 6 of 6 (100%) | 0 of 6 | 0 | the control; nine home rows are too few |
| Forrest · rectangular channel | yes | published correlation | 0 of 1 | 4 of 4 (100%) | not tested | — | one training row; triage-grade values |

- **Where it helps, with a home baseline:** Casper and Dirker — and NACA, which is the part 2
  case itself.
- **Where the reading stops:** Jin and Velazquez keep their counts — 15 and 18 wrong predictions
  only PhysMAP flags — but their correlations are wrong almost everywhere, at home too, so the
  counts cannot show that deployment created the failure.
- **Where it adds nothing:** Marineau, where the cause is a surrogate input and the detectors
  see it.
- **Accurate predictions flagged anyway:** PhysMAP flags every prediction outside a closure's
  supported region, accurate or not — 19 for NACA, 16 for Dirker. Read as detection they are
  false alarms; read as applicability assurance, they are predictions the closure does not
  support.

No gate decides a vehicle's reading: the counts and rates are the evidence, and each vehicle's
interpretation is written prose, printed by `physmap benchmark report`. The bank is v0.4.1: it
corrects the NACA source data. The original bank's NACA row came from an automated read of the
figure later found invalid; that bank is kept unchanged for audit, not as evidence
([`data/naca/CORRECTION_v0_4_1.md`](../../data/naca/CORRECTION_v0_4_1.md)).

---

## 5. What the evidence establishes — and what it does not

**Established — applicability assurance (part 2):**

1. In the NACA entrance region, Gnielinski is within the numerical-error threshold on 40 of 40
   fully developed points and exceeds it on 9 of 45 entrance points, all at x/D ≤ 5.
2. PhysMAP identifies all 45 entrance predictions as outside the closure's supported region;
   the input-based detectors fire on 0. The 36 numerically acceptable ones are not physically
   supported by that closure.

**Established — causal materiality (part 3), for this construction:**

3. With every visible input inside the training data, the input-based detector's output is
   identical with gravity off and gravity on. Its inputs are identical, so it must be; the
   shipped detector shows it.
4. PhysMAP's materiality separates the two states: 0 with gravity off, up to 0.195 with gravity
   on, growing down the tube.
5. On the control the surrogate is accurate, within 0.06 %. Against the measurement it is
   17–18 % off downstream.
6. Downstream, the measurement sides with the gravity-on CFD — within 1.6–6.6 % — not the
   gravity-off CFD. The buoyancy effect that materiality measures is present in the
   experiment.

**Established — supporting evidence (part 4):**

7. On Casper, three model types each pass the home-accuracy check, and each leaves 4 of 8
   deployment errors that only PhysMAP flags. Dirker adds a second dataset with a home baseline.
8. Where the cause is a surrogate input, PhysMAP adds nothing: 0 of 6 for Marineau.
9. All of it reruns from a clean clone.

**Not established:**

1. **That PhysMAP beats OOD detection in general.** It adds nothing when the cause is an input,
   and its gain is counted per dataset, in digitised data, never pooled.
2. **That every benchmark count shows a failure deployment created.** Jin and Velazquez are
   wrong almost everywhere; Marineau and Forrest have too few home rows.
3. **Any detection rate for the causal check.** Lewis is one run; its stations are not cases; no
   precision, recall or F1. There is no independent evaluation set yet.
4. **A θ.** It is unlocked, so nothing in part 3 is a categorical verdict.
5. **That materiality predicts surrogate error in general.** Here the surrogate and the
   materiality both rest on the gravity-off CFD, so their agreement is partly built in. What the
   test shows is which output moves when the physics moves.
6. **That PhysMAP sees every error.** At x/D 2.45 and 16.32 the Lewis surrogate is off because
   the base CFD differs from the experiment there. PhysMAP checks the mechanisms it is given.
7. **That materiality cuts the flags on accurate predictions in part 4.** That is what it is
   for; it is not shown yet.
8. **Generality of part 3.** One run, one geometry, one mechanism, laminar aiding flow.
9. **The abstract's precision, recall and F1** — see
   [`historical-reconciliation.md`](historical-reconciliation.md).
10. **Anything about NVIDIA PhysicsNeMo** or any other product. Neither of its checks was run.

> **Close:** "OOD asks whether inputs look familiar. PhysMAP asks whether the model's physics
> remains applicable, and whether an omitted mechanism materially changes the quantity of
> interest. NACA demonstrates applicability assurance; Lewis demonstrates causal materiality;
> Casper shows supporting evidence across surrogate architectures."
