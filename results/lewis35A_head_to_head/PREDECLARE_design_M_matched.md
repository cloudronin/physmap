# Pre-declaration — design M, the operating-point-matched check

Written 2026-09-23T21:28Z and committed **before design M is run**. At the time of writing no
design-M output of any kind exists: no surrogate fit, no detector score, no prediction, no
error. Git history is the proof of order — this file lands in a commit that precedes every
design-M result file.

## Why this check exists

Designs A and A3 could not test the intended blind spot. 35A's operating point sat between the
training runs', so the input-based OOD detector fired everywhere for a reason unrelated to
buoyancy — and gave the identical answer with gravity off. That supports a claim about
**specificity and causal diagnosis**, and is recorded as such. It does not show what an
input-based OOD detector *misses*.

Design M removes the input-gap confound. The evaluated `(Re, Pr, x/D)` values become training
inputs, while gravity and Ri stay withheld from both the surrogate and the detector. If the
detector is then quiet for **both** gravity states while PhysMAP's output changes, that is the
blind spot, shown directly.

## Everything identical to design A3

- **Detectors:** `physmap.benchmarks.benchmark_v0_4._DETECTORS`, imported unchanged.
  Operating percentiles 50, 75, 90, 95, 99, 100; reference 99.
- **Surrogate recipe:** GP on (log10 Re, Pr, log10 x/D) → log Nu, same kernel, bounds, restarts
  and seed.
- **The twelve A3 training runs**, sampled exactly as in A3 — 40 log-spaced stations each.
- **Inputs to both surrogate and detector:** `Re`, `Pr`, `x_over_D`. Gravity and Ri withheld.
- **PhysMAP:** the applicability screen; calibration window Ri ∈ [0, 0] (the surrogate's
  training never saw buoyancy); materiality from the matched pair `pair_gON` / `pair_gOFF`;
  flags shown at θ = 0.10 and 0.20 as illustrations, θ being unlocked.
- **Comparable stations:** Lewis's own exclusions — x/D 0.31 and 0.85 (axial wall conduction),
  159.33 (suspect).
- **Test sets:** the 35A experiment (gravity on) and `pair_gOFF` CFD (gravity off), 12 stations
  each, inputs Re 1143.4, Pr 8.46.

## The one change

**Add one gravity-off training run at 35A's operating point:** `pair_gOFF`, the existing
gravity-off half of the matched pair — converged, energy closure +0.11 %. It is sampled at the
same 40 log-spaced stations as every other run **plus** Lewis's 12 stations. Thirteen runs.

**Its rows are labelled with the evaluated inputs, Re 1143.4 and Pr 8.46.** Evaluated through
Lewis's own property polynomials its inlet values are Re 1142.69 and Pr 8.4719 — offsets of
−0.062 % and +0.141 %, inside the spread between Lewis's B.1 and B.2 property equations. The run
was built at 35A's reported operating point; labelling it with the reported values makes every
evaluated input an exact training input, which is the thing this check exists to establish. The
resulting error in the surrogate's training targets is about 0.1 % in the entrance and less
downstream.

Nothing else changes.

## How the result will be read — fixed now

**The stronger "what the input-based OOD detector misses" claim is supported only if all three
hold:**

1. at the reference percentile 99, the input-based OOD detector (distance OR GP variance) fires
   at **no** comparable station, for **either** gravity state;
2. PhysMAP flags at least one comparable station with gravity on (θ = 0.10);
3. PhysMAP flags **no** station with gravity off.

**If the detector fires at any comparable station at 99**, the stronger claim is not supported.
Those stations are reported with score, threshold and the reason; no change to the design is
made to quiet them; and Lewis stays framed as specificity and causal diagnosis.

**Lower percentiles are reported but do not decide.** At percentile p, roughly (100 − p) % of the
training points themselves exceed the threshold by construction, because each training point is
its own nearest neighbour. A test input identical to such a point fires for that reason alone.
The full sweep is reported, together with the fraction of training points that fire at each p,
so a reader can see the detector's built-in alarm rate next to its output.

## Stated expectation — for honesty, not as a criterion

The detector should be quiet at 99 at the comparable stations for both gravity states, and its
output should be identical between them because its inputs are. PhysMAP should be quiet with
gravity off and flag x/D ≥ 67.55 with gravity on. Writing this down now is what makes a
different outcome visible rather than explainable after the fact.

## Existing results

`design_A_8runs.json`, `design_A3_12runs.json` and `control_gravity_off.json` are preserved
unchanged. Design M writes new files only.

## Status

Development demonstration. 35A is a spent run; stations are not independent cases; no
precision, recall or F1.
