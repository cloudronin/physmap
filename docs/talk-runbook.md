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
the entrance region. It never saw `x/D`. Neither did the statistical novelty detector.
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

The line to land on is the last one: **the statistical baseline is silent, and it is silent
for a structural reason, not a tuning reason.** It cannot see the variable that broke the
surrogate. No threshold change would fix it.

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

The command prints, before anything else:

> Source data ships for 7 of 7 vehicles.
> **NOTHING WAS RECOMPUTED IN THIS RUN.**

Read that second line out. All seven datasets are published; the substrate runner is not
yet ported, so today every number comes from the banked matrix. Shipping the data and
reproducing the result are different claims and the demo must not blur them.

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

### The label that goes on the slide

**Right now, and for the talk as scheduled:**

> Historical result of the original study. The public release does not reproduce these
> numbers. A reconstruction is under way under a locked protocol.

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

---

## Sentences not to say

Each of these is false or misleading given what the repository actually does. The
replacement is not a hedge — it is the accurate sentence, and it is usually shorter.

| Do not say | Say instead |
|---|---|
| "PhysMAP achieves precision 1.00, recall 0.65, F1 0.79." | "The original study reported 1.00, 0.65 and 0.79. The public release does not reproduce them." |
| "The benchmark you just saw demonstrates the causal method." | "What you just saw is observability. The causal method is a different claim, and it is on the next slide." |
| "This reproduces the results in the abstract." | "This is a reconstruction. The best it can reach is independent corroboration." |
| "We validated against experimental truth." | "Whether that truth is experimental or a closure-style correlation is unresolved. That is why no performance claim ships." |
| "The seven vehicles validate the materiality screen." | "The seven vehicles are a closure-observability benchmark. They say nothing about materiality." |
| "It flags untrustworthy predictions with 100% precision." | "In the original study it flagged no false positives on the evaluated set. The public release computes no precision." |
| "Materiality was 0.04, so the mechanism doesn't matter." | Only if the status is `estimated`. If it is `insufficient_evidence`, say "we could not assess it" — those are different findings. |
| "Out of calibration, so the prediction is untrustworthy." | "Out of calibration **and** material. Either alone is not a verdict." |
| "`physmap benchmark run` reproduces the seven-vehicle benchmark." | "All seven datasets ship. Nothing is recomputed yet — the runner is not ported. Every number is from the bank." |
| "All seven vehicles are covered, including do-no-harm." | "Do-no-harm has one vehicle with one training row and no detector fit. It is present, not earned." |
| "All the benchmark data is openly licensed." | "Two of the seven are. Five ship without a licence, four of those against express publisher terms. It is in NOTICE." |
| "Elsevier's terms don't apply because facts aren't copyrightable." | "The term is a contract, not a copyright claim. We took the risk knowingly and we remove the data if they object." |
| "Forrest shows the guard correctly staying quiet." | "Forrest has one training row, so there is no detector to stay quiet. Its values are triage-grade by its own header." |
| "All seven vehicles reproduce from a clean clone." | "All seven **ran**. Two **rerun** publicly." |
| "The public subset shows the method working across domains." | "The public subset is thermal-fluids only, and it happens to contain only the cases where the method fires. The restraint cases are in the report, not the rerun." |
| "The open-source release reproduces the paper." | "The open-source release contains the method and the observability benchmark. The causal numbers are historical." |
| "PhysMAP uses an LLM to explain its verdicts." | "Explanations are deterministic templates. Same input, same bytes. No model call anywhere." |

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
The data for all seven is published, so eventually yes. Not today: the substrate runner is
not yet ported into the public repository, so every number in the report currently comes
from the banked matrix, and the command says so before it says anything else.

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
- [ ] `physmap benchmark run --report` → prints "7 of 7 ship" and "NOTHING WAS RECOMPUTED"
- [ ] `physmap benchmark coverage` → shows `DO_NO_HARM` resting on n_train=1
- [ ] You can state, in one sentence and without defensiveness, which five datasets ship
      without a licence and why
- [ ] Both `physmap screen` refusals print `declarative`
- [ ] `physmap reproduce nafems-2026` → *invalid choice*. If this ever prints a
      data-missing error instead, the release state and the shipped data disagree
- [ ] Terminal capture of every demo saved as a fallback slide
- [ ] Every slide bearing 1.00 / 0.65 / 0.79 carries the historical label
- [ ] Read the "sentences not to say" table once more, out loud
