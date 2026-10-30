<!-- Mirrored from cloudronin/praxis-tools docs/specs/surrogate-governance-loop.md on 2026-10-30 (commit 9e6daa0). The praxis-tools copy is the working copy; this one is the public reference for the NWC27 talk, the UQAIS paper and the three open-model cases. The governed review workbench that dispositions firings is private until requirement C6 publishes it; this repository's public-surface audit forbids naming private repositories, so it is called "the Workbench" here. The public uofa tooling is at github.com/cloudronin/uofa. -->

# Surrogate Governance Loop: requirements

Version 0.2, 2026-10-29. Adds section 4.5, outside physics PhysMAP can take in. Written for the NAFEMS World Congress 2027 talk (abstract due 2026-11-09,
paper due 2027-01-31, talk 2027-04-25 to 28) and for the open stack it demonstrates.

The three repos: `cloudronin/physmap` (MIT, 0.2.5), `cloudronin/uofa` (Apache-2.0, 0.20.0),
the review-workbench repository (private, 0.1.0, to be opened under C6). Facts below were read from those repos on
2026-10-29 at their current heads. Anything marked **INVESTIGATE** was not confirmed in code and must
be checked before it is built on.

## 1. The one sentence

A surrogate's credibility is decided one prediction at a time. A physics-aware check raises the flag,
a named engineer decides, and the decision is signed into a package anyone can verify. The same check
runs in production, and when the flags say the context of use has moved, the engineer decides again
and the package gets a signed successor.

## 2. The three stages

| Stage | The check (physmap) | The human (workbench) | The record (uofa) |
|---|---|---|---|
| Before reuse | Is a mechanism outside calibration, and does it matter? Lewis 35A: Ri 0.29 against a window of 0; materiality 0.006 to 0.195 downstream | Reuse, or not, with a reason | Signed package with the decision |
| At deployment | Does the physics the prediction relies on still apply? NACA: 45 of 45 outside the closure's region, 36 numerically close | Disposition each flag: Confirmed, Overruled, Not Applicable | Flags, dispositions and the ledger sealed under the signature |
| In production | Same check on every prediction; the share outside the supported region and the materiality trend | Review the backlog in batches; re-decide the context of use when a trend crosses a line | A signed successor package linked to the one before (`wasDerivedFrom`) |

## 3. The four layers and what each repo owes

| Layer | Repo | Owes for the loop | Exists today |
|---|---|---|---|
| Check | physmap | Flags exported as UofA annotations with no disposition, a source agent, and surrogate-pack pattern ids; a `monitor` command | `assess()` per prediction; `pipeline/assessment_v06.py` exports `Discrepancy`, `CredibilityFactor`, `WeakenerAnnotation`, `OffsetRationale`, `Disposition`; its adjudicator picks the action class itself |
| Format and catalog | uofa | Two new surrogate-pack patterns; the external-annotation rule; a plain `uofa disposition` command | `packs/surrogate` v0.1 with W-SURR-01 to 04 and the SIP measured-evidence path; sign, verify, cross-version verify |
| Engine | workbench | A second firing source with a source chip; the Evolve minimum; the status statement for CI | Ingest, Extract, Review, Dispositions, Finalize; ledger by construction; `engine.py` runs `uofa rules --format json`; `dispositions.rows()` one row per expected factor; live on HF; Evolve and continuous checks specified, not built |
| Demo and paper | praxis-tools, talk repo | The NACA and Lewis runs end to end, one figure, the runbook | Both PhysMAP runs, numbers and figures, in `physmap/docs/talk` |

## 4. Requirements

Each row: an id, what must be true when done, the done-gate (how it is checked), the hours at
Vishnu-plus-Claude-Code pace. Hours are build hours; the done-gate is the test.

### 4.1 uofa (public): the contract and the catalog

| Id | Requirement | Done-gate | Hours |
|---|---|---|---|
| U1 | The surrogate pack gains pattern **W-SURR-05, prediction relies on a closure outside its validated range**. Fires on a `WeakenerAnnotation` whose justification names a closure id, a bound variable, the validated range and the observed value. Severity High. Distinct from W-SURR-03 (inputs outside the training envelope): this is physics the surrogate cannot see. | Rule fires on the NACA export (45 annotations) and stays quiet on the 40 fully developed points | 3 |
| U2 | The surrogate pack gains pattern **W-SURR-06, an omitted mechanism is active and material**. Fires on an annotation naming the mechanism, its dimensionless group, the calibration window, the observed value and the materiality. Severity High. Materiality below the declared threshold does not fire; the threshold is recorded as illustrative when it is. | Fires on Lewis 35A gravity-on at the three downstream stations at θ = 0.10; quiet on gravity-off at every station | 3 |
| U3 | **External annotation rule.** A `WeakenerAnnotation` may arrive with no `Disposition`. It must carry `prov:wasAttributedTo` a software agent with name and version, and a `source` of `external`. The shapes accept it; `uofa rules` lists it as a firing with `source: external`; `uofa verify` covers it. | SHACL accepts the NACA export; `rules --format json` emits the external firings with the source field; a package signed with them verifies on a second machine | 4 |
| U4 | **Recommendation, not decision.** An external annotation may carry `recommendedAction` from the five action classes. It is never read as a `Disposition`. | Fixture with a recommendation and no disposition: `rules` reports the firing as undispositioned | 1 |
| U5 | **`uofa disposition` command.** Lists undispositioned firings (engine and external) for a package; records Confirmed, Overruled or Not Applicable with a reason and a named reviewer; writes the ledger entry; refuses `Accepted`. The same three verdicts as the Workbench's Part B, parsed from the protocol, not retyped. | Disposition one NACA firing from the CLI; the ledger entry has actor, timestamp, prior value; `sign` then `verify` pass | 6 |
| U6 | **Successor link.** A package may declare `prov:wasDerivedFrom` the hash of a prior package. `verify` checks the hash is well formed and, when the prior package is present, that it verifies. **INVESTIGATE:** the praxis says a revision is a new package with a provenance link; confirm the property name and whether `verify` already follows it. | Two packages, the second derived from the first: `verify` reports the chain | 3 |

### 4.2 physmap (public): the export and the monitor

| Id | Requirement | Done-gate | Hours |
|---|---|---|---|
| P1 | **`physmap assess … --emit-uofa out.jsonld`.** Writes the v0.6 subgraph with no `Disposition` node, `source: external`, `prov:wasAttributedTo` physmap and its version, and the pattern ids W-SURR-05 and W-SURR-06 from the pack. The current adjudicator's action class goes to `recommendedAction`. Existing export unchanged under its current flag. | The NACA example emits 45 annotations with W-SURR-05 and no disposition; the Lewis stress test emits W-SURR-06 at the downstream stations; `uofa shacl` accepts both | 4 |
| P2 | **Pattern bridge made real.** `corpus/calibration.py` requires `weakener_link` to UofA pattern ids. **INVESTIGATE:** no `W-` ids were found in `data/` or `src/` on 2026-10-29; find what the corpus entries carry today and point them at the surrogate pack. | Every calibration entry links to a pattern that exists in `packs/surrogate` | 2 |
| P3 | **`physmap monitor stream.csv --package case.uofa --out report.jsonld`.** Runs `assess()` on each row; writes one annotation per flag (P1 format) appended to a monitoring annotation set; reports the applicability rate (share of predictions flagged W-SURR-05), the materiality trend (W-SURR-06 magnitude over the stream order), and the count of undispositioned flags. No threshold decides anything; the report states the numbers. **INVESTIGATE:** whether `assess()` runs per row at stream rate or only in batch; the Lewis bank is 12 stations, so batch is enough for the demo. | On the Lewis stations in order, gravity on: the report shows materiality rising from 0.006 to 0.195 and three W-SURR-06 flags; gravity off: zero flags | 6 |
| P4 | **Bring your own physics: closure spec.** A YAML or JSON file declares a closure: id, source citation, geometry class, bound variables with validated range and status (confirmed, claimed, assumed), which variables the surrogate observes, and optionally an executable `predict(**inputs)`. Loaded at `CredibilityGuardrail` setup beside the bundled registry. A closure with no bounds is "registered, not curated" and PhysMAP says so. | Gnielinski re-declared through the spec reproduces the NACA 40 of 40 and 45 of 45 result exactly | 8 |
| P5 | **Bring your own physics: mechanism spec.** Declares a mechanism: name, dimensionless group, how to compute it from the data columns, the calibration window, and optionally a `run(inputs, mechanism_on)` callable for matched ablation. Materiality is computed only when the callable exists; otherwise the mechanism is out-of-calibration-only and the report says so. | Buoyancy re-declared through the spec reproduces the Lewis materiality column to the printed precision | 6 |
| P6 | **Declared bounds are evidence.** A closure or mechanism spec exported with `--emit-uofa` carries its bound ranges as claims with their source and status. An `assumed` bound with no source fires W-SURR-01 or a new pattern. **INVESTIGATE:** whether W-SURR-01 (physics-constraint check evidence missing) covers it or a W-SURR-07 is needed. | A spec with an unsourced bound produces a firing the reviewer must disposition | 3 |

Kill criterion for P4 and P5: if the spec cannot express Gnielinski and the Lewis buoyancy mechanism
without special cases, the abstraction is wrong. Stop, ship P1 to P3, and the talk shows the bundled
physics only.

#### P4 amendment, 2026-10-30: bound kinds

An applicability bound is any checkable statement about the point of use, with a source and a status. The numeric range is one kind, not the definition. The closure spec (P4) and the mechanism spec (P5) accept four kinds; every kind carries the variable, how it is computed from the point of use and the model's own configuration, and the status (confirmed by validation, claimed by the maker, assumed by us) with its source.

| Kind | Reads as | Example |
|---|---|---|
| `range` | the variable lies between a and b (either side may be open) | x/D at or above 10; SST anomaly up to +2 K |
| `set` | the variable is one of these | element in the 89 MACE-MP-0 was trained on; structure class in {bulk crystal} |
| `point` | the variable equals this, within a tolerance | Re 7.19e6, yaw 0, the one condition DoMINO was trained at |
| `ratio` | a derived quantity against a threshold | storm core size over grid spacing at or above k; distance from equilibrium geometry below a cutoff |

Each kind reduces to a yes or no per point, so the rule engine and W-SURR-05 do not change. Outside any bound the applicability term is unbounded. A bound with no source fires W-SURR-07 (Q6). The claims rule does not change: outside a bound means unsupported by the validation evidence the model ships with, never wrong. The three cases of section 4.7 need `set` (X3), `point` (X1) and `ratio` or `range` (X2, X2b); the acceptance test for this amendment is that all three declare through the spec with no code written per case.

### 4.3 workbench (to be opened): the engine

| Id | Requirement | Done-gate | Hours |
|---|---|---|---|
| C1 | **Second firing source.** `engine.py` reads external annotations from the package graph beside the `uofa rules` run, into the same `Firing(pattern, severity, factors, message)` plus a `source` field (`uofa rules` or the agent name and version). `dispositions.rows()` is unchanged. Invariant 1 holds: the read uses the public wheel's surface (U3), nothing private. | The NACA export ingested: Dispositions shows one row per expected factor with the PhysMAP firings, source chip reading "physmap 0.2.x" | 4 |
| C2 | **Factor mapping for surrogate flags.** The surrogate pack's expected factors must include the ones PhysMAP flags land on, so the silence rule holds (a factor with no flag still gets a row). **INVESTIGATE:** `WorkingSet.expected_factors` comes from the pack; confirm the surrogate pack declares them and which factor W-SURR-05 and 06 map to through `weakener_focus.enrich_firings`. | Every PhysMAP firing lands on a factor row; none falls to package level | 3 |
| C3 | **Machine candidate for external firings.** An external annotation's `recommendedAction` renders as an inert candidate, never a selection, and never on a judgment-class row. Same as today's machine draft. | Candidate visible, not selected, adoption is one logged click | 1 |
| C4 | **Evolve minimum.** Import a sealed package, run `uofa verify` first and record the finding as the opening fact, carry `wasDerivedFrom` the prior hash (U6), re-open only the factors whose evidence changed, re-seal. Prior judgments keep their original actor. | The Lewis package after `monitor` imports as a successor; the three new flags are the only open rows; the successor verifies and names its predecessor | 10 |
| C5 | **Status statement for CI.** A machine-readable JSON per package: undispositioned flag count, applicability rate, materiality trend, last reviewer, last signature, predecessor hash. No pass or fail; the customer pipeline decides. From the continuous-assurance spec v2.1 §3.3. | File validates against a published schema; a sample GitHub Actions step reads it and prints the numbers | 3 |
| C6 | **Public repo cut.** A new repository with `workbench/` (the package), `docs/guide`, the vendored protocol, `tests/`, a README and a license matching uofa (Apache-2.0) or AGPL-3.0 if the hosted service stays the paid tier. Not included: `docs/specs`, `dev/`, `cases/`, `deploy/`, `stranger-prompt.md`. `store/` audited for any key or account artifact that was ever real. CI runs the tests on the public wheel. | Fresh clone, `pip install -e ".[dev]"`, tests pass; `git log` starts at the cut; no secret scanner hit | 12 |

Rename note: the praxis and Figure 4.5.3 say Credibility Inspector; the public repo says the Workbench.
Both stay. Nothing in the praxis changes.

### 4.4 Demo and paper

| Id | Requirement | Done-gate | Hours |
|---|---|---|---|
| D1 | **End-to-end runbook, NACA.** `physmap assess --emit-uofa` → the Workbench ingest → disposition one of the 36 numerically-close points as Overruled with a reason → sign → `uofa verify` on a second machine. Captured output committed. | Runs from a clean clone in under five minutes; the captured output matches | 4 |
| D2 | **Production demo, Lewis.** `physmap monitor` on the 12 stations in order → successor package → the three new flags dispositioned → re-seal → chain verified. | Same as D1 | 3 |
| D3 | **One figure.** PhysMAP verdict → annotation → disposition → signature → successor, with the real NACA rationale text in it. | Figure in the talk repo with its data file, like the existing `bench_` figures | 3 |
| D4 | **Claims ledger entries.** Every headline sentence the talk says, with command, artifact, scope and limits, in the style of `physmap/docs/talk/claims-ledger.md`. No detection rate, no F1, Lewis is one run. | Ledger builds; `check` passes | 3 |

### 4.5 Physics PhysMAP can take in beyond the bundled corpus

Searched 2026-10-29. The bundled corpus holds thirteen closures (Gnielinski, Dittus-Boelter, Petukhov,
Sieder-Tate, Sparrow-Cur, Pohlhausen, McAdams, Churchill and Aung-Worku mixed convection, two
supercritical-CO2 variants, Pate and Marineau hypersonic bounds) on circular pipes, flat plates, narrow
channels and hypersonic bodies. Four kinds of outside physics fit the P4 and P5 specs.

| Kind | Source | License | What it gives PhysMAP | Spec row | Caveat |
|---|---|---|---|---|---|
| Correlation library | `ht` (Caleb Bell), ht.readthedocs.io | MIT | Hundreds of Nusselt correlations (internal, external, free convection, tube banks, packed beds, supercritical); docstrings cite the paper and state limits | P4 done-gate: Gnielinski re-declared from `ht` must reproduce NACA 40 of 40 and 45 of 45 | Ranges live in docstrings, not a table; each imported closure needs its range read and a status set |
| Correlation library | `fluids` (Caleb Bell), fluids.readthedocs.io | MIT | Friction factors (Colebrook, Blasius, curved pipe), laminar switch at Re 2040 | P4, second closure family for pressure-drop surrogates | Same docstring caveat |
| Validation database | NASA Turbulence Modeling Resource, turbmodels.larc.nasa.gov | Public | RANS model documentation with verification and validation cases; the validated envelope of Spalart-Allmaras and others | P4 bounds for any RANS-trained surrogate (AirfRANS surrogates are SA) | Cases, not a range table; the spec is written per model by hand |
| Validation database | ERCOFTAC Classic Collection, ercoftac.org | Free with registration | Experimental turbulence cases with data and references | P5 reference measurement for materiality on flow surrogates | Registration to download |
| Validation database | FDA benchmark nozzle and blood pump, Round Robins 1 and 2, and the hemolysis dataset (cdrh-rst.fda.gov) | Public | PIV, wall shear and plasma-free hemoglobin versus flow rate for both geometries | The medical-device case for the paper: a hemolysis surrogate checked against the FDA benchmark joins the talk to Morrison and to the V&V 40 audience | Confirm the hemolysis download before promising it; the NCI hub URL appears under two spellings |
| Open solver | OpenFOAM or SU2 | GPL / LGPL | Source terms switchable: gravity, buoyancy, chemistry | P5 `run(inputs, mechanism_on)` callable for Lewis-type ablations on a user's case | The Lewis bank was built this way; the spec names the interface only |
| Open solver | Eilmer (gdtk-uq/gdtk) | GPL-3 | Compressible and hypersonic flow, finite-rate chemistry, conjugate heat transfer | P5 ablation for the hypersonic cases already in the corpus (Casper, Pate, Marineau) | Call it, never vendor it |
| Open solver | Cantera, with GRI-Mech 3.0 built in | BSD | Reaction mechanisms; a reduced mechanism's valid temperature, pressure and equivalence-ratio window | P5 mechanism spec for combustion surrogates | No published validity envelope for full GRI 3.0; reduced-mechanism papers state theirs |
| Benchmark dataset | AirfRANS (NeurIPS 2022), already the example in `uofa/packs/surrogate` | Open | 103 train, 200 test, 496 out-of-distribution RANS airfoil cases, OpenFOAM SA | A ready reuse case: train on the regular split, deploy on the OOD split, SA envelope from TMR as the closure | None |
| Benchmark dataset | PDEBench | Open | Advection, Burgers, Navier-Stokes, time-dependent | Applicability in time: temporal extrapolation failures | Secondary |
| Benchmark dataset | The Well (PolymathicAI, NeurIPS 2024) | CC-BY | 16 datasets, 15 TB, fluids, MHD, acoustics, biology, with parameter sweeps | Each sweep is a calibration window; a surrogate trained on part of it is a Lewis-type reuse test at scale | Size; pick one dataset |

Picks: `ht` for the P4 done-gate (one afternoon, Gnielinski comes from it). The FDA blood pump for
the paper's second case (joins the surrogate talk to the praxis). AirfRANS plus the TMR
Spalart-Allmaras envelope for the "bring your own turbulence model" example (the dataset is already
in the surrogate pack).

| Id | Requirement | Done-gate | Hours |
|---|---|---|---|
| P7 | **`ht` import path.** A loader that reads one `ht` correlation into a P4 closure spec: function, geometry class, bound variables and the range from the docstring, status `claimed` until a human confirms it against the cited paper. | Gnielinski via `ht` reproduces the NACA counts; Dittus-Boelter via `ht` matches the bundled entry | 4 |
| P8 | **FDA blood-pump case.** A hemolysis surrogate (any simple fit on the Round Robin 2 data) with the benchmark's flow-rate range as its envelope and the hemolysis dataset as measurement; applicability outside the tested flow rates, materiality by comparison against measured plasma-free hemoglobin. **INVESTIGATE:** the hemolysis download and its terms. | A PhysMAP run on the pump data emits W-SURR-05 outside the tested range and a disposition-ready package | 8 |
| P9 | **AirfRANS with the TMR envelope.** The SA validated envelope written as a P4 closure spec; the AirfRANS OOD split run through PhysMAP as a deployment. | Flags on the OOD split where the SA envelope is left; none on the regular test split | 6 |

These three rows add 18 hours and are optional for the talk. P7 is the cheapest proof that the
bring-your-own-physics spec works on physics PhysMAP did not ship.

### 4.6 UQAIS: uncertainty quantification for AI surrogates (added 2026-10-30)

**Name (Vishnu, 2026-10-30): UQAIS**, pronounced like "ukase": Uncertainty Quantification for AI Surrogates. It accounts for the uncertainty a surrogate inherits from the physics it learned. The talk's hook is "physics debt"; UQAIS is how it goes on the books before deployment. Use the name in the abstract, the paper, the talk, the CLI help and the handoffs.

**The translation sentence (for the talk, the paper's introduction and the README).** The simulation audience knows Oberkampf's epistemic framing; the machine-learning audience does not. Where "epistemic" first appears, say: *"Your ensembles and conformal intervals measure how unsure the student is. These two terms are the teacher's mistakes, and no amount of training data from the same solver makes them smaller."* A surrogate distilled from a solver inherits the solver's closure validity the way a student inherits a teacher's misconceptions; training longer makes it more confidently wrong in the same places. That is also the precise sense in which the inherited terms are epistemic but not reducible by more of the same data, which is the distinction the ML toolbox cannot make on its own.

Framing (Vishnu, 2026-10-30): Roy and Oberkampf's accounting, aleatory and epistemic kept apart,
applied to a surrogate that replaces a simulation. The machine-learning UQ toolbox (ensembles,
dropout, Bayesian layers, conformal intervals) quantifies epistemic uncertainty relative to the
training distribution. It is silent about the model-form term the surrogate inherits from the
physics it learned. W-SURR-05 says whether that term is bounded by any validation at all;
W-SURR-06 estimates its size when a mechanism model exists. This block makes the stack produce
the term, show it on the two cases, and carry it as evidence. It is the content of stage one and
of the human decision; it is not a fourth stage.

| ID | Requirement | Acceptance | Hours |
|---|---|---|---|
| Q1 | **Coverage figure, NACA.** A (Re, Pr) -> Nu surrogate trained on fully developed points only (x/D >= 10), with a split-conformal interval at a nominal 90 percent calibrated on held-out fully developed points. Report empirical coverage on fully developed test points and on the 45 entrance points, per Reynolds curve, counts never pooled. One figure: interval and measured error against x/D, with the W-SURR-05 flags marked. x/D is not a surrogate input, so the entrance points are in-distribution to the interval and to any input-based detector. | Fully developed coverage inside the binomial band for 90 percent; entrance coverage reported with its count; flags on 45 of 45; every number in a data table beside the figure, in the `docs/talk/figures` style but under a new `docs/uq/` so `tools/talk_package.py check` is untouched | 6 |
| Q2 | **Materiality interval figure, Lewis 35A.** The same interval machinery trained with gravity off is unchanged at the gravity-on stations (the input columns are identical, per the bank). The W-SURR-06 materiality from matched ablation is the interval that opens. One figure: statistical interval, materiality interval and measured error against x/D. | Reproduces the bank's materiality at the three downstream stations at theta = 0.10 (0.111, 0.154, 0.195) and the identical-interval fact; theta stated as illustrative | 4 |
| Q3 | **`physmap uq`, the minimal propagation.** Inputs: predictions (callable or CSV), aleatory input samples, and the epistemic terms kept separate: emulation error interval from held-out runs; closure status per point (inside: carry the declared validation metric; outside: unbounded unless an extrapolation band is declared, and then flagged as declared); mechanism materiality interval. Output: a probability box on the quantity of interest (lower and upper CDF at named quantiles) and a JSON report with each term listed on its own line, Roy and Oberkampf style. Never a single number. "Unbounded" is a legal and reported outcome. | On NACA fully developed points the box width is the emulation term plus the validation term; on entrance points the report says unbounded (or names the declared band); on Lewis the box widens by the materiality at the three stations and nowhere else. numpy and scipy only; `import physmap` stays free of sklearn | 10 |
| Q4 | **UQ report as evidence.** The Q3 report attaches to the `--emit-uofa` export (P1) as claims with source and status, so the disposition in the Workbench sees the box, the terms, and any unbounded line. | A package carrying the report validates; the Workbench shows the terms on the factor row | 3 |
| Q5 | **Paper section and claims ledger.** The process table (steps 0 to 7), the two figures, and ledger entries for every headline sentence, with limits. No coverage rate pooled across datasets. | Ledger `check` passes | 3 |
| Q6 | **UQ-bounded context of use (added 2026-10-30).** The package states, in one place attached to the context-of-use node, a credibility-bounds claim per quantity of interest: the box bounds at named quantiles, the terms they are built from (Q3), and the validation domain in which they hold (closure ranges, mechanism windows, training envelope, from P6). A new pattern **W-SURR-07, context of use not covered by declared bounds**, fires when a quantity of interest in the context of use has no bounds claim, or when the context of use reaches outside the domain the bounds were established in. Severity High. The production monitor (P3) reads the same claim: a prediction outside the bounded domain is the applicability event it counts. This is the sentence an engineer signs: credible for this use, within these bounds, with these lines unbounded. | NACA package with bounds declared for the fully developed domain: W-SURR-07 quiet on the 40, fires on the 45; a package with no bounds claim for its quantity of interest fires once at package level; `uofa verify` covers the claim; `physmap monitor` reports the share outside the bounded domain | 6 |

Total 32 hours. Q1 and Q2 depend on nothing; Q3 on neither figure but is best written after them; Q4 on P1 and Q3; Q6 on Q3 and P6 (and settles the P6 investigation: W-SURR-07 is the new pattern for unsourced or missing bounds); Q5 on all.

Kill criteria for the block:
- If 40 fully developed points cannot calibrate a conformal interval to nominal coverage, Q1 uses the Gnielinski emulator with the digitisation's residual noise as synthetic replicates and says so on the figure; if that also fails the binomial band, Q1 ships as a table, not a figure.
- If Q3's box on the fully developed NACA points is wider than the measured error band by more than the emulation term, the propagation is wrong and nothing downstream runs until it is fixed.

What this block may claim: that the statistical interval is calibrated where the physics applies and does not know when it stops applying, and that the physics-inherited term is the one that opens there. It may not claim a detection rate, a coverage rate pooled across cases, or that the box is complete.

### 4.7 The three open models: the talk's cases (added 2026-10-30)

Decision (Vishnu, 2026-10-30): the NWC27 talk and the paper do not reuse the Multiphysics 2026 cases
(NACA entrance region, Lewis 35A, the seven-vehicle benchmark). They apply the process to public,
pretrained, physics-based surrogate models from three domains, each shipped with an accuracy score and
no declared validation domain. NACA and Lewis stay as the uofa pack examples and the regression
fixtures; they are not on a slide. Where a model cannot be run from its public artifacts, that slot
falls back to NACA or Lewis and the talk says so (kill line below).

**Success criterion (Vishnu, 2026-10-30).** A case is done when UQAIS (section 4.6, steps 0 to 7) has been followed on the model and the result is a dispositioned, signed UofA package: the context of use stated; the model's physics declared through P4 and P5 with its bounds and their sources; the epistemic terms separated (emulation error, applicability, materiality) with each bounded, estimated, or marked unbounded; the bounds claim attached to the context of use (Q6); every flag dispositioned by a named reviewer with a reason; the package sealed and verifiable. The case does not have to show the model failing, thin, or wrong. A model whose declared bounds cover its intended use, with every term bounded and every flag dispositioned Not Applicable, is a complete and honest case. The acceptance column of each X row is read in that light: the flags listed there are what the published record leads us to expect, not a requirement.

The claim, per case, is never "the model is wrong." It is "this prediction lies outside the validation
evidence the model ships with, and its maker declared no domain." Every number carries the case name;
nothing is pooled.

| ID | Case | What was verified on 2026-10-30 | Applicability term (W-SURR-05) | Mechanism term (W-SURR-06) | Reference truth | Hours |
|---|---|---|---|---|---|---|
| X1 | **Automotive external aerodynamics.** NVIDIA DoMINO pretrained on DrivAerML (checkpoint bundle `nvidia/domino_drivaerml` on Hugging Face; DrivAerML dataset CC-BY-SA, 500 morphed DrivAer variants, Re_L 7.19e6 on the 2.786 m wheelbase, SA-based hybrid RANS-LES with DDES shielding). NAFEMS home turf. | Checkpoint location, dataset license, Reynolds number, turbulence treatment. NOT verified: inflow speed, yaw, ground and wheel boundary conditions, and whether DoMINO takes any inflow parameter as input. | The single training condition is the validated range. If inflow is not a model input, Reynolds number and yaw are structurally invisible to the surrogate and to any input-based detector, exactly as x/D was. Bound variables: Re, yaw angle, ground clearance. | Candidate: wheel rotation and moving ground, or crosswind. Matched ablation by OpenFOAM RANS on one DrivAer variant with the mechanism on and off; a RANS ablation is an estimate of materiality and is labelled as such. | DrivAerML held-out cases in domain; published DrivAer wind-tunnel data at other conditions out of domain (investigate which exist) | 30 |
| X2 | **Weather and climate.** NeuralGCM: a differentiable dynamical core plus a learned physics parameterization. Google checkpoints at `gs://neuralgcm/models/` under CC-BY-SA 4.0; code Apache-2.0. Published: reproduces the climate response at +1 K and +2 K SST and diverges from physics-based expectations at +4 K (hierarchical testing study, 2026); an earlier study reports failure when the parameterization is trained on the baseline climate only. | Checkpoint license and location (third-party mirrors; confirm on the Google repo). The +4 K finding is one published study. | The learned parameterization's calibration window is the training climate. Bound variable: SST anomaly; validated range 0 to about +2 K per the published tests. | The dynamical core is open, so a physics-parameterization baseline would give matched ablation; whether one ships with the code is an investigation item. Otherwise the published +4 K divergence is the magnitude, cited not computed. | ERA5 for the present climate; the physics GCM runs in the 2026 study for the warmed cases | 25 |
| X2b | **Fallback for X2.** ECMWF AIFS Single 1.1 (weights CC-BY-4.0 on Hugging Face; ERA5 1979 to 2022 pretraining; 31 km; 13 levels). The model card itself states "reduced intensity of some high-impact systems such as tropical cyclones"; ECMWF's 2025 evaluation gives a global wind-speed bias near -29 knots, and the 2026 AIFS-TC preprint reports raw AIFS missing rapid intensification entirely. | Model card text, license, resolution, the stated limitation. | Bound variable: storm core size against the 31 km grid; the inner core is unresolved by construction. | No ablation possible (IFS is closed); materiality is the observed bias against best-track data, cited. | IBTrACS best track; ECMWF's own evaluation | 12 |
| X3 | **Atomistic materials.** MACE-MP-0, the universal interatomic potential replacing density functional theory (MIT license; trained on MPtrj at PBE(+U); 89 elements). The dispersion interaction is omitted by construction and `mace_mp(dispersion=True)` switches a D3 correction on at inference. Documented: C11 of one material 33 percent low against DFT before fine-tuning; softened phonons, wrong surface energies, unstable high-temperature dynamics as the practitioner-reported failure modes; spurious imaginary phonons in a dispersion-free variant on MOFs. | License, training data, the dispersion switch, the published failure reports. | Trained on bulk, near-equilibrium structures. Bound variables: distance from equilibrium, temperature, surface versus bulk, element and pressure coverage of MPtrj. | **Exact and cheap.** Dispersion on versus off is a matched ablation at inference; materiality is the energy and force difference on layered and molecular systems. The one case where W-SURR-06 is computed, not estimated. | DFT+D3 energies from open datasets (which one is an investigation item) | 12 |

Order: X3 first (cheapest, and the only exact materiality), then X1 (the demo case, D1 to D3 move to it), then X2, with X2b if NeuralGCM cannot be run or its physics baseline does not exist. The demo rows D1 to D3 run on X1; D4's ledger covers all three.

Kill line per case: if the model cannot be run from its public artifacts, or its physics cannot be declared through P4 and P5 even with the extensions those specs need (categorical coverage, resolution bounds, a single training condition), by 2026-12-20, that slot reverts to NACA or Lewis and the abstract's reuse email to nwc-reviews goes out then. A case whose result is "all terms bounded, nothing fires" is not a kill; it is a finished case.

Licence note: DrivAerML and the NeuralGCM checkpoints are share-alike (CC-BY-SA). Any UofA example package built from their outputs carries that license, separate from the repository's Apache-2.0. Record it on the package.

Investigation items for this section: DoMINO's input signature and DrivAerML's inflow, yaw, ground and wheel conditions (from the dataset paper's setup section and the DoMINO config); whether a physics parameterization baseline ships with NeuralGCM for ablation; which open DFT+D3 dataset serves as X3's truth; the DrivAer wind-tunnel conditions published outside the dataset's single point.

## 5. Totals and order

| Block | Hours | Depends on |
|---|---|---|
| uofa U1 to U6 | 20 | nothing |
| physmap P1 to P3 | 12 | U1 to U4 |
| physmap P4 to P6 | 17 | P1 |
| workbench C1 to C5 | 21 | U3, U5, U6, P1 |
| workbench C6, the public cut | 12 | nothing; can run first |
| demo D1 to D4 | 13 | everything above |
| **Total, required** | **95** | |
| physmap P7 to P9, outside physics (optional) | 18 | P4, P5 |
| UQAIS Q1 to Q6 (section 4.6) | 32 | Q1, Q2 nothing; Q4 on P1; Q6 on Q3, P6 |
| the three open models X1 to X3 (section 4.7; X2b fallback 12 more) | 67 | X3 nothing; X1, X2 on P4 and P5 |
| **Total, with the optional rows** | **212** | |

At the measured pairing pace that is about four weekends and the weeknights between. The abstract
(2026-11-09) promises nothing that needs any of it: the PhysMAP cases, UofA signing and verification,
and the Workbench disposition step already exist. The build only decides how much of the talk runs live.

Order: C6 first, because the public repo is the thing the talk points at and it blocks nothing. Then
U1 to U4 and P1 together (the contract), then C1 (the first live moment), then U5, P3, U6, C4 (the
production stage), then P4 to P6 (bring your own physics), then the demo rows.

## 6. Kill criteria

- **Contract:** if U3 needs a change to core shapes that breaks existing packages, stop; the demo
  shows the three stages with PhysMAP's current export and a hand disposition.
- **Monitor:** if P3 and C4 are not running on the Lewis stream by 2027-01-15, the paper says "first
  implementation" and the talk shows the deployment stage live and the production stage as D3's figure.
- **Bring your own physics:** the P4 and P5 criterion above.
- **Open-sourcing:** if the `store/` audit finds anything that cannot be scrubbed from history, the
  public repo starts from a fresh tree with no history. That is still a cut, not a stop.

## 7. Investigation items, in one place

1. U6: the successor-link property and whether `verify` follows it.
2. P2: what `weakener_link` carries in the calibration corpus today.
3. P3: `assess()` at stream rate or batch only.
4. P6: W-SURR-01 or a new pattern for unsourced declared bounds.
5. C2: the surrogate pack's expected factors and the factor each new pattern maps to.
6. C6: the `store/` audit and the license choice.
7. P8: the FDA hemolysis dataset download and its terms of use.
8. Q1: how many fully developed points each NACA Reynolds curve holds, and whether split conformal or jackknife+ is the honest choice at that count.
9. Q2: whether the Lewis bank holds the headline design M predictions needed to train the interval, or only the per-station summaries.
10. Q5: what ASME V&V 70 (verification and validation of machine learning models) has published, so the paper positions this as the instrument and the evidence record such assessments consume, not as a new VVUQ method.

## 8. What the talk may claim, and what it may not

May: the two PhysMAP results with their stated limits; signed packages verified on another machine
and across uofa versions; 10 of 10 pre-registered stranger runs through the Workbench with 30 of 30 checks;
one open-source stack once C6 lands.

May not: a detection rate for PhysMAP; any F1; that Lewis is more than one run; that the monitor
decides anything; that a signature means the surrogate is correct; that any of this is regulatory
acceptance.

## 9. Remaining work for the talk and the paper (as of 2026-10-30)

Done and merged: U1 to U4 (uofa main, PR #142, surrogate pack v0.2); Q1 to Q3 (physmap main, PR #1: the NACA coverage figure, the Lewis materiality interval, `physmap uq`, bound kinds in the report). Specified and not built: everything below. Hours are pairing hours. "Due" is the date the row has to exist for the deliverable it feeds, not a calendar slot.

| Row | What | Depends on | Hours | Due | Repo |
|---|---|---|---|---|---|
| P4 amendment | The four bound kinds (range, set, point, ratio) in the closure and mechanism specs | nothing | 4 | Nov 6 sessions | physmap |
| U5, U6 | `uofa disposition` command; successor link; the three core-namespace terms moved into core vocab | nothing | 9 | Nov 6 sessions | uofa |
| P1, P2 | `physmap assess --emit-uofa`; what `weakener_link` carries | U3 (done) | 6 | Nov 6 sessions | physmap |
| P4, P5 | Bring-your-own closure and mechanism specs, with the bound kinds | P4 amendment | 14 | Dec 12 | physmap |
| X3 | MACE-MP-0 through UQAIS: physics declared (`set` bound, dispersion as the mechanism), truth set chosen, flags, dispositions, signed record | P4, P5; U5 or a hand disposition in the Workbench | 12 | Dec 20 | physmap, uofa |
| X1 | DoMINO on DrivAerML: input-signature investigation first, then `point` bound, RANS ablation, record | P4, P5 | 30 | Dec 20 | physmap |
| X2 or X2b | NeuralGCM (`range` bound on SST anomaly) or AIFS Single (`ratio` bound on core size over grid) | P4, P5 | 25 or 12 | Dec 20 | physmap |
| C6 | Public the Workbench cut | license (Nov 5) | 12 | Dec | workbench |
| C1 to C5 | Second firing source; factor mapping; machine candidate; Evolve minimum; CI status statement | U3, U5, U6, P1 | 21 | Jan 15 | workbench |
| P3 | `physmap monitor` and the applicability rate | P1 | 6 | Jan 15 (kill line) | physmap |
| Q4 | The UQAIS report attached to the export as evidence | P1, Q3 | 3 | Jan | physmap, uofa |
| Q6 | Bounds claim on the context of use; W-SURR-07 | Q3, P6 | 6 | Jan | uofa |
| D1 to D4 | End-to-end runbook on X1, production demo, the one figure, the claims ledger | X1, C1, C4 | 13 | Jan 31 | physmap talk package |
| Q5 | Paper section and ledger entries | all above | 3 | Jan 31 | paper |

About 165 pairing hours remain of the 212 in section 5, with roughly 47 done. The optional outside-physics rows P7 to P9 are not counted.

Deliverables and their dates:

| Deliverable | Date | What it needs from the table |
|---|---|---|
| NWC27 abstract | 2026-10-30 (deadline 11-09) | nothing; submitted from the Google Doc |
| Per-case kill line | 2026-12-20 | X1, X2 or X2b, X3 run from public artifacts with physics declared, or revert to NACA or Lewis |
| Journal paper preregistration | 2026-12-13 block | written before any X-case number is read |
| Monitor kill line | 2027-01-15 | P3 and C4 on a stream, else "first implementation" in the paper |
| NWC27 full paper | 2027-01-31 | the three signed records, the two method figures, the process table, the claims ledger |
| Talk | 2027-04-25 to 28, Vancouver | one case shown end to end (X3 or X1), the other two one slide each; the translation sentence on the slide where "epistemic" first appears; D3's figure |

Investigation items still open: DoMINO's input signature and DrivAerML's boundary conditions; a physics-parameterization baseline for NeuralGCM; the open DFT+D3 truth set for X3; the NWC27 acceptance notification date and the paper length limit; ASME V&V 70's published output.
