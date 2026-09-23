# Rebuilt mixed-convection CFD

A **development and demonstration** case, built from the geometry and boundary condition
Mohammed & Salman (2008) state in their paper. It is not a reproduction of the original
study, and nothing here is tuned toward any previously reported number.

## Running it

Requires Docker. No local OpenFOAM install — Homebrew could not build poppler or OpenFOAM
on this machine (outdated Command Line Tools), so the solver runs in a container.

```bash
python cfd/run.py --workdir /some/scratch --name myrun \
       --Re 800 --qw 50 --gravity on --nr 20 --ny 200 --iters 8000
```

| | |
|---|---|
| Solver | OpenFOAM **v2312**, `buoyantSimpleFoam`, `opencfd/openfoam-default:2312`, native arm64 |
| Geometry | Vertical pipe, D = 30 mm, heated length 900 mm, L/D = 30 |
| Mesh | Axisymmetric wedge, 5°, exactly 1/72 of the full circle (verified against the patch area the solver reports) |
| Fluid | Air, perfect gas, `mu` 1.831e-5, `Pr` 0.705, `Cp` 1004.4 |
| Wall | Uniform heat flux, `externalWallHeatFluxTemperature` in flux mode |
| Turbulence | Laminar |
| Gravity | `(0 -9.81 0)` for buoyancy-on, exactly `(0 0 0)` for its matched pair. **That is the only difference between a pair.** |

## Numerical checks

`run.py` records all of these per run into `result.json`:

- per-field final residuals and cumulative continuity error
- energy balance: wall heat in versus enthalpy rise, from the solver's own **outlet patch
  integral**
- Nusselt-extraction sensitivity: bulk temperature computed flux-weighted *and*
  area-weighted, with the gap reported rather than one silently chosen
- count of axial stations with non-positive net flux, i.e. flow reversal
- `checkMesh` output and wall-clock time

**Acceptance is judged on these.** The Eq 13 comparison is computed separately and is
never a gate.

## Results so far

`results/runs.json`. Grid convergence at Re = 800, q_w = 50 W/m², buoyancy on:

| Mesh | Cells | `Nu` | Change |
|---|---|---|---|
| 15 × 150 | 2,250 | 6.80648 | — |
| 20 × 200 | 4,000 | 6.79413 | 0.181% |
| 30 × 300 | 9,000 | 6.79140 | 0.040% |
| 40 × 400 | 16,000 | 6.79071 | **0.010%** |

Monotone and converged. **20 × 200 is the working mesh**: within 0.04% of the next
refinement and an order of magnitude cheaper.

Energy closure at that mesh: **0.073%**.

## Open numerical issues, stated rather than smoothed

1. **The steady solver does not meet residual control at high Richardson number.** At
   `Ri ≈ 1.3` the `Ux` residual limit-cycles between 2.8e-2 and 7e-2 over 20,000
   iterations while `Nu` moves only 0.03%. The solution is essentially stationary but the
   residual is not, which is the signature of a steady solver chasing an unsteady flow.
   Energy closure at that condition stays around 7%.
2. **Nusselt-extraction sensitivity is large — about 21%** between the flux-weighted and
   area-weighted bulk temperature, even with zero flow-reversal stations. This is a real
   property of the extraction, not a convergence artifact, and it is why both are
   reported.
3. **Finer meshes need more iterations.** At a fixed 8,000 iterations the energy closure
   degrades with refinement (0.07% → 4.3% → 12.0%) while `Nu` barely moves. The thermal
   field at the outlet develops more slowly than the near-inlet region that sets `Nu`.

## First matched ablation pair, and a materiality from it

`Re = 400`, `q_w = 50 W/m²`, `Ri = 1.310`, 20 × 200 mesh. The two runs differ **only** in
the gravity vector.

| | `Nu` | Energy closure |
|---|---|---|
| Buoyancy on (`Nu_M`) | 6.2903 | 8.29% |
| Gravity off (`Nu_F`) | 5.4979 | **0.011%** |

```
materiality = 1 − 5.49787/6.29032 = 0.126    provenance: matched_ablation
```

Put through the shipped estimator, not computed by hand, so it carries
`provenance = matched_ablation` — the allowed kind — and `evidence_state = measured`,
its first use on real CFD rather than a fixture. The causal flag **fires**: buoyancy is
outside its window (`Ri` 1.31 against `[0, 0.1]`) **and** `0.126 ≥ θ = 0.10`. Both halves,
as designed.

**What this number is worth.** The buoyancy-on run of the pair closes energy to only
8.29% and does not meet residual control, so the materiality inherits that. It is a real
measurement from a real matched ablation, and it is not yet a well-converged one.

**Not compared to anything.** No precision, recall or F1 — there is no evaluable truth
set. And the value was not steered: nothing in the setup was chosen by reference to a
previously reported materiality.

## Gravity-off costs 12× more per iteration

Measured, and worth knowing before planning a sweep. With `g = 0` the GAMG pressure solve
needs 20–26 sweeps against 4–6 with buoyancy. At 4,000 cells that is ~75 ms/iteration
against ~6.3 ms.

It also *converges* much faster physically — `Ux` residual reached 4e-3 by iteration 30,
where the buoyancy-on run was still at 1.8e-2 after 3,000. So the gravity-off pair wants
**fewer** iterations, not more: 2,000 gives 0.011% energy closure. An 8,000-iteration
gravity-off run is ten minutes of mostly wasted pressure sweeps.

## One error found in this work, recorded

The energy balance first read the bulk temperature from the **last cell centre**, giving a
systematic 3.7% imbalance that looked like a solver problem. Reading the solver's own
outlet **patch integral** instead brings it to 0.07%. Measured both ways on the same runs
before the change was made.
