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
than asserted. In the seven-vehicle benchmark and the Lewis stress test it is the benchmark's
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

### The benchmark: recompute all seven, then show the report

Order matters here. Run the recompute first, then show the report — never the report alone,
because the report reads the bank and recomputes nothing.

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

That is the strongest reproducibility moment in the talk: seven vehicles across two domains,
recomputed live from a clone anyone in the room can make, matching a matrix committed
before the talk. Let it sit for a beat.

**Then point at the block under the table: "What the closure-validity check adds to the
input-based detectors".** That is the point of PhysMAP, per dataset, at percentile 99:

- where the cause of failure is hidden from the inputs, the closure check catches what the OOD
  detectors miss — `20 of 20` at the pipe entrance;
- where the cause is an input, it adds nothing — `0 of 6` for Marineau;
- the right-hand column is the cost: false alarms, `24` and `16`.

Land it: *"Where the cause of failure isn't one of the surrogate's inputs, PhysMAP catches what
the OOD detectors can't. Where it is, it adds nothing. And it costs false alarms."* The same
numbers are on the chart, `docs/talk/figures/bench_3_what_physmap_adds.png`.

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

### Lewis 35A — a controlled model-reuse stress test (one run)

**The full package for this part is in [`docs/talk/`](talk/README.md):** figures, a generated
facts sheet, the claims ledger, speaker notes, hostile questions and the slide order. Its
numbers are generated from the committed records and checked by
`python tools/talk_package.py check`.

**What it is — say this first:**

> *"The surrogate was trained for forced convection, where gravity did not vary and was not an
> input. It was then reused in vertical heated flow, where buoyancy became material. A
> mixed-convection surrogate designed for this regime should include Richardson number,
> Grashof number, or equivalent physical information."*

**The claim:**

> *"PhysMAP detects when model reuse activates a physically relevant mechanism outside the
> surrogate's observable input space. An input-only OOD detector cannot identify a change
> absent from its input contract."*

**One run. A development example.** Its stations are not independent cases, so no precision,
recall or F1 — and nothing on the slide may look like a scorecard. Full record:
`docs/findings/lewis-ood-head-to-head.md`.

**The slide — design M, the headline.** Two parts, in this order.

*1. The input contract.* Both the surrogate and the input-based OOD detector receive `Re`, `Pr`
and `x_over_D`. **Neither** receives gravity, `Ri`, `Gr` or heat flux. **Every visible deployment
input exactly matches a training input.** Say that sentence out loud — it is what makes this a
controlled test rather than a stacked one.

*2. The result, same visible inputs, two physical states:*

| | surrogate error | OOD scores | PhysMAP materiality |
|---|---|---|---|
| **gravity off** — the accurate control | within 0.06 % | *identical to the row below* | **0** |
| **gravity on** — Lewis's measurement | **17–18 %** at x/D 67.55, 101.69, 135.84 | quiet at the benchmark's reference percentile | rises to **0.195** downstream |

**The line to land:** *"Same inputs, same OOD scores. Different physics, different materiality —
and where materiality is largest, the surrogate is 17–18 % off."*

An earlier draft ended *"and the materiality is where the error is"*. Do not use it: at x/D 2.45
and 16.32 the surrogate is off by +9.9 % and −12.8 % with almost no materiality.

**Show materiality as numbers, not verdicts.** θ is unlocked. If a flag appears at all, label it
*"at the illustrative θ = 0.10"* — the original study's value, not a chosen one. The headline
needs no θ: identical OOD scores and zero-versus-0.195 materiality are threshold-free.

**Pre-declared.** Design M and its success criteria were committed in
`results/lewis35A_head_to_head/PREDECLARE_design_M_matched.md` before any of its output existed,
and all three were met: the detector quiet at every comparable station for both gravity states
at the reference percentile 99; PhysMAP flagging a comparable station with gravity on — at the
illustrative θ = 0.10, and for any θ ≤ 0.195; PhysMAP flagging nothing with gravity off, at any
θ. Say "pre-declared" out loud — it is what makes the result worth more than a demo.

**Then the secondary result — designs A and A3, specificity.** When the visible operating point
falls *between* training runs, the OOD detector warns in both the accurate and the inaccurate
case — identically — while PhysMAP changes with the physical mechanism:

> *"The OOD detector detected unfamiliar inputs but could not identify whether buoyancy caused an
> error. PhysMAP distinguished the accurate control from the materially affected prediction and
> named the mechanism."*

**Running it.** `physmap stress-test lewis-reuse` reproduces everything from a clone, asserts the
exact input overlap and the unchanged OOD scores, and checks itself against a committed bank. It
takes a few minutes — 212 s from a clean public clone, recorded with its commit, environment and
exit status in `docs/talk/reproduction/`. Run it before the talk and show the output rather than
waiting on it live. It reproduces the analysis from committed CFD-derived profiles; it does not
rerun OpenFOAM. On a machine unlike the recorded one, the last line reads "matches the banked
record: matches within …" instead of "exactly". Both pass: the surrogate's last few digits move
between machines, and every flag, count and label is still compared exactly.

**Say plainly, unprompted:**

- **This is not "OOD detectors fail".** The detector does exactly its job — it reports whether the
  inputs are familiar. The change that matters is outside its inputs.
- **This is not "leave gravity out".** A mixed-convection surrogate built correctly should expose
  Ri, Gr or equivalent. The test reuses a forced-convection surrogate on purpose.
- **Nothing here is about NVIDIA PhysicsNeMo.** Its OOD and physics checks are distinct, and
  neither was run.

**Volunteer these before anyone asks.** They are true, and a sharp questioner will find them:

1. **The detector's answer tracked where the inputs sat — never gravity.** Quiet with 35A on a
   training operating point (design M), warning with it between them (A and A3), and identical
   with gravity on and off in every design. The same explains NACA, where it was silent: those
   entrance points shared the training operating point.
2. **At low operating percentiles the detector does fire downstream** — at 75, on the stations
   where materiality is high. It fires identically with gravity off, where those stations are
   right to 0.03 %, and at that setting it already fires on 97–100 % of its own training rows
   beyond x/D 50. It is flagging sparse training coverage, not buoyancy. The reference
   percentile is 99, and it is quiet there.
3. **PhysMAP does not see every error.** At x/D 2.45 and 16.32 the surrogate is off by +10 % and
   −13 %, mostly because the base CFD model differs from the experiment there. PhysMAP checks one
   mechanism and does not claim to see others.
4. **θ is not locked.** At θ = 0.10 three comparable stations would flag; at 0.05, five; at 0.20,
   none. Buoyancy is worth 6–9 % at x/D 33.39 and 50.47; whether those flag is the open θ
   decision. The protocol sets θ, not this outcome.
5. **Materiality with gravity off is zero by construction** — there is no buoyancy to remove. The
   finding is the gravity-on profile, and that the OOD output does not move while it grows.
6. **The surrogate and the materiality share the gravity-off CFD**, so their agreement is partly
   built in — the same coupling that retired the abstract's precision. That is why no rate is
   computed. What the measurement adds independently: downstream it sides with the gravity-on
   CFD, within 1.6–6.6 %.

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
| "OOD detectors fail at this." / "OOD detection doesn't work." | "An input-only OOD detector cannot identify a change absent from its input contract. Here the change was gravity, which was not an input." |
| "Engineers shouldn't bother including gravity." | "A mixed-convection surrogate built for this regime should include Ri, Gr or equivalent. This test shows what reuse without it looks like." |
| "PhysMAP flagged three stations." (as a verdict) | "Materiality rose to 0.195 downstream. At the illustrative θ = 0.10 three stations would flag; θ is not locked." |
| "The materiality is where the error is." | "Where materiality is largest, the surrogate is 17–18 % off. At x/D 2.45 and 16.32 the error comes from the base model, not buoyancy." |
| "Materiality predicts the surrogate's error." | "Here the two share the gravity-off CFD, so the agreement is partly built in. The test shows which output moves when the physics moves." |
| "Lewis gives us twelve test cases." | "One run. Its stations are positions along one tube, not cases." |
| "PhysMAP outperforms OOD detection." | "Where the cause of failure isn't one of the surrogate's inputs, it catches what the OOD detectors can't. Where it is, it adds nothing. And it costs false alarms." |
| "Across the benchmark PhysMAP catches N of M." (a pooled rate) | "Per dataset: 20 of 20 at the pipe entrance, 4 of 8 in the hypersonic case, 15 of 26 for supercritical CO2 — with the false alarms beside them." |
| "The CFD is validated against Lewis." | "From x/D 9.92 on it is grid-converged and within 9.6 % of the measurement. That is development evidence, not validation — 35A was inspected while the model was built." |
| "The OOD detector caught the downstream stations too." (citing percentile 75) | "At 75 it fires on its own training data there, and identically with gravity off. At the reference 99 it is quiet." |
| "PhysMAP catches the surrogate's errors." | "It catches the errors the mechanism it checks causes. On Lewis it missed two stations whose error came from the base model — by design." |
| "It flags untrustworthy predictions with 100% precision." | "In the original study it flagged no false positives on the evaluated set. The public release computes no precision." |
| "Materiality was 0.04, so the mechanism doesn't matter." | Only if the status is `estimated`. If it is `insufficient_evidence`, say "we could not assess it" — those are different findings. |
| "Out of calibration, so the prediction is untrustworthy." | "Out of calibration **and** material. Either alone is not a verdict." |
| "`physmap benchmark report` reproduces the benchmark." | "`report` reads the bank. `run` is the one that recomputes and diffs." |
| "All seven vehicles are covered, including do-no-harm." | "Do-no-harm has one vehicle with one training row and no detector fit. It is present, not earned." |
| "All the benchmark data is openly licensed." | "Two of the seven are. Five ship without a licence, four of those against express publisher terms. It is in NOTICE." |
| "Elsevier's terms don't apply because facts aren't copyrightable." | "The term is a contract, not a copyright claim. We took the risk knowingly and we remove the data if they object." |
| "Forrest shows the guard correctly staying quiet." | "Forrest has one training row, so there is no detector to stay quiet. Its values are triage-grade by its own header." |
| "All seven vehicles are validated." | "All seven recompute from a clean clone and match the committed matrix. That shows the benchmark reproduces, not that its data are benchmark-grade — Forrest is triage-only." |
| "The benchmark shows the method working across domains." | "It shows the failure variable's observability across two domains. The one restraint case, DO_NO_HARM, rests on Forrest, which is not earned." |
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
Everything this repository uses is open: the code is MIT and the corpus data CC BY 4.0.
Fifteen closures ship with their bounds, plus an index of 201 closures with no bounds. A larger
53-closure corpus exists and is not published — and nothing here needs it. The benchmark, the
Lewis stress test and the examples all run on the published fifteen, and CI checks that on a
clean checkout. What gets published passes through an allowlist, the evidence corpus included.

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
- [ ] `physmap stress-test lewis-reuse` from a FRESH clone → exit 0 and "The record matches the
      banked record exactly." (last recorded: `docs/talk/reproduction/`)
- [ ] `python tools/talk_package.py check` → passes
- [ ] Every Lewis slide says "one run", and shows θ = 0.10 only with the word "illustrative"
- [ ] Read `docs/talk/hostile-questions.md` aloud once
- [ ] Terminal capture of every demo saved as a fallback slide
- [ ] Every slide bearing 1.00 / 0.65 / 0.79 carries the historical label
- [ ] Read the "sentences not to say" table once more, out loud
- [ ] You can say "correlation-referenced" without hesitating, and explain in one sentence
      why recovering 1.00 would be a bad sign rather than a good one
