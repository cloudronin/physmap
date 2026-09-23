# What produced `Nu_pred`, and what measured points exist

*Two read-only investigations, September 2026. No labels, flags or performance metrics
were computed. Nothing was refitted. Every claim below cites a surviving artifact.*

---

## Investigation 2 — how `Nu_pred` was produced

### Headline

**It was a forced-convection closure fitted to the gravity-off CFD runs** — not a fitted
ML surrogate on `(Re, Pr)`, and not a textbook correlation. That is a third possibility,
and it is neither of the two options previously put to you.

**The code that implemented it did not survive.** The evidence is a design document
written *before* the run, plus a writeup. The surviving *committed* loader describes a
different construction (below), and the two do not agree.

### The primary evidence

`PhysMAP-vehicle3-step4-design.md`, headed *"documented BEFORE running… so the framing
isn't reverse-engineered from the result"*:

> **Surrogate** `Nu_s` = a **forced-convection closure** `Nu_forced(Re)` (**fit from the
> g-off CFD**), which **ignores Gr\***

and the unified writeup, §4.3 Step 4:

> surrogate = forced-convection closure (ignores Gr\*, physics-blind to buoyancy)

A PhysicsNeMo MLP existed, but the same sentence says what it was for: it was trained on
the closure and used to generate the **guardrail baseline** signals (OOD / residual /
variance). It did not produce `Nu_s`.

### The contradiction in the surviving code

`substrate/corpus_real.py::pipe_to_rows` — the only committed loader for this case — sets:

```python
surrogate_prediction = Nu_M      # the FULL mixed-convection CFD
cfd_truth            = Eq13      # the Mohammed & Salman correlation
cfd_uncertainty      = 0.0
```

That is **not** a forced-convection closure. It is the full CFD, checked against the
experimental correlation.

The reconciliation that fits all the evidence: `pipe_to_rows` ingests
`conv_step3_final.json`, which is **Step 3** — the validation and ablation sweep, `n = 3`
rows at `Ri = 0.52, 3.14, 13.06`. Step 3 produced the materiality curve. **Step 4**
produced the abstract's metrics, on a dense 2-D grid, with the fitted forced closure as
the surrogate — and Step 4's code lived in `~/physmap-wall/`, which is gone.

So the committed code is not the code that produced the numbers, and it should not be read
as if it were.

### What this means for the evaluable set

Step 4's grid is `Re ∈ [400, 1600] × Gr* ∈ [1e5, 7.4e6]`, with `Ri = Gr*/Re²`. On that
grid:

- **truth** is Eq 13, an analytic correlation — evaluable at every point;
- **surrogate** is a closure fitted to the g-off CFD — evaluable at every point;
- **materiality** is a fit through **three** CFD ablation points.

Every metric in the abstract was therefore computed over a grid on which **nothing was
measured**, against a correlation, with a materiality interpolated from three points.

### The shared-input coupling, worked through

Previously raised as a question. It has now been derived, and it is stronger than
suspected.

#### Setup, entirely from the surviving construction

| | |
|---|---|
| Materiality | `m = 1 − Nu_F/Nu_M`  ⟹  `Nu_F = Nu_M(1 − m)` |
| CFD vs correlation | `d = (Nu_M − Nu_t)/Nu_t`  ⟹  `Nu_M = Nu_t(1 + d)` |
| Surrogate | fitted to the g-off CFD: `Nu_s = Nu_F + ε·Nu_t`, with `ε` the relative fit residual |
| Label | untrustworthy ⟺ `|Nu_s − Nu_t| > tol·scale`, scale = `Nu_t` |
| Flag | causal fires ⟺ out-of-box **and** `m ≥ θ`, with `θ ≈ tol = 0.10` |

#### The derivation

Substituting:

```
E ≡ (Nu_s − Nu_t)/Nu_t = d − m(1 + d) + ε
```

With `|d|, |ε|` small against `m`, this is `E ≈ −m`, so **`|E| ≈ m`**.

The label rule `|E| > tol` therefore becomes, to first order, **`m > tol`**. And the flag
rule is `m ≥ θ`. With `θ = tol`, a flagged point is labelled untrustworthy, so

> **causal precision near 1.00 is strongly favoured by the construction rather than
> earned against the data.**

**That is the claim, and it is narrower than "an identity".** An earlier version of this
document said precision 1.00 was an identity. It is not established as one, and cannot be
until three things are settled:

1. **Step 4's error scale** is unknown (A2). The algebra above assumes normalisation by
   the truth.
2. **The surrogate fit residual `ε` is unrecorded** (A1). `ε ≈ 0` is what makes `|E| ≈ m`.
3. **The behaviour of `d` across the grid is unknown** (A5). Two negative values at
   `Ri ≥ 1.8` do not establish that `d < 0` everywhere, and the sign is what decides
   whether the correction reinforces or cancels.

What the algebra does establish is a **mechanism** by which the flag and the label are
linked through a shared input, and a quantification of how large `ε` would have to be to
overcome it under the observed `d`. That is enough to stop the performance table being
read as independent evidence. It is not enough to call the number an identity.

#### Where `d` was observed, it reinforces rather than rescues

A causal false positive needs `m ≥ θ` **and** `|E| ≤ tol` at once. Since `−m(1+d)` is
negative, a **negative** `d` pushes `|E|` further past the tolerance rather than back
inside it. Both validated points have `d < 0`:

| Ri | `Nu_M` (CFD) | Eq 13 | `d` |
|---|---|---|---|
| ≈1.8 | 8.155 | 8.47 | **−0.037** |
| 13 | 9.17 | 10.11 | **−0.093** |

**Two points, both at `Ri ≥ 1.8`.** They do not establish the sign of `d` across the
grid, and the low-`Ri` corner — where materiality is smallest and the tolerance
comparison is tightest — was never validated at all. Cancellation would need `d > 0`,
which was not observed *at the two conditions that were checked*. That is the honest
scope of the evidence.

#### How large a fit residual would be needed to break it

Solving `|d − m(1+d) + ε| ≤ tol` for `ε`, at `tol = θ = 0.10`:

| materiality `m` | `d` | required `ε` for even one false positive |
|---|---|---|
| 0.10 | −0.037 | ≥ **+3.3%** |
| 0.10 | −0.093 | ≥ +8.4% |
| 0.15 | −0.037 | ≥ +8.1% |
| 0.20 | −0.037 | ≥ +13.0% |
| 0.26 | −0.093 | ≥ **+22.9%** |

At `ε = 0` the label and the flag agree everywhere. A false positive is only reachable in
a narrow band just above `θ`, and only if the fit **over-predicts** the g-off CFD in one
specific direction. Across most of the materiality range it would take a fit residual no
usable fit has.

**The fit residual was never recorded.** Nothing in the surviving documents states how
well `Nu_forced(Re)` reproduced the g-off CFD.

#### What this does and does not impugn

- **Causal precision is favoured by the construction.** Fitting the surrogate to the same
  g-off CFD that supplies the materiality numerator, then aligning `θ` with `tol`, links
  the flag to the error. It is not evidence that the method avoids false alarms on an
  independent problem.
- **Recall 0.65 is not explained by this coupling** — it is limited by calibration-box
  placement, and the algebra says nothing about it. **That does not make it evidence of
  performance.** It was scored against correlation-based labels like every other number in
  the table. "Unaffected by defect A" is not "sound"; these are two separate defects and
  the second applies to every cell.
- **Naive precision 0.73 is likewise not independent evidence.** Naive flags on box
  membership, which is not coupled to the error — so the *lift* comparison is less
  compromised than the absolute figure. But its labels came from the same correlation, so
  0.73 is a correlation-referenced quantity too.
- **The design document's defence was half right.** It argued the precision lift escapes
  the circularity because it turns on box-edge versus threshold. That is right about the
  coupling on *naive's* side, and wrong about *causal's*. Neither side escapes the
  correlation referencing.

#### Assumptions, and which are unverified

| # | Assumption | Status |
|---|---|---|
| A1 | `ε` is small — the fit tracks the g-off CFD closely | **UNRECOVERABLE.** Traced: no coefficients, no R², no residual for `Nu_forced(Re)` survive anywhere. The only `Nu_forced` in the codebase is the Pohlhausen flat-plate closure used by unrelated loaders |
| A2 | The label scale is `Nu_t` (relative error) | **PARTIALLY RECOVERED.** `_norm_for` with `per_row_truth` returns `row.cfd_truth`, and `normalize_row` computes `err = 1 − Nu_s/Nu_t` — exactly this assumption, and the only normalisation any surviving loader uses. But that is the *Step-3* substrate; Step 4's `scale` is written as an undefined symbol and **remains unknown** |
| A3 | `θ = tol = 0.10` | Documented in the writeup |
| A4 | `m = 1 − Nu_F/Nu_M`, truth = Eq 13, surrogate fitted to the same `Nu_F` | Documented in the step-4 design |
| A5 | `d < 0` across the grid | **NOT ESTABLISHED.** Two observations, both at `Ri ≥ 1.8`. The low-`Ri` corner was never validated |

A2 is the load-bearing one. If step 4 normalised by something other than the truth — an
absolute tolerance, say — the algebra changes and the conclusion must be redone.

#### Where independent evidence could break the link

1. **A truth that is not `Nu_M`-adjacent.** Pointwise measurements replace `d` with an
   experiment-versus-CFD difference that has no reason to be systematically signed, and
   carries its own uncertainty. This is the single cleanest break.
2. **A surrogate not fitted to the g-off CFD.** Any surrogate whose errors are not tied to
   `Nu_F` decouples `E` from `m`. Note this cannot be adopted merely because it is
   convenient — it would be a different experiment from the one the abstract reports.
3. **The two-condition label rule.** Requiring the gap to exceed the truth's own
   uncertainty as well as the tolerance introduces a term that is not a function of `m`.
4. **Recording `ε`.** If the rebuilt fit's residual against the g-off CFD is genuinely
   negligible, the coupling is confirmed outright. If it is a few percent, a narrow
   false-positive band exists and precision becomes measurable rather than pinned.

Items 1 and 4 need no new CFD beyond what is already planned.

### The θ discrepancy resolves — both numbers are real

The code says `0.20`; the abstract says `θ ≈ tol = 0.10`. The writeup shows they are
different roles:

| Role | Value | Evidence |
|---|---|---|
| **Precondition** — "does materiality vary across the grid?" | **0.20** | *"Ablation materiality rises 0.04 → 0.15 → 0.26 across Ri 0.5/3/13, crossing θ=0.20"* |
| **Flag rule** — the threshold the reported metrics use | **0.10** | *"(at the principled θ ≈ tol = 0.10)"* under the metrics table |

`protocol.json` already has two slots for exactly this: `theta_precondition` and
`theta_flag_rule`.

### The label rule does not match the abstract

The step-4 design states the rule as a **single** condition:

> **Truth label**: untrustworthy ⇔ `|Nu_s − Nu_t| > tol·scale`

The known-results declaration records the abstract's rule as requiring the gap to exceed
**both** the tolerance **and** the truth's own uncertainty. No uncertainty term appears in
either surviving construction, and the committed loader sets `cfd_uncertainty = 0.0`.

Either the abstract describes a rule the run did not use, or the uncertainty term was
added somewhere that did not survive. This needs resolving before the label rule is locked.

---

## Investigation 1 — independently measured vertical-pipe conditions

### Headline

**None are in hand, and none were ever used.** The "experimental truth" is the authors'
own **correlation**, evaluated densely. No individual measured operating point from
Mohammed & Salman appears anywhere in the surviving record.

### The anchor, verified

| | |
|---|---|
| Citation | Mohammed, H. A. & Salman, Y. K. (2008). *Heat Transfer Measurements of Mixed Convection for Upward and Downward Laminar Flows Inside a Vertical Circular Cylinder*. **Experimental Heat Transfer 21(1):1–23** |
| DOI | `10.1080/08916150701647801` (Taylor & Francis / Informa) |
| Access | **Closed.** No open copy; no licence deposited in Crossref |
| Geometry | Vertical pipe, D = 30 mm, L/D = 30, constant wall heat flux |
| Flows | Upward (assisting) **and** downward (opposing) |
| Range | `Ri ≈ 0.1–30` |
| Uncertainty | **±8%** — a single global figure |
| Correlations | up: `Nu = 3.7151 (Ra/Re)^0.11868` · down: `Nu = 3.6254 (Ra/Re)^0.08697` |

The writeup's citation is **correct**; I doubted it and was wrong. A companion paper by
the first author alone also exists — *Energy Conversion and Management* 49(8):2006–2015,
DOI `10.1016/j.enconman.2008.02.009`, likewise closed, Elsevier TDM licence only — which
reports `Re 400–1600` and `Gr 2.0e5–6.2e6`.

### What was actually used as truth

Eq 13, the assisting-flow correlation, evaluated at every grid point:

> **Truth** `Nu_t` = **Eq 13** (Mohammed & Salman experimental correlation,
> `3.7151·(Ra/Re)^0.11868`) — *experimental*, dense

The committed loader stores that value in the field named `cfd_truth`, and the repository's
own recon states the consequence:

> **As implemented, vehicle-3 disqualifies because the truth value is a correlation, not
> the raw experiment.**

The independence flag in code says the same thing:

> *"Eq13 is a closure-style correlation, so closure-vs-Eq13 measures closure-vs-correlation,
> not closure-vs-reality. A real-closure-divergence test requires raw experimental
> measurement not fit to a closure form."*

### The inventory, as it stands

| Item | Count | Source location | Uncertainty |
|---|---|---|---|
| Measured operating points extracted from the paper | **0** | — | — |
| CFD conditions validated against Eq 13 | **3** | `Ri = 0.52, 3.14, 13.06`, from `conv_step3_final.json` (**file gone**) | Deviations −3.7% (Ri≈1.8) and −9.3% (Ri=13) survive in the writeup; the file does not |
| Correlation-derived truth values | dense | Eq 13, evaluated on the step-4 grid | Global ±8% on the correlation; `cfd_uncertainty = 0.0` in the loader |

**Usable per-point measurement uncertainty: none exists anywhere.** The only uncertainty
figure in the record is the paper's global ±8% band on the correlation.

### Therefore: the abstract's metrics are correlation-referenced

Since no pointwise measurement was used, precision 1.00, recall 0.65 and F1 0.79 were
scored against **Mohammed & Salman's experimental correlation**, not against their
measurements. They should be described that way — *correlation-referenced* — wherever they
appear, and not as experimental-truth performance, unless and until pointwise values are
recovered and actually used.

This is a description of what was done. It is not a criticism of the correlation, which is
a legitimate experimental product with a stated ±8% band.

### Two further facts that bear on the grid

1. **CORRECTED — there is no established grid overrun.** An earlier version of this
   document claimed the step-4 grid extended past the experimental envelope at both ends.
   That was wrong. The `Gr 2.0e5–6.2e6` figure came from the **companion paper** (*Energy
   Conversion and Management* 49(8), Mohammed alone), not from Mohammed & Salman.
   Mohammed & Salman's own abstract reports `Re = 400–1600` and `Gr = 1.1e5–7.4e6`, which
   **matches** the stated step-4 grid bounds. The claim is withdrawn.

   **Source for the correction:** the authors' university record at KFUPM,
   <https://pure.kfupm.edu.sa/en/publications/heat-transfer-measurements-of-mixed-convection-for-upward-and-dow/>,
   which gives *Experimental Heat Transfer* 21(1):1–23 (2008), DOI
   `10.1080/08916150701647801`, an aluminium cylinder of 30 mm inside diameter with a
   900 mm heated length (L/D = 30), `Re = 400–1600`, `Gr = 1.1e5–7.4e6`, `Ri ≈ 0.1–30`,
   and results "correlated empirically as Log Nu against Log Ra/Re" for both flow
   directions.

   **What the envelope match does and does not establish.** It establishes that the grid
   lies inside the range the experiments spanned. It does **not** establish measurement
   coverage at every grid point: experiments sit at discrete conditions, and a correlation
   fitted across a range is still being interpolated between them and evaluated where
   nothing was measured. The evaluable rule still has to say what it does about grid points
   with no nearby measurement — but that is a coverage question, not an extrapolation one.
2. **A provenance inconsistency, minor but worth fixing.** The calibration corpus registers
   `Ri ∈ [0.1, 10]` under `aung-worku-mixed-convection-1986` with the note *"Eq13 family"*,
   `primary_source: false`, and the reason *"mixed-convection regime is typically reported
   as Ri ∈ [0.1, 10]"*. That is a textbook regime boundary attributed to Aung & Worku —
   not Mohammed & Salman's measured `Ri ≈ 0.1–30`. Two different things share the name
   "Eq13" in this repository.

---

## The paper, read — inventory of what it actually reports

*Mohammed, H. A. & Salman, Y. K. (2008), Experimental Heat Transfer 21(1):1–23,
DOI `10.1080/08916150701647801`. 24 pages. Read in full.*

### The correction that matters most: ±8% is not the measurement uncertainty

This project has carried **±8%** as Mohammed & Salman's experimental uncertainty. **It is
not.** The paper is explicit, and the two quantities are different things:

> "…the overall accuracy of heat transfer **data in these correlations** is expected to be
> of the order of ±8%, **as shown in Figure 16**."

±8% is the **scatter of the data about the fitted correlation**. It is a property of the
fit.

The measurement uncertainty is reported separately, following Moffat's method, and it is
far tighter:

| Quantity | Uncertainty |
|---|---|
| Heater input power | ±0.13% |
| Temperature difference `Ts − Ta` | ±0.21% |
| Heat transfer rate | ±1.1% |
| Cylinder surface area | ±1.2% |
| Air flow rate | ±0.01% |
| **Nusselt number (combined maximum)** | **±1.27%** |
| Reynolds number | ±1.35% |
| Rayleigh number | ±1.13% |

**A factor of about six**, and the two are not interchangeable.

**This decides whether the label rule's second condition does any work.** The abstract's
rule requires the gap to exceed both the tolerance *and* the truth's own uncertainty. With
`tol = 0.10`:

- **truth = measurement** → uncertainty 1.27%, far below the tolerance, so the second
  condition almost never binds and the rule collapses to the single-condition form;
- **truth = correlation** → the relevant band is 8%, comparable to the tolerance, so the
  second condition binds often and materially changes the labels.

So the truth choice and the label-rule choice are not independent decisions.

### What the paper contains

| | |
|---|---|
| **Data tables** | **None.** 16 figures, zero tables of measured values |
| **Test runs** | **88 total**, covering four entrance-section lengths (L/D = 20, 40, 60, 80) for **both** upward and downward flow |
| **Surface thermocouples** | 35 along the cylinder, positions in Figure 3 |
| **Bulk air temperature** | One thermocouple at inlet, two at the exit mixing chamber; local bulk temperature by straight-line interpolation between them |
| **Steady state** | Declared when no thermocouple drifted more than a stated threshold |
| **Correlations** | Eq 13 `Nu = 3.7151 (Ra/Re)^0.11868` **upward** — confirmed as the one used as truth. Eq 14 `Nu = 3.6254 (Ra/Re)^0.08697` downward |

### Where the individual values live

All of them are in figures. Coverage is uneven, and **the upward/assisting case — the one
Eq 13 describes and the one the NAFEMS case uses — is the thinner half of the paper.**
Most of the detailed sweeps are downward flow or inclination studies.

| Figure | Content | Upward flow? |
|---|---|---|
| 5, 6 | Surface temperature vs axial distance | No — downward |
| 7, 8 | Surface temperature, inclination angles | Inclination study |
| 9 | Surface temperature, **different flow situations** | **Yes**, among others |
| 10, 11 | Local Nusselt vs dimensionless axial distance | No — downward |
| 12, 13 | Local Nusselt, inclination angles | Inclination study |
| 14 | Local Nusselt, **different flow situations** | **Yes**, among others |
| 15 | Average Nusselt vs axial distance, Re 400 | No — downward |
| **16** | **Log Nu vs Log Ra/Re**, Re 400–1600, Gr 1.1e5–7.4e6, with literature and Sieder–Tate comparisons | **Yes** — this is the average-Nu data the correlation was fitted through |

88 runs across four lengths and two directions is roughly 11 per combination. The directly
relevant count for a single upward configuration is of that order, not 88.

### The figures are vector, which changes what recovery means

The figure pages carry thousands of path-construction operators (`m`, `l`, `c`) and no
meaningful raster images — the embedded bitmaps are 67-byte stubs. **The plots are vector
graphics, so the plotted marker coordinates are in the file exactly.**

Recovery is therefore *extraction from the content stream*, not visual digitisation. The
only error introduced is axis calibration, not marker reading. That is a materially better
provenance than the ±18% read uncertainty this project has had to accept elsewhere, and it
should be done that way rather than with a screen digitiser.

**Not attempted here.** Extraction is a build step, and doing it now would mean producing
evaluation inputs before the protocol is locked.

### Inventory, stated plainly

- **Individual measured values: recoverable, not yet recovered.** They exist as vector
  coordinates in Figures 9, 14 and 16 for the upward case.
- **Per-point uncertainty: does not exist.** The paper reports a single global maximum
  (±1.27% on Nu), not a per-condition band. The two-condition label rule still has no
  per-point term to operate on — but it now has a defensible *global* one, which is a
  different and better position than before.
- **The ±8% figure should be removed** wherever this project uses it as measurement
  uncertainty.

## A proposed evaluation against independent measured points

Offered as a design, not a decision. It is written to break the coupling, not to recover
the old numbers.

### The inversion to keep in view

Given the mechanism derived above, **reproducing precision ≈ 1.00 would now be a warning
sign rather than a success.** It would be consistent with the coupling having survived the
rebuild. A design that targets the old triple is therefore targeting the wrong thing, and
this proposal deliberately does not.

### 1. The evaluable set is the measured conditions, and only those

Truth comes from Mohammed & Salman's reported values at the conditions they actually ran.
Grid points with no measurement are **not evaluable**, however comfortably they sit inside
the `(Re, Gr)` envelope. Envelope membership is not coverage.

This is likely to be a small set. That is a fact about the available evidence, and the
measurement inventory exists to establish it before any criterion is fixed.

### 2. The surrogate is fitted on data disjoint from its evaluation points

This is the change that attacks `ε ≈ 0`.

- Fit `Nu_forced(Re)` on gravity-off CFD at a set of `Re` values, and **evaluate only at
  `Re` values held out of that fit**.
- At an evaluation point the surrogate is then interpolating or extrapolating, so `ε` is a
  genuine generalisation error rather than a residual against the very value that also
  forms the materiality numerator.
- **Record `ε` on both the fitted and the held-out conditions.** This is precisely the
  number that was never recorded, and it decides how much of the coupling survives.

The split is by operating condition, not by row, so that no evaluation point's `Nu_F`
appears in the fit.

### 3. Truth is measured, so `d` is replaced by something unsigned

With measured truth, the `d` term becomes an experiment-versus-CFD difference carrying the
experiment's own uncertainty, with no structural reason to share a sign with the
materiality. That is the cleanest break in the chain, and the one that most changes what
the metrics mean.

### 4. Pre-specify what Step 4 left undefined

- **The error scale.** Write it down. Step 4's `scale` was an undefined symbol and that is
  why A2 is still an assumption.
- **The label rule.** Single-condition or two-condition, decided explicitly; the
  two-condition form needs per-point uncertainty, which may not exist.
- **`θ` and `tol` separately**, with the sweep reported, since aligning them is part of
  what produces the coupling.

### 5. Report accordingly

- Metrics with their uncertainty, never as bare point estimates.
- **Measurement-referenced** only where measured truth was used; **correlation-referenced**
  everywhere else, in those words.
- `ε` reported alongside, on fitted and held-out conditions.
- If the evaluable set is too small to separate the method from its baselines, the outcome
  is `INCONCLUSIVE` and that is a result.

### What this cannot fix

The paper reports **no per-point uncertainty** — only a global maximum of ±1.27% on Nu. So
a two-condition label rule still has no per-condition term to operate on. It can use the
global figure, which is defensible and is a better position than the ±8% this project was
carrying, but it is not the per-point uncertainty the abstract's rule implies.

Note the consequence, because it cuts against the reconstruction rather than for it: at
±1.27% against `tol = 0.10`, **the uncertainty condition almost never binds**, so the
two-condition rule collapses to the single-condition rule in practice. Choosing measured
truth does not rescue the second condition; it removes the need for it.

## What is now decidable, and what is not

**Established by reading the paper:**

- **±8% is the correlation's fit scatter, not the measurement uncertainty.** The measured
  uncertainty on Nu is **±1.27%** (Moffat's method). The project has been using the wrong
  number, by a factor of about six, and it should be removed wherever it stands in for
  experimental uncertainty.
- **No data tables exist.** 88 test runs across four entrance lengths and both flow
  directions; all values live in 16 figures.
- **Individual values are recoverable exactly.** The figures are vector, so the marker
  coordinates are embedded — extraction, not visual digitisation.
- **Per-point uncertainty does not exist.** Only the global ±1.27%.
- **Upward-flow coverage is the thinner half of the paper**; Figures 9, 14 and 16 carry it.
- **Eq 13 confirmed** as the upward correlation used as truth.

**Established by the coupling check:**

- **Causal precision 1.00 is structural**, under assumptions A1–A5. It follows from
  fitting the surrogate to the same gravity-off CFD that supplies the materiality
  numerator and then aligning `θ` with `tol`. A false positive would need a fit residual
  of at least +3.3% just above `θ`, rising past +20% at `m = 0.26`, and only in one
  direction. The residual was never recorded.
- **Recall 0.65 is not structural** in the same way. It is set by calibration-box
  placement, and the coupling says nothing about it.
- **The metrics are correlation-referenced.** No pointwise measurement was used.
- `theta_precondition = 0.20`, `theta_flag_rule = 0.10`, `tolerance = 0.10`.
- Grid extent `Re ∈ [400, 1600] × Gr* ∈ [1e5, 7.4e6]`, **inside** the experimental range.

**Still unknown:**

- The surrogate fit residual `ε`. Not recorded. Decides whether precision was pinned
  exactly or merely nearly.
- How many upward-flow points Figure 16 actually plots, and at which conditions. Counting
  them is part of the measurement inventory, not of this trace.
- The step-4 label scale. A2 is inferred from the Step-3 substrate, not from step 4.
- Whether pointwise measurements exist in the paper at all — it is closed access, 23
  pages, and no open copy was found.
- Whether `d < 0` holds generally. Two observations, both at `Ri ≥ 1.8`.
- Measurement coverage at the grid points, as distinct from envelope membership.

**Still yours to decide:**

1. **What claim the causal result supports.** If precision 1.00 is structural, the honest
   headline is not "no false alarms" — it is the causal-versus-naive comparison, where
   naive's 0.73 is uncoupled and therefore real. That is a smaller claim and a sounder one.
2. **Whether to extract the pointwise measurements.** The paper is now in hand and the
   values are recoverable exactly from the vector figures. This remains the cleanest break
   in the coupling and the only route to an experimental-truth claim. It is now a build
   task rather than an access problem.
3. **Which label rule — and note it is now entangled with the truth choice.** With
   measured truth the uncertainty is ±1.27%, which against `tol = 0.10` almost never
   binds, so the two-condition rule collapses to the single-condition one. With
   correlation truth the relevant band is ±8%, comparable to the tolerance, so the second
   condition binds often and changes labels. These are not two independent decisions.
4. **What the evaluable rule says about coverage** — grid points far from any measured
   condition, now that extrapolation beyond the envelope is off the table.

**Explicitly not decided here.** No surrogate, label rule or grid has been selected, and
none should be selected because it would make the original numbers recur. The finding
above cuts the other way: the construction that produced 1.00 is the one that makes 1.00
uninformative, so reproducing it would reproduce the problem rather than the result.
