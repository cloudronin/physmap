# Locked reconstruction protocol — NAFEMS 2026 mixed convection

**Status: DRAFT — NOT LOCKED.** Four decisions are outstanding (marked **DECISION
REQUIRED**). The protocol is locked by filling them in, setting `status` to `locked` in
`protocol.json`, and recording its SHA-256. **No reconstructed outcome may be examined
before the lock.**

Read [`known-results-declaration.md`](known-results-declaration.md) first. It records what
was already known, and it is why this is a *reconstruction protocol* and not a
pre-registration.

## Scope

One case: laminar mixed convection in a vertical pipe, buoyancy-assisting, constant wall
heat flux. Quantity of interest: wall Nusselt number. Competing mechanisms: forced and
natural convection.

## 1. Grid and the evaluable set

The CFD grid and the **evaluable set are not the same thing**, and conflating them is the
main way this reconstruction could quietly overstate itself.

- The CFD grid may be dense. Materiality is computed from CFD, so it exists everywhere
  the CFD ran.
- Precision and recall exist **only where independent truth exists**. If the source
  experiment measured a handful of conditions, the evaluable set is that handful.

Every row carries an `evaluable` flag. Metrics are computed over evaluable rows only, and
the reported `n` is the evaluable count, never the grid count.

> **DECISION REQUIRED — grid.** State the `(Re, Gr*)` points, how they were chosen, and
> the rule that decides `evaluable`.

## 2. Surrogate under test

> **DECISION REQUIRED — surrogate.** State exactly what is being guarded: whether
> `Nu_pred` is a separately fitted surrogate model, or the forced-convection calculation
> itself. This changes what `surrogate_predictions.csv` contains and how the structural
> nature of the lift must be described.

## 3. Label rule

A prediction is labelled **untrustworthy** iff the surrogate-truth gap exceeds **both**:

1. the trust tolerance, and
2. the truth's own uncertainty at that point.

Both conditions are required. A gap inside the experiment's own error bar is not evidence
of anything. This is why `independent_truth.csv` must carry a per-point uncertainty;
truth without uncertainty is refused by the readiness gate.

> **DECISION REQUIRED — tolerance and uncertainty.** State the trust tolerance value, and
> how per-point experimental uncertainty is obtained (reported by the source, digitised
> from error bars, or estimated — and if estimated, by what rule).

## 4. Materiality

Materiality is causal: the fractional change in the QoI attributable to a mechanism,
estimated by counterfactual removal.

    materiality = 1 - Nu_F / Nu_M

`Nu_M` is the mixed (buoyancy-on) result. `Nu_F` is the counterfactual with buoyancy
removed. `Nu_F` must come from either:

- **matched CFD ablation** — same mesh, same boundary conditions, buoyancy term removed
  (preferred; it is what the abstract claims), or
- a **geometry-appropriate** forced-convection calculation for a pipe under constant wall
  heat flux.

A flat-plate correlation applied to a pipe is **not** acceptable and is a hard refusal in
the readiness gate. The choice is recorded per row as `nu_f_provenance`.

> **DECISION REQUIRED — threshold.** One `θ` per job. The existing code uses `0.20`; the
> abstract states `θ ≈ tol = 0.10`; the original writeup uses both for different purposes.
> State the value used for the applicability precondition and the value used for the flag
> rule, and whether they are the same number.

## 5. Flag rule

    flag(mechanism, point, qoi) ⟺ outside_calibration(mechanism, point)
                                   AND materiality(mechanism, point, qoi) ≥ θ

Out-of-range **and** material. Out-of-range but immaterial stays quiet — that is the disc
region, and staying quiet there is the point of the method.

## 6. Baselines

Both must be defined well enough for a third party to reimplement without reading our code.

- **Physics-blind input-space OOD** — operates on surrogate inputs only.
- **Naive box-check** — flags any mechanism outside its calibration range, regardless of
  materiality.

## 7. Metrics

Precision, recall and F1 against the label of §3, computed over evaluable rows only.
TP/FP/FN counted per operating point. A threshold sweep over `θ` is reported alongside the
single-threshold table, because the abstract's precision advantage is claimed as
unconditional across that sweep while the F1 advantage is claimed as conditional.

## 8. Truth independence

Only `experimental` or `independent_high_fidelity` truth may back a reported metric.
Same-closure truth raises before any metric is computed.

**Open issue carried into the lock:** the previous implementation marked this substrate
`divergent_truth_substrate=False`, on the grounds that the truth column was a
closure-style correlation rather than measurement. Until that is resolved — by sourcing
measured points, or by restating what the metrics are measured against — no
experimental-truth performance claim may be published.

## 9. How the reconstruction's result may be described

Fixed here, before any rebuilt number exists.

### The word "reproduced" is reserved, and this reconstruction cannot earn it

"Reproduced the original numbers" means a close rerun of the original evaluation: the same
grid, the same truth source, the same counterfactual. The original inputs are gone — see the
known-results declaration — so that rerun is not available. This reconstruction changes the
grid, the truth source and the counterfactual by necessity.

`REPRODUCED` is therefore defined in the vocabulary below and is **unreachable under this
protocol**. It is kept precisely so the word has a fixed meaning and cannot drift onto a
weaker result.

This is the position the known-results declaration already takes. The two documents are
deliberately consistent, and neither may be changed without the other.

### What a matching result would be instead

**Independent corroboration of the causal finding.** Different grid, different truth source,
different counterfactual, same conclusion. That is evidentially valuable and it is worth
presenting. It is also a different and weaker claim than reproduction: it supports the
finding, it does not recover the numbers.

### Containment in a confidence interval is not the test

An earlier draft of this section asked whether each original value fell inside the
reconstruction's 95% interval. **That is the wrong test, and it is removed.**

A value sitting inside an interval means the data fail to reject it. That is not the same as
showing the two agree, and a wide enough interval contains almost anything. Establishing
agreement requires an equivalence margin and an equivalence test against it. An equivalence
margin cannot be chosen honestly before the available measurements are known.

The earlier draft also proposed a minimum evaluable-set size and a maximum interval width.
Both are removed for the same reason: they were numbers picked in ignorance of the data.

### Prerequisite — the measurement inventory

Before any criterion is fixed, produce and commit
`data/benchmarks/mixed_convection/measurement_inventory.md`.

**It records inputs only.** Everything below can be established by looking at the sources
and the operating conditions, without running the surrogate, applying the label rule, or
running the detector.

| Item | Why it matters |
|---|---|
| The measurement sources — which publication, which table or figure, how digitised | Fixes what independent truth actually exists |
| The available operating points, with their `(Re, Gr*)` | Sets the ceiling on every claim |
| Which points are eligible under the §1 evaluable rule, and why each is or is not | Metrics are computed over evaluable rows only |
| Whether each eligible point carries a stated uncertainty, and its source | The §3 label rule needs a per-point uncertainty; a point without one cannot be labelled |
| The redistribution determination for each source | No file enters the repository without one |

### What the inventory must NOT contain

**No labels. No flags. No class balance.**

Specifically: not how many points are trustworthy or untrustworthy, not how many the
detector flags, and not any count derived from comparing predictions against truth.

Those are **outcomes**, not inputs. "Trustworthy" is the §3 label rule applied to a
surrogate prediction, a truth value and an uncertainty. "Flagged" is the §5 flag rule
applied to a calibration check and a materiality estimate. A class balance is a summary
of both. Reading any of them before the criterion is fixed is reading a projection of the
result, and a criterion chosen afterwards is a criterion chosen knowing which way it
would fall. That is precisely the freeze this protocol exists to hold.

These counts are computed **after** the stage-2 lock, and reported with the result.

### How stage 2 is fixed without seeing the balance

There is a real tension here, and it is resolved rather than ignored: the power of
precision and recall genuinely depends on the class balance, which is exactly what stage 2
may not look at.

**So stage 2 fixes a decision rule, not a number.** The criterion is written as a function
of the balance — evaluated once the balance is computed, but specified before it is seen.
For example, a minimum count of positives below which the outcome is `INCONCLUSIVE`
is stated as a rule with its reasoning, and then applied to whatever the balance turns
out to be. What is forbidden is choosing that threshold after seeing the number it will
be compared against.

### The locks, and why the ordering changed

**Revised.** An earlier version put the grid (§1) and the surrogate (§2) in the first lock,
to be fixed *before* the measurement inventory. That ordering was wrong: both depend on
knowing which measured conditions exist, and fixing a grid before that is fixing it in
ignorance. It has been corrected.

**The invariant is not "lock early". It is: lock every scoring choice before any label,
flag or performance number is examined.** Everything else follows from that, and nothing
more is required by it.

| | What it fixes | When |
|---|---|---|
| **Lock A** | The things that do not depend on what data exists: the result vocabulary (§9), the materiality definition and its refused provenances (§4), the flag rule (§5), the truth-independence requirements (§8), and the baselines (§6) | **Now.** Nothing blocks it |
| *(no lock)* | **Source discovery and the input-only inventory**, and the CFD's own **numerical verification** — grid convergence, residuals, energy balance, sensitivity of the Nusselt extraction | Now, in parallel. These are genuinely neutral |
| **Lock B** | Every scoring choice: the grid and evaluable rule (§1), the surrogate **form and split** (§2), the label rule and tolerance (§3), `θ` (§4), the metric definitions (§7), and the corroboration criterion | **After** the inventory, and **before materiality or fit residuals are inspected at any evaluation condition** |

This is not a loosening. Lock B still precedes every outcome. It simply stops the protocol
demanding a grid before anyone knows which conditions were measured.

### Not everything that precedes a label is a neutral input

The distinction that matters, and it is finer than "inputs versus outcomes":

**Materiality at an evaluation condition, and the surrogate's fit residual there, are not
neutral.** Through the coupling derived in the findings —
`E = d − m(1+d) + ε` — both of them carry information about that condition's eventual
error label. Seeing either before the scoring choices are fixed is seeing a shadow of the
answer, even though neither is a label.

| Quantity | Neutral? | May be inspected before Lock B? |
|---|---|---|
| Source inventory: conditions, geometry, stated uncertainty | Yes | Yes |
| CFD grid convergence, residuals, energy balance | Yes | Yes |
| Nusselt-extraction sensitivity | Yes | Yes |
| **Materiality at an evaluation condition** | **No** | **No** |
| **Surrogate fit residual at an evaluation condition** | **No** | **No** |
| Labels, flags, class balance, metrics | No | No |

### Development conditions, kept apart from evaluation conditions

Developing a surrogate needs residuals — you cannot choose a functional form blind. So the
conditions are split three ways, not two:

| Set | Purpose | May its residuals be inspected before Lock B? |
|---|---|---|
| **Development** | Choosing the surrogate's functional form, diagnosing fit problems | **Yes.** That is what it is for |
| **Fit** | Fitting the final surrogate once the form is fixed | Only as a fitted residual, after Lock B |
| **Evaluation** | Scoring | **No.** Untouched until Lock B is recorded |

Development conditions are **discarded from the evaluation entirely** — they are not held
out, they are spent. A condition whose residual was examined while choosing the functional
form cannot afterwards serve as an unbiased test of that form.

#### Applied to Lewis (recorded 2026-09-23)

**Runs 13A, 16A and 35A are spent.** Every station of all three has been inspected against
agreement — against Lewis's measurement, against his own Figure 7.4 laminar prediction
curves, and across a constant-property basis sweep. They may be used to build and debug the
solver and to argue about mechanisms. They may not contribute to any precision, recall, F1
or materiality figure, and no eligibility rule may be tuned on them.

**One boundary in particular must not be reused.** The 13A laminar cutoff near x/d ≈ 102 was
located *by looking at where measurement and prediction diverge*. As a diagnostic that is
exactly right — it is how the constant-property defect was found. As a scoring boundary it is
circular: a line drawn where agreement fails selects for agreement inside it, so any metric
computed within it is biased upward by construction. The cutoff is a finding about the
experiment. It is not an eligibility rule and cannot become one.

**Before any remaining run or region is scored**, the eligibility and QoI rules are fixed and
committed first. While fixing them, these may be consulted:

- source-reported operating conditions — `Re`, `Pr`, `Gr_q`, wall boundary condition, geometry;
- source-reported energy balance and heat loss;
- the absolute bulk-temperature error expressed against the wall-to-bulk difference;
- source-reported instrument accuracies;
- a transition criterion from an **independent** source, used **inside** its stated validity
  range;
- Lewis's Table 7.1 predicted-reversal list, carrying its known limitation that a laminar
  code cannot predict transition at all.

These may **not**:

- measurement-versus-prediction agreement for the candidate run;
- any PhysMAP flag, materiality value or detector outcome;
- any CFD result for the candidate run;
- class balance, or how many runs a proposed rule would admit.

**The flow-eligibility rule cannot currently be closed.** No independent transition criterion
qualifies: Hallman's was tested and rejected because Lewis's stations lie 1.5× to 24× outside
its stated validity range. Until one exists, there is no eligible evaluation set, and metrics
stay closed.

### Outcomes

| Outcome | Meaning |
|---|---|
| `REPRODUCED` | Reserved for a close rerun of the original evaluation. **Unreachable under this protocol** |
| `CORROBORATED` | The reconstruction independently supports the causal finding, under the stage-2 criterion |
| `NOT_CORROBORATED` | It does not |
| `INCONCLUSIVE` | The available measurements cannot support a metric claim either way |
| `NOT_ATTEMPTED` | The reconstruction has not been run |

### In every outcome

The reconstruction's metrics are reported **with their uncertainty**, always — never as bare
point estimates. The numbers presented are the reconstruction's. The original triple is never
presented as a number this repository produces.

## 10. Order of operations

1. **Lock A.** The data-independent decisions above. Record the hash.
2. **Source discovery and the input-only inventory**, in parallel with the rebuild. Record
   per candidate source: flow direction, `Re`, `Gr` or `Ra`, geometry and entrance length,
   measured `Nu`, and uncertainty. Inputs only — no labels, no flags, no class balance.
3. **The rebuilt CFD and its matched gravity-off runs**, with numerical checks recorded.
   Acceptance rests on the CFD's own criteria — grid convergence, residuals, energy
   balance, sensitivity of the Nusselt extraction. **Eq 13 is a reported correlation check,
   not the acceptance test.**
4. **Surrogate development** on the **development conditions** only. Residuals there may
   be inspected freely; those conditions are then spent and take no part in the
   evaluation.
5. **Lock B.** Every scoring choice, given what the inventory found — including the
   surrogate's form and the fit/evaluation split. Record the hash.
6. **Only now** fit the final surrogate, compute its residual at evaluation conditions,
   compute materiality there, run the detector, and derive labels and class balance.
7. Examine outcomes. Report metrics with their uncertainty, and say what they are
   referenced against — measured points or a correlation.

Steps 2, 3 and 4 may run in any order or together; none of them is a scoring choice, and
none of them touches an evaluation condition's materiality or residual. **Step 5 must
precede step 6.** That single ordering is what the freeze protects.

### If no evaluable truth set is found

Steps 3 and 4 still produce something worth having: a rebuilt CFD with recorded numerical
checks, matched ablation runs, and a surrogate with a measured generalisation residual.
That is a **reproducible demonstration of the method**, and it is reported as such — with
no performance metrics attached, because none would be supportable.
