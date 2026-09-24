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

## The source paper, read — and one figure corrected

Mohammed & Salman (2008) has since been obtained and read in full. Two facts change what
can be written into the protocol.

**The measurement uncertainty on Nusselt number is ±1.27%, not ±8%.** The paper reports
±1.27% following Moffat's method, combined from heater power (±0.13%), temperature
difference (±0.21%), heat transfer rate (±1.1%), surface area (±1.2%) and air flow rate
(±0.01%); also ±1.35% on Re and ±1.13% on Ra. The **±8%** this project carried is the
paper's stated *"overall accuracy of heat transfer data in these correlations"* — the
scatter of the data about the fit, a property of the correlation, not of the measurement.

**This entangles the truth choice with the label rule.** The abstract's rule needs the gap
to exceed both the tolerance and the truth's own uncertainty, so which uncertainty enters
depends on what the truth is: ±1.27% for a measured value, ±8% for a correlation. A third
term — the error in recovering values from the published plots — is **not yet quantified**
and could be the largest of the three. **No claim is made about whether the second
condition binds**; that needs the extraction error measured first.

**Individual values are recoverable but not yet recovered.** No data tables exist: 88 test
runs across four entrance lengths and both flow directions, all reported in 16 figures.
The figures are vector graphics, so marker coordinates are embedded exactly and recovery
is extraction rather than visual digitisation. Upward flow — the case Eq 13 describes — is
the thinner half of the paper, carried by Figures 9, 14 and 16. Per-point uncertainty does
not exist; only the global ±1.27%.

## How these numbers were produced — established after this declaration was written

Two properties of the original construction were traced from surviving artifacts and
recorded here, because they change what the table above can be read as saying.

**The table is correlation-referenced.** No pointwise measurement was used. The truth was
Mohammed & Salman's assisting-flow correlation `Nu = 3.7151 (Ra/Re)^0.11868`, evaluated
densely across the grid. Every cell in the table — including recall and including the
baselines' figures — was scored against that correlation, not against their measurements.
The numbers are to be described as **correlation-referenced** wherever they appear.

**The table may be strongly favoured by the test construction.** The surrogate was a
forced-convection closure fitted to the gravity-off CFD, and the materiality numerator
`Nu_F` is that same gravity-off CFD. The relative surrogate error then satisfies

    E = d − m(1 + d) + ε

so that for small `d` and `ε` the label rule `|E| > tol` approaches the flag condition
`m ≥ θ`, and with `θ ≈ tol` a flagged point is labelled untrustworthy.

**This is a mechanism, not a proof.** It is conditional on three things that are not
established: Step 4's error scale (unknown), the surrogate fit residual `ε` (unrecoverable
— no coefficients, R² or residual survive), and the behaviour of `d` across the grid (two
observations, both at `Ri ≥ 1.8`, both negative; the low-`Ri` corner was never validated).

The consequence for the reconstruction is an inversion worth stating plainly:
**recovering precision ≈ 1.00 would be evidence that the coupling survived, not evidence
that the method works.**

Full derivation, assumptions with their recovery status, and the conditions under which
false positives remain possible: `docs/findings/surrogate-and-truth-provenance.md`.

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

## Protocol wording clarified — 2026-09-23

Recorded here because this declaration and the protocol change together.

The protocol's rule for the spent Lewis runs — 13A, 16A and 35A — said they "may not
contribute to any precision, recall, F1 or materiality figure". It now says any **scored**
figure. Read literally, the old wording contradicted the protocol's own rule for presenting
results while θ is unlocked, which reports 35A's materiality as a labelled development
demonstration.

The author's ruling: a spent run may not enter any metric, or any figure counted as
validation. It may appear in a labelled development demonstration.

Wording only. No run, result, threshold or rule changed; metrics stay closed. Nothing in
this declaration's record of what was known is affected.
