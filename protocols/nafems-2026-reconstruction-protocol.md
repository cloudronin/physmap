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

## 9. What counts as reproducing the original numbers

Fixed here, **before any rebuilt number exists**.

This section exists because the original results are already known — they are listed in the
known-results declaration. Without a criterion agreed in advance, "did it reproduce?" becomes
a judgement made after seeing the answer, and the acceptable band quietly widens until the
answer fits. Locking the criterion now is what lets a successful reconstruction be presented
as a reproduction rather than as a claim the reader has to take on trust.

The reconstruction does **not** re-run the original study. The grid changes, the truth source
changes, and the counterfactual changes. Agreement is therefore a statistical question, not an
equality check.

### Inputs to the decision

- The reconstruction's triple: precision, recall, F1 over the evaluable set.
- A 95% bootstrap confidence interval for each, by resampling evaluable points.
  `B = 10000`; the random seed is recorded in the lock.
- The original triple **1.00 / 0.65 / 0.79**, as recorded in the known-results declaration.

### Preconditions — checked first

> **DECISION REQUIRED — power.** Both numbers below are set at lock time and never afterwards.
>
> 1. **Minimum evaluable set size `N_min`.** Proposed: **12**.
> 2. **Maximum interval width `W_max`**, absolute, for every metric. Proposed: **0.35**.

The second precondition is the one that matters. With a small evaluable set, a bootstrap
interval can grow wide enough to contain almost any value, which would make agreement
automatic and meaningless. A result too imprecise to separate the method from its baselines
is not a reproduction; it is a result with no power. If either precondition fails, the
outcome is `INCONCLUSIVE` regardless of where the numbers landed.

### Outcomes

| Outcome | Condition |
|---|---|
| `REPRODUCED` | Preconditions pass, **and** all three original values fall inside their intervals, **and** all three qualitative claims below hold |
| `SUPERSEDED` | Preconditions pass, and at least one original value falls outside its interval |
| `INCONCLUSIVE` | A precondition fails |
| `NOT_ATTEMPTED` | The reconstruction has not been run |

### The three qualitative claims

Taken verbatim from the known-results declaration:

1. The **precision** advantage over both baselines holds across the whole `θ` sweep —
   claimed as unconditional.
2. The **F1** advantage over both baselines is claimed as conditional.
3. The lift is **structural**, not the product of a tuned threshold.

A quantitative match with a failed qualitative claim is `SUPERSEDED`, not `REPRODUCED`. The
qualitative claims are what the abstract actually argues; the triple is evidence offered for
them.

### What may be said, per outcome

| Outcome | The talk and the repository may say |
|---|---|
| `REPRODUCED` | The results are reproduced. Present the **reconstruction's** triple as the reported numbers, point to the new evidence, and state that the original inputs are unavailable and these come from the reconstruction |
| `SUPERSEDED` | Present the **new** numbers as the result. The original triple is reported as the earlier figure the reconstruction did not recover, with the difference stated plainly |
| `INCONCLUSIVE` | Present the method, not a performance claim. State that the reconstruction lacked the power to settle it |
| `NOT_ATTEMPTED` | The original triple is a historical result that the public release does not reproduce |

**One rule holds in every outcome.** The numbers presented are always the reconstruction's,
never the original's. Even under `REPRODUCED`, the slide shows the new triple and the new
interval. The original triple is never presented as a number this repository produces.

## 10. Order of operations

1. Fill the decisions: the four in §§1–4, and the two power numbers in §9.
2. Lock the protocol; record its hash.
3. Run the reconstruction.
4. Only then examine outcomes, evaluate §9, and write `expected_metrics.json` — stamped with
   the protocol hash, every input hash, and the resulting agreement outcome.
