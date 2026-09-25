# PhysMAP

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22950742.svg)](https://doi.org/10.5281/zenodo.22950742)

Physics-aware credibility checks for AI surrogates in multiphysics simulation.

An input-based OOD detector asks whether a prediction's inputs look familiar. PhysMAP asks two
other questions: **does the physics the model relies on still apply here**, and **does a
mechanism the model left out materially change the quantity of interest?** It keeps the OOD
detectors, and adds the checks they cannot make — because what breaks a surrogate is often not
one of its inputs.

- **Applicability assurance** — shown on the entrance region of a heated pipe (NACA TN-1451).
- **Causal materiality** — shown in a controlled model-reuse stress test on Lewis (1992)
  Test 35A, the main controlled demonstration.
- **Supporting evidence** across seven published datasets, led by a hypersonic transition case
  (Casper) where three different surrogate architectures give the same result.

No LLM is in any path. Every explanation is a deterministic rendered template.

## Applicability assurance: the NACA x/D entrance region

![Applicability assurance: the x/D entrance region](https://raw.githubusercontent.com/cloudronin/physmap/main/docs/talk/figures/bench_1_naca_entrance.png)

A heat-transfer surrogate that takes only `(Re, Pr)` relies on a closure — here the Gnielinski
correlation — validated for fully developed flow, from x/D = 10 on. Near a pipe's inlet, `x/D`
governs the heat transfer, and neither the surrogate nor an input-based OOD detector sees it:
in `(Re, Pr)` the entrance points look perfectly ordinary. On NACA TN-1451's Fig 10 (two-reader
digitisation), against the measurement, at the numerical-error threshold (17.5 %):

- Gnielinski is **within the threshold on 40 of 40** fully developed points.
- It **exceeds the threshold on 9 of 45** entrance points — all at x/D ≤ 5, the largest 38 % at
  the inlet.
- PhysMAP identifies **all 45 entrance predictions as outside the closure's supported
  applicability region**. The input-based OOD detectors fire on none.
- **The other 36 are numerically acceptable, but not physically supported by that closure.**

Numerical agreement does not by itself establish that a prediction is credibly supported.
PhysMAP reads the bound variable from the test coordinates rather than from the surrogate's
inputs, checks it against the closure's validated range, and knows at setup that `x/D` is
structurally invisible to this surrogate:

```
verdicts: {'REJECT': 45}
rationale: Prediction relies on gnielinski-1976 beyond its validated x_over_D bound
           (x_over_D >= 10); x_over_D is not a surrogate input (unobservable to
           input-based OOD detectors), and the literature (Tam & Ghajar 1998) reports
           divergence up to -63% past this bound. Input-based OOD detectors are silent
           because they cannot observe x_over_D.
```

The −63% is the literature's figure; on this data the largest entrance error is 38%. Run it:
[`examples/naca_entrance_region.py`](https://github.com/cloudronin/physmap/blob/main/examples/naca_entrance_region.py).

## Causal materiality: a controlled model-reuse stress test (Lewis 35A)

Applicability asks whether the physics a prediction relies on still applies. This asks
something else: when a mechanism the surrogate never saw becomes active, does it change the
answer — and where?

```bash
physmap stress-test lewis-reuse
```

**The setup.** The surrogate was trained for forced convection, where gravity did not vary
and was not an input. It was then reused in vertical heated flow, where buoyancy became
material. A mixed-convection surrogate designed for this regime should include Richardson
number, Grashof number, or equivalent physical information — this test reuses one without
it, on purpose.

**The claim.** PhysMAP detects when model reuse activates a physically relevant mechanism
outside the surrogate's observable input space. An input-only OOD detector cannot identify a
change absent from its input contract.

**The input contract.** Both the surrogate and the input-based OOD detector — the
seven-vehicle benchmark's own, unchanged — receive `Re`, `Pr` and `x_over_D`. Neither
receives gravity, `Ri`, `Gr` or heat flux. **Every visible deployment input exactly matches a
training input.**

**The result**, same visible inputs, two physical states, on Lewis's (1992) vertical-tube
experiment:

| | surrogate error | input-based OOD scores | PhysMAP materiality |
|---|---|---|---|
| gravity off — the accurate control | within 0.06 % | quiet at the reference percentile, 99; identical in both rows, because the inputs are | 0 |
| gravity on — Lewis's measurement | 17–18 % downstream | quiet at the reference percentile, 99; identical in both rows, because the inputs are | up to 0.195 |

Identical OOD scores and zero-versus-0.195 materiality need no threshold. The flag threshold θ
is not yet locked, so materiality is reported as numbers, and θ = 0.10 appears only as an
illustration.

A secondary result shows specificity: when the visible operating point falls *between*
training runs, the OOD detector warns in both the accurate and the inaccurate case —
identically — while PhysMAP changes with the physical mechanism.

**What it is not.** Not a claim that OOD detectors fail in general — this one does exactly its
job. Not a suggestion to leave gravity out. Not a claim about NVIDIA PhysicsNeMo, whose OOD
and physics checks are distinct and were not run. **One run, a development demonstration:** its
stations are not independent cases, and no precision, recall or F1 is computed.

The command recomputes everything from this checkout in a few minutes, asserts the exact
input overlap and the unchanged OOD scores, and diffs itself against a committed bank — the
same contract as `physmap benchmark run`, deliberately kept a separate command because this is
a causal-materiality result. It recomputes from committed CFD-derived profiles and does not rerun
OpenFOAM. Full record:
[docs/findings/lewis-ood-head-to-head.md](https://github.com/cloudronin/physmap/blob/main/docs/findings/lewis-ood-head-to-head.md). The NAFEMS
talk package — figures, facts sheet, claims ledger, and a clean-clone reproduction record — is
in [docs/talk/](https://github.com/cloudronin/physmap/blob/main/docs/talk/README.md).


## Supporting evidence: seven published datasets

The seven-vehicle benchmark asks, per dataset: which wrong predictions does PhysMAP flag that
the input-based detectors (distance-to-training and GP variance) miss — and was the surrogate
accurate at home, so that deployment is what created the failure?

**Casper leads.** Hypersonic transition; the cause, tunnel freestream noise, is not a surrogate
input. The surrogate is wrong on 6 of 159 home rows held out (4%), and on 8 of 8 deployed. A
Gaussian process, a DeepONet and gradient-boosted trees each pass the same home-accuracy check,
and **each leaves 4 of 8 deployment errors that only PhysMAP flags**.

**Dirker supports it.** Water in a horizontal tube; the cause, buoyancy, is partly visible to
the inputs. Wrong on 0 of 31 home rows held out, and on 11 of 60 deployed; PhysMAP flags 2 of
those 11 that the detectors miss.

![The home baseline behind each count](https://raw.githubusercontent.com/cloudronin/physmap/main/docs/talk/figures/bench_4_home_baseline.png)

**The full matrix** — every dataset, at the default setting (the 99th percentile), with how its
home error was obtained, its error rates and its limitation:

| Dataset | Detectors see the cause? | Home error: how obtained | Home wrong | Deployed wrong | Wrong, flagged only by PhysMAP | Accurate, flagged anyway | Limitation |
|---|---|---|---|---|---|---|---|
| `casper_hypersonic_transition` — hypersonic transition | no | fitted; held out by refit (in-sample 2 of 159) | 6 of 159 (4%) | 8 of 8 (100%) | 4 of 8 | 0 | — |
| `dirker_water` — water, horizontal tube | partly | fitted; held out by refit (in-sample 0 of 31) | 0 of 31 (0%) | 11 of 60 (18%) | 2 of 11 | 16 | the cause is partly visible |
| `naca_tn1451` — heated pipe, entrance region | no | published correlation; 40 of 40 inside its range | 0 of 40 (0%) | 9 of 45 (20%) | 9 of 9 | 19 | the applicability case above, same data — not separate evidence |
| `jin_sco2_buoyancy` — supercritical CO2, vertical tube | no | published correlation; 11 of 17 inside its range | 17 of 17 (100%) | 26 of 27 (96%) | 15 of 26 | 0 | wrong almost everywhere: no home baseline |
| `velazquez_sco2` — supercritical CO2, property variation | partly | published correlation; 197 of 393 inside its range | 386 of 393 (98%) | 67 of 67 (100%) | 18 of 67 | 0 | wrong almost everywhere: no home baseline |
| `marineau_hypersonic_transition` — hypersonic transition | yes | fitted; held out by refit (in-sample 0 of 9) | 5 of 9 (56%) | 6 of 6 (100%) | 0 of 6 | 0 | the control; nine home rows are too few |
| `forrest` — rectangular channel | yes | published correlation | 0 of 1 | 4 of 4 (100%) | not tested | — | one training row; triage-grade values |

"Wrong" is each dataset's own threshold, set from measurement noise; "accurate" is a tighter
one, with a dead band between them. Home error is labelled by how it was obtained: where the
surrogate was fitted to the home rows, it is also refitted without each row in turn; a
published correlation was never fitted to them.

- **Where the evidence holds:** Casper and Dirker have a home baseline from which deployment
  fails — and NACA, which is the applicability case above.
- **Where the reading stops:** Jin and Velazquez keep their counts, but their correlations are
  wrong almost everywhere, at home too, so the counts cannot show that deployment created the
  failure.
- **Where PhysMAP adds nothing:** Marineau, where the cause is a surrogate input and the
  detectors already see it.
- **Accurate predictions flagged anyway:** PhysMAP flags every prediction outside a closure's
  supported region, accurate or not — 19 for NACA, 16 for Dirker. As detection those are false
  alarms; as applicability assurance, they are predictions the closure does not support.
- **The kind of model:** on Casper, three model types pass the home check and each leaves 4 of
  8 errors only PhysMAP flags. On NACA all three pass too, but its home reads repeat — 40 rows,
  5 distinct values — so leave-one-out says little there. On Jin and Velazquez none passes.

No gate decides a dataset's reading: the counts and rates are the evidence, and
`physmap benchmark report` prints each dataset's interpretation as prose. Counts are rows of
each dataset, not independent cases, never pooled into a rate, and digitised from publications.
A one-sided Fisher exact test was run after the counts were seen; it is reported as exploratory
and decides nothing.

**Bank v0.4.1.** It corrects the NACA source data: the original bank's NACA row came from an
automated read of the figure later found invalid — wrong axis calibration, points on gridline
crossings — and its "20 of 20" is withdrawn. The original bank is kept unchanged for audit, not
as evidence. See [`data/naca/CORRECTION_v0_4_1.md`](https://github.com/cloudronin/physmap/blob/main/data/naca/CORRECTION_v0_4_1.md).

## The benchmark: seven vehicles, all rerunnable

```bash
physmap benchmark report     # all seven outcomes, the counts above and the home baseline
physmap benchmark run        # recomputes all seven from this checkout, diffs against the bank
physmap benchmark coverage   # what that subset does and does not cover
physmap benchmark architectures --banked   # three model types per vehicle; drop --banked to retrain (PyTorch)
```

All seven vehicles ran, all seven outcomes are reported, and **all seven now ship their
source data**.

**`physmap benchmark run` recomputes all seven from this checkout and diffs the result
against the committed matrix.** Every field of every cell, not just the headline outcome.
It exits non-zero if anything drifted, and never writes the bank it is checking itself
against.

Floats are compared within `1e-9` relative, everything else exactly — and the distinction
is load-bearing rather than a convenience. Every field that decides an outcome is an int
or a string (counts, verdicts, outcome labels, observability classes), so the tolerance
cannot absorb a real change. It exists because a clean-clone check on numpy 2.5 found
`dirker_water.observability_score` differing from the banked value by **one unit in the
last place**. A match that needed the tolerance is reported as such, not as "identical".

`physmap benchmark report` reads the bank without running anything, and says so — the
report distinguishes a recomputed row from a banked one, and the counts are computed
rather than written down, so they cannot quietly go stale.

**Shipping is also not licensing.** Two of the seven carry affirmative permission:
`naca_tn1451` (public domain) and `velazquez_sco2` (CC BY 4.0). **Five do not**, and the
registry and report label them rather than calling everything clear:

- `marineau_hypersonic_transition` — no licence and **no prohibition**. Values transcribed
  from a published table in a publicly funded, public-release, government-hosted document.
- `forrest`, `casper_hypersonic_transition`, `dirker_water`, `jin_sco2_buoyancy` —
  published **against** express publisher terms. AIAA prohibits using its content to
  develop machine-learning models; ASME and Elsevier require permission to reproduce, and
  Elsevier's licence forbids systematic redistribution. Risks accepted knowingly, not
  findings that the terms do not apply.

All five redistribute **numbers only** — no paper, figure or PDF, enforced by two audits —
and all five are removed on objection, from the repository and every later release. A version
already archived on Zenodo stays archived; only Zenodo can withdraw it. The full basis,
including the arguments against, is in [data/REDISTRIBUTION.md](https://github.com/cloudronin/physmap/blob/main/data/REDISTRIBUTION.md) and [NOTICE](https://github.com/cloudronin/physmap/blob/main/NOTICE).

**One dataset is published but not benchmark-grade.** `forrest`'s own header calls its
values visual estimates for triage only, and its cell is degenerate — one training row, no
detector fit — so its `DO_NO_HARM` outcome is short-circuited rather than earned. Being
legal to publish and being fit to benchmark on are different questions; the registry tracks
them on separate axes. `physmap benchmark coverage` prints it.

## Three checks, deliberately kept apart

These are different claims resting on different evidence. Conflating them is the
specific error this project is built to avoid, so nothing here attributes the results of
one to another.

| Check | Question | Status | Evidence |
|---|---|---|---|
| **Closure validity** | Is this closure relation being applied outside the range it was calibrated on? | Shipping | applicability assurance (NACA x/D); the seven-vehicle benchmark |
| **Surrogate observability** | Can the surrogate's inputs even represent the variable that governs the failure? | Shipping | the same |
| **Causal materiality** | Is the out-of-range mechanism large enough to matter for the quantity of interest? | Preview — method, plus one controlled stress test | Lewis 35A, the main controlled demonstration |

## What this release claims

This build is `CAUSAL_PREVIEW`. `physmap.release.CURRENT_RELEASE_STATE` says so, and the
command-line surface is derived from that constant rather than from which files happen to
be on disk — so an unfinished feature is an unrecognised command, never a runtime
data-missing error.

The causal-materiality API is present: the ablation counterfactual, the applicability
screen, the independence guard, and deterministic explanations. Its fixtures are
**synthetic or declarative** — constructed inputs, or preconditions asserted from a case
description. Beyond them, **one controlled stress test runs the causal path on a real
experiment** (below) — a development demonstration on a single run, not an evaluation.

**No precision, recall or F1.** None is computed, reported or shipped anywhere in this
package, and a test parses the package and fails if one appears. The benchmark reports counts
per dataset, never a rate across datasets. The causal-materiality results presented in the NAFEMS
Multiphysics 2026 abstract are **not** reproduced here: the original study's inputs are
gone, and the basis for its experimental truth is unresolved. A reconstruction is under
way under a locked protocol that fixes its rules before any rebuilt number is examined.

Because the original grid, truth source and counterfactual all change, the best outcome
available to that reconstruction is **independent corroboration** of the causal finding —
not reproduction of the published numbers. The protocol defines `REPRODUCED` and marks it
unreachable, so the word cannot drift onto a weaker result. See
[`protocols/`](https://github.com/cloudronin/physmap/tree/main/protocols).

## Install

```bash
pip install physmap
```

That gives you the library, the `physmap` command and the seed corpus. Python 3.10 or newer.

**To run the benchmark, the Lewis stress test or the examples, install from a clone:**

```bash
git clone https://github.com/cloudronin/physmap
cd physmap
pip install -e .
```

Their data lives in the repository, outside the package, on purpose — partly because of
redistribution terms and partly because it is not runtime data. From a plain
`pip install physmap`, those commands say so in one sentence and stop.

Optional extras: `[jsonld]` adds evidence export via `uofa`, `[experiment]` adds
`matplotlib` for benchmark figures, `[architectures]` adds PyTorch for the DeepONet in
`physmap benchmark architectures`, `[dev]` adds the test tooling.

## Using the guardrail

The guardrail does not guess which checks to combine. Its setup decides.

```python
from physmap import ColumnMap, CredibilityGuardrail, Regime

guard = CredibilityGuardrail(
    surrogate_inputs=["Re", "Pr"],          # exactly the inputs your surrogate takes
    regime=Regime.ENTRANCE_REGION_PIPE,     # the physics it is used in: picks the closures
)
cols = ColumnMap(inputs=["Re", "Pr", "x_over_D"])   # the surrogate inputs, plus every
                                                    # variable those closures put a bound on
guard.fit(train_X, train_y=train_y, columns=cols)   # arrays whose columns follow `cols`
for a in guard.assess(test_X, columns=cols):
    print(a.verdict.name, a.rationale)
```

**What each piece does**

- **`surrogate_inputs`** — the columns your surrogate actually uses. The input-based OOD
  detectors are fitted on exactly these.
- **`regime`** — picks the closure relations whose validated ranges the closure check uses.
  Choose the regime that matches your physics, or name one closure with `closure_id=`. If none
  matches, use `Regime.UNLISTED`: the guardrail then runs the OOD detectors alone.
- **The data columns** — must include every variable those closures bound, even ones the
  surrogate never sees (here `x_over_D`). If one is missing, `fit` stops and names it.
- **`train_y`** — the training targets. The GP-variance detector needs them.
- **`detectors=`** — optional. The default is novelty density and GP variance (the input-based
  OOD detectors) plus closure validity. Distance-to-training and a conformal residual check are
  also available.

**How the verdict is combined, for each prediction**

- At setup, each bounded variable is classed **observable** (it is a surrogate input),
  **unobservable** (it is not), or **partial**. `guard.observability_classification` shows the
  result.
- The closure check fires on an **unobservable** variable → `REJECT`. The OOD detectors
  cannot see that variable, so the closure check is trusted.
- It fires on a **partial** variable → a calibrated blend where a calibration exists,
  otherwise `UNCERTAIN`.
- Otherwise — the closure check is quiet, or the variable is one the detectors can see — the
  OOD detectors decide: none fired → `TRUSTWORTHY`, a reject-level fire → `REJECT`, anything
  else → `WARN`.

Every listed regime's closures ship in the published corpus. A complete, runnable version of
the example above is
[`examples/naca_entrance_region.py`](https://github.com/cloudronin/physmap/blob/main/examples/naca_entrance_region.py).

## The corpus

The code is MIT and the corpus data is CC BY 4.0 — see the licences below.

Published here is the **seed**: 15 closure relations with their validated bounds, plus an
index of 201 closures with no bounds. A larger 53-closure corpus exists and is not published.
**Nothing in this repository needs it.** The seven-vehicle benchmark, the Lewis stress test
and the examples all run on the published seed, and CI checks that on a clean checkout.

What gets published is decided by an **allowlist**, not a blacklist: an entry ships only if
it is on the list, and every published bound's provenance grade reads `seed`. The evidence
corpus follows the same list, so its claims and sources cannot carry bounds for closures that
are not published. It is derived deterministically by
[`dev/tools/split_evidence_corpus.py`](https://github.com/cloudronin/physmap/blob/main/dev/tools/split_evidence_corpus.py), whose
`--check` mode fails on drift.

To use a different corpus, point `$PHYSMAP_CORPUS` at it. The loader checks
`$PHYSMAP_CORPUS`, then an installed corpus package, then the bundled seed — no code changes.

## Licences

Two, because the code and the data are different things.

- **Code** — MIT. See [LICENSE](https://github.com/cloudronin/physmap/blob/main/LICENSE).
- **Data** — CC BY 4.0. See [LICENSE-CORPUS](https://github.com/cloudronin/physmap/blob/main/LICENSE-CORPUS).

[NOTICE](https://github.com/cloudronin/physmap/blob/main/NOTICE) states which files fall under which, in one page.

The data licence is scoped, and the scope matters. It covers the curated corpus as
authorship: the selection, structuring, regime mapping, bound assignment and provenance
annotation. It does **not** cover numerical values digitised from third-party
publications — those measurements were not made here, so no copyright in them is claimed.
They are governed by their publishers' terms, by public-domain status, or are
uncopyrightable facts, and each file records its own redistribution determination. A
citation is attribution, not permission.

No source PDF is redistributed. Papers are cited, not copied.

## Citing

Cite the software by its DOI, [10.5281/zenodo.22950742](https://doi.org/10.5281/zenodo.22950742). That DOI always points to
the latest version; each version also has its own DOI, listed on the Zenodo record.
[`CITATION.cff`](https://github.com/cloudronin/physmap/blob/main/CITATION.cff) holds the full metadata. Attribution is required by
CC BY when you redistribute or build on the data.

## Tests

```bash
pytest tests/ -q -n auto
```

Several tests guard failures whose symptom is a wrong answer rather than an exception:
the closure index loading as empty, the corpus silently resolving to the wrong tier, the
evidence corpus leaking a non-seed closure, and `rdflib` creeping back onto the import
path through an unused import.
