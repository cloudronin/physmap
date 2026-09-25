# The talk, as a story

Four parts. Part 2 is the point of PhysMAP and what sets it apart; part 3 is a separate,
causal question with its own evidence. Each part says what to claim, what backs it, and which
figure carries it. Every number here is in [`facts-sheet.md`](facts-sheet.md); every headline
sentence, with its limits, is in [`claims-ledger.md`](claims-ledger.md).

---

## 1. What input-based OOD guardrails can and cannot see

A surrogate is fast because it learned from a set of runs. The usual guardrail asks one
question: **do this prediction's inputs look like the training inputs?** Distance to the
training data and Gaussian-process variance are two ways of asking it. It is a good question,
and these detectors answer it well.

But it is a question about inputs. A surrogate can be used where its inputs look ordinary and
the physics has changed — because what changed was never an input. Train a surrogate on the
fully developed part of a heated pipe and it never needs x/D, the distance from the entrance.
Ask it about the entrance region, where x/D is what matters, and its inputs look perfectly
familiar.

An input-based detector cannot report a change that is not in its inputs. That is not a flaw in
the detector. It is the edge of the question it asks.

> **Say:** "An input-based OOD detector tells you whether the inputs are familiar. It cannot
> tell you whether the physics is."

---

## 2. What PhysMAP adds — the point of it

A surrogate leans on physics relations — closures, such as a heat-transfer correlation — and
each closure is validated only over a tested range of certain variables. **PhysMAP reads those
variables from the data even when the surrogate never saw them, tests them against the
closure's validated range, and knows at setup which of them the OOD detectors can see.** It
keeps the OOD detectors, and overrides them only where they are structurally blind.

**The x/D entrance region**
([figure](figures/README.md#the-xd-entrance-region-closure-validity-fires-both-input-based-detectors-silent)).
The surrogate is trained on the fully developed pipe using Re and Pr, then asked about the
entrance. The closure it relies on, gnielinski-1976, is validated only from x/D = 10. On the 45
entrance points, PhysMAP's closure check fires on all 45. The two input-based detectors —
novelty density and GP variance — fire on 0. They are quiet because they cannot see x/D, not
because the points are safe.

**Seven published datasets, two domains**
([figure](figures/README.md#what-physmap-adds-to-input-based-ood-detection)). The benchmark
asks one question per dataset: which wrong predictions did the closure check catch that the
input-based detectors missed — and which right predictions did it flag anyway? At the default
setting (the 99th percentile):

| Dataset | Can the OOD detectors see the cause? | Wrong predictions caught only by PhysMAP | Right predictions flagged anyway |
|---|---|---|---|
| NACA · pipe entrance | no | 20 of 20 | 24 |
| Casper · hypersonic transition | no | 4 of 8 | 0 |
| Jin · sCO2, vertical tube | no | 15 of 26 | 0 |
| Velazquez · sCO2 property variation | partly | 18 of 67 | 0 |
| Dirker · water, horizontal tube | partly | 2 of 11 | 16 |
| Marineau · hypersonic transition | yes | 0 of 6 | 0 |
| Forrest · rectangular channel | yes | not tested: one training row | — |

- **Where it helps:** when the cause of failure is hidden from the surrogate's inputs. There it
  catches wrong predictions the OOD detectors miss entirely.
- **Where it doesn't:** when the cause is an input, the OOD detectors already see it and PhysMAP
  adds nothing. Marineau is the control that shows it.
- **The cost:** the closure check flags anything outside a closure's validated range, even when
  the surrogate happens to be right — 24 false alarms for NACA, 16 for Dirker.

> **The line to land:** "Where the cause of failure isn't one of the surrogate's inputs,
> PhysMAP catches what the OOD detectors can't — all 20 wrong predictions at the pipe entrance.
> Where the cause is an input, it adds nothing. And it costs false alarms."

What this is: a reproducible benchmark — `physmap benchmark run` recomputes all seven from a
clone, and `physmap benchmark report` prints these counts. What it is not: a rate pooled across
datasets, a claim that PhysMAP beats OOD detection in general, or evidence for causal
materiality. Counts are rows of each dataset, not independent cases, and the values are
digitised from publications. The full table with each dataset's licence basis is in backup.

---

## 3. A separate question: does a mechanism the surrogate never saw matter?

Part 2 asks whether a variable has left its tested range. This asks something else, with
different evidence:

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
| Seven-vehicle benchmark, x/D example (part 2) | Is the variable that breaks the surrogate visible to an input-based detector at all? | `physmap benchmark run` |
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

## 4. What the evidence establishes — and what it does not

**Established — what PhysMAP adds (part 2):**

1. Where the cause of failure is hidden from the surrogate's inputs, the closure check catches
   wrong predictions the input-based detectors miss: 20 of 20 for NACA, 4 of 8 for Casper,
   15 of 26 for Jin; where it is partly hidden, 18 of 67 for Velazquez and 2 of 11 for Dirker.
2. Where the cause is an input, it adds nothing: 0 of 6 for Marineau.
3. It costs false alarms: 24 for NACA, 16 for Dirker.
4. In the x/D example, the closure check fires on 45 of 45 entrance points and the input-based
   detectors on 0.

**Established — the separate causal question (part 3), for this construction:**

5. With every visible input inside the training data, the input-based detector's output is
   identical with gravity off and gravity on. Its inputs are identical, so it must be; the
   shipped detector shows it.
6. PhysMAP's materiality separates the two states: 0 with gravity off, up to 0.195 with gravity
   on, growing down the tube.
7. On the control the surrogate is accurate, within 0.06 %. Against the measurement it is
   17–18 % off downstream.
8. Downstream, the measurement sides with the gravity-on CFD — within 1.6–6.6 % — not the
   gravity-off CFD. The buoyancy effect that materiality measures is present in the
   experiment.
9. All of it reruns from a clean clone.

**Not established:**

1. **That PhysMAP beats OOD detection in general.** It adds nothing when the cause is an input,
   and its gain is counted per dataset, in digitised data, never pooled.
2. **Any detection rate for the causal check.** Lewis is one run; its stations are not cases; no
   precision, recall or F1. There is no independent evaluation set yet.
3. **A θ.** It is unlocked, so nothing in part 3 is a categorical verdict.
4. **That materiality predicts surrogate error in general.** Here the surrogate and the
   materiality both rest on the gravity-off CFD, so their agreement is partly built in. What the
   test shows is which output moves when the physics moves.
5. **That PhysMAP sees every error.** At x/D 2.45 and 16.32 the Lewis surrogate is off because
   the base CFD differs from the experiment there. PhysMAP checks the mechanisms it is given.
6. **That materiality cuts the false alarms of part 2.** That is what it is for; it is not shown
   yet.
7. **Generality of part 3.** One run, one geometry, one mechanism, laminar aiding flow.
8. **The abstract's precision, recall and F1** — see
   [`historical-reconciliation.md`](historical-reconciliation.md).
9. **Anything about NVIDIA PhysicsNeMo** or any other product. Neither of its checks was run.

> **Close:** "An input-based OOD detector tells you whether the inputs are familiar. PhysMAP
> tells you when the physics behind a surrogate has left its tested range in a variable the
> surrogate never saw — and, as a separate question, whether a mechanism it never saw has become
> large enough to matter."
