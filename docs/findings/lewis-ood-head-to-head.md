# Lewis 35A head-to-head — the input-based OOD detector against PhysMAP

**Status: development demonstration.** 35A is a spent run: every station of it had already been
inspected against agreement. Its twelve stations are twelve measurements of **one** operating
condition, not twelve cases. No precision, recall or F1 is computed, and none may be computed
from this.

## The short answer

**The input-based OOD detector did not stay quiet.** It fired at every 35A station, in both
pre-committed training designs, at every operating percentile including the most lenient.

**But its firing carries no information about where the surrogate is wrong.** Its output is
*identical* when the surrogate is accurate to 0.25 % and when it is wrong by 17–18 %, because
what separates those two cases — gravity — is not one of its inputs. It fires because 35A's
operating point sits between the training runs' operating points, which is true and irrelevant.

**PhysMAP's flag lands on real errors, and names their cause.** It flags x/D 67.55, 101.69 and
135.84, where the surrogate is off by 17.0 %, 16.8 % and 18.0 % — six to eleven times the
experiment's bulk-error uncertainty at those stations — and buoyancy accounts for most of each.
It stays quiet on the control where the surrogate is right.

**PhysMAP does not catch errors with other causes.** At x/D 2.45 (+9.9 %) and 16.32 (−12.8 %) the
surrogate is wrong mostly because of the base model's own gap to the experiment, not buoyancy.
PhysMAP does not flag them and is not built to.

## Input contract

| | |
|---|---|
| Surrogate inputs | `Re`, `Pr`, `x_over_D` |
| OOD detector features | `log10_Re`, `Pr`, `x_over_D` — the guardrail's own `input_to_feature` map |
| Position | **included** — the surrogate predicts local Nu, so `x_over_D` is an input to both |
| Not an input to either | `Gr_q`, `Ri`, wall heat flux, gravity, flow direction |
| Deploy inputs | Re 1143.4, Pr 8.46 — Lewis Appendix D-2, inlet-bulk basis |

The OOD detector receives **every** input the surrogate receives. Nothing is withheld from it.

## The OOD detector is the shipped one, unchanged

`physmap.benchmarks.benchmark_v0_4._DETECTORS`, imported, not rebuilt. Two baselines, fired if
either fires, exactly as the benchmark reads them:

- **distance-to-training** — Mahalanobis, mean distance to the 3 nearest training rows;
- **GP variance** — Matérn-5/2, posterior std / |mean|, threshold floored at 0.05.

Each fires when its score exceeds the given percentile of the **training rows' own** scores. The
benchmark's percentiles were swept — 50, 75, 90, 95, 99, 100 — with 99 as reference. Both
baselines are marked "locked v0.2, do not change" in the source, and were not.

## The surrogate

The NAFEMS original's own recipe: a forced-convection model fitted to **gravity-off** CFD. It
mirrors the benchmark's buoyancy vehicle, Jin: a surrogate that omits the mechanism, trained
where the mechanism is absent, deployed where it is present, over the same input range.

- GP on (log10 Re, Pr, log10 x/D) → log Nu, fitted to variable-property CFD with Lewis's
  Appendix B properties and his Nu definition applied to each run's own inlet-bulk values.
- **Design A (pre-committed):** 8 runs, Re {750, 950, 1350, 1550} × inlet {12.0, 14.5} °C,
  35A's heat flux, 40 log-spaced stations each. 35A's operating point is interior, not a node.
- **Design A3 (pre-committed sensitivity):** A plus a third inlet level, 13.25 °C.
- Every training run converged and closed energy within 0.5 %. The four low-Re runs first
  closed only to −0.6…−2.25 % at 2000 iterations with the enthalpy residual still falling; they
  were continued to 4000 and then closed within 0.35 %. A numerical acceptance fix, made on the
  residual history, before any head-to-head output existed.

**It is an excellent forced-convection model.** Leave-one-run-out error: worst 0.58 % (A),
0.42 % (A3). At 35A it reproduces gravity-off CFD at 35A's exact conditions to within **0.27 %**
(A) and **0.25 %** (A3) at every station. So its error against the experiment is not a fitting
problem.

## What the OOD detector actually responds to

Firing at every station, in both designs, at every percentile:

| design | distance score along the tube | threshold | fires |
|---|---|---|---|
| A | 1.08 → 1.14 | 0.45 | everywhere |
| A3 | 0.60 → 0.70 | 0.47 | everywhere |

The distance score is almost flat along the tube, so position is not what drives it. Decomposing
it from the training inputs alone — moving 35A's value onto the nearest training level, one axis
at a time — shows why:

| | distance score | fires? |
|---|---|---|
| as deployed | 1.08–1.13 | yes |
| Pr gap closed only | 0.58–0.67 | **yes** |
| Re gap closed only | 0.91–1.00 | yes |
| both closed | 0.007–0.33 | no |

35A is off the training grid in both Re and Pr, and **either gap alone fires it**. The
pre-committed third inlet level closed the Pr gap — and the Re gap still fired it, as the
decomposition predicted. The detector is correctly reporting "no training run at this operating
point". It is not reporting anything about buoyancy, because it cannot.

The GP-variance score is not flat: it is near zero at the dense entrance stations and 0.2–1.7
downstream, where the training stations thin out. It does not track the error either — it is
lowest of the downstream stations at x/D 135.84, where the error is largest.

## The control: same inputs, gravity off

Same surrogate, same detectors, same inputs, scored against **gravity-off** CFD at 35A — where
the surrogate is accurate — instead of against the experiment.

| x/D | gravity OFF: error | OOD | PhysMAP | gravity ON (experiment): error | OOD | PhysMAP | materiality |
|---|---|---|---|---|---|---|---|
| 2.45 | −0.04 % | fires | quiet | +9.9 % | fires | quiet | 0.006 |
| 9.92 | −0.06 % | fires | quiet | −2.6 % | fires | quiet | 0.020 |
| 16.32 | −0.06 % | fires | quiet | −12.8 % | fires | quiet | 0.032 |
| 33.39 | −0.03 % | fires | quiet | −11.0 % | fires | quiet | 0.061 |
| 50.47 | −0.01 % | fires | quiet | −10.0 % | fires | quiet | 0.087 |
| 67.55 | −0.00 % | fires | quiet | −17.0 % | fires | **flags** | 0.111 |
| 101.69 | +0.00 % | fires | quiet | −16.8 % | fires | **flags** | 0.154 |
| 135.84 | +0.05 % | fires | quiet | −18.0 % | fires | **flags** | 0.195 |

**The OOD detector's output is bit-identical in the two columns**, at every station and every
percentile. That is true by construction — its scores read only the inputs — and the run
confirms it. It cannot tell a condition where the surrogate is right from one where it is wrong,
when the difference is a mechanism outside its inputs.

**PhysMAP separates them.** With gravity off, Ri = 0 sits inside the surrogate's calibrated
window, so the flag rule's out-of-range half fails and it stays quiet. With gravity on,
Ri = 0.287 is outside it, and the flag follows materiality.

## Does the flag correspond to an actual prediction error?

The surrogate matches gravity-off CFD to 0.25 %, so its error against the experiment splits
cleanly into **missing buoyancy** — PhysMAP's materiality — times **the base model's own gap**
to the experiment (the gravity-*on* CFD against the measurement). The split closes to within
0.2 % at every station.

| x/D | surrogate error | from missing buoyancy | from base model gap | exp. bulk-error unc. | PhysMAP (θ = 0.10) |
|---|---|---|---|---|---|
| 2.45 | +9.9 % | −0.6 % | +10.6 % | 0.1 % | quiet |
| 5.65 | −6.4 % | −1.2 % | −5.2 % | 0.1 % | quiet |
| 9.92 | −2.6 % | −2.0 % | −0.6 % | 0.2 % | quiet |
| 16.32 | −12.8 % | −3.2 % | −9.8 % | 0.4 % | quiet |
| 33.39 | −11.0 % | −6.1 % | −5.2 % | 0.8 % | quiet |
| 50.47 | −10.0 % | −8.7 % | −1.4 % | 1.1 % | quiet |
| 67.55 | −17.0 % | −11.1 % | −6.6 % | 1.5 % | **flags** |
| 101.69 | −16.8 % | −15.4 % | −1.6 % | 2.3 % | **flags** |
| 135.84 | −18.0 % | −19.5 % | +1.8 % | 3.1 % | **flags** |

(Surrogate errors from design A3; design A differs by at most 0.01 percentage points. Comparable
stations only. Lewis disowns x/D 0.31 and 0.85 for axial wall conduction and 159.33
as "suspect". The uncertainty column is only the bulk-temperature component; a combined
per-point uncertainty is not reported by the source and is a protocol decision.)

**Where PhysMAP flags, the error is real and large** — 17–18 %, far above the bulk-error
uncertainty — **and the mechanism it names is the main cause.** At x/D 101.69 and 135.84
buoyancy accounts for essentially all of it.

**Where PhysMAP is quiet, the errors split three ways:**

- **x/D 9.92 and 5.65** — small errors, correctly quiet.
- **x/D 33.39 and 50.47** — buoyancy is real (−6.1 %, −8.7 %) but below θ = 0.10. Whether these
  should flag is exactly the θ decision the protocol has not locked.
- **x/D 2.45 and 16.32** — the error is mostly the base model's gap to the experiment, not
  buoyancy. PhysMAP does not flag it and is not designed to. The surrogate inherits this gap from
  the CFD it was trained on; a surrogate built on a better base model would carry less of it.

## What this says about when an input-based OOD detector fires

The NACA demo and this run look contradictory and are not. In NACA the input-based OOD detector
was silent on all 45 entrance points; here it fired on all 12 stations. The difference is **where
the deploy point sits in the input space**, not whether the unmodelled mechanism is active:

- NACA's entrance points share their operating point with the training data — only `x/D` differs,
  and `x/D` is not an input — so they look in-distribution.
- 35A is at an operating point between the training runs, so it looks out-of-distribution.

In both, the detector's answer is independent of the mechanism that breaks the surrogate. Silent
in one, firing in the other, informative about the mechanism in neither.

## What may and may not be said

- **Say:** "An input-based OOD detector gives the same answer whether buoyancy is on or off,
  because gravity is not one of its inputs. On Lewis 35A it fired everywhere in both cases —
  including the case where the surrogate is right to a quarter of a percent. PhysMAP stayed
  quiet there, and flagged the downstream stations of the real run, where the surrogate is off
  by 17–18 % and buoyancy accounts for most of it."
- **Do not say** the OOD detector "missed it" or "stayed quiet" on Lewis. It fired.
- **Do not say** PhysMAP "caught what the OOD detector missed" on Lewis. Both fired downstream;
  only one fired *because of* the error.
- **Do not say** PhysMAP catches every surrogate error. It missed the base-model errors at x/D
  2.45 and 16.32, by design.
- **Do not say** anything about NVIDIA PhysicsNeMo. Its out-of-distribution check and its physics
  checks are separate things; neither was run here, and no faithful equivalent was built or tested.
- **Always say** it is one development run, and its stations are not independent cases.

## Adherence to the pre-commitment

`results/lewis35A_head_to_head/PRECOMMIT.md` was written before any head-to-head output for
the real design existed, and discloses the one-run smoke test that preceded it. Its rules were
followed: design A's result is reported first and unreplaced; the single permitted sensitivity
(the third inlet level, triggered by the Pr gap being a driver of the distance score) was run and
is reported alongside; nothing else about the design changed in response to any result. The
gravity-off control is an additional analysis of the matched pair built earlier, not a change to
the training design.

## Files

- `cfd/lewis_head_to_head.py` — the run
- `results/lewis35A_head_to_head/design_A_8runs.json`, `design_A3_12runs.json` — full outputs
- `results/lewis35A_head_to_head/control_gravity_off.json` — the control
- `results/lewis35A_head_to_head/PRECOMMIT.md` — the pre-commitment
