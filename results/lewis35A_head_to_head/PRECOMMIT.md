# Head-to-head pre-commitment

Written 2026-09-23T19:40Z, after 2 of 8 training runs finished. Committed with the results
so its timing is checkable against the run logs.

**Disclosure, corrected before commit.** One detector output for 35A already existed when
this was written. An API smoke test ran the detectors with a SINGLE training run (Re 750,
12.0 degC) to check the calls worked, and displayed one station (x/D 16.32): both detectors
fired (distance 347 against a threshold of 0.48; GP 0.59 against 0.05). A one-run training
set has zero spread in Re and Pr, so any other Re or Pr must look far away; that output says
nothing about this design and informed no choice below. The same smoke test computed, but did
not display, surrogate predictions from a one-run fit. No prediction error was computed.

## The design is fixed as it stands

- Surrogate inputs and OOD detector features: `Re`, `Pr`, `x_over_D`, via the guardrail's own map.
- Detectors: `physmap.benchmarks.benchmark_v0_4._DETECTORS`, imported unchanged; the
  benchmark's operating percentiles; 99 as reference.
- Training: 8 gravity-off runs, Re {750, 950, 1350, 1550} x inlet {12.0, 14.5} degC, q_w
  fixed at 35A's value, 40 log-spaced stations each.

## If the OOD detector fires on 35A

That result is reported as found, first, and is not replaced.

One sensitivity check is allowed, decided now: if the detector's firing is driven by the gap
between the two training Prandtl levels -- a coverage property of the training set, checkable
from the detector's scores and the training inputs alone, without reference to buoyancy,
materiality or error -- a THIRD inlet level at the midpoint, 13.25 degC, is added at the same
four Re values (12 runs, a standard 3-level design) and the head-to-head is rerun. BOTH
designs are reported side by side. Nothing else about the design may change in response to
any result.

## If the OOD detector is quiet on 35A

Reported as found. No sensitivity run is added to make it fire.

## How the two questions are answered

1. Does the OOD detector stay quiet where PhysMAP flags a material mechanism?
   Read at every COMPARABLE station (Lewis's own exclusions: x/D 0.31, 0.85, 159.33) where
   materiality >= theta, at theta 0.10 and 0.20. theta is not locked; both are illustrations.
2. Does the extra flag correspond to an actual prediction error?
   Report |prediction error| at the flagged stations against (a) the experiment's bulk-error
   Nu uncertainty and (b) a 10 % reference. Report the UNFLAGGED stations' errors too, so any
   error neither detector catches is visible, and name its likely cause rather than hide it.

No precision, recall or F1. 35A is a spent development run; stations are not cases.
