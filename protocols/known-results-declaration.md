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
