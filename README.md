# PhysMAP

Physics-aware credibility checks for AI surrogates in multiphysics simulation.

A surrogate trained on `(Re, Pr)` over the fully-developed region of a heated pipe is
blind to `x/D`, the variable that actually governs the entrance region. So it fails
there, confidently. And so does an input-space novelty detector, because it sees the
same two columns the surrogate does — and in those two columns the entrance points look
perfectly ordinary.

PhysMAP reads the bound variable from the test coordinates instead of from the
surrogate's inputs, checks it against the closure relation's validated range, and knows
at fit time whether that variable is structurally observable to the surrogate at all.

```
verdicts: {'REJECT': 45}
rationale: Prediction relies on gnielinski-1976 beyond its validated x_over_D bound
           (x_over_D >= 10); x_over_D is not a surrogate input (unobservable to
           statistical detectors), and the literature (Tam & Ghajar 1998) reports
           divergence up to -63% past this bound. Statistical baselines are silent
           because they cannot observe x_over_D.
```

No LLM is in any path. Every explanation is a deterministic rendered template.

Run it yourself: [`examples/naca_entrance_region.py`](examples/naca_entrance_region.py).

## Three checks, deliberately kept apart

These are different claims resting on different evidence. Conflating them is the
specific error this project is built to avoid, so nothing here attributes the results of
one to another.

| Check | Question | Status |
|---|---|---|
| **Closure validity** | Is this closure relation being applied outside the range it was calibrated on? | Shipping |
| **Surrogate observability** | Can the surrogate's inputs even represent the variable that governs the failure? | Shipping |
| **Causal materiality** | Is the out-of-range mechanism large enough to matter for the quantity of interest? | Not built yet |

## What this release claims

This build is `GUARDRAIL`. `physmap.release.CURRENT_RELEASE_STATE` says so, and the
command-line surface is derived from that constant rather than from which files happen to
be on disk — so an unfinished feature is an unrecognised command, never a runtime
data-missing error.

**It makes no performance claim.** No precision, recall or F1 is computed, reported or
shipped anywhere in this package. The causal-materiality results presented in the NAFEMS
Multiphysics 2026 abstract are **not** reproduced here: the original study's inputs are
gone, and the basis for its experimental truth is unresolved. A reconstruction is under
way under a locked protocol that fixes its rules before any rebuilt number is examined.

Because the original grid, truth source and counterfactual all change, the best outcome
available to that reconstruction is **independent corroboration** of the causal finding —
not reproduction of the published numbers. The protocol defines `REPRODUCED` and marks it
unreachable, so the word cannot drift onto a weaker result. See
[`protocols/`](protocols/).

## Install

```bash
pip install -e .
```

Python 3.10 or newer.

**The editable install from a checkout is the supported path**, not a wheel. Fixture and
benchmark data live in the repository, outside the package, on purpose — partly because
of redistribution terms and partly because they are not runtime data. A wheel install
gives you the library and the seed corpus; it cannot run the benchmark.

Optional extras: `[jsonld]` adds evidence export via `uofa`, `[experiment]` adds
`matplotlib` for benchmark figures, `[dev]` adds the test tooling.

## The corpus is open-core

The library is open. The calibration corpus is the commercial moat.

Published here is the **seed**: 15 closures with their validated bounds, plus a
verdict-free index of 201 closures. The full 53-closure corpus is not published. The
firewall is an **allowlist**, not a blacklist — an entry ships only if it is on the list,
and every bound's provenance grading is replaced with `seed`.

The same firewall applies to the evidence corpus, so claims and sources cannot leak
bounds for closures the seed withholds. It is derived deterministically by
[`dev/tools/split_evidence_corpus.py`](dev/tools/split_evidence_corpus.py), which has a
`--check` mode that fails on drift.

Resolution order is `$PHYSMAP_CORPUS` → an installed premium package → the bundled seed.
A premium holder drops the file in; no code changes.

## Licences

Two, because the code and the data are different things.

- **Code** — MIT. See [LICENSE](LICENSE).
- **Data** — CC BY 4.0. See [LICENSE-CORPUS](LICENSE-CORPUS).

The data licence is scoped, and the scope matters. It covers the curated corpus as
authorship: the selection, structuring, regime mapping, bound assignment and provenance
annotation. It does **not** cover numerical values digitised from third-party
publications — those measurements were not made here, so no copyright in them is claimed.
They are governed by their publishers' terms, by public-domain status, or are
uncopyrightable facts, and each file records its own redistribution determination. A
citation is attribution, not permission.

No source PDF is redistributed. Papers are cited, not copied.

## Citing

[`CITATION.cff`](CITATION.cff). Attribution is required by CC BY when you redistribute or
build on the data.

## Tests

```bash
pytest tests/ -q -n auto
```

Several tests guard failures whose symptom is a wrong answer rather than an exception:
the closure index loading as empty, the corpus silently resolving to the wrong tier, the
evidence corpus leaking a non-seed closure, and `rdflib` creeping back onto the import
path through an unused import.
