# Lewis (1992) — truth-source assessment, inputs only

*J. S. Lewis, **An Experimental and Computational Study of Laminar Combined Natural and
Forced Convection in Vertical Ducts**, doctoral thesis, City, University of London, 1992.
323 pages. Open access:*
<https://openaccess.city.ac.uk/id/eprint/28530/>

**No labels, flags, detector outputs or performance metrics appear here.** Screening is on
source-reported diagnostics only, as it must be: the source's own energy-balance errors
are read *before* anything about detector behaviour.

## Why this source is different from everything assessed so far

It is **openly accessible**. Every other candidate — Mohammed & Salman, the ECM companion,
Behzadmehr, Joye, Brown & Gauvin — is paywalled. This one can be read, checked and
re-checked by anyone, which changes what a determination based on it is worth.

And it reports **per-run identifiable conditions**, which is the thing Figure 16 could not
give: `Re`, `Pr`, `Gr`, `Gr(q)`, `Ra`, `Gz`, flow rate, inlet and exit bulk temperature,
mean wall temperature, heat input, heat loss, wall heat flux — and an **energy-balance
error per run**.

## It cannot validate the existing air case

| | Mohammed & Salman / the rebuilt case | Lewis |
|---|---|---|
| Fluid | Air, `Pr ≈ 0.7` | **Water, `Pr ≈ 6.7–8.5`** |
| Diameter | 30 mm | **11.9 mm** |
| Heated `L/D` | 30 | **≈ 160** |
| Wall condition | Uniform heat flux | Uniform heat flux |
| Direction | Upward | Upward |

An order of magnitude in Prandtl number and more than five times the `L/D`. **Lewis needs
its own matched CFD case**, built to its geometry and its fluid. It is not a check on the
air case and is not treated as one.

## Run 35A — the one fully tabulated run

Appendix D prints a complete data reduction for **35A**, and it is the only run with
printed numerical local Nusselt values.

| | Inlet-bulk basis | Mean-bulk basis |
|---|---|---|
| `Re` | 1143.4 | 1417.1 |
| `Pr` | 8.46 | 6.66 |
| `Gr` (ΔT-based) | 39,244 | 105,624 |
| `Gr(q)` (flux-based) | 374,663 | 985,678 |
| Mean `Nu` | 9.55 | 9.33 |

Flow 0.7679 L/min, 11.189 V × 81.44 A = **911.20 W**, wall flux **12,749.6 W/m²**, inlet
bulk 13.06 °C, exit bulk 29.32 °C, mean wall 48.36 °C, heat loss 5.58 W,
**energy-balance error −3.96%**.

**Twelve local values**, at `x/d` = 0.31, 0.85, 2.45, 5.65, 9.92, 16.32, 33.39, 50.47,
67.55, 101.69, 135.84, 159.33 — each with `(T_w − T_b)_x`, `h(x)`, `(x/d)/RePr` and
`Nu(x)`, on both property bases. Wall thermocouples sit at 4, 10, 29, 67, 118, 194, 397,
601, 804, 1210, 1617 and 1896 mm.

**These twelve are twelve observations of ONE case, not twelve cases.** The operating
condition is what a detector would be evaluated on; the axial profile is that condition's
measurement.

## Eligibility screen — source-reported energy balance, before anything else

All 30 runs, from Table E.1. Transcribed as reported; nothing derived or adjusted.

| \|error\| | Runs | Which |
|---|---|---|
| ≤ 2% | **12** | 6A 7A 11A 12A 13A 15A 19A 25A 29A 30A 31A 32A |
| ≤ 3% | 16 | + 8A 14A 23A 24A |
| ≤ 5% | 19 | + 10A 28A **35A** |
| ≤ 10% | 29 | all but 18A |

Distribution: minimum 0.04%, **median 2.32%**, maximum 12.52%. Worst five: 18A (−12.52%),
16A (−9.32%), 26A (−8.92%), 21A (−8.87%), 22A (−7.40%).

**The best-documented run is not the best-behaved one.** 35A carries −3.96%, worse than
the median. It is the only run with printed local `Nu`, so it is where any work must
start, and it is not a run that would survive a strict energy-balance screen.

## What uncertainty can actually be reconstructed

**Per-point measurement uncertainty: not established.** Do not assume it exists. What the
thesis demonstrably provides per run:

- the **energy-balance error**, a closure diagnostic, not a measurement uncertainty;
- the **heat-loss correction** `Q_loss` alongside `Q_g`, so the loss fraction is
  computable (0.5–3.1% of input across the runs);
- both an **inlet-bulk** and a **mean-bulk** property basis, whose difference is a real
  and quantifiable sensitivity in the reduction — for 35A, mean `Nu` 9.55 versus 9.33, and
  `Re` 1143 versus 1417.

That last is worth naming: **the property basis changes `Re` by 24%.** Any matched CFD
case has to state which basis it targets, and the two are not interchangeable.

Whether Lewis states instrument accuracies or a formal uncertainty analysis has **not yet
been checked** — the sections around the energy-balance discussion (pp. 181–184) and the
data-reduction appendix have been read only for the quantities above.

## Not yet done

- The remaining 29 runs' local `Nu` exists only as **Figures 6.7–6.13**, not as printed
  numbers. Recovering those is a digitisation task with its own error budget, and the
  lesson from Figure 16 applies: a figure is not a pointwise benchmark until proven so.
- Lewis reports flow-regime observations, including where the flow ceased to be
  unidirectional. **Those are the flow issues to screen on**, and they have not been
  extracted yet. The abstract already flags the limit: numerical predictions were compared
  with experiment *"where the flow remained unidirectional"*.
- A redistribution determination. The thesis is open access; the licence is **not stated**
  on the record page, so it is not yet established what may be republished here.

## Kept separate

Nothing from Lewis is compared with, combined with, or used to reinterpret the historical
NAFEMS causal numbers. It is a different fluid, a different geometry, a different
experiment, and it would need its own CFD case and its own protocol entry.
