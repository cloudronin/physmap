# The abstract's precision, recall and F1

**Short version:** the accepted abstract reports precision 1.00, recall 0.65 and F1 0.79 for
PhysMAP. The talk does not present them as experimental validation, and it says so on a slide,
by name. Rebuilding the study showed two things: the numbers were scored against a fitted
correlation rather than measurements, and the way the test was built ties the flag to the label.
That led to a stronger test — controlled, pre-declared, on one real experiment — and a smaller
claim.

---

## What the abstract says

From the accepted extended abstract (Multi26-0009318), on laminar mixed convection in a vertical
pipe, at θ ≈ tol = 0.10:

| | precision | recall | F1 |
|---|---|---|---|
| Physics-blind guardrails (input-space OOD) | 0.88 | 0.06 | 0.12 |
| Naive box-check | 0.73 | 0.68 | 0.71 |
| PhysMAP causal materiality | 1.00 | 0.65 | 0.79 |

It also reports the CFD agreeing with an independent experiment "to within about nine percent",
and materiality rising from 0.04 to 0.26 across Richardson number. It describes the scores as
"against experimental truth".

The same values are recorded in `protocols/known-results-declaration.md`, written before any
reconstruction was examined.

## They stay in the record

Nothing is deleted, softened or silently swapped. The abstract says what it says. The talk names
the numbers, explains what they are, and moves on. It does not put a new number in their place
on the same slide.

## What rebuilding them showed

**1. The truth was a correlation, not measurements.** The "experimental truth" was Mohammed &
Salman's assisting-flow correlation, evaluated densely across a (Re, Gr*) grid. No individual
measurement entered. Every cell of the table — the baselines included — was scored against it.
The accurate word is *correlation-referenced*.

**2. The construction couples the flag to the label.** The surrogate was a forced-convection fit
to the gravity-off CFD, and the materiality's numerator is that same gravity-off CFD. The
surrogate's relative error then works out as

    E = d − m(1 + d) + ε

where m is the materiality, d is the CFD's own gap to the truth, and ε is the fit error. When d
and ε are small, "error above the tolerance" becomes "materiality above θ". With θ set equal to
the tolerance, a flagged point tends to be labelled untrustworthy by construction. **A high
precision is what the construction produces, whether or not the method is doing useful work.**
Recovering 1.00 in a rebuild would show that the coupling survived — not that the method works.
This is a mechanism, not a proof: how strongly it acted depends on quantities that no longer
exist.

**3. The inputs are gone.** The CFD working tree, the ablation pairs, the evaluated grid, the
surrogate predictions and the truth table no longer exist. The numbers cannot be rerun, only
rebuilt on different inputs — and then the most a match could mean is corroboration, not
reproduction.

Full derivation: `docs/findings/surrogate-and-truth-provenance.md`.

## What replaced them

A narrower claim, tested harder:

- **An explicit input contract**, asserted by the command: the surrogate and the input-based OOD
  detector see the same inputs, and every deployment input is a training input.
- **A matched CFD ablation**: two cases differing only in gravity.
- **A pre-declared design**, with success criteria committed before any output existed.
- **Continuous materiality**, θ unlocked, and **no rates**.
- **One command from a clean clone**, which checks itself against a committed record.

The claim it supports: PhysMAP detects when model reuse activates a mechanism outside the
surrogate's observable inputs, and an input-based detector cannot. It is not a detection rate.

## The coupling has not gone away — it is disclosed

The Lewis test has the same structure: the surrogate and the materiality both rest on the
gravity-off CFD. That is one reason it reports no rate. What it shows instead is which output
changes when the physics changes, with the visible inputs held exactly fixed. The measurement
adds one independent fact: downstream, Lewis's data side with the gravity-on CFD, not the
gravity-off one.

## What to say on the slide — about thirty seconds

> "The abstract reports precision 1.00 and recall 0.65. When we rebuilt the study, we found they
> were scored against a fitted correlation rather than measurements, and that the way the test
> was built ties the flag to the label — so a high precision was partly built in. We are not
> presenting them as experimental validation. What follows is a smaller claim we can defend: a
> controlled test on one real experiment."

## What would change this

New precision and recall only from an eligible set of independent cases, each with its own
measured truth and uncertainty, chosen by rules fixed before any outcome is seen, and scored
under the locked protocol — reported with their uncertainty, and never beside the original
triple.
