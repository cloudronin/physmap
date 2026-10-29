# PhysMAP closure benchmark on a public high-lift wing: experiment spec v0.1

**Status:** draft for review, 2026-10-29. Not started.
**Owner:** Vishnu Vettrivel. **Executes in:** the PhysMAP repo (`cloudronin/physmap`); the uofa side is already built (surrogate pack v0.2, branch `claude/surrogate-governance-u1-u4`).
**Audience:** NAFEMS World Congress 2027 paper (due 2027-01-31) and the praxis.

## 1. The one sentence

A surrogate trained on CFD inherits the CFD's closure, so it can match its training data to four nines and miss the wind tunnel by half, with every input inside the training envelope. PhysMAP should flag those points from the closure's validated range and a matched ablation, before any wind-tunnel data is seen, while an input-based OOD detector stays silent.

## 2. Why now

Luminary Cloud published the failure on a NASA CRM wing-body: a GeoTransolver surrogate trained on about 2,300 CFD runs scored R² above 0.9994 against CFD for lift, drag and moment, and R² 0.36 to 0.76 against wind-tunnel pressure-sensitive-paint data, before a wind-tunnel correction head lifted it to 0.94 to 0.97. They name the cause as turbulence closure, transition modelling and mesh artifacts, worst at suction peaks, shocks and separation onset. That is the W-SURR-05 and W-SURR-06 story, told by a vendor, on public geometry. The uofa fixtures for NACA and Lewis 35A are pipe flows; this adds a 3D aerospace case a NAFEMS audience already knows.

## 3. Claims

| Id | Claim | Measured by |
|---|---|---|
| C1 | At operating points inside the surrogate's input envelope, PhysMAP's closure screen (W-SURR-05: closure outside its validated range) separates the points where surrogate-vs-tunnel error is large from the points where it is small | Flag at each point before tunnel data is used; then error against tunnel Cp and CL. Report the split as a 2x2 table and an AUC |
| C2 | A mechanism omitted from the training CFD (laminar-turbulent transition, when the training runs are fully turbulent) is active at the tunnel Reynolds number and material, and PhysMAP's matched ablation (W-SURR-06) says so | Transition model on versus off at the same point, same mesh; materiality as a continuous value per point; theta 0.10 illustrative, never locked |
| C3 | Both flags land in a signed UofA package as external, undispositioned annotations, through the pack built on the branch above | `uofa shacl`, `uofa rules --format json`, `uofa verify` on the export |

**Null controls (must fail, or the result is void):**

- N1: The input-based OOD detector from PhysMAP's own benchmark (`benchmark_v0_4._DETECTORS`, unchanged) fires on none of the flagged points, or fires identically on flagged and unflagged points at every operating percentile. If N1 fires selectively on the high-error points, the closure screen is not adding anything and C1 is void.
- N2: The matched ablation with the mechanism switched off (transition off versus off, two runs differing only by a seed or a solver tolerance) reports materiality at the numerical-noise floor. If it does not, materiality is measuring the solver and C2 is void.

**Not claimed:** that RANS or any closure is wrong in general; that transition is the only omitted mechanism (wind-tunnel wall and support interference is another, and is named in §6); anything about Luminary's model, which is not run here; a performance metric from one wing.

## 4. Gate G0: what is true before anything is built (2 h, pairing)

Four things this spec could not verify at writing time. Each is an investigation item for the execution session, with the source to read.

| # | Open question | Why it matters | Read |
|---|---|---|---|
| G0.1 | Which configuration and conditions did Luminary actually use? Their post names "NASA CRM-HL Wing-Body (No Tail) … HLPW-5 validation study" and training at Mach 0.70 and 0.85. A high-lift configuration at transonic Mach does not fit; HLPW-5's CRM-HL tests are at Mach 0.2. One of the two statements is wrong, or the post mixes SHIFT-Wing (cruise CRM) with CRM-HL | Decides whether Luminary's R² values are a control (same configuration, comparable) or context (different configuration, cited only) | The GeoTransolver paper, arXiv 2512.20399, full text; Luminary's post; HLPW-5 test-case document |
| G0.2 | Is CRM-HL tunnel surface pressure public in digital form? HLPW-4 served QinetiQ 5m forces, moments, tufts and rake data; a note on that page says "the Cps themselves are not corrected for wind tunnel effects", which implies Cp exists. HLPW-5 uses ONERA F1 data and holds some of it back. The NASA pages moved; `aiaa-hlpw.org` is the current host | Without per-tap Cp, C1 degrades to CL-only, which cannot localise a suction-peak failure | `aiaa-hlpw.org` data pages for HLPW-4 and HLPW-5; AIAA 2020-2770 and 2020-2771 (QinetiQ test papers) |
| G0.3 | What is the validated range of a fully turbulent SST training closure on a high-lift element, in a variable PhysMAP can read? The closure index (`closures/data/closure_index.json`) already holds `menter-sst-1994`, `spalart-allmaras-1992` and `langtry-menter-transition-2009` as metadata-only entries (coordinates Reynolds number and wall y+; no bounds, the case-2b path). Bounds live in the curated corpus: a `validated_range` entry in `corpus/data/corpus_seed.jsonl` and an evidence claim in `corpus/data/evidence_claims_seed.jsonl` naming the source. Neither file has a separation or transition bound for these closures today | The bound variable for W-SURR-05 must be named with a literature source and curated through the corpus path, not chosen to fit | Rumsey's HLPW-4 and HLPW-5 summary papers (transition sensitivity findings); Langtry and Menter 2009 for the transition window in momentum-thickness Reynolds number and turbulence intensity |
| G0.4 | What does one 3D CRM-HL RANS run cost on the compute you can reach? HLPW committee meshes are tens of millions of cells | Sets whether Phase 2 is fundable or the result stays 2D | HLPW-4 grid files and participant reports of core-hours per point |

**Gate rule:** G0.2 answered "no public Cp" is a kill for the CRM-HL arm (K1 below). G0.1 answered "different configuration" demotes Luminary's numbers from control to context and the spec still runs. G0.3 unanswered after 2 h stops the spec until it is answered: a bound variable without a source is the keyword-not-claim substitution.

## 5. Design

Two tiers. Tier 1 is cheap and settles the method. Tier 2 is the paper figure and depends on compute.

### Tier 1: 2D multi-element airfoil pilot (10 to 14 h pairing, plus solver wall time)

| Element | Choice | Note |
|---|---|---|
| Geometry | A public 2D high-lift section with public tunnel Cp. First candidate: McDonnell Douglas 30P30N (NASA LaRC LTPT, Mach 0.2, Re 9M, Cp taps on all three elements). Confirm a digital Cp table exists in Phase 0 | Same physics as CRM-HL (slat, main, flap; transition and separation onset), at 2D RANS cost |
| Training CFD | Fully turbulent SST k-omega, one mesh, AoA sweep 0° to beyond CL_max in 1° steps, plus a second geometric parameter (flap gap or deflection, 5 levels). About 100 to 150 runs | The closure the surrogate inherits is SST fully turbulent. Record solver, version, mesh y+, residuals per run |
| Surrogate | The same Gaussian process PhysMAP used for Lewis 35A, inputs (AoA, flap parameter), outputs CL and Cp at the tap stations | Deliberately simple. The claim is about the closure, not the architecture |
| Closure screen (C1) | Bound variable from G0.3. Working hypothesis, to be confirmed or replaced: (a) separation state, AoA relative to the CFD's own CL_max, with the validated range "attached or incipiently separated"; (b) element chord Reynolds number against the fully turbulent assumption's lower end, with the transition window from Langtry and Menter as the source | PhysMAP reads the bound variable from the operating point, checks it against the closure entry, and flags before any tunnel data is read |
| Matched ablation (C2) | Transition model (Langtry-Menter gamma-Re_theta) on versus off at every operating point, same mesh, same everything else. Materiality per point = max over elements of RMS(ΔCp)/RMS(Cp), and ΔCL/CL | Mirrors the Lewis gravity-on versus gravity-off pair exactly |
| Tunnel comparison | Per-tap Cp RMSE and R², and CL, at the matching tunnel points | Tunnel data enters only here, after the flags are frozen |
| Null control N1 | PhysMAP's benchmark OOD detector at operating percentiles 50 to 100, fitted on the training inputs, run on the test points | Reported as a table like Lewis: fired count by percentile, flagged versus unflagged |
| Null control N2 | Transition off versus off, differing only in a solver seed or tolerance | Noise floor for materiality |

**Done gate T1:** C1 split table and AUC reported; N1 and N2 both failed as required; materiality values reported continuously with theta 0.10 shown as a line, not a verdict; one signed UofA package per operating-point set through the existing fixture path.

### Tier 2: CRM-HL wing-body, 3D (20 to 30 h pairing, plus compute; only if T1 passes and G0.4 is fundable)

Same design on the CRM-HL geometry at the tunnel's Mach and Reynolds number (QinetiQ 5m: Mach 0.2, Re 5.49M on mean aerodynamic chord, 10% semispan model). Training sweep over AoA only (the HLPW alpha polar), 15 to 25 runs on one committee mesh. Matched ablation at three to five points spanning attached, near-CL_max and post-stall. Tunnel comparison at the tap rows the data provides. If G0.1 confirms the same configuration, report Luminary's before-and-after R² beside PhysMAP's flagged and unflagged error bands.

**Done gate T2:** as T1, plus the comparison figure for the paper.

### Tier 3: UofA packaging (2 h)

Reuse `dev/tools/scripts/build_physmap_examples.py` on the uofa side, or better, have PhysMAP's `assessment_v06.py` emit the shape directly (its P1 work): `patternId` W-SURR-05 or W-SURR-06, `source: external`, agent attribution with name and version, the observation fields. `closureId` is the registry id (`menter-sst-1994`), `boundVariable` the G0.3 variable, `mechanism` `laminar-turbulent-transition`, `dimensionlessGroup` the G0.3 group. The uofa pack needs no change for this.

## 6. What could make the result wrong, and the check for each

| Threat | Check |
|---|---|
| Wind-tunnel wall and support interference is the real cause, not the closure | HLPW data is corrected for AoA only. Report the comparison at the corrected AoA and name interference as a second omitted mechanism in the write-up. If the flagged points coincide with the AoA correction's largest values, say so |
| Mesh, not closure | One mesh for training; a second, finer mesh at the three ablation points. If ΔCp from mesh refinement is of the order of the ablation ΔCp, materiality is not attributable to the mechanism and C2 is downgraded to "mesh-limited" |
| The bound variable was picked after seeing the errors | Freeze the closure entry and the bound variable in the registry, commit it, and record the commit hash in the result before the first tunnel comparison runs. Pin inputs at read time (hash the tunnel file when loaded, not when written) |
| A number better than expected | Check the matcher: plot flagged and unflagged points on the Cp error axis before computing any AUC |
| The surrogate is too good or too bad to say anything | Report surrogate-vs-CFD error first. If it is above the tunnel-vs-CFD gap, the surrogate is the problem and the closure story cannot be read |

## 7. Kill criteria

| Id | Condition | Action |
|---|---|---|
| K1 | No public digital Cp for CRM-HL after G0.2 | Drop Tier 2 to CL-only or drop it; Tier 1 stands on its own |
| K2 | Tier 1: C1 AUC at or below 0.6, or N1 fires selectively on the high-error points | Stop. Write it up as a negative result with the tables. Do not tune the bound variable |
| K3 | Tier 1: N2 noise floor within a factor of 2 of the transition ablation materiality | Stop C2. Report materiality as unmeasurable at this mesh |
| K4 | G0.4: one CRM-HL point costs more than the compute you can reach for 25 points plus 10 ablation runs | Publish Tier 1 only; cite Luminary as context |
| K5 | Total pairing time past 20 h with T1 not closed | Stop and write up |

## 8. Schedule, at pairing speed

| Session | Hours | Output | Gate |
|---|---|---|---|
| S0 | 2 | G0.1 to G0.4 answered with sources; closure entry and bound variable drafted | G0 |
| S1 | 3 | 2D mesh, solver settings, one converged point at three AoA; residual and y+ record | runs converge |
| S2 | 3 | Training sweep scripted and launched; surrogate fit; surrogate-vs-CFD error table | surrogate error reported |
| S3 | 3 | Closure entry committed; flags computed and frozen; N1 run | flags frozen before tunnel data |
| S4 | 3 | Ablation pairs; N2; materiality table | C2 numbers |
| S5 | 2 | Tunnel Cp loaded (hash at read); C1 split table and AUC; figures | T1 |
| S6 | 2 | UofA export, `shacl`/`rules`/`verify` green, package signed | C3 |
| S7+ | 20 to 30 | Tier 2, if T1 and G0.4 allow | T2 |

Tier 1 total: 18 h pairing. Solver wall time is extra and runs unattended.

## 9. Deliverables

- PhysMAP: a new stress test module beside `stress_tests/lewis_reuse.py`, a banked result JSON with `inputs_sha256`, the corpus entries for the closure bound (`corpus_seed.jsonl` plus its evidence claim), and a reproduction log.
- uofa: one or more signed packages under `packs/surrogate/examples/physmap/`, built from the banked result, with the three commands and their outputs in the README.
- Paper: one figure (flagged versus unflagged error bands, OOD detector silent), one table (materiality per point with theta as a line), and, if G0.1 allows, Luminary's R² beside them.

## 10. Score against the declared criteria

End-user value: an engineer with a vendor surrogate and a wind-tunnel polar can run PhysMAP's screen on the operating points before buying the correction head, and gets a signed list of where the closure is being asked past its range. Praxis: a third demonstration, 3D and aerospace, with two null controls and a vendor's published failure as the motivating case. The baseline is you without the program, not the field finished.

## Sources read for this spec

- Luminary, "Why Physics AI Models Need to Be Anchored to Reality" (R² before and after; the CRM-HL and Mach 0.70/0.85 statements that G0.1 must reconcile)
- Luminary, Physics AI Factory page ("Today's models cannot generalize to physical phenomena they have not encountered in training")
- Adams, Ranade, Cherukuri, Choudhry, GeoTransolver, arXiv 2512.20399 (abstract only)
- HLPW-4 wind-tunnel data page (QinetiQ 5m: forces, moments, tufts, rake; Cp uncorrected note) and HLPW-5 test-case documents; `hiliftpw.larc.nasa.gov` now redirects, `aiaa-hlpw.org` hosts
- PhysMAP `closures/data/closure_index.json` at commit 675729b: 201 closures, 20 in the `rans-turbulence` family, including `menter-sst-1994`, `spalart-allmaras-1992`, `langtry-menter-transition-2009`; `corpus/calibration.py` and `corpus/data/corpus_seed.jsonl` for where `validated_range` bounds are curated
- PhysMAP `stress_tests/lewis_reuse.py` for the matched-ablation and null-control pattern this spec copies
