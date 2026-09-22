# Known-results declaration — NAFEMS 2026 reconstruction

**Status:** final. Written 2026-09-22, *before* any reconstructed outcome was examined.

## Why this document exists

The usual honesty device for an evaluation is pre-registration: you write down what you
will measure before you know the answer. That is **not available here**, because the
results are already published in the NAFEMS Multiphysics 2026 extended abstract
(Multi26-0009318). Calling the accompanying protocol a "pre-registration" would be false.

This declaration is the honest substitute. It records, in full and in advance, exactly
which original results were already known to the people performing the reconstruction.
A reader can then judge the reconstruction knowing precisely what its authors knew.

## What was already known

From the submitted extended abstract, on the mixed-convection vertical-pipe case:

| Quantity | Known value |
|---|---|
| Physics-blind guardrails (input-space OOD) | precision 0.88, recall 0.06, F1 0.12 |
| Naive box-check | precision 0.73, recall 0.68, F1 0.71 |
| PhysMAP causal materiality | precision 1.00, recall 0.65, F1 0.79 |
| Materiality range across Richardson number | 0.04 to 0.26 |
| Materiality threshold used | θ ≈ trust tolerance = 0.10 |
| CFD vs independent experiment | agreement to within about 9%; 3.7% and 9.3% at two Richardson numbers |

Qualitative claims also known in advance:

- The precision (false-alarm) advantage over naive box-checking is **unconditional** across
  the threshold sweep.
- The F1 advantage over naive box-checking is **conditional** on aligning the materiality
  threshold with the trust tolerance.
- The lift is **structural**: causal materiality predicts the forced-convection surrogate's
  error because both reflect the same buoyancy physics.
- Screening outcomes: mixed convection → lift demonstrated; conjugate heat transfer →
  screened out (conduction-dominated, same-closure truth); FDA benchmark blood pump →
  screened out (shear-dominated, apparent shift refused as an artifact).

## What was NOT available

The original study's inputs are gone. Specifically absent at the time of writing:

- The CFD working tree (`~/physmap-wall/`) and `conv_step3_final.json`.
- Per-operating-point `Nu_M` and `Nu_F` (the ablation pair).
- The two-dimensional `(Re, Gr*)` grid actually evaluated.
- The surrogate predictions.
- The experimental-truth table and its per-point uncertainties.

Only the abstract's figures (as raster images) and its prose survive.

## Consequence

This is a **reconstruction, not a reproduction**. It will produce its own numbers under a
locked protocol. Those numbers are not the numbers above, and the public release does not
present them as reproducing the abstract. Any divergence is reported as measured, not
reconciled toward the published values.

### The best outcome available to it

Not reproduction. **Independent corroboration of the causal finding.**

Reproduction would mean a close rerun of the original evaluation — the same grid, the same
truth source, the same counterfactual. The list above shows why that is not available: those
inputs are gone. The reconstruction necessarily changes all three, so however well its numbers
land, the claim it can support is corroboration under different inputs, not recovery of the
published values.

The protocol names the same thing the same way. Its section 9 defines `REPRODUCED` and marks
it **unreachable**, so the word keeps a fixed meaning and cannot slide onto a weaker result;
a matching result is `CORROBORATED` instead.

**These two documents must agree. Neither may be changed without the other.**

### What the numbers will look like when reported

Always with their uncertainty, never as bare point estimates.

How much those metrics can establish depends on how many independent measurements exist,
and on how they are balanced across trustworthy, untrustworthy and flagged. Neither is
known yet, so no threshold, minimum sample size or agreement margin is proposed here.

The two are **not** discovered at the same time, and the order is load-bearing. The
measurement inventory establishes what exists — sources, operating points, eligibility,
whether each point has an uncertainty — and records **no labels, no flags and no class
balance**, because those are outcomes of applying the label rule and the flag rule, not
properties of the data. The corroboration criterion is then fixed as a decision rule over
the balance, before the balance is computed. Only afterwards are labels, flags and counts
derived, and they are reported with the result.

Choosing the criterion after seeing the balance would be choosing it knowing which way it
falls. See the measurement inventory and the two-stage lock in the protocol.
