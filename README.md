# PhysMAP

Physics-aware credibility checks for AI surrogates in multiphysics simulation.

A surrogate trained on `(Re, Pr)` over the fully-developed region of a heated pipe is
blind to `x/D`, the variable that actually governs the entrance region. So it fails
there, confidently. And so does an input-based OOD detector, because it sees the
same two columns the surrogate does — and in those two columns the entrance points look
perfectly ordinary.

PhysMAP reads the bound variable from the test coordinates instead of from the
surrogate's inputs, checks it against the closure relation's validated range, and knows
at fit time whether that variable is structurally observable to the surrogate at all.

```
verdicts: {'REJECT': 45}
rationale: Prediction relies on gnielinski-1976 beyond its validated x_over_D bound
           (x_over_D >= 10); x_over_D is not a surrogate input (unobservable to
           input-based OOD detectors), and the literature (Tam & Ghajar 1998) reports
           divergence up to -63% past this bound. Input-based OOD detectors are silent
           because they cannot observe x_over_D.
```

No LLM is in any path. Every explanation is a deterministic rendered template.

Run it yourself: [`examples/naca_entrance_region.py`](https://github.com/cloudronin/physmap/blob/main/examples/naca_entrance_region.py).

## Three checks, deliberately kept apart

These are different claims resting on different evidence. Conflating them is the
specific error this project is built to avoid, so nothing here attributes the results of
one to another.

| Check | Question | Status |
|---|---|---|
| **Closure validity** | Is this closure relation being applied outside the range it was calibrated on? | Shipping |
| **Surrogate observability** | Can the surrogate's inputs even represent the variable that governs the failure? | Shipping |
| **Causal materiality** | Is the out-of-range mechanism large enough to matter for the quantity of interest? | Preview — method, plus one controlled stress test |

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

**It makes no performance claim.** No precision, recall or F1 is computed, reported or
shipped anywhere in this package. A test parses the package and fails if one appears. The causal-materiality results presented in the NAFEMS
Multiphysics 2026 abstract are **not** reproduced here: the original study's inputs are
gone, and the basis for its experimental truth is unresolved. A reconstruction is under
way under a locked protocol that fixes its rules before any rebuilt number is examined.

Because the original grid, truth source and counterfactual all change, the best outcome
available to that reconstruction is **independent corroboration** of the causal finding —
not reproduction of the published numbers. The protocol defines `REPRODUCED` and marks it
unreachable, so the word cannot drift onto a weaker result. See
[`protocols/`](https://github.com/cloudronin/physmap/tree/main/protocols).

## A controlled model-reuse stress test: Lewis 35A

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
| gravity off — the accurate control | within 0.06 % | identical in both rows | 0 |
| gravity on — Lewis's measurement | 17–18 % downstream | identical in both rows | up to 0.195 |

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

## The benchmark: seven vehicles, all rerunnable

```bash
physmap benchmark report     # all seven outcomes, each marked recomputed or banked
physmap benchmark run        # recomputes all seven from this checkout, diffs against the bank
physmap benchmark coverage   # what that subset does and does not cover
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
and all five are removed on objection. The full basis, including the arguments against, is
in [data/REDISTRIBUTION.md](https://github.com/cloudronin/physmap/blob/main/data/REDISTRIBUTION.md) and [NOTICE](https://github.com/cloudronin/physmap/blob/main/NOTICE).

**One dataset is published but not benchmark-grade.** `forrest`'s own header calls its
values visual estimates for triage only, and its cell is degenerate — one training row, no
detector fit — so its `DO_NO_HARM` outcome is short-circuited rather than earned. Being
legal to publish and being fit to benchmark on are different questions; the registry tracks
them on separate axes. `physmap benchmark coverage` prints it.

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
`matplotlib` for benchmark figures, `[dev]` adds the test tooling.

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

[`CITATION.cff`](https://github.com/cloudronin/physmap/blob/main/CITATION.cff). Attribution is required by CC BY when you redistribute or
build on the data.

## Tests

```bash
pytest tests/ -q -n auto
```

Several tests guard failures whose symptom is a wrong answer rather than an exception:
the closure index loading as empty, the corpus silently resolving to the wrong tier, the
evidence corpus leaking a non-seed closure, and `rdflib` creeping back onto the import
path through an unused import.
