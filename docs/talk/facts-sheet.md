# Facts sheet — generated, do not edit

Built by `python tools/talk_package.py build` from committed records. `python tools/talk_package.py check` fails if anything here drifts from those records or from the clean-clone CLI output. Every section names its source.

## 1. What is being counted

- **One experimental run.** Lewis (1992) Test 35A. Its 12 thermocouple stations are **positions within that one run, not independent cases**. 9 are comparable; Lewis disowns x/D 0.31 and 0.85 (axial wall conduction) and 159.33 (suspect).
- **Training data are CFD runs, not experiments.** Design M: 13 gravity-off runs, 532 rows — 40 positions in each of twelve runs, 52 in the matched run. The rows are positions within runs.
- **The matched ablation is two CFD cases**, gravity on and gravity off. No measurement enters materiality.
- **NACA:** the 45 entrance points are 9 positions on each of 5 curves of one figure.
- **Benchmark:** n_train and n_test are data rows, not independent cases.
- **No precision, recall or F1** is computed anywhere in this package.

Sources: `results/lewis35A_head_to_head/stress_test_lewis_reuse.json`, `data/stress_tests/lewis_reuse/cfd_profiles.json`, `data/naca/cross_validated_fig10.csv`.

## 2. The physical case — Lewis Test 35A

| quantity | value |
|---|---|
| tube diameter | 0.0119 m |
| heated length | 1.900 m (L/d 159.66) |
| unheated entry before heating | 2.5 d |
| wall heat flux | 12749.6 W/m² |
| inlet bulk temperature | 13.06 °C |
| flow rate | 0.7679 L/min |
| Re, Pr (inlet-bulk basis) | 1143.4, 8.46 |
| Gr_q (heat-flux based) | 374663 |
| Ri = Gr_q / Re², gravity on | 0.29 |
| exit bulk: calculated / measured | 30.00 / 29.32 °C |
| Lewis's own energy-balance error | -3.96 % |
| Nu reduction | linear bulk to the calculated exit; k at inlet bulk, 0.5922 W/m·K |

Source: `data/lewis1992/test_35A_reduction.json`; Ri from `results/lewis35A_head_to_head/stress_test_lewis_reuse.json`.

## 3. Input contract

| | |
|---|---|
| surrogate receives | Re, Pr, x_over_D |
| input-based OOD detector receives | Re, Pr, x_over_D |
| neither receives | gravity, Ri, Gr, wall heat flux, flow direction |
| training | 13 gravity-off CFD runs: Re 750, 950, 1350, 1550 × inlet 12, 13.25, 14.5 °C, plus the gravity-off half of the matched pair at 35A's operating point |
| deployment | Re 1143.4, Pr 8.46, x/D at 12 stations |
| every visible deployment input exactly matches a training input | yes |
| how the matched run is labelled | with the deployment values Re 1143.4, Pr 8.46; its own inlet values differ by -0.062 % and +0.141 %. Pre-declared in `results/lewis35A_head_to_head/PREDECLARE_design_M_matched.md` |
| PhysMAP's calibration window | 0 <= richardson_number <= 0 — the training never saw buoyancy |

Source: `results/lewis35A_head_to_head/stress_test_lewis_reuse.json` (input_contract), `data/stress_tests/lewis_reuse/cfd_profiles.json`.

## 4. Per station — design M, reference percentile 99

| x/D | comparable | control error (gravity off) | error vs measurement (gravity on) | Nu measured | Nu surrogate | OOD distance | OOD GP | OOD | materiality off | materiality on |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.31 | no | -0.03 % | +63.0 % | 33.72 | 54.96 | 0.000 | 0.0009 | quiet | 0.000 | 0.001 |
| 0.85 | no | -0.08 % | +11.7 % | 32.69 | 36.52 | 0.001 | 0.0016 | quiet | 0.000 | 0.003 |
| 2.45 | yes | -0.02 % | +9.9 % | 22.15 | 24.35 | 0.003 | 0.0025 | quiet | 0.000 | 0.006 |
| 5.65 | yes | -0.06 % | -6.4 % | 19.07 | 17.85 | 0.008 | 0.0036 | quiet | 0.000 | 0.012 |
| 9.92 | yes | -0.04 % | -2.6 % | 14.92 | 14.53 | 0.013 | 0.0044 | quiet | 0.000 | 0.020 |
| 16.32 | yes | -0.04 % | -12.8 % | 13.95 | 12.17 | 0.021 | 0.0053 | quiet | 0.000 | 0.032 |
| 33.39 | yes | -0.02 % | -11.0 % | 10.76 | 9.58 | 0.046 | 0.0067 | quiet | 0.000 | 0.061 |
| 50.47 | yes | -0.01 % | -10.0 % | 9.38 | 8.44 | 0.063 | 0.0076 | quiet | 0.000 | 0.087 |
| 67.55 | yes | -0.01 % | -17.0 % | 9.37 | 7.78 | 0.087 | 0.0082 | quiet | 0.000 | 0.111 |
| 101.69 | yes | -0.00 % | -16.8 % | 8.41 | 7.00 | 0.142 | 0.0091 | quiet | 0.000 | 0.154 |
| 135.84 | yes | +0.03 % | -18.0 % | 7.99 | 6.55 | 0.167 | 0.0098 | quiet | 0.000 | 0.195 |
| 159.33 | no | +0.20 % | -28.1 % | 8.82 | 6.34 | 0.195 | 0.0101 | quiet | 0.000 | 0.221 |

Source: `results/lewis35A_head_to_head/stress_test_lewis_reuse.json` (headline_design_M.stations). Same formats as the command's own table; `check` compares them line by line.

## 5. Summary values

- **Control accuracy:** within 0.06 % of the gravity-off CFD at every comparable station. Leave-one-run-out, worst station of any run: 0.45 % (`results/lewis35A_head_to_head/design_M_matched.json`).
- **Error against the measurement, downstream** (x/D 67.55, 101.69, 135.84): 17–18 %.
- **OOD thresholds at p99:** distance 0.408, GP variance 0.050. Fired at p99: 0 of 9 comparable stations, in both states.
- **OOD scores identical between the two gravity states:** yes. Largest difference over every station, score and percentile: 0.
- **Comparable stations where it fires, by operating percentile** (identical in both states): p50 6/9, p75 3/9, p90 0/9, p95 0/9, p99 0/9, p100 0/9.
- **In-sample alarm rate** — the share of its own training rows that fire: p50 50.0 %, p75 24.8 %, p90 9.2 %, p95 4.5 %, p99 1.1 %, p100 0.0 %. At p75, 97 % of training rows at x/D 50–100 fire, and 0 % at x/D 0–10 (`results/lewis35A_head_to_head/design_M_matched.json`, `results/lewis35A_head_to_head/design_M_low_pct_mechanism.json`).
- **Materiality, gravity on:** 0.006 to 0.195 at the comparable stations. **Gravity off:** 0 at every station, by construction — the gravity-off state has no buoyancy to remove.
- **θ is unlocked.** Illustrative value 0.10, the original study's. Comparable stations that would flag with gravity on: θ = 0.05 → 5; θ = 0.10 → 3; θ = 0.20 → 0. At least one for any θ ≤ 0.195. With gravity off, none at any θ. At the illustrative value: x/D 67.55, 101.69, 135.84.
- **Design A3 (secondary):** the operating point between training runs. OOD fires at 9 of 9 comparable stations with gravity off and 9 with gravity on; scores identical: yes; distance 0.60–0.68 against 0.473; control within 0.07 %.
- **Pre-declared criteria** (`results/lewis35A_head_to_head/PREDECLARE_design_M_matched.md`): ood quiet at every comparable station both states at 99: met; physmap flags a comparable station with gravity on: met (at the illustrative θ = 0.10; it holds for any θ ≤ 0.195); physmap flags nothing with gravity off: met.

Source: `results/lewis35A_head_to_head/stress_test_lewis_reuse.json` unless named.

## 6. How the surrogate's error splits

(1 + error) = (1 − materiality) × (1 + base-model gap) × (1 + fit error). The base-model gap is the gravity-on CFD against the measurement; the fit error is the surrogate against the gravity-off CFD. The identity is exact, not fitted.

| x/D | error vs measurement | missing buoyancy (−materiality) | base-model gap | fit error |
|---|---|---|---|---|
| 2.45 | +9.9 % | -0.6 % | +10.6 % | -0.02 % |
| 5.65 | -6.4 % | -1.2 % | -5.2 % | -0.06 % |
| 9.92 | -2.6 % | -2.0 % | -0.6 % | -0.04 % |
| 16.32 | -12.8 % | -3.2 % | -9.8 % | -0.04 % |
| 33.39 | -11.0 % | -6.1 % | -5.2 % | -0.02 % |
| 50.47 | -10.0 % | -8.7 % | -1.4 % | -0.01 % |
| 67.55 | -17.0 % | -11.1 % | -6.6 % | -0.01 % |
| 101.69 | -16.8 % | -15.4 % | -1.6 % | -0.00 % |
| 135.84 | -18.0 % | -19.5 % | +1.8 % | +0.03 % |

Downstream, the base-model gap is 1.6–6.6 % in size: there the measurement sides with the gravity-on CFD. The link between materiality and this error is partly built in — the surrogate and the materiality both rest on the gravity-off CFD — which is one reason no detection rate is computed from it.

Sources: `data/stress_tests/lewis_reuse/cfd_profiles.json` (ablation_full, ablation_removed), `results/lewis35A_head_to_head/stress_test_lewis_reuse.json`.

## 7. Energy closure — two definitions, one flow field

> mixing-cup temperature rise across the heated section against Q / (m_dot * cp), with cp and rho at the run's INLET bulk temperature. cp falls as water heats, so a correctly converged case sits slightly POSITIVE on this measure. For the matched pair this reads +0.15 % and +0.30 %; against Lewis's own calculated rise of 16.94 K the same fields read -0.05 % and +0.11 %. Two references, one flow field.

- Matched pair against the inlet-property balance: +0.15 % (gravity on), +0.30 % (gravity off).
- The same fields against Lewis's calculated rise of 16.94 K: -0.05 % and +0.11 %.
- Every training run: |closure| ≤ 0.35 % on the inlet-property balance. Reversed cells in the heated section, all runs together: 0.
- Lewis's own measured exit temperature differs from his calculated one by -3.96 %. That is a property of the experiment, not of the CFD.

Sources: `data/stress_tests/lewis_reuse/manifest.json`, `data/stress_tests/lewis_reuse/cfd_profiles.json`, `data/lewis1992/test_35A_reduction.json`.

## 8. Mesh and convergence

- **Grid pair** (gravity on, 20×300 and 30×400 cells, 25000 iterations): 8 of 12 stations change by less than 1 % — x/D 9.92 to 159.33, largest change there 0.94 %. The entrance stations x/D 0.31, 0.85, 2.45, 5.65 are grid-sensitive. Energy closure recorded with that pair: -0.05 % (the record does not name its reference; it equals the gravity-on figure against Lewis's rise).
- **No separate grid study** was run for gravity off or for the training runs. They use the finer mesh of the pair.
- **Iterations:** the matched pair ran 3000 each. The manifest records: "the gravity-on half at 3000 reproduces a 25000-iteration run to within 0.063 % at every station". That comparison was made when the inputs were banked, and the profile it used is not in the committed data, so this one figure is a recorded statement, not recomputable here.
- **Two extraction paths.** The grid pair reads Nu at the nearest cell centre (`cfd/compare_lewis_vp.py`); the stress test interpolates linearly between cell centres (`cfd/lewis_head_to_head.py`, `lewis_nu`). The two committed gravity-on profiles — the grid pair's fine mesh and the matched pair — differ by at most 0.45 % in the grid-converged band and 0.07 % at the downstream stations, but at the entrance by x/D 0.31: 8.8 %; x/D 0.85: 7.8 %; x/D 2.45: 2.3 %; x/D 5.65: 0.9 %. Near the start of heating Nu changes fast along the tube, so where you read it matters. The entrance stations are sensitive to both mesh and extraction; downstream, each effect stays under 1 %.
- **Training runs:** 2000 or 4000 iterations; the low-Re runs were continued because their enthalpy residual was still falling, decided before any head-to-head output existed.
- **Grid convergence is numerical stability, not validation.** Whether a steady laminar model represents the experiment is a separate question. On the grid pair's fine mesh, in the grid-converged band, the gravity-on CFD differs from Lewis's measurement by at most 9.6 %, and from Lewis's own steady laminar prediction by 4.3–6.0 % where that prediction was traced. That is development evidence: 35A was inspected while the model was built.

| run | Re | Pr | inlet °C | iterations | energy closure | h residual | reversed cells |
|---|---|---|---|---|---|---|---|
| doe_Re1350_T12p0 | 1350.0 | 8.755 | 12 | 2000 | -0.08 % | 7.1e-06 | 0 |
| doe_Re1350_T13p25 | 1350.0 | 8.423 | 13.25 | 2000 | -0.13 % | 7.8e-06 | 0 |
| doe_Re1350_T14p5 | 1350.0 | 8.109 | 14.5 | 2000 | -0.19 % | 8.5e-06 | 0 |
| doe_Re1550_T12p0 | 1550.0 | 8.755 | 12 | 2000 | +0.11 % | 5.6e-06 | 0 |
| doe_Re1550_T13p25 | 1550.0 | 8.423 | 13.25 | 2000 | +0.10 % | 6.1e-06 | 0 |
| doe_Re1550_T14p5 | 1550.0 | 8.109 | 14.5 | 2000 | +0.07 % | 6.6e-06 | 0 |
| doe_Re750_T12p0 | 750.0 | 8.755 | 12 | 4000 | +0.35 % | 9.7e-09 | 0 |
| doe_Re750_T13p25 | 750.0 | 8.423 | 13.25 | 4000 | +0.33 % | 1.0e-08 | 0 |
| doe_Re750_T14p5 | 750.0 | 8.109 | 14.5 | 4000 | +0.31 % | 1.1e-08 | 0 |
| doe_Re950_T12p0 | 950.0 | 8.755 | 12 | 4000 | +0.33 % | 3.2e-09 | 0 |
| doe_Re950_T13p25 | 950.0 | 8.423 | 13.25 | 4000 | +0.31 % | 3.9e-09 | 0 |
| doe_Re950_T14p5 | 950.0 | 8.109 | 14.5 | 4000 | +0.30 % | 4.5e-09 | 0 |
| pair_gOFF | 1142.7 | 8.472 | 13.06 | 3000 | +0.30 % | 6.9e-08 | 0 |

| x/D | Nu 20×300 | Nu 30×400 | change | under 1 %? |
|---|---|---|---|---|
| 0.31 | 54.45 | 60.36 | +10.85 % | no |
| 0.85 | 38.22 | 34.01 | -11.03 % | no |
| 2.45 | 25.15 | 23.95 | -4.79 % | no |
| 5.65 | 18.39 | 17.91 | -2.58 % | no |
| 9.92 | 15.04 | 14.90 | -0.89 % | yes |
| 16.32 | 12.72 | 12.61 | -0.86 % | yes |
| 33.39 | 10.30 | 10.20 | -0.94 % | yes |
| 50.47 | 9.33 | 9.25 | -0.87 % | yes |
| 67.55 | 8.82 | 8.75 | -0.88 % | yes |
| 101.69 | 8.34 | 8.28 | -0.73 % | yes |
| 135.84 | 8.20 | 8.14 | -0.76 % | yes |
| 159.33 | 8.19 | 8.12 | -0.76 % | yes |

Sources: `results/lewis35A_vp/grid_pair.json`, `data/stress_tests/lewis_reuse/cfd_profiles.json`, `data/stress_tests/lewis_reuse/manifest.json`.

## 9. Seven-vehicle benchmark — closure validity and observability

Not evidence for causal materiality. Outcomes are observability classes, not rates.

| vehicle | domain | failure variable | observability | outcome | redistribution | data quality | train rows | test rows |
|---|---|---|---|---|---|---|---|---|
| naca_tn1451 | thermal-fluids | x_over_D | unobservable | PHYSMAP_WINS | clear | benchmark_grade | 29 | 47 |
| casper_hypersonic_transition | aerospace | freestream_noise_pct | unobservable | PHYSMAP_WINS | against_publisher_terms | benchmark_grade | 159 | 8 |
| jin_sco2_buoyancy | thermal-fluids | Bu | unobservable | PHYSMAP_WINS | against_publisher_terms | benchmark_grade | 17 | 27 |
| velazquez_sco2 | thermal-fluids | ratio_mu_w_b | partial | PARTIAL | clear | benchmark_grade | 393 | 67 |
| dirker_water | thermal-fluids | Ri | partial | PARTIAL | against_publisher_terms | benchmark_grade | 31 | 60 |
| marineau_hypersonic_transition | aerospace | st_xsw_ratio | observable | BASELINE_VISIBLE | no_licence_facts_basis | benchmark_grade | 9 | 6 |
| forrest | thermal-fluids | Re | observable | DO_NO_HARM | against_publisher_terms | triage_only | 1 | 4 |

**What the closure check adds, at percentile 99** — per vehicle, counts of rows, never pooled:

| vehicle | failure variable | wrong predictions caught only by PhysMAP | right predictions flagged anyway |
|---|---|---|---|
| naca_tn1451 | unobservable | 20 of 20 | 24 |
| casper_hypersonic_transition | unobservable | 4 of 8 | 0 |
| jin_sco2_buoyancy | unobservable | 15 of 26 | 0 |
| velazquez_sco2 | partial | 18 of 67 | 0 |
| dirker_water | partial | 2 of 11 | 16 |
| marineau_hypersonic_transition | observable | 0 of 6 | 0 |
| forrest | observable | not tested: no detector fit | — |

Observability guards all passed: yes. Forrest: triage-only values; one training row, no detector fit; DO_NO_HARM short-circuited, not earned.

Sources: `data/benchmarks/v0_4/matrix_full_seven.json`, `src/physmap/benchmarks/registry.py`.

## 10. NACA x/D entrance-region example

- Training: 40 fully developed points (x/D ≥ 10). Deployment: 45 entrance points. Pr 0.71 (air).
- Closure validity fired on 45 of 45; novelty density on 0; GP variance on 0.
- The benchmark's NACA cell uses its own split — 29 training rows, 47 test rows — with the same pattern.

Source: `examples/naca_entrance_region.py` on `data/naca/cross_validated_fig10.csv`.

