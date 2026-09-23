# Lewis 35A — a controlled model-reuse stress test

```bash
physmap stress-test lewis-reuse
```

One command, from a clone, in about two minutes. It recomputes everything below from the
checkout, asserts the two properties the test rests on, and checks itself against a committed
bank — the same contract as `physmap benchmark run`, kept apart from that command because this is
a causal-materiality result and that one is a closure-observability benchmark.

## What it is

> The surrogate was trained for forced convection, where gravity did not vary and was not an
> input. It was then reused in vertical heated flow, where buoyancy became material. A
> mixed-convection surrogate designed for this regime should include Richardson number, Grashof
> number, or equivalent physical information.

## The claim

> **PhysMAP detects when model reuse activates a physically relevant mechanism outside the
> surrogate's observable input space. An input-only OOD detector cannot identify a change absent
> from its input contract.**

## What it is not

- **Not a claim that OOD detectors fail in general.** The input-based OOD detector here does
  exactly its job: it reports whether the inputs are familiar. The change that matters is not in
  its inputs.
- **Not a suggestion to leave gravity out.** A mixed-convection surrogate built correctly should
  expose the relevant physics — Richardson number, Grashof number, or equivalent. This test
  reuses a forced-convection surrogate *on purpose*, to show what happens when that has not been
  done.
- **Not a claim about NVIDIA PhysicsNeMo.** Its out-of-distribution check and its physics checks
  are distinct; neither was run, and no faithful equivalent was built or tested.

## Status

**Development demonstration.** One run, Lewis Test 35A, already inspected during development.
Its twelve stations are twelve measurements of one operating condition, not twelve cases. No
precision, recall or F1 is computed, and none may be computed from this.

**θ is unlocked.** Materiality is reported as continuous values. θ = 0.10 — the original study's
value, recorded before any Lewis work — appears only as an illustration, never as a verdict.

## Headline — design M

### Input contract

| | |
|---|---|
| Surrogate receives | `Re`, `Pr`, `x_over_D` |
| Input-based OOD detector receives | `Re`, `Pr`, `x_over_D` — every input the surrogate receives, nothing withheld |
| Neither receives | gravity, `Ri`, `Gr`, wall heat flux, flow direction |
| Deployment inputs | Re 1143.4, Pr 8.46 (Lewis Appendix D-2, inlet-bulk basis), `x_over_D` at Lewis's 12 stations |
| **Every visible deployment input exactly matches a training input** | **yes — asserted by the command** |

The surrogate is a forced-convection model fitted to thirteen gravity-off CFD runs, one of them
at 35A's own operating point. So there is no input gap for the detector to notice: the
deployment looks exactly like training. What changed is gravity, and gravity is not an input.

### Result

Scored twice with the **same visible inputs**: against gravity-off CFD at 35A — the accurate
control — and against Lewis's measurement, where buoyancy is active.

| x/D | control error (gravity off) | experimental error (gravity on) | OOD distance | OOD GP variance | OOD at 99 | materiality, gravity off | materiality, gravity on |
|---|---|---|---|---|---|---|---|
| 2.45 | −0.02 % | +9.9 % | 0.003 | 0.0025 | quiet | 0 | 0.006 |
| 5.65 | −0.06 % | −6.4 % | 0.008 | 0.0036 | quiet | 0 | 0.012 |
| 9.92 | −0.04 % | −2.6 % | 0.013 | 0.0044 | quiet | 0 | 0.020 |
| 16.32 | −0.04 % | −12.8 % | 0.021 | 0.0053 | quiet | 0 | 0.032 |
| 33.39 | −0.02 % | −11.0 % | 0.046 | 0.0067 | quiet | 0 | 0.061 |
| 50.47 | −0.01 % | −10.0 % | 0.063 | 0.0076 | quiet | 0 | 0.087 |
| 67.55 | −0.01 % | **−17.0 %** | 0.087 | 0.0082 | quiet | 0 | **0.111** |
| 101.69 | −0.00 % | **−16.8 %** | 0.142 | 0.0091 | quiet | 0 | **0.154** |
| 135.84 | +0.03 % | **−18.0 %** | 0.167 | 0.0098 | quiet | 0 | **0.195** |

Comparable stations only; Lewis disowns x/D 0.31 and 0.85 (axial wall conduction) and 159.33
("suspect"), and the detector is quiet there too. OOD thresholds at the benchmark's reference
percentile 99: distance 0.408, GP variance 0.050.

**The OOD scores are identical with gravity off and gravity on** — every score, every
percentile, asserted by the command. The two cases are indistinguishable to it, because they
differ only in something outside its input contract.

**PhysMAP's materiality is zero with gravity off and rises to 0.195 with gravity on**, growing
down the tube as buoyancy distorts the flow. The surrogate is right to within 0.06 % on the
control and off by 17–18 % at the downstream stations with buoyancy active.

**Neither of those two sentences depends on a threshold.** That is the headline.

### What does depend on a threshold

| Result | Threshold | Holds for |
|---|---|---|
| OOD scores identical between gravity states | none | exact equality |
| every visible deployment input is a training input | none | exact set membership |
| materiality 0 with gravity off; continuous with gravity on | none | reported as values |
| control and experimental errors | none | reported as values, no right/wrong label |
| OOD fired or quiet at a station | operating percentile — the benchmark's shipped reference 99 | full sweep reported below |
| PhysMAP flags nothing with gravity off | none | **every θ** — materiality is 0 and Ri = 0 sits inside the surrogate's window |
| PhysMAP flags at least one comparable station with gravity on | **θ, unlocked** | any θ ≤ 0.195 |
| which stations PhysMAP flags | **θ, unlocked** | each station flags for θ up to its own materiality |

**At the illustrative θ = 0.10** — not a verdict — PhysMAP would flag x/D 67.55, 101.69 and
135.84 with gravity on, and nothing with gravity off. At θ = 0.05 it would add 33.39 and 50.47;
at θ = 0.20, none of the comparable stations. θ will be set by the protocol, not by this outcome.

### Pre-declared, and met

Design M was pre-declared, with its success criteria, in
`results/lewis35A_head_to_head/PREDECLARE_design_M_matched.md`, committed in `b3da673` before any
of its output existed.

| Pre-declared criterion | Result |
|---|---|
| 1. Detector quiet at every comparable station, both gravity states, at 99 | met |
| 2. PhysMAP flags a comparable station with gravity on (θ = 0.10) | met — and would be for any θ ≤ 0.195 |
| 3. PhysMAP flags nothing with gravity off | met — for every θ |

Criterion 2 used the illustrative θ. It is recorded that way, with the range over which it holds,
rather than read as a fixed verdict.

### The lower operating percentiles

The detector is quiet at 90, 95, 99 and 100. At 75 it fires on 3 of the 9 comparable stations
(x/D ≥ 67.55), and at 50 on 6 — the downstream stations — **identically with gravity off**, where
those stations are accurate to 0.03 %.

That is the detector's own alarm pattern, measured from training inputs alone
(`design_M_low_pct_mechanism.json`). Each training point is its own nearest neighbour, the
training stations are log-spaced, and the detector measures raw `x_over_D`, so downstream is the
sparsest part of the grid. At 75 it already fires on 97–100 % of its **own training rows** beyond
x/D 50, and on none below x/D 10. Buoyancy also builds with distance, so the two line up — by
geometry, not by detection. The pre-declaration said in advance that low percentiles do not
decide.

## Secondary — designs A and A3: specificity

The same test with 35A's operating point **between** training runs instead of on one: eight runs
(design A), then twelve with a third inlet temperature (design A3, the pre-committed
sensitivity). Everything else identical.

> **The OOD detector detected unfamiliar inputs but could not identify whether buoyancy caused an
> error. PhysMAP distinguished the accurate control from the materially affected prediction and
> named the mechanism.**

The detector warns at all 9 comparable stations in both gravity states, at every operating
percentile — on the control where the surrogate is right to within 0.07 %, and on the experiment
where it is off by 17–18 %. Its scores are identical between the two. PhysMAP's materiality is exactly the
headline's: it follows the physics, not the training design.

Why it warns, measured from training inputs alone: 35A is off the training grid in both Re and
Pr, and either gap alone trips it.

| design A, distance score | value | fires? (threshold 0.452) |
|---|---|---|
| as deployed | 1.08–1.13 | yes |
| Pr gap closed only | 0.58–0.67 | yes |
| Re gap closed only | 0.91–1.00 | yes |
| both closed | 0.007–0.33 | no |

The third inlet level (A3) closed the Pr gap and the score fell to 0.60–0.70 — still above 0.47,
as the decomposition predicted.

## Across all three designs

| | 35A's visible operating point | input-based OOD detector | PhysMAP |
|---|---|---|---|
| **M** (headline) | on a training operating point | quiet — accurate and inaccurate alike | materiality 0 → up to 0.195 when buoyancy is active |
| **A, A3** | between training operating points | warns — accurate and inaccurate alike | the same |

The detector's answer followed where the visible inputs sat and **never changed when gravity was
switched**, in any design. PhysMAP's answer did not depend on the training design and **always
changed when gravity was switched**.

## How the surrogate's error splits

The surrogate reproduces gravity-off CFD at 35A to within 0.25 %, so its error against the
experiment splits cleanly into **missing buoyancy** (PhysMAP's materiality) times **the base
model's own gap** to the experiment (gravity-on CFD against the measurement). The split closes to
within 0.2 % at every station.

| x/D | surrogate error | from missing buoyancy | from base model gap | bulk-error unc. | materiality | above illustrative θ = 0.10? |
|---|---|---|---|---|---|---|
| 2.45 | +9.9 % | −0.6 % | +10.6 % | 0.1 % | 0.006 | no |
| 5.65 | −6.4 % | −1.2 % | −5.2 % | 0.1 % | 0.012 | no |
| 9.92 | −2.6 % | −2.0 % | −0.6 % | 0.2 % | 0.020 | no |
| 16.32 | −12.8 % | −3.2 % | −9.8 % | 0.4 % | 0.032 | no |
| 33.39 | −11.0 % | −6.1 % | −5.2 % | 0.8 % | 0.061 | no |
| 50.47 | −10.0 % | −8.7 % | −1.4 % | 1.1 % | 0.087 | no |
| 67.55 | −17.0 % | −11.1 % | −6.6 % | 1.5 % | 0.111 | yes |
| 101.69 | −16.8 % | −15.4 % | −1.6 % | 2.3 % | 0.154 | yes |
| 135.84 | −18.0 % | −19.5 % | +1.8 % | 3.1 % | 0.195 | yes |

The uncertainty column is only the bulk-temperature component; a combined per-point uncertainty is
not reported by the source and is a protocol decision.

- **Where materiality is largest, buoyancy causes most of the error.** At the three stations
  above the illustrative θ the error is six to eleven times the bulk-error uncertainty (11.2×,
  7.3×, 5.9×); at x/D 101.69 and 135.84 buoyancy is essentially all of it.
- **x/D 33.39 and 50.47** carry real buoyancy (−6.1 %, −8.7 %) with materiality below the
  illustrative θ. Whether they should flag is the open θ decision.
- **x/D 2.45 and 16.32** are wrong mostly because of the base model, not buoyancy. PhysMAP checks
  one mechanism and does not claim to see others; the surrogate inherits this gap from the CFD it
  was trained on.

## Provenance

- **The input-based OOD detector** is the seven-vehicle benchmark's own:
  `physmap.benchmarks.benchmark_v0_4._DETECTORS`, imported unchanged — Mahalanobis k = 3
  distance-to-training OR a Matérn-5/2 GP's posterior std / |mean| (floored at 0.05), each firing
  above the given percentile of its training rows' own scores. Operating percentiles 50–100, the
  benchmark's reference 99. Both marked "locked v0.2, do not change" in the source, and not
  changed. The guardrail's closure layer is inactive (regime `UNLISTED`): the shipped corpus has
  no laminar vertical-tube closure, and a turbulent one would fire on Re < 3000 for a reason
  unrelated to buoyancy.
- **The surrogate** is a GP on (log10 Re, Pr, log10 x/D) → log Nu, fitted to variable-property
  gravity-off CFD with Lewis's Appendix B water properties and his own Nu definition. Leave-one-run-out
  worst 0.45 %; 0.30 % with the matched run itself held out.
- **The matched ablation** is `pair_gON` against `pair_gOFF`, provenance `matched_ablation`. The two
  cases differ only in `constant/g` — checked by a recursive diff when the inputs were banked. 3000
  iterations each; the gravity-on half reproduces a 25 000-iteration run to within 0.063 %. Energy
  closes to +0.15 % and +0.30 % against the inlet-property energy balance, which reads slightly
  positive for a correct case because water's cp falls as it heats; against Lewis's own calculated
  rise of 16.94 K the same fields read −0.05 % and +0.11 %.
- **Every training run** closes energy within 0.5 % with no reversed cells, asserted when the
  inputs were banked. The four low-Re runs were continued from 2000 to 4000 iterations because their
  enthalpy residual was still falling; that was decided on the residual history, before any
  head-to-head output existed.
- **Reproduction.** The command recomputes from CFD-derived inputs banked at full precision in
  `data/stress_tests/lewis_reuse/`, and reproduces `cfd/lewis_head_to_head.py`'s pre-declared
  design M to the bit — asserted in `tests/test_stress_test_lewis_reuse.py`. Regenerating the CFD
  itself needs Docker; the manifest records how.

## NACA and Lewis do not contradict each other

In NACA the input-based OOD detector was silent on all 45 entrance points. In Lewis designs A and
A3 it warned on every station; in design M it was silent again. What decides it is **where the
visible deployment inputs sit relative to training** — not whether the unmodelled mechanism is
active. NACA's entrance points and design M's deployment both share their visible operating point
with training; designs A and A3 do not. In every case the detector's answer is independent of the
mechanism that breaks the surrogate.

## What may and may not be said

- **Say:** "The surrogate was trained for forced convection, where gravity did not vary and was not
  an input, and reused in vertical heated flow where buoyancy became material. Every visible input
  matched training. The input-only OOD detector gave the same scores with buoyancy on and off.
  PhysMAP's materiality went from zero to about 0.2, at the stations where the surrogate was off by
  17–18 %."
- **Say:** "A mixed-convection surrogate built for this regime should include Richardson number,
  Grashof number, or equivalent. This is what reuse without it looks like."
- **Say, for designs A and A3:** "When the visible operating point fell between training runs, the
  OOD detector warned in both the accurate and the inaccurate case. PhysMAP changed with the
  physical mechanism."
- **Do not say** OOD detectors fail in general, that engineers should omit gravity, or anything
  about NVIDIA PhysicsNeMo.
- **Do not present a flag as a verdict.** θ is unlocked; show materiality, and θ = 0.10 only as an
  illustration.
- **Do not cite the low operating percentiles** as the detector "catching" the downstream stations.
  It fires there on its own training data, and identically with gravity off.
- **Do not say** PhysMAP catches every surrogate error. It does not see the base-model errors at
  x/D 2.45 and 16.32, by design.
- **Always say** it is one development run, and its stations are not independent cases.

## Pre-commitments

- `results/lewis35A_head_to_head/PRECOMMIT.md` — designs A and A3, written before any real-design
  output existed, disclosing the one-run smoke test that preceded it. Followed: design A reported
  first and unreplaced; the single permitted sensitivity (A3) run and reported alongside.
- `results/lewis35A_head_to_head/PREDECLARE_design_M_matched.md` — design M, committed in `b3da673`
  before any of its output existed. All three criteria met; criterion 2's θ-dependence recorded.
- Both designs' result files are byte-unchanged since their commits.

## Files

- `physmap stress-test lewis-reuse` — the one-command path (`src/physmap/stress_tests/lewis_reuse.py`)
- `data/stress_tests/lewis_reuse/` — the banked CFD-derived inputs and their manifest
- `results/lewis35A_head_to_head/stress_test_lewis_reuse.json` — the committed bank the command checks itself against
- `results/lewis35A_head_to_head/design_M_matched.json`, `design_A_8runs.json`, `design_A3_12runs.json`, `control_gravity_off.json` — the original runs
- `cfd/lewis_head_to_head.py`, `cfd/bank_lewis_reuse_inputs.py` — the CFD-side scripts
