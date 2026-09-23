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

## Flow-regime screen — done, and it is a *predicted* screen

Lewis's Table 7.1 (p. 203) is the screen. It lists the axial distance at which his own
marching code first produced a **negative axial velocity**, for the conditions he actually
computed. Transcribed to `data/lewis1992/table_7_1_flow_reversal.json`.

| Test | Re | Gr_q | Gr_q/Re | (x/d) at reversal |
|---|---|---|---|---|
| 7A | 296 | 1.72e5 | 581 | 157.0 |
| 6A | 609 | 3.78e5 | 620 | 134.5 |
| 10A | 81.2 | 7.96e4 | 980 | 73.5 |
| 12A | 309 | 3.36e5 | 1090 | 54.0 |
| 25A | 687 | 1.03e6 | 1500 | 69.0 |
| 15A | 74.9 | 1.55e5 | 2070 | 11.5 |

Three things about this table have to be said plainly.

**It is predicted, not measured.** These are outputs of Lewis's own numerical code, on the
inlet-bulk property basis. He measured no velocity field. A reversal in this table is a
reason to *doubt* a station, not an observation of one.

**It does not cover all 30 runs.** It covers only the conditions plotted in Figures
7.1–7.3. A run's absence means either "not computed" or "no reversal predicted", and only
the surrounding text distinguishes them — the table alone cannot.

**35A is in the clear.** Lewis states that *no* flow reversals were predicted within the
heated tube for the Figure 7.4 conditions, Re 1098–1181, which is 35A's group. 35A's
buoyancy parameter, Gr_q/Re = 328, is below every entry in the table. Of the fully
tabulated run, this is the most benign one on the buoyancy axis.

### The fluctuation measurements do not cover the main test series

An earlier reading of this treated the wall-temperature fluctuations as a per-run property
of Tests 1A–35A. That was wrong. Section 6.5 is explicit: the fluctuation records come
from **eight separate tests, 36–43**, run afterwards specifically to sample temperature at
1 Hz for 4 minutes. Only Test 36 is plotted. The main-series runs carry no fluctuation
record at all.

What Tests 36–43 do establish, and it is still useful:

- fluctuation magnitude **increases with both heat flux and flow rate**;
- in the **lower** half of the tube the record is dominated by occasional large excursions
  *below* the mean, growing then decaying with axial distance;
- in the **upper** half, *"rapid and irregular wall temperature fluctuations of larger
  amplitude ... were observed in many tests"*;
- thermocouples on diametrically opposite walls correlate in two distinct groups, which
  Lewis reads as **strong evidence of asymmetric flow**;
- Lewis calls these measurements **"of only a preliminary nature"**.

So the honest screen is: the upper tube is where the flow stops being cleanly laminar, and
that is a *qualitative* finding from a side experiment, not a per-run flag.

### Two stations Lewis himself discounts

Independent of buoyancy, Lewis rules out three measurement positions on instrumentation
grounds, and these apply to **every** run including 35A:

- **x/d = 0.31 and x/d = 0.85.** Predictions over-predict Nu here. Lewis attributes it to
  **axial wall conduction** preheating the water upstream of x = 0, and confirms it
  directly: the copper power-connection flange put the wall at x = 0 between **0.5 and
  5.7 °C above the measured inlet bulk**, depending on heat flux. No correction for this
  was applied in the data reduction.
- **x/d = 159.33.** Called **"suspect"**. It sits about 1/3 of a tube diameter from the end
  of the heated section and its accuracy *"is also impaired by axial conduction because of
  heat loss through the adjacent power connection flange"*.

That leaves **9 of 12 stations** on 35A that Lewis does not himself disown.

## Property basis and QoI — fixed, and verified against his spreadsheet

These were chosen before the rebuilt case was run and are now checked line by line against
the Appendix D-2 spreadsheet for 35A. Recorded in
`data/lewis1992/test_35A_reduction.json`.

**Property basis: inlet bulk, 13.06 °C.** Lewis tabulates four bases (inlet bulk, mean
bulk, mean wall, exit bulk) and reports derived groups on two of them. The choice is not
cosmetic:

| | Re | Pr | Gr_q | mean Nu |
|---|---|---|---|---|
| inlet bulk (13.06 °C) | 1143.4 | 8.46 | 3.75e5 | 9.55 |
| mean bulk (21.53 °C) | 1417.1 | 6.66 | 9.86e5 | 9.33 |

**The basis moves Re by 24% and Gr_q by a factor of 2.6.** Inlet bulk is taken because it
is the basis on which Lewis prints the local Nu table, Table 7.1, and Figures 7.1–7.4.

**Expansion coefficient: 1.27e-4 /K**, the inlet-bulk value, passed as an explicit input to
the case generator rather than derived. On the mean-bulk basis it would be 2.23e-4 — a
factor of 1.76, and the single largest lever on Gr_q.

**QoI: Nu(x) on a linear energy-balance bulk temperature.** This is Lewis's experimental
definition, and it has a detail that matters:

> the bulk rises linearly from the **measured** inlet, 13.06 °C, to the **calculated**
> exit, 30.00 °C — not to the measured exit, 29.32 °C.

The gap between those two exit temperatures *is* the −3.96 % energy-balance error. Which
one the reduction uses was settled by arithmetic, not assumption: reproducing the printed
`(Tw − Tb)` at x/d = 159.33 gives 29.06 K with the calculated exit and 29.73 K with the
measured one. The printed value is **29.06 K**. The whole reduction rule then reproduces
all 12 printed Nu values — at x/d = 0.31, `12749.6/7.60 = 1677.6` against a printed 1678.0,
and `1677.6 × 0.0119 / 0.5922 = 33.71` against a printed 33.72.

**Lewis's own two sides use two different bulk definitions.** His experiment uses the
linear rise above. His prediction code integrates a true **mixing-cup** bulk — Appendix F,
the `SUMUCT` loop, summing `U·cp·r·T` across the radius. These are different quantities,
and the rebuilt case reports both so they are never silently swapped.

## Test 35A rebuilt — numerical reconstruction check

`cfd/gencase_lewis.py` + `cfd/compare_lewis.py`, solver `buoyantBoussinesqSimpleFoam`
(OpenFOAM v2312), axisymmetric wedge, two meshes at 25 000 iterations each. Banked in
`results/lewis35A/grid_pair.json`.

**The case reproduces Lewis's stated operating point almost exactly**, which is the first
thing it had to do:

| | Lewis | rebuilt | |
|---|---|---|---|
| Re | 1143.4 | 1143.3 | −0.01 % |
| Pr | 8.46 | 8.465 | +0.06 % |
| Gr_q | 3.7466e5 | 3.7493e5 | +0.07 % |

### Grid convergence is station-dependent, and that is the useful part

| x/d | 20×300 | 30×400 | grid Δ | experiment | CFD − exp |
|---|---|---|---|---|---|
| 0.31 | 73.334 | 100.498 | **+37.0 %** | 33.72 | +198.0 % |
| 0.85 | 50.311 | 39.683 | **−21.1 %** | 32.69 | +21.4 % |
| 2.45 | 26.345 | 24.495 | **−7.0 %** | 22.15 | +10.6 % |
| 5.65 | 17.777 | 17.264 | −2.9 % | 19.07 | −9.5 % |
| 9.92 | 14.043 | 13.949 | −0.67 % | 14.92 | −6.5 % |
| 16.32 | 11.568 | 11.508 | −0.52 % | 13.95 | −17.5 % |
| 33.39 | 8.990 | 8.941 | −0.55 % | 10.76 | −16.9 % |
| 50.47 | 7.908 | 7.865 | −0.54 % | 9.38 | −16.1 % |
| 67.55 | 7.288 | 7.248 | −0.56 % | 9.37 | −22.6 % |
| 101.69 | 6.577 | 6.558 | −0.30 % | 8.41 | −22.0 % |
| 135.84 | 6.183 | 6.164 | −0.30 % | 7.99 | −22.9 % |
| 159.33 | 5.575 | 6.227 | **+11.7 %** | 8.82 | −29.4 % |

**Seven stations, x/d 9.92 to 135.84, are grid-converged to better than 0.7 %.** The three
entrance stations and the outlet station are not.

**This is a statement about the solver, not about the physics.** Grid convergence says the
discretisation no longer moves the answer. It says nothing about whether a steady laminar
model represents the experiment at those stations — and the section below argues it does
not. A converged station is a station where the model's own answer is trustworthy as *the
model's answer*. It is not a validated prediction.

The stations the rebuild cannot resolve and the stations Lewis disowns are **almost the
same set**. x/d 0.31, 0.85 and 159.33 appear in both lists, for unrelated reasons — mesh
sensitivity on one side, axial wall conduction on the other. That agreement was not
arranged; it is what the two grids and the thesis text independently say.

### What the converged band shows

Over the seven grid-converged stations the CFD sits **6.5 % to 22.9 % below the
experiment**, mean 17.8 %, and the gap **widens monotonically downstream**.

Lewis reports the same divergence against his own code, and names the cause:

> a divergence is noted at higher Grashof numbers, with the latter achieving significantly
> larger values near to the end of the heated tube

He attributes this *"tail-up"* to **transition from laminar flow** driven by instability of
the buoyancy-distorted velocity profile, citing Barozzi et al (1984), and notes Kemeny and
Somers (1962) measured up to 30 % increases under comparable nonlaminar conditions.

So a steady laminar solver under-predicting downstream Nu by up to 23 % is the **expected**
outcome. It is also a hard ceiling: **no amount of mesh refinement will close this gap**,
because the missing physics is unsteady transition, and the grid study above shows those
stations are already converged.

Expected is not the same as acceptable, and it is worth being blunt about which this is.
The rebuild is not defective — it solves the equations it was given, correctly, on a
converged grid. But **the equations it was given are the wrong ones for this part of the
tube.** A model that is missing the mechanism driving the measurement is not validated
there, however cleanly it converges. Lewis's account makes the gap *explicable*; it does
not make it *small*, and it does not make these stations usable as agreement.

### One real defect found and fixed

The first version of the comparison script reported *"flow-reversal stations: 0 of 300"*.
That number was meaningless. It tested whether the **net** axial flux across a section was
negative — which mass conservation prevents, whatever the profile does. Lewis's criterion
is per-cell: *"the axial position where negative values of the axial velocity first
appeared"*. Corrected, the rebuilt case reports a single reversed row.

That row is **the last one**, at x/d 159.5, with a minimum axial velocity of −0.111 m/s in
the three cells nearest the wall. A buoyancy reversal of the kind Table 7.1 predicts
develops over many rows upstream; one confined to the final row is an **outlet boundary
artifact**. The script now says so explicitly rather than reporting a bare count. It also
explains why the solver's own outlet patch integral disagrees with the last-cell mixing-cup
value by 3.5 K: negative face fluxes corrupt a flux-weighted average.

### Convergence status, stated honestly

The run reaches a **limit cycle, not a converged steady state** — over the final 2000
iterations the radial-velocity residual oscillates between 3.8e-2 and 3.3e-1 and is not
decreasing. The same behaviour appeared in the air case near Ri ≈ 1.3.

It does not move the answer. The axial-velocity and temperature residuals are steady at
~1.4e-3 and ~1e-3, and Nu at every station below x/d 136 differs by less than 0.01 %
between 4 000 and 25 000 iterations. The oscillation lives in the outlet recirculation
described above. Energy closure on the fine mesh is **+0.65 %**.

## Still not an evaluable set

Nothing above licenses a performance metric. Three things are missing, and no ordering of
them is meant — each blocks on its own:

1. **Model adequacy over the comparison band.** A steady laminar solver is missing the
   transition that drives the measured Nu downstream. That is a physics gap, not a mesh
   gap, and grid convergence does not touch it. Where the model lacks the mechanism, the
   station is not a validated prediction no matter how stable the number is.
2. **Per-point measurement uncertainty** (below). Not reported by the source; constructible
   by propagation, but that construction is a modelling choice and belongs in the locked
   protocol.
3. **Independent cases.** The seven grid-converged stations come from **one** operating
   condition. One run is one case, not seven. Precision and recall over twelve axial
   positions of a single test would be counting the same experiment twelve times.

A redistribution determination is also outstanding, but that is a rights question, not an
evidence one, and it does not gate the analysis.

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

### Instrument accuracies — checked, and they exist

Chapter 5 has now been read. Lewis presents **no combined uncertainty on Nu**, and no
error bars appear on any Nu figure. What he does give is component accuracies:

| Component | Stated |
|---|---|
| Flow rate, calibration re-checks | within ±1.2 % in 9 of 12 checks |
| Flow rate, run-to-run fluctuation | typically ±1.5 % |
| Heating voltage, heating current | each within ±1 % of the data-logger value |
| Thermocouple calibration correction | +0.13 K (ice) to +0.56 K (steam), fitted by a 5th-degree polynomial and **applied** in the reduction |
| Resistance thermometers, probe-to-probe | differences < 0.1 K in the majority of cases |
| Local wall heat generation uniformity | −4 % to +1 % of average in the highest-flux test; ±3.5 % in Test 15A |
| Water property equations | ±1 % |

Two caveats Lewis states himself and that a user of this data inherits:

- **The resistance thermometers were never traceably calibrated** — *"no proper calibration
  ... could be undertaken because no traceable temperature standard was available"*. The
  agreement figures above are probe-against-probe, not probe-against-standard.
- Wall temperatures are measured on the **outside** surface and corrected to the inside by
  a steady radial-conduction expression (Eq 5.1) that assumes no axial or circumferential
  gradient — an assumption the axial-conduction discussion later partly contradicts.

So a per-point uncertainty is **constructible** by propagating these components, but it is
**not reported**. Building one is a modelling choice with real freedom in it, and that
choice belongs in the locked protocol, decided before any label or metric, not here.

### One thing the accuracies settle outright

Lewis writes that the exit bulk temperature was *"not used for the evaluation of
experimental Nusselt numbers"* and was measured only *"to indicate the level of overall
energy balance"*. That independently confirms what the arithmetic above already showed:
the local-Nu reduction runs on the **calculated** exit bulk, 30.00 °C, and the measured
29.32 °C serves only as the energy-balance check.

## The other 29 runs — screened first, then digitised

### The figure legends give every run's conditions without digitising anything

Figures 6.7–6.13 group the 30 runs by Reynolds number, and each legend **names the tests
and prints their `Re` and `Gr_q`**. That is printed text, not marker positions, so reading
it costs nothing in accuracy. It yields a quantity Table E.1 never had: the dimensionless
groups for all 30 runs. Banked in `data/lewis1992/run_inventory.json`.

The six runs that also appear in Table 7.1 agree with their legends to within rounding,
which is the transcription check.

### Which runs Lewis actually screened — verified, not inferred

Figures 7.1–7.4 name the eleven conditions Lewis computed. Read directly from those four
legends:

| Group | Computed | Reversal predicted | Clear |
|---|---|---|---|
| 7.1, Re 75–81 | 10A, 15A | both | — |
| 7.2, Re 296–321 | 21A, 7A, 12A | 7A, 12A | **21A** |
| 7.3, Re 609–687 | 18A, 6A, 25A | 6A, 25A | **18A** |
| 7.4, Re 1098–1143 | 16A, 35A, 13A | none | **16A, 35A, 13A** |

So **11 of 30 conditions were screened and 5 came back clear.** The other 19 runs Lewis
never computed. That is absence of evidence, not a clearance, and the inventory marks them
`NOT_SCREENED` rather than passing them.

### The two screens pull against each other

Ranking by energy balance and ranking by buoyancy safety are **anti-correlated, r = −0.865**
between `log₁₀(Gr_q/Re)` and the absolute energy-balance error.

The mechanism is not subtle: a higher `Gr_q` means a higher heat input, which makes the
roughly fixed heat loss a smaller *fraction* of it. The runs that close energy best are the
hard-driven, strongly buoyant ones.

**So "start with the cleanest energy balance" selects, unaided, for the runs most likely to
have reversed or transitioned.** The cleanest run of all 30 is 30A at 0.04 %, and its
`Gr_q/Re` of 1215 is higher than four of the six runs where Lewis *did* find reversal — and
he never computed it. Ten of the nineteen unscreened runs sit above the lowest `Gr_q/Re` at
which he found reversal. The screens have to be applied together.

Applying both, the flow-cleared runs ranked by energy balance:

| Test | Re | Gr_q | Gr_q/Re | \|EB\| % | Figure |
|---|---|---|---|---|---|
| **13A** | 1138 | 8.06e5 | 708.3 | **0.14** | 6.13 |
| 35A | 1143 | 3.75e5 | 328.1 | 3.96 | 6.13 |
| 21A | 321 | 7.15e4 | 222.7 | 8.87 | 6.9 |
| 16A | 1098 | 7.78e4 | 70.9 | 9.32 | 6.13 |
| 18A | 625 | 1.03e5 | 164.8 | 12.52 | 6.11 |

**13A is the next case**, and it is not close: flow-screened clear by Lewis, and an energy
balance of 0.14 %, second-best of all thirty.

### Digitisation, with the error measured rather than assumed

`tools/digitise_lewis_fig613.py`. Figure 6.13 was chosen over Figure 7.4, which covers three
of the same runs, because 7.4 overlays the prediction curves and those curves merge with the
markers into single ink components.

Axes were calibrated by locating major tick centres from inward ink-run length, then least
squares on log₁₀(value) against pixel: 734.5 px/decade in `x*` with a maximum residual of
0.0008 dex, and a maximum residual of 0.0023 dex — 0.54 % in `Nu` — on the `Nu` axis. The
five legend glyphs served as classifier templates, separated by hole count, central-cross
versus diagonal ink, vertical centroid offset and corner occupancy, with wide margins on
every pair.

**Twelve of the thirty-two ink components were multi-marker clusters. They were skipped, not
split.** A guessed decomposition would put invented points into an evaluation set.

**Test 35A is a calibration standard inside the plot** — it appears in this figure and its
twelve local `Nu` are printed in Appendix D-2. Against those:

| | bias | spread | max \|error\| |
|---|---|---|---|
| `Nu` | −1.17 % | **0.40 %** | 1.40 % |
| `x*` | +1.77 % | **0.47 %** | 2.06 % |

The error is almost entirely a **systematic calibration offset**. The random part — the
spread — is under 0.5 % on both axes, and that is the number that governs runs whose answer
is unknown.

One check is genuinely independent of all of this. Correcting the `x*` bias and forming
`Re·Pr = (x/d)/x*` recovers **Pr = 8.46** for 35A, which is exactly Lewis's printed value.
`Pr` entered neither the axis fit nor the glyph templates; it comes out of marker positions
alone.

A bias-corrected `Nu` column is reported **alongside** the raw one, never instead of it, and
the 1.0117 factor is disclosed as coming from 35A.

### What came out

**13A: 7 of 12 stations**, at x/d 9.92, 33.39, 50.47, 67.55, 101.69, 135.84 and 159.33. Every
recovered point lands on Lewis's fixed thermocouple grid to within 0.41 %, which is a second
check that the classification is right. The five missing stations are the entrance cluster,
where all five series bunch and merge.

`9A` also yielded 7 stations and is recorded, but it is `NOT_SCREENED` and its energy balance
is 6.05 %, so it is held as inventory only. `20A` recovered one marker and implied a Prandtl
number of 0.15 instead of ~8; every 20A value is **discarded**, and the tool now refuses any
series under three points rather than reporting a snapped single. `16A` merges too heavily to
attempt.

### 13A makes the physics problem worse, not better

13A's bias-corrected `Nu` falls from 17.27 at x/d 9.92 to 11.50 at 50.47, then **rises to
18.77 at 159.33** — a 63 % climb across the back half of the tube. 35A's rise over the same
stretch is far gentler.

That is the tail-up again, and stronger, exactly as the higher `Gr_q` predicts. So the run
that best survives the energy and flow screens is also **the run where transition is most
violent** — and transition is the mechanism a steady laminar solver does not have. The
anti-correlation found in the screens reappears at the level of the measurement itself.

13A is a **second case**. It is not a test set, and it does not touch the model-adequacy
problem.

## Closing the assessment

### 16A was dropped on a bad screen, and the screen was mine

16A was listed among the five flow-cleared runs and then left out of the next-step decision
because its energy balance is 9.32 %. That was the wrong test.

**The energy-balance error is a percentage of the bulk temperature rise. What corrupts a
reduced Nusselt number is the absolute bulk error measured against the wall-to-bulk
difference that `Nu` divides by.** Those are not the same quantity, and for a low-power run
they differ by an order of magnitude.

| Test | Ri | EB % | rise (K) | bulk error (K) | `Nu` uncertainty, mid | at exit |
|---|---|---|---|---|---|---|
| 16A | 0.065 | −9.32 | 4.25 | ±0.40 | **2.5 %** | **6.9 %** |
| 35A | 0.287 | −3.96 | 16.93 | ±0.67 | 1.2 % | 3.6 % |
| 13A | 0.622 | −0.14 | 37.97 | ±0.05 | 0.1 % | 0.2 % |
| 18A | 0.264 | −12.52 | 8.05 | ±1.01 | 5.6 % | 20.1 % |
| 21A | 0.694 | −8.87 | 8.89 | ±0.79 | 7.4 % | **92.6 %** |

16A's 9.32 % costs 0.4 % in `Nu` at x/d 16 and 6.9 % at the exit. **21A, whose energy
balance looks only slightly worse, is destroyed**: its wall-to-bulk difference at the exit is
0.85 K against a 0.79 K bulk error. Ranking runs by percent energy balance gets the order
wrong, and it is the ranking I used.

**16A's measured curve is the most laminar in the thesis.** In Figure 7.4 its markers track
the lowest prediction curve over the whole plotted range including the final stations — the
only one of the three runs there with no visible departure. That is what `Ri = 0.065`, the
lowest of all thirty runs, predicts.

**But that is also what disqualifies it.** At `Ri = 0.065` buoyancy is a small perturbation
and 16A is close to a forced-convection case. Whether buoyancy is *material* to `Nu` there is
a question for a matched ablation, not for a screen, and it is not yet answered.

### A laminar-validity window does exist, and Lewis supplies it

The three numerical-prediction curves of Figure 7.4 were traced from the page image — thin
ink followed column by column, seeded mid-plot where the curves separate. Axis fit residuals
0.0020 dex in `x*` and 0.0029 dex (0.68 %) in `Nu`. Banked in
`data/lewis1992/fig74_prediction_curves.json`.

This matters because it gives a laminar reference that is **entirely Lewis's**. Comparing his
measurement against his own laminar code separates *"the flow stopped being laminar"* from
*"our CFD is built wrong"* — a distinction our CFD alone cannot make.

**Test 35A, measurement against Lewis's own laminar prediction:**

| x/d | 50.47 | 67.55 | 101.69 | 135.84 | 159.33 |
|---|---|---|---|---|---|
| measured − predicted | −3.0 % | +2.5 % | −3.9 % | −7.7 % | +2.4 % |

**No departure from laminar is detectable for 35A anywhere in the traced range.** His steady
laminar code reproduces his own measurement to within 8 % across the entire downstream half
of the tube.

**Test 13A:** −1.9 % to −9.6 % over x/d 33 to 102, then **+33.7 % at x/d 135.84**. The
departure sits between x/d 102 and 136, and Figures 6.13 and 7.4 show the same jump
independently.

So the source-based window is:

- **lower bound x/d > 1**, on Lewis's authority — he attributes the entrance over-prediction
  to axial wall conduction and writes of *"the deviations seen in this work for x/d < 1.0"*;
- **upper bound, 13A: x/d ≈ 102**;
- **upper bound, 35A: none found** within the traced range.

**"No predicted reversal" is not part of this argument, and must not be.** Lewis's marching
code assumes steady laminar flow, so it cannot predict transition at all; its silence is
structural, not evidence. Every departure above is located by the *measurement* leaving the
prediction.

### The correction this forces: the 35A gap is our model, not transition

Earlier this document argued that the 6.5–22.9 % gap between our CFD and Lewis's 35A
measurement was the expected consequence of transition. **That was wrong.**

| x/d | Lewis measured | Lewis predicted | our CFD | ours vs *his prediction* |
|---|---|---|---|---|
| 50.47 | 9.38 | 9.67 | 7.87 | **−18.7 %** |
| 67.55 | 9.37 | 9.14 | 7.25 | **−20.7 %** |
| 101.69 | 8.41 | 8.75 | 6.56 | **−25.1 %** |
| 135.84 | 7.99 | 8.66 | 6.16 | **−28.8 %** |
| 159.33 | 8.82 | 8.61 | 6.23 | **−27.7 %** |

Our CFD sits a fifth to a quarter below **another steady laminar prediction of the same run,
at the same stations, where that prediction matches the measurement to within 8 %.** Two
laminar codes disagreeing by a quarter is a model defect, not a physics limit. Transition is
real in 13A beyond x/d ≈ 102 and in the high-`Gr` runs Lewis names, but it does not explain
35A, and attributing the gap to it was an error that would have hidden a fixable fault.

**Cause one, found and fixed: the missing unheated entry.** Lewis runs 2.5 diameters of
adiabatic tube before x = 0 and his code models it; our case began heating on a plug profile.
Adding it (`--entry-diameters 2.5`):

| x/d | 0.31 | 0.85 | 2.45 | 5.65 |
|---|---|---|---|---|
| without entry | +198.0 % | +21.4 % | +10.6 % | −9.5 % |
| with entry | +73.9 % | **−0.5 %** | **+2.1 %** | −12.7 % |

x/d 0.85 and 2.45 go from tens of percent out to under 2 %. **Downstream of x/d 16 nothing
moves** — so the entry was a real defect, and it is not the downstream one.

**Cause two, confirmed by measurement: constant properties.** Lewis's code carries
polynomial property variation with temperature *"for all properties"*. Ours is Boussinesq
with properties frozen at the inlet bulk. Water's viscosity falls by a factor of **2.1**
between 13.06 °C and the 48.36 °C mean wall.

Three solver property bases were run at a matched 20×300 mesh, all with the unheated entry,
with **`beta` held fixed at 2.23e-4** so the test isolates viscosity and conductivity.
`Nu` is reduced on inlet-bulk `k` throughout, matching Lewis.

| x/d | measured | inlet bulk | mean film | mean wall | wall vs measured |
|---|---|---|---|---|---|
| 9.92 | 14.92 | 13.88 | 14.89 | 15.59 | +4.5 % |
| 16.32 | 13.95 | 11.61 | 12.43 | 13.01 | −6.7 % |
| 33.39 | 10.76 | 9.18 | 9.82 | 10.31 | −4.2 % |
| 50.47 | 9.38 | 8.15 | 8.75 | 9.18 | −2.1 % |
| 67.55 | 9.37 | 7.56 | 8.13 | 8.56 | −8.7 % |
| 101.69 | 8.41 | 6.86 | 7.48 | 7.90 | −6.1 % |
| 135.84 | 7.99 | 6.60 | 7.87 | 8.35 | +4.6 % |

**The property assumption alone moves `Nu` by 12–27 %** — the same size and the same sign as
the 19–29 % gap against Lewis's laminar prediction. Frozen at the mean wall the case lands
within ±9 % of the measurement where inlet-bulk properties were 16–23 % low.

That settles the attribution. **It does not license picking `mean_wall`.** Choosing the basis
that agrees best would be tuning the model to the measurement it is about to be tested
against — precisely the failure this project exists to detect. The defensible fix is a
variable-property solver, which removes the choice rather than making it well. Banked with
its caveats in `results/lewis35A/property_sensitivity.json`; because `beta` was pinned, none
of the three is a self-consistent property set and their absolute agreement is not the point.

### An external transition criterion exists, and it does not transfer

Hallman (NASA TN D-1104, 1961) measured the same geometry — vertical tube, water, uniform
heat flux, aiding flow — and separated his steady runs from his fluctuating ones, giving a
transition correlation:

> `Ra_D = 9470 · [Re·Pr / (2x/D)]^1.83`, stated valid for `1 < Re·Pr/(2x/D) < 20`

Applied to Lewis, **every station returns "steady laminar" — and the result should be
discarded.** Lewis's stations sit at `Re·Pr/(2x/D)` between **30 and 488**, from 1.5 to 24
times outside the range Hallman validated. The extrapolation runs in the permissive
direction, so it would return "laminar" almost regardless, and it contradicts the direct
observation that 13A's measured `Nu` jumps 34 % above laminar prediction at x/d 135.84.

This is worth stating plainly because it is this project's own method turned on its own
working: a correlation used outside its calibrated range, producing a confident answer that
the data contradicts. The criterion is not evidence about Lewis.

## The variable-property solver — the diagnosis confirmed

The constant-property Boussinesq case is retired as the model of record. `cfd/gencase_lewis_vp.py`.

### Properties are Lewis's own, not a re-derivation

His Appendix B gives the polynomials **his numerical code used** — B.2 viscosity, B.4
conductivity, B.5 specific heat, B.6 density — as distinct from the ESDU forms his
spreadsheet used. Recovered from the thesis and checked against his own tabulated property
table at all four of his bases: `k`, `c_p` and `ρ` agree to within **0.04 %**, `μ` to within
**0.42 %**, which is the B.1-versus-B.2 difference he documents himself as *"less than
0.8 %"*.

One check is independent of that table. Deriving `β = −(1/ρ)·dρ/dT` from the density
polynomial reproduces his tabulated expansion coefficient at all four temperatures to within
**0.1 %** — and `β` was nowhere in the fit.

OpenFOAM's polynomials are in kelvin and Lewis's are in celsius; the coefficients used are
the exact binomial shift, round-trip accurate to 1e-11 over 5–80 °C.

### Two things improve structurally, not just numerically

**`beta` stops being an input.** Buoyancy enters as `ρ(T)·g`. The expansion coefficient was
the single largest lever in the Boussinesq case — a factor of 1.76 between bases — and the
choice simply disappears.

**The wall temperature is read, not reconstructed.** `externalWallHeatFluxTemperature`
imposes `q` using the *local* conductivity, which a `fixedGradient` cannot once `k` varies
with temperature, and it writes the wall temperature out. The first-order
`T_cell + (q/k)(dr/2)` estimate is gone.

### The outlet had to be moved, and why that is not a fudge

With the outlet flush against the end of heating the case manufactured a **centreline**
recirculation over the last 8 rows — minimum axial velocity −0.415 m/s — while the wall flow
stayed positive throughout. Wall-positive, core-negative, confined to 2 % of the tube at the
boundary is an outlet artifact, not a developing buoyancy reversal, and it drove x/d 159.33
to **+49 %** against measurement.

Appending 15 diameters of unheated tube fixes it completely: **zero reversed cells anywhere**,
minimum axial velocity +0.013 m/s, and that station lands at −7.9 %. Lewis's rig did continue
past the heated length into a flange and outlet pipe, so it is not unphysical — but the
justification is numerical, the extension carries no measurements, and the comparison drops
its cells.

### Result

| x/d | 20×300 | 30×400 | grid Δ | measured | vs measured | Lewis predicted | vs prediction | old constant-property |
|---|---|---|---|---|---|---|---|---|
| 0.31 | 54.45 | 60.36 | +10.9 % | 33.72 | +79.0 % | — | — | 100.50 |
| 0.85 | 38.22 | 34.01 | −11.0 % | 32.69 | +4.0 % | — | — | 39.68 |
| 2.45 | 25.15 | 23.95 | −4.8 % | 22.15 | +8.1 % | — | — | 24.50 |
| 5.65 | 18.39 | 17.91 | −2.6 % | 19.07 | −6.1 % | — | — | 17.26 |
| 9.92 | 15.04 | 14.90 | −0.9 % | 14.92 | **−0.1 %** | — | — | 13.95 |
| 16.32 | 12.72 | 12.61 | −0.9 % | 13.95 | −9.6 % | — | — | 11.51 |
| 33.39 | 10.30 | 10.20 | −0.9 % | 10.76 | −5.2 % | — | — | 8.94 |
| 50.47 | 9.33 | 9.25 | −0.9 % | 9.38 | −1.4 % | 9.67 | **−4.3 %** | 7.87 |
| 67.55 | 8.82 | 8.75 | −0.9 % | 9.37 | −6.7 % | 9.14 | **−4.3 %** | 7.25 |
| 101.69 | 8.34 | 8.28 | −0.7 % | 8.41 | −1.5 % | 8.75 | **−5.3 %** | 6.56 |
| 135.84 | 8.20 | 8.14 | −0.8 % | 7.99 | +1.9 % | 8.66 | **−6.0 %** | 6.16 |
| 159.33 | 8.19 | 8.12 | −0.8 % | 8.82 | −7.9 % | 8.61 | **−5.6 %** | 6.23 |

**Against Lewis's own steady laminar prediction the gap falls from 18.7–28.8 % to
4.3–6.0 %.** That is the diagnosis confirmed: the old gap was the frozen-property
assumption, and it was never transition.

**Eight of twelve stations are grid-converged to better than 1 %, x/d 9.92 to 159.33** — now
including the outlet station, which the constant-property model moved 11.7 % between grids.
The remaining shift is a uniform −0.9 %, so Richardson extrapolation puts the converged
answer roughly 1 % below the fine grid and the residual against Lewis nearer 5–7 %.

Energy closes to **−0.05 %**.

The three entrance stations stay grid-sensitive. x/d 0.31 is the axial-conduction station
Lewis discounts on his own authority; x/d 0.85 and 2.45 now land at +4.0 % and +8.1 %,
against +21.4 % and +10.6 % before.

### What the residual 5 % is not

It is not tuned away, and it should not be. Two independently written steady laminar codes
agreeing to about 5 % on the same case is a reasonable place to stop. The residual has at
least three plausible contributions that have not been separated: the curve-tracing error in
our reading of his Figure 7.4 (0.68 % from the axis fit alone, plus tracing), discretisation
differences, and the fact that Lewis solves an integral energy balance at each axial step
where this case solves an enthalpy transport equation.

### Still development evidence

35A is a **spent** run and so are 13A and 16A. Everything above is a debugging signal — it
says the implementation is now sound, not that anything has been validated. No metric may be
computed from any of it, and the boundary at x/d ≈ 102 found in 13A remains a finding about
the experiment, never an eligibility rule.

## Matched ablation, and the causal path end to end

`--gravity off` on the corrected variable-property setup. A recursive diff of the two case
directories touches exactly two files: `constant/g`, and the flag recording it in
`case.json`. Mesh, property polynomials, boundary conditions, schemes, solver settings,
iteration count, QoI and extraction code path are identical.

**Both halves converge and close energy.** Gravity on: `h` 4.2e-5, `p_rgh` 3.3e-5, energy
−0.05 %. Gravity off: `h` 7.0e-8, `p_rgh` 1.3e-7, energy +0.11 %. Zero reversed cells in the
heated section of either. The ablated half converges far harder, which is what removing the
instability should do.

The pair runs 3000 iterations, not 25 000. With gravity off, GAMG hit its 1000-sweep cap
every step while residuals sat at 1e-6 — 4.8 hours of grinding on a solved problem. Both
halves were rerun at a matched 3000, and the gravity-on half at 3000 reproduces the
25 000-iteration answer to **within 0.063 %** at every station.

### Materiality is position-dependent

| x/d | Nu full | Nu ablated | materiality | fires at θ = 0.10 |
|---|---|---|---|---|
| 0.31 | 60.359 | 60.287 | 0.0012 | no |
| 0.85 | 34.007 | 33.908 | 0.0029 | no |
| 2.45 | 23.951 | 23.802 | 0.0062 | no |
| 5.65 | 17.911 | 17.690 | 0.0124 | no |
| 9.92 | 14.902 | 14.605 | 0.0200 | no |
| 16.32 | 12.613 | 12.213 | 0.0317 | no |
| 33.39 | 10.207 | 9.585 | 0.0610 | no |
| 50.47 | 9.246 | 8.443 | 0.0869 | no |
| 67.55 | 8.745 | 7.774 | 0.1110 | **yes** |
| 101.69 | 8.281 | 7.004 | 0.1542 | **yes** |
| 135.84 | 8.137 | 6.551 | 0.1950 | **yes** |
| 159.33 | 8.124 | 6.325 | 0.2214 | **yes** |

All twelve return `estimated` with `matched_ablation` provenance. The mechanism — buoyancy as
a Richardson number, `Ri = 0.287` against a forced-convection window of `Ri ≤ 0.1` — is
outside calibration, so the flag rule's other half is satisfied and the materiality decides.

**The flag fires downstream and stays quiet upstream, within one run.** Buoyancy needs axial
distance to distort the velocity profile, so the same mechanism is immaterial at the inlet and
dominant at the outlet of the same tube.

That is a structural finding, not a curiosity: **any protocol that assigns one materiality per
operating condition is choosing an aggregation**, and the choice changes which cases flag. The
mean over all twelve stations is 0.0383, which would *not* fire — but it is dominated by the
entrance, where `Nu` is 60 and materiality is 0.001. That aggregation belongs in the locked
protocol, decided before any label.

The refusal control behaves: the same two numbers with `flat_plate_correlation` provenance
return `refused_provenance` with **no value**, not a zero.

One clarification. x/d 0.31 and 0.85 are the stations Lewis discounts for axial wall
conduction. That exclusion governs comparisons with his *measurement*. Materiality here is
CFD against CFD with no experimental value anywhere in it, so the exclusion does not apply —
and `evidence_state: measured` means *recorded data with stated provenance*, not *from an
experiment*.

## Flow-regime eligibility for the uninspected runs

Three independent criteria were assessed against source-reported quantities only. No CFD
result, no measured-versus-predicted divergence and no PhysMAP output entered any of it.

**Metais & Eckert (1964) regime diagram — rejected.** The data exist at the right basis:
Lewis's Table E.4 gives `Gr·Pr·d/L` at mean film for 29 runs, and Aung (1987) fixes mean film
externally. But Lewis reports that **Barozzi et al (1984) found the diagram unreliable for
water flowing upward in a uniformly heated vertical tube** — this configuration exactly — and
notes its limits have never been revisited. His own partial validation is self-described as
"cursory" and was built from his measured data *and* his numerical predictions, so his
endorsement rests on evidence this rule may not use.

**Petukhov et al (1969) transition correlation — rejected.** `x*_tr = 12.9·C·(Gr_q/Re)^−0.8`,
measured on upflow of water at uniform heat flux using wall-temperature fluctuations — the
same detection method Lewis used, in the same configuration. Applied to Lewis it puts
transition at x/d between 170 and 6500, so **no run transitions inside a 159.66-diameter
tube** — contradicting Lewis's own fluctuation observations. Their data covered
`10³ < Gr_q/Re < 4×10⁵`; most Lewis runs sit *below* that, and with a −0.8 exponent the
extrapolation pushes transition further away. Permissive extrapolation outside the calibrated
range, exactly what disqualified Hallman.

**Yao (1987a) linear stability — applicable, but it does not yield enough runs.** A stability
analysis rather than a fitted correlation, for fully-developed buoyancy-aided flow in a
vertical pipe at uniform heat flux: the flow *can* become unstable for `Gr_q/Re > 300` and
`Re > 80`. Below that boundary it is a **stability statement**, which is the direction
eligibility needs, and it is conservative — using it to exclude is the safe error.

Its problem is that Yao's analysis is constant-property and Lewis's water is not. Mapping the
experiment onto a single `Gr_q/Re` needs a reference temperature the analysis cannot supply.
Evaluating the verdict on all three of Lewis's own bases (Tables E.2, E.3, E.4):

- **stable on every basis: 16A, 20A, 26A**
- **verdict flips with the basis: 15A, 18A, 21A, 27A, 34A**

### The arithmetic, and what it settles

16A is a **spent** development run. That leaves **two** runs, 20A and 26A. Two runs are two
cases, and axial stations are not cases, so there is no arithmetic that makes this an
evaluation set. It is worse than that: both have local `Nu` only in figures and would need
digitising, and **20A is the run the digitiser already rejected** — one marker recovered, an
implied Prandtl number of 0.15 instead of about 8.

**Lewis cannot support an independent eligibility rule that yields a scoreable set.** It is
retained as a reproducible causal demonstration — richest per-run conditions of anything
reachable, published property laws, and a rebuild that now tracks Lewis's own laminar
prediction to about 5 %. A different source is needed for scored validation.

Metrics stay closed. Nothing above opens them.

## Redistribution — the licence was there all along

The record page states no licence, which is why this was left open. **The PDF itself carries
the City Research Online policy on its cover sheet**, and Lewis and Barozzi carry the same
text:

> Copyright and Moral Rights remain with the author(s) and/or copyright holders. Copies of
> full items can be used for personal research or study, educational, or not-for-profit
> purposes without prior permission or charge, unless otherwise indicated, provided that the
> authors, title and full bibliographic details are credited, a hyperlink and/or URL is given
> for the original metadata page and the content is not changed in any way.

Two things follow, and they point in different directions.

**It covers the thesis, which we do not redistribute.** The terms govern *copies of full
items*. This repository holds transcribed numerical values — operating conditions, energy
balances, reduced Nusselt numbers — and no part of the document. `*.pdf` is gitignored and no
PDF has ever been tracked.

**The scope is narrower than this repository's own licence.** The policy permits
*not-for-profit* use; the corpus here ships CC BY 4.0, which permits commercial use. Anyone
relying on these numbers downstream should know that the underlying document's terms are the
narrower of the two. The numbers themselves are measurements rather than expression, which is
the same basis on which the other benchmark vehicles were cleared, and the owner has ruled
that the numbers publish and the paper stays out.

Recorded so the determination is on the record as *made*, not as *outstanding*.

## Not yet done The thesis is open access; the licence is **not stated**
  on the record page, so it is not yet established what may be republished here.

## Kept separate

Nothing from Lewis is compared with, combined with, or used to reinterpret the historical
NAFEMS causal numbers. It is a different fluid, a different geometry, a different
experiment, and it would need its own CFD case and its own protocol entry.
