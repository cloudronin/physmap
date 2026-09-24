# The talk, as a story

Five parts. Each says what to claim, what backs it, and which figure carries it. Every number
here is in [`facts-sheet.md`](facts-sheet.md); every headline sentence, with its limits, is in
[`claims-ledger.md`](claims-ledger.md).

---

## 1. What input-based OOD guardrails can and cannot see

A surrogate is fast because it learned from a set of runs. The usual guardrail asks one
question: **do this prediction's inputs look like the training inputs?** Distance to the
training data and Gaussian-process variance are two ways of asking it. It is a good question,
and these detectors answer it well.

But it is a question about inputs. A surrogate can be reused where its inputs look ordinary and
the physics has changed — because the thing that changed was never an input.

Gravity is this talk's example. In a forced-convection training set gravity does not vary, so
nobody makes it an input. Reuse that model in vertical heated flow and buoyancy starts to
matter. Nothing in the input vector says so.

An input-based detector cannot report a change that is not in its inputs. That is not a flaw in
the detector. It is the edge of the question it asks.

> **Say:** "An input-based OOD detector tells you whether the inputs are familiar. It cannot
> tell you whether the physics is."

---

## 2. The question PhysMAP asks instead

> **Is a physical mechanism that applies here outside the range the surrogate was calibrated
> on — and does it change the quantity of interest by a material amount?**

Both halves are needed.

- **Outside calibration.** The mechanism is named, with the dimensionless group that measures
  it. For buoyancy that is the Richardson number, Ri. The surrogate's calibrated window comes
  from its training data. This training never saw buoyancy, so the window is Ri = 0 exactly.
  Lewis Test 35A with gravity on has Ri = 0.29.
- **Material.** Materiality is measured by ablation. Run the same case with the mechanism and
  without it, change nothing else, and compare the quantity of interest:
  materiality = 1 − Nu(gravity off) / Nu(gravity on). A mechanism can be out of range and still
  not matter. Then PhysMAP stays quiet.

This complements an input-based detector; it does not replace it. It reads information the
surrogate never had — the mechanism, and a matched ablation — so it can see a change the input
vector cannot.

**The talk has two results, and they answer different questions.**

| Result | Question | Command |
|---|---|---|
| Seven-vehicle benchmark, x/D example | Is the variable that breaks the surrogate visible to an input-based detector at all? | `physmap benchmark run` |
| Lewis 35A stress test | When a mechanism the surrogate never saw becomes active, does it matter to the answer? | `physmap stress-test lewis-reuse` |

Neither is evidence for the other.

---

## 3. The seven-vehicle benchmark and the x/D example

**The x/D entrance region** ([figure](figures/README.md#the-xd-entrance-region-closure-validity-fires-both-input-based-detectors-silent)).
A surrogate is trained on the fully developed part of a heated pipe, using Re and Pr, then asked
about the entrance region. There its inputs look ordinary: the same Re and Pr it trained on.
What changed is x/D, which it never had. The closure it relies on, gnielinski-1976, is
validated only from x/D = 10. On the 45 entrance points, PhysMAP's closure check fires on all
45. The two input-based detectors — novelty density and GP variance — fire on 0. They are quiet
because they cannot see x/D, not because the points are safe.

**The benchmark** ([figure](figures/README.md#seven-vehicle-benchmark-closure-validity-and-observability))
asks the same observability question of seven published datasets in two domains. Three come back
`PHYSMAP_WINS` — NACA, Casper and Jin: the failure variable is invisible to the input-based
baseline, and the closure check caught wrong rows the baseline missed. Two are `PARTIAL`.
Marineau is the negative control: the baseline sees its failure variable. Forrest is
triage-grade data with one training row, so its `DO_NO_HARM` is short-circuited, not earned.

What this is: a reproducible observability benchmark. `physmap benchmark run` recomputes all
seven from a clone and diffs them against the committed matrix. What it is not: a performance
rate, or evidence for causal materiality.

---

## 4. Lewis 35A — a controlled model-reuse stress test

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

## 5. What the evidence establishes — and what it does not

**Established, for this construction:**

1. With every visible input inside the training data, the input-based detector's output is
   identical with gravity off and gravity on. Its inputs are identical, so it must be; the
   shipped detector shows it.
2. PhysMAP's materiality separates the two states: 0 with gravity off, up to 0.195 with gravity
   on, growing down the tube.
3. On the control the surrogate is accurate, within 0.06 %. Against the measurement it is
   17–18 % off downstream.
4. Downstream, the measurement sides with the gravity-on CFD — within 1.6–6.6 % — not the
   gravity-off CFD. The buoyancy effect that materiality measures is present in the
   experiment.
5. In the x/D example, the closure check fires on 45 of 45 entrance points and the input-based
   detectors on 0.
6. All of it reruns from a clean clone.

**Not established:**

1. **Any detection rate.** One run; its stations are not cases; no precision, recall or F1.
   There is no independent evaluation set yet.
2. **A θ.** It is unlocked, so nothing here is a categorical verdict.
3. **That materiality predicts surrogate error in general.** Here the surrogate and the
   materiality both rest on the gravity-off CFD, so their agreement is partly built in. What the
   test shows is which output moves when the physics moves.
4. **That PhysMAP sees every error.** At x/D 2.45 and 16.32 the surrogate is off because the
   base CFD differs from the experiment there. PhysMAP checks one mechanism.
5. **Generality.** One run, one geometry, one mechanism, laminar aiding flow.
6. **The abstract's precision, recall and F1** — see
   [`historical-reconciliation.md`](historical-reconciliation.md).
7. **Anything about NVIDIA PhysicsNeMo** or any other product. Neither of its checks was run.

> **Close:** "A mixed-convection surrogate built correctly should include Ri, Gr or an
> equivalent. When a model is reused past what it was built for, PhysMAP asks whether a
> mechanism it never saw has become material — a question its inputs cannot answer."
