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

### A coupling worth checking before you lock anything

This is offered as a question, not a finding.

The surrogate `Nu_s` is fitted to the **g-off** CFD. The materiality numerator `Nu_F` is
the **g-off** CFD. If `Nu_s ≈ Nu_F` by construction, and the truth `Nu_t ≈ Nu_M` (the CFD
validates against Eq 13 within −3.7% and −9.3%), then the surrogate error

    |Nu_s − Nu_t| ≈ |Nu_F − Nu_M| = Nu_M · materiality

is not merely *correlated* with materiality — it is approximately materiality times the
truth, through a shared input.

The step-4 design anticipated part of this and called it near-circularity, but scoped the
concern to the **recall** arm:

> the causal materiality and the surrogate error both reflect the *same* physical buoyancy
> effect, so they correlate by physics… The precision lift on the disc region does **not**
> inherit this circularity (it turns on box-edge vs threshold, not on the error).

If the relation above holds algebraically rather than only physically, then a causal false
positive requires `materiality ≥ θ` **and** `Nu_M · materiality ≤ tol` simultaneously —
which, when `θ` is aligned to `tol`, may be close to impossible by construction. That
would make **precision = 1.00 structural too**, not only recall.

**This is checkable without any CFD**: it needs only the functional form of the fitted
`Nu_forced(Re)` and the definition of the label scale. It should be settled before the
grid and θ are locked, because if it holds, the headline precision result changes meaning.

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

### Two further facts that bear on the grid

1. **Part of the step-4 grid sits outside the experimental envelope.** The grid runs
   `Gr* ∈ [1e5, 7.4e6]`; the companion paper's experiments run `Gr 2.0e5–6.2e6`. Both ends
   of the grid extend past it. Whatever the evaluable rule turns out to be, it has to say
   what happens where the correlation is being extrapolated beyond the data it was fitted
   to.
2. **A provenance inconsistency, minor but worth fixing.** The calibration corpus registers
   `Ri ∈ [0.1, 10]` under `aung-worku-mixed-convection-1986` with the note *"Eq13 family"*,
   `primary_source: false`, and the reason *"mixed-convection regime is typically reported
   as Ri ∈ [0.1, 10]"*. That is a textbook regime boundary attributed to Aung & Worku —
   not Mohammed & Salman's measured `Ri ≈ 0.1–30`. Two different things share the name
   "Eq13" in this repository.

---

## What is now decidable, and what is not

**Decidable from this evidence:**

- `theta_precondition = 0.20`, `theta_flag_rule = 0.10` — both are documented, in
  different roles.
- `tolerance = 0.10`.
- The grid's stated extent: `Re ∈ [400, 1600] × Gr* ∈ [1e5, 7.4e6]`.
- The materiality provenance is `matched_cfd_ablation`, which the protocol already allows.

**Not decidable — these are yours:**

1. **Is the truth experimental?** The evidence says the truth was a correlation fitted by
   the authors to their data, with a global ±8%. Recovering measured points means
   obtaining a closed-access paper and extracting its tables or figures. Until then, no
   per-point uncertainty exists, and the label rule's uncertainty term has nothing to
   operate on.
2. **Which surrogate definition do you lock?** The one that produced the numbers is a
   forced-convection closure fitted to the g-off CFD, and its code is gone. Reimplementing
   it means refitting from the new CFD — reproducing the *method*, not the artifact.
3. **Does the shared-input coupling hold?** Settle it before locking the grid and θ. It is
   answerable on paper.
4. **What is the evaluable rule where the correlation is extrapolated** past `Gr 6.2e6` and
   below `2.0e5`?
5. **Which label rule is correct** — the single-condition one that the surviving design
   documents, or the two-condition one the abstract describes?
