# NAFEMS Multiphysics 2026 — talk runbook

**Two parts, and the separation between them is the whole point.**

| Part | What it is | Where it lives |
|---|---|---|
| **1. Live** | Closure validity and surrogate observability, reproducing from a clean clone | The machine, in front of the room |
| **2. Slides** | Causal materiality — the method, and the original study's numbers | Slides only. Never demonstrated live |

The risk this runbook exists to manage is simple: the live demo is convincing, and the
slides carry numbers. If those two run together in a listener's head, they will leave
believing the demo produced the numbers. It did not, it cannot, and saying so is not a
weakness in the talk — it is the talk.

---

## Part 1 — the live demo

### What it shows

A surrogate trained on `(Re, Pr)` in a heated pipe's fully-developed region, asked about
the entrance region. It never saw `x/D`. Neither did the input-based OOD detector.
PhysMAP reads `x/D` from the test coordinates, checks it against the closure's validated
range, and refuses with a reason.

### The commands

Run from a fresh clone. Total runtime under five seconds.

```bash
python examples/naca_entrance_region.py
```

Expected, and verified: **45 entrance points, every one `REJECT`, every one firing on
`x_over_D`, every one `UNOBSERVABLE`.** `closure_validity fired=True`,
`gp_variance fired=False`. The rationale names `gnielinski-1976`, the bound `x_over_D ≥ 10`,
and Tam & Ghajar's reported divergence of up to −63%.

The line to land on is the last one: **the input-based OOD detector is silent, and it is silent
for a structural reason, not a tuning reason.** It cannot see the variable that broke the
surrogate. No threshold change would fix it.

**What "input-based OOD detector" means, precisely.** It is the talk's one name for the
detectors that judge a prediction only by where its *inputs* sit relative to the training
data. In this demo that is the guardrail's default pair — novelty density and GP variance —
and the demo prints both, plus a count over all 45 points, so the silence is on screen rather
than asserted. In the seven-vehicle benchmark and the Lewis head-to-head it is the benchmark's
pair, distance-to-training and GP variance. Do not call it "the statistical baseline" or "the
novelty detector": the first is vague and the second is wrong for the benchmark, which
excludes novelty density.

Then the refusals, which take a tenth of a second each:

```bash
physmap screen conjugate-heat-transfer --qoi peak_solid_temperature
physmap screen fda-blood-pump --qoi haemolysis_index
```

Both return `NOT APPLICABLE`, for **different** reasons, and both print
`evidence: declarative`. Say that word out loud when it appears on screen. It means the
preconditions are asserted from the case description, not measured.

### If it breaks

Do not debug live. Say "the recorded run is on the next slide" and move on — have a
terminal capture ready. The demo is evidence, not theatre; a broken demo costs nothing
compared to a live fix that eats four minutes.

### The benchmark: run the subset, then show all seven

Order matters here. Run the public subset first, then show the full report — never the
other way round, and never the full report alone.

```bash
physmap benchmark run --report
```

It recomputes all seven vehicles from the clone and diffs every field against the
committed matrix. Expect, and point at:

> Recomputed 7 vehicles.
> **Every cell matches the banked matrix exactly.**

(On a different numpy build the second line reads *"matches within 1e-9 relative"* and
names the float fields that differ in their last bits. Both mean pass; the command exits
non-zero only on real drift. If someone asks, that distinction is worth a sentence — it
is the difference between a benchmark that checks itself and one that only claims to.)

That is the strongest single moment in the talk: seven vehicles across two domains,
recomputed live from a clone anyone in the room can make, matching a matrix committed
before the talk. Let it sit for a beat.

Takes two to three minutes. Start it, talk over it, come back to it — do not stand in
silence. If you would rather not wait, `physmap benchmark report` shows the same table
instantly from the bank, and says plainly that nothing was recomputed.

### Two things to volunteer, before anyone asks

**One. `DO_NO_HARM` is present but not earned.**

```bash
physmap benchmark coverage
```

Every outcome class now has a vehicle. But `DO_NO_HARM` — the case where the guard
correctly stays *quiet* — rests entirely on Forrest, whose cell has **one training row and
no detector fit**. It does no harm because it does nothing. The coverage output prints
that in full.

Do not show `DO_NO_HARM` as evidence the method knows when to hold back. It is the one
claim in the matrix that is not yet supported, and the repository says so.

**Two. Five of the seven datasets ship without a licence.**

Get this one right. Heat-transfer researchers are in that room and several of these papers
are theirs.

- `marineau` — no licence, and no prohibition. Transcribed from a published table in a
  publicly funded, government-hosted, public-release document. Facts.
- `forrest`, `casper`, `dirker_water`, `jin_sco2_buoyancy` — published **against** express
  publisher terms. Risks taken deliberately, not claims the terms do not apply.

Numbers only: no paper, no figure, no PDF. Removed on objection, no argument made. If
asked, say exactly that — do not defend it as though it were a licence. `NOTICE` and
`data/REDISTRIBUTION.md` already say it, which is the answer to give.

---

## Part 2 — the slides

### The causal-materiality numbers

Precision **1.00**, recall **0.65**, F1 **0.79**. Materiality range 0.04–0.26.

**These are results of the original study. The public release does not reproduce them.**

Say it in those words, on the slide, in the voice-over. The original inputs are gone: the
CFD working tree, the per-point ablation pairs, the evaluated grid, the surrogate
predictions and the experimental-truth table. What survives is the abstract's figures and
its prose.

### Two things now known about how that table was produced

Both were traced from surviving artifacts. Both change what the slide may claim, and both
are better volunteered than discovered by a questioner.

**One — the table is correlation-referenced.** No pointwise measurement was used. The
truth was Mohammed & Salman's correlation, evaluated densely. **Every** cell was scored
against it, including recall and including the baselines. Say *correlation-referenced*,
not *experimental*.

**Two — the table may be strongly favoured by the test construction.** The surrogate was a
forced-convection closure fitted to the gravity-off CFD, and the materiality numerator is
that same gravity-off CFD. The relative surrogate error then works out as

```
E = d − m(1+d) + ε
```

so for small `d` and `ε` the label rule `|E| > tol` approaches the flag condition
`m ≥ θ` — and with `θ ≈ tol`, a flagged point is labelled untrustworthy.

**Do not overclaim this either.** It is a mechanism, not a proof. It rests on Step 4's
error scale (unknown), the surrogate fit residual (unrecoverable), and the sign of `d`
across the grid (two observations, both at high `Ri`). If asked how confident you are:
confident there is a coupling, not confident it fully explains the number.

**The inversion is the memorable part.** Given the mechanism, **a rebuild that recovers
precision ≈ 1.00 would be evidence the coupling survived, not evidence the method works.**
That is why the reconstruction is not aimed at the old numbers.

### If anyone asks about the experimental uncertainty

The paper reports **±1.27%** on Nusselt number, following Moffat's method. Not ±8%.

The ±8% figure — which this project carried for a while, wrongly — is the paper's stated
accuracy of the **data about the fitted correlation**. A property of the fit, not of the
measurement. Six times larger, and a different quantity.

Worth knowing because it is the kind of number a heat-transfer audience will have opinions
about. There is also a third quantity — the error in recovering values off the published
plots — which is not yet measured and could be larger than either. Do not assert which of
the three governs until it is.

### What Part 2 is, until an evaluable truth set exists

**Present the causal method as a reproducible demonstration, not as a validated result.**

That is not a hedge; it is what the work currently supports. The method runs, its refusals
fire, its explanations are deterministic, and — once the rebuild lands — its CFD carries
recorded numerical checks and its surrogate a measured generalisation residual. All of
that is demonstrable and none of it needs a performance number.

**New metrics appear only if a properly evaluable truth set supports them.** Evaluable
means per-run `Re`, `Gr`, geometry, entrance length, measured `Nu` and uncertainty —
enough to identify each case. No such set is in hand.

### The label that goes on the slide

**Right now, and for the talk as scheduled:**

> **Historical results of the original study, scored against an experimental
> correlation** — not validated against individual measurements — and possibly strongly
> favoured by the test construction. The public release does not reproduce them. A
> reconstruction is under way under a locked protocol.

**Not** "not yet reproduced", which implies it is a matter of time.

### If the reconstruction lands before the talk

The label changes, and it changes to exactly one of four things. Which one is decided by
the protocol, not on the day.

| Outcome | The slide says |
|---|---|
| `CORROBORATED` | Independently corroborated under different inputs. Show the reconstruction's numbers with their uncertainty, and point at the new evidence |
| `NOT_CORROBORATED` | Show the new numbers. State plainly that they differ from the published figures, and by how much |
| `INCONCLUSIVE` | Show the method. State that the available measurements could not settle it |
| `NOT_ATTEMPTED` | The historical label above |

`REPRODUCED` is **not** on that list. It is defined in the protocol and marked unreachable,
because reproduction means a close rerun of the original evaluation and the grid, the
truth source and the counterfactual all change. Keeping the word unavailable is what stops
it drifting onto a weaker result.

**In every outcome the slide shows the reconstruction's numbers, never the original
triple.** Even under corroboration.

### The Lewis head-to-head — one worked example, one run

**What it is.** Lewis (1992) Test 35A, a real vertical-tube mixed-convection experiment. A
forced-convection surrogate fitted to gravity-off CFD, judged by the benchmark's own
input-based OOD detector and by PhysMAP, at each of Lewis's thermocouple stations. **One run.
A development example.** Its stations are not independent cases, so no precision, recall or
F1 — and none should be implied by the slide's layout. Full record:
`docs/findings/lewis-ood-head-to-head.md`.

**The slide is the control, not the scorecard.** Same surrogate, same detector, same inputs —
once against gravity-off CFD, where the surrogate is right to 0.25 %, and once against
Lewis's measurement, where it is off by up to 18 %:

| | surrogate error | input-based OOD detector | PhysMAP |
|---|---|---|---|
| 35A, gravity off (control) | ≤ 0.25 % | fires at every station | quiet |
| 35A, the experiment | up to −18 % | fires at every station — **identically** | flags x/D ≥ 67.55, where the error is 17–18 % |

**The line to land:** *"The input-based OOD detector gives the same answer whether buoyancy is
on or off, because gravity isn't one of its inputs. PhysMAP is the one whose answer changes."*

**Volunteer these three before anyone asks.** They are true, and a sharp questioner will find
them:

1. **The OOD detector was not quiet on Lewis — it fired everywhere.** It fired because 35A's
   operating point sits between the training runs'. That is correct and has nothing to do with
   buoyancy; its output does not change when buoyancy is switched off. Contrast NACA, where it
   was silent: there the entrance points shared the training operating point. Silent in one,
   firing in the other, informative about the mechanism in neither.
2. **PhysMAP missed two real errors, by design.** At x/D 2.45 and 16.32 the surrogate is off by
   +10 % and −13 %, mostly because the base CFD model differs from the experiment there — not
   because of buoyancy. PhysMAP checks one mechanism and does not claim to see the others.
3. **The threshold is not locked.** At θ = 0.10 it flags three comparable stations. Buoyancy is
   worth 6–9 % at two more; whether those flag is the open θ decision.

---

## Sentences not to say

Each of these is false or misleading given what the repository actually does. The
replacement is not a hedge — it is the accurate sentence, and it is usually shorter.

| Do not say | Say instead |
|---|---|
| "PhysMAP achieves precision 1.00, recall 0.65, F1 0.79." | "The original study reported 1.00, 0.65 and 0.79. The public release does not reproduce them." |
| "The benchmark you just saw demonstrates the causal method." | "What you just saw is observability. The causal method is a different claim, and it is on the next slide." |
| "This reproduces the results in the abstract." | "This is a reconstruction. The best it can reach is independent corroboration." |
| "We validated against experimental truth." | "The truth was their experimental correlation, evaluated densely. No pointwise measurement was used. It is correlation-referenced." |
| "These numbers were validated against measurements." | "They were scored against a fitted correlation. No individual measurement entered the comparison." |
| "The causal method is validated." | "The causal method is demonstrated. Validation needs an evaluable truth set and we do not have one." |
| "Recall 0.65 is unaffected by the coupling, so it's the solid number." | "It is unaffected by that coupling and still correlation-referenced. Two different defects; the second applies to every cell." |
| "The naive baseline's 0.73 is real performance." | "It is a correlation-referenced number too. The comparison is less compromised than the absolute figure; the figure is not independent evidence." |
| "If the rebuild gets 1.00 again, that confirms it." | "It would suggest the coupling survived. That is why we are not aiming at the old numbers." |
| "The seven vehicles validate the materiality screen." | "The seven vehicles are a closure-observability benchmark. They say nothing about materiality." |
| "There's no mixed-convection vertical-pipe case in the benchmark." | "jin_sco2_buoyancy is one. It measures observability of the buoyancy parameter, not materiality." |
| "The statistical baseline / novelty detector is silent." | "The input-based OOD detector is silent." |
| "NVIDIA PhysicsNeMo fails here." / "PhysicsNeMo's guardrail would miss this." | "An input-based OOD detector misses this. PhysicsNeMo's out-of-distribution check and its physics checks are separate things; we have not run its guardrail, so we make no claim about it." |
| "The OOD detector was starved of inputs." | "It got every input the surrogate gets, position included. The contract is recorded in the head-to-head output." |
| "The OOD detector missed the buoyancy error on Lewis." | "It fired everywhere on Lewis, with the same answer whether buoyancy was on or off. It fired because the operating point was between the training runs, not because of buoyancy." |
| "PhysMAP caught what the OOD detector missed." (of Lewis) | "Both fired downstream. Only PhysMAP's answer changes when buoyancy is switched off." |
| "PhysMAP catches the surrogate's errors." | "It catches the errors the mechanism it checks causes. On Lewis it missed two stations whose error came from the base model — by design." |
| "It flags untrustworthy predictions with 100% precision." | "In the original study it flagged no false positives on the evaluated set. The public release computes no precision." |
| "Materiality was 0.04, so the mechanism doesn't matter." | Only if the status is `estimated`. If it is `insufficient_evidence`, say "we could not assess it" — those are different findings. |
| "Out of calibration, so the prediction is untrustworthy." | "Out of calibration **and** material. Either alone is not a verdict." |
| "`physmap benchmark report` reproduces the benchmark." | "`report` reads the bank. `run` is the one that recomputes and diffs." |
| "All seven vehicles are covered, including do-no-harm." | "Do-no-harm has one vehicle with one training row and no detector fit. It is present, not earned." |
| "All the benchmark data is openly licensed." | "Two of the seven are. Five ship without a licence, four of those against express publisher terms. It is in NOTICE." |
| "Elsevier's terms don't apply because facts aren't copyrightable." | "The term is a contract, not a copyright claim. We took the risk knowingly and we remove the data if they object." |
| "Forrest shows the guard correctly staying quiet." | "Forrest has one training row, so there is no detector to stay quiet. Its values are triage-grade by its own header." |
| "All seven vehicles reproduce from a clean clone." | "All seven **ran**. Two **rerun** publicly." |
| "The public subset shows the method working across domains." | "The public subset is thermal-fluids only, and it happens to contain only the cases where the method fires. The restraint cases are in the report, not the rerun." |
| "The open-source release reproduces the paper." | "The open-source release contains the method and the observability benchmark. The causal numbers are historical." |
| "PhysMAP uses an LLM to explain its verdicts." | "Explanations are deterministic templates. Same input, same bytes. No model call anywhere." |

### The vehicle that will catch you out

`jin_sco2_buoyancy` is a **mixed-convection vertical tube** whose failure driver is a
buoyancy parameter. That is geometrically the closest thing in the benchmark to the
NAFEMS causal case, and it comes back `PHYSMAP_WINS`.

Someone will notice. Get there first: it measures whether the buoyancy parameter is
**observable** to the surrogate. It computes no ablation, no counterfactual, no
materiality, no metric. Its truth is a measured heat-transfer coefficient, not a quantity
of interest with a mechanism removed. `physmap explain jin_sco2_buoyancy` prints exactly
that, unprompted, in its header.

Do not say "there is no mixed-convection vertical-pipe vehicle in the benchmark". There
is. Saying otherwise is a denial a listener can check and find wrong in thirty seconds,
which is far more damaging than the caveat it was trying to avoid.

### The one-sentence version, if you only remember one thing

**Nothing in Part 1 is evidence for Part 2.**

---

## Questions you will get, and the honest answers

**"Can I reproduce your NAFEMS numbers?"**
No. The original inputs are gone. You can reproduce the observability benchmark today, and
the reconstruction — when it lands — will publish its own numbers under a protocol that
was frozen before those numbers existed.

**"Why not just rerun it?"**
The CFD working tree is gone. Rerunning means rebuilding the grid, sourcing independent
truth, and constructing a geometry-appropriate counterfactual. That is a different study
that answers the same question, which is why the right word is corroboration.

**"Isn't this just an out-of-range check?"**
No, and the difference is testable. A naive box check fires on every excursion. The causal
rule fires only when the excursion also reaches the quantity of interest. There is a test
in the repository asserting the two disagree on the same input — if they ever agreed
everywhere, the materiality term would be doing no work.

**"What stops you tuning the threshold until it looks good?"**
The protocol is locked in two stages and the second stage fixes a decision *rule* over the
class balance, not a number chosen against it. The class balance is not even computed until
after that lock. The known-results declaration records what was already known going in,
because the original results were already public and pretending otherwise would be false.

**"Where did you get Dirker's and Jin's data, and did you have permission?"**
Digitised from the published figures, and no. Elsevier's licence forbids systematic
redistribution of the dataset. We published the numbers anyway — numbers only, no paper or
figure — and we say so in NOTICE and in the redistribution manifest rather than implying a
licence we do not have. If the publisher or the authors object, the files come out and we
will not argue. That is a risk we took deliberately, not an oversight.

**"Can I rerun all seven?"**
Yes. Clone it, `pip install -e .`, `physmap benchmark run`. It recomputes all seven and
diffs every field against the committed matrix, and exits non-zero if anything drifted.
CI does the same on every push. Note it needs the checkout, not a wheel — the substrate
CSVs live in the repository, outside the package, on purpose.

**"Isn't the benchmark cherry-picked?"**
All seven vehicles ship, so nothing is withheld. The honest weakness is elsewhere:
`DO_NO_HARM` rests on a single vehicle with one training row and no detector fit, so the
claim that the method knows when to hold back is the one claim in the matrix not yet
supported. `physmap benchmark coverage` prints that, unprompted.

**"Why is the corpus not fully open?"**
The library is open, the calibration corpus is the commercial moat. Fifteen closures ship
with their bounds, and a verdict-free index of 201 closures ships alongside. The seed is an
allowlist, and everything published passes through it — including the evidence corpus.

**"What licence?"**
MIT for the code, CC BY 4.0 for the corpus. Digitised third-party measurements are under
neither: those measurements were not made here, so no copyright in them is claimed. Each
file carries its own redistribution determination.

---

## Pre-talk checklist

- [ ] `git clone` fresh, `pip install -e .`, `pytest tests/ -q -n auto` green
- [ ] `python examples/naca_entrance_region.py` → 45 REJECT
- [ ] `physmap benchmark run` from a FRESH clone → exit 0, and `git status` clean
      afterwards ("exactly" or "within 1e-9 relative" both pass)
- [ ] `physmap benchmark coverage` → shows `DO_NO_HARM` resting on n_train=1
- [ ] You can state, in one sentence and without defensiveness, which five datasets ship
      without a licence and why
- [ ] Both `physmap screen` refusals print `declarative`
- [ ] `physmap reproduce nafems-2026` → *invalid choice*. If this ever prints a
      data-missing error instead, the release state and the shipped data disagree
- [ ] Terminal capture of every demo saved as a fallback slide
- [ ] Every slide bearing 1.00 / 0.65 / 0.79 carries the historical label
- [ ] Read the "sentences not to say" table once more, out loud
- [ ] You can say "correlation-referenced" without hesitating, and explain in one sentence
      why recovering 1.00 would be a bad sign rather than a good one
