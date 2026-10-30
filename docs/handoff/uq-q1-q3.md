UQAIS, uncertainty quantification for AI surrogates: it accounts for the uncertainty a surrogate inherits from the physics it learned.

# Handoff: UQAIS, Q1 to Q3

Branch `claude/uq-roy-oberkampf`. Everything new is under `docs/uq/`, `src/physmap/uq/`,
`tests/test_uq.py`, one new subcommand in `src/physmap/cli.py`, and this file. Nothing under
`docs/talk/` changed.

## What was built

| Piece | File | One line |
|---|---|---|
| Conformal arithmetic | `src/physmap/uq/conformal.py` | split-conformal half-width, the "needs 9 scores at 90 %" rule, binomial bands |
| Q1 computation | `src/physmap/uq/naca.py` | the NACA interval, both calibration attempts, coverage per curve, PhysMAP's flags |
| Q2 computation | `src/physmap/uq/lewis.py` | held-out-run emulation interval, the identical-interval assertion, the materiality term at θ |
| Q3 propagation | `src/physmap/uq/pbox.py` + `physmap uq` | aleatory samples through the prediction, epistemic terms on separate lines, a probability box out |
| Figures, tables, examples | `src/physmap/uq/figures.py` → `docs/uq/figures/`, `docs/uq/examples/` | `build` makes them; `check` recomputes and compares |
| Held-out scores bank | `docs/uq/data/uq_2_lewis_emulation_heldout.json` | twelve GP refits, minutes each; `python -m physmap.uq.lewis --recompute` |
| Method note | `docs/uq/README.md` | what each figure shows and does not |
| Tests | `tests/test_uq.py` | 15 tests, including Q3's acceptance on the committed examples |

## Does each requirement pass

| Req | Acceptance | Result | How to see it |
|---|---|---|---|
| Q1 | fully developed coverage inside the 90 % binomial band | **pass**: 34 of 40 test replicates, band 32–39; per curve 7, 8, 7, 5, 7 of 8 (band 5–8) | `docs/uq/figures/data/uq_1_naca_counts.csv` |
| Q1 | entrance coverage reported with its count | 36 of 45 reads (band 36–44); per curve 8, 8, 8, 7, 5 of 9; the Re 26400 curve is below its band | same table |
| Q1 | PhysMAP flags 45 of 45 entrance points | **pass**; input-based detectors 0 of 45 | same table; `python -m physmap.uq.naca` |
| Q1 | one figure, numbers in tables beside it, SVG and PNG, caption | **pass** | `docs/uq/figures/uq_1_naca_coverage.{svg,png}`, `docs/uq/figures/README.md` |
| Q2 | reproduces 0.111, 0.154, 0.195 at x/D 67.55, 101.69, 135.84 at θ = 0.10 | **pass** (bank values, to the digit) | `docs/uq/figures/data/uq_2_lewis_interval.csv` |
| Q2 | the identical-interval fact | **pass**, asserted in code: inputs identical (bank) → interval identical | `src/physmap/uq/lewis.py`, `compute()` |
| Q2 | θ stated as illustrative on the figure | **pass** | the figure's legend and side table |
| Q3 | NACA fully developed: box width = emulation + validation | **pass** on 40 of 40 (emulation 0, validation 2 × 19.2 %) | `python -m physmap.uq.figures check` |
| Q3 | NACA entrance: unbounded | **pass**, 45 of 45 say `unbounded` | `docs/uq/examples/naca_stdout.txt` |
| Q3 | Lewis: widens by the materiality at the three stations, nowhere else | **pass** among the 9 comparable stations; it also widens at x/D 159.33, which flags at θ = 0.10 but Lewis disowns | `docs/uq/examples/lewis_stdout.txt` |
| Q3 | numpy and scipy only; bare import stays light | **pass**; a test holds it | `tests/test_uq.py` |
| Kill 1 | 40 points cannot calibrate → Gnielinski + synthetic replicates, said on the figure | **fired, fallback used, said on the figure** | below |
| Kill 2 | box wider than the measured band by more than the emulation term | **did not fire**: box half-width 19.2 % = band, emulation 0 | `figures.acceptance()` |

Commands and their last output are in `docs/uq/examples/*_stdout.txt`. The test command and
result are at the end.

## Kill criterion 1 fired. What that means

The 40 fully developed NACA reads are 5 numbers. Each Reynolds curve's 8 reads at x/D 10 to 17
are the same digitised asymptote. A 90 % split-conformal interval needs 9 exchangeable
calibration scores; there are 5. Point-level splitting gives a finite number, 1.6 %, whose 20
"held-out" scores are copies of the 5 training residuals. Both attempts are in
`docs/uq/figures/data/uq_1_naca_calibration_attempts.csv`.

So Q1 is the named fallback: Gnielinski as the emulator, nothing fitted, synthetic replicates
from the CSV's own noise model (3 % paper, 5 % digitisation, in quadrature). The figure says so
in its subtitle and side panel. The half-width is 19.2 %, wide because Gnielinski sits 9 to 14 %
above the reads on every home curve. That bias is the validation term; the interval learned it.

Read the entrance result plainly: the interval covers 36 of 45 entrance reads. It under-covers
clearly only on the lowest curve. The home interval is wide enough that the entrance region
mostly fits inside it. The figure's point is not "the interval fails"; it is that the interval
cannot tell an entrance read from a home read, and W-SURR-05 can. The 36 covered reads are
numerically close, not supported by validation evidence for this region.

## Investigation 1: points per curve, and split conformal or jackknife+

| Curve | Fully developed reads | Distinct values |
|---|---|---|
| each of the five (Re 55570, 50600, 41800, 36500, 26400) | 8 | 1 |

Source: `src/physmap/uq/naca.py`, `data_trained_attempt()`; data
`data/naca/cross_validated_fig10.csv` rows 10 to 17 of each curve.

Choice: **neither, on the raw reads; split conformal on synthetic replicates.** Jackknife+ does
not rescue this. Its guarantee is 1 − 2α, so at 90 % it would need 1 − 2α = 0.8, and its
leave-one-out residuals over 5 curves are 5 numbers; over 40 reads they are 40 copies of 5
numbers. The honest unit is the curve, and 5 curves cannot calibrate a 90 % interval by any
conformal method. With synthetic replicates the unit is a replicate, exchangeability between
calibration and test replicates holds by construction, and split conformal is the plain choice:
one calibration set, one order statistic, no refitting, nothing to argue about. Say on any slide
that this tests the noise model plus the closure's home bias, not the interval on a new Re.

## Investigation 2: does the Lewis bank hold per-station predictions

**Yes.** `results/lewis35A_head_to_head/stress_test_lewis_reuse.json`,
`headline_design_M.stations[*].surrogate_prediction`, 12 values, with
`control_gravity_off_truth`, `experiment_Nu`, both error percentages, both materialities and
the flag at θ. That is enough for the figure's points and for the `physmap uq` Lewis example.

It does **not** hold what the emulation interval needs: residuals on runs the surrogate did not
train on. The bank's control errors are in-sample (every deployment input is a training input,
by design). So Q2 refits the design M surrogate twelve times, each without one DOE run, using
the stress test's own `_fit_surrogate` and `_training_rows` (`src/physmap/stress_tests/lewis_reuse.py`,
lines 108 to 126), and banks the per-run scores in `docs/uq/data/uq_2_lewis_emulation_heldout.json`.
Worst held-out error per run: 0.144 % to 0.447 %. The 90 % half-width, one unit per run, k = 12 of
12, is the largest: **0.45 %**. The matched run stays in training, as design M has it.

## Assumptions, every one

| # | Assumption | Where |
|---|---|---|
| 1 | Noise model for replicates: the CSV's `Nu_unc_paper_pct` 0.03 and `Nu_unc_digitization_pct` 0.05, in quadrature, multiplicative, normal | `naca.py`, `noise_sd`, `replicates` |
| 2 | One calibration replicate and one test replicate per read, seeds 1 and 2 | `naca.py` constants |
| 3 | Nonconformity score is the relative error against the value, two-sided | `conformal.py`, `relative_scores` |
| 4 | Entrance reads are scored as read, no replicates | `naca.py`, `compute` |
| 5 | Binomial band is the central 95 % of Binomial(n, 0.9) | `conformal.py`, `binomial_band` |
| 6 | Lewis emulation unit is a run; the half-width is the largest of 12 per-run worst errors | `lewis.py`, `emulation_half_width` |
| 7 | Lewis emulation term is one global half-width, not per station | same |
| 8 | Materiality term is symmetric ±m relative to the prediction; the ablation's sign is not used | `lewis.py`, `compute`; `pbox.py` allows signed |
| 9 | Materiality is applied only where m ≥ θ = 0.10, the illustrative value; below it the term is 0 and the value is still printed | `pbox.py`, `terms_for_point` |
| 10 | Lewis closure status is `inside` with validation 0: the surrogate is a GP, no closure; the gravity-off control (within 0.06 %) sits inside the emulation term | `lewis.py`, `uq_terms` |
| 11 | NACA emulation term is 0: the emulator is the closure | `naca.py`, `uq_terms` |
| 12 | NACA aleatory spread, Re with 2 % relative sd, 50 samples, seed 3, is illustrative; TN-1451 declares none | `figures.py`, `naca_examples`; the samples file's first line |
| 13 | Lewis aleatory: one nominal sample per station, the CDF is a step | `figures.py`, `lewis_examples` |
| 14 | Epistemic terms add as intervals (Minkowski sum) and shift the aleatory CDF; relative box width = sum of term widths | `pbox.py`, module docstring |
| 15 | A term that is not declared is an error; `none` for materiality means not assessed, reported, not zero | `pbox.py` |
| 16 | `bound_kind` behind each closure status: NACA `range` (x/D ≥ 10); Lewis `point` (every deployment input exactly a training condition, design M) | `naca.py`, `lewis.py`, `uq_terms` |

## What Q4 needs (attach the report to the UofA export)

- The report: `docs/uq/examples/naca_report.json` and `lewis_report.json`, one JSON object,
  `points[*].terms[*]` one line per term with `name`, `interval` or `"unbounded"`, `status`,
  `note`; `points[*].closure_status` and `closure_bound_kind` (range, set, point or ratio);
  `points[*].pbox` at the named quantiles; `relative_box_width` and `sum_of_term_widths`
  (equal by construction, a cheap integrity check); the top-level `process` names UQAIS.
- Provenance to carry: the terms file and samples file names and their first-line notes
  (echoed into the report as `samples_file_notes`, `terms_file_notes`), `theta` and
  `theta_note`, and for Lewis the bank's `inputs_sha256`.
- Stable term names to map to UofA evidence kinds: `emulation`, `model_form_validated`,
  `model_form_unvalidated`, `omitted_mechanism`; statuses `declared`, `zero`, `unbounded`,
  `not_applied`, `not_assessed`.
- The report has no run metadata (time, version, host). Add `physmap.__version__` and the
  input files' hashes at the export step, or ask for them in the report; the latter is a
  ten-line change in `pbox.propagate`.

## What Q5 needs (paper section)

- Framing sentence, ready: the ML UQ toolbox quantifies epistemic uncertainty relative to the
  training distribution; W-SURR-05 says whether the model-form term is bounded by any validation
  at all; W-SURR-06 sizes it when a mechanism model exists; `physmap uq` carries each on its own
  line into a p-box.
- Q1 numbers: half-width 19.2 %; home 34 of 40 (band 32–39); entrance 36 of 45 (band 36–44);
  per curve in `uq_1_naca_counts.csv`; flags 45 of 45; detectors 0. Say the fallback and why.
  Do not call it a test on a new Reynolds number.
- Q2 numbers: emulation half-width 0.45 % from 12 held-out runs; interval identical with
  gravity off and on; materiality 0.111, 0.154, 0.195 at θ = 0.10, illustrative; measurement
  against prediction at those stations +20.5 %, +20.1 %, +22.0 %; the rest is the base model's gap
  (facts sheet §6). One run, stations are not cases, no rate.
- Q3: the arithmetic (interval sum, CDF shift, width identity) is in the `pbox.py` docstring;
  the acceptance table is in `docs/uq/README.md`.
- Open design choice to state in the paper: symmetric versus signed materiality interval
  (assumption 8). The signed form, [0, m / (1 − m)] relative to the prediction, is the exact
  correction factor the ablation gives; it is tighter and one-sided.

## What is left

- Q4 and Q5, above.
- A per-station emulation term (assumption 7) if a reviewer asks; the held-out scores per
  x/D are in the bank file already.
- The NACA interval on a genuinely new Re needs more curves than TN-1451 Fig 10 holds.
- `figures.py` is 500 lines in `src/`; if the package should stay lean, move the matplotlib
  parts to `tools/`. Left in `src/physmap/uq/` because the brief put everything new there.

## Test command and result

```
python -m pytest tests/ -q -n auto --dist loadfile -m 'not slow'
python tools/talk_package.py check
python dev/tools/audit_public_surface.py
```

Result on the final tree (Linux x86-64, Python 3.13, numpy 2.5.3, scipy 1.18.1, scikit-learn 1.9.1):

| Check | Result |
|---|---|
| `pytest tests/ -q -n auto --dist loadfile -m 'not slow'` | 446 passed, 3 skipped, 0 failed, 33 minutes on 4 cores |
| `python tools/talk_package.py check` | passed, 412 registered numbers |
| `python dev/tools/audit_public_surface.py` | clean |
| `python -m physmap.uq.figures check` | every table, example and report is what the code gives |

