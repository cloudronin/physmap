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

## 9. Order of operations

1. Fill the four decisions. Lock the protocol; record its hash.
2. Run the reconstruction.
3. Only then examine outcomes and write `expected_metrics.json`, stamped with the protocol
   hash and every input hash.
