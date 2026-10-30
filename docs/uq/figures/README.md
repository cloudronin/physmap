# UQAIS figures — generated, do not edit

UQAIS, Uncertainty Quantification for AI Surrogates: the uncertainty a surrogate inherits from
the physics it learned, kept on its own lines. Built by `python -m physmap.uq.figures build` from committed records only. Each figure ships
as an editable vector SVG and a 1920-pixel PNG, with a table twin in `data/` holding every
plotted value. Blue is gravity off and orange is gravity on; the only dashed line would be an
illustrative threshold. Light theme only.

## A 90 % interval that cannot see x/D (NACA TN-1451)

![A 90 % interval that cannot see x/D](uq_1_naca_coverage.png)

The emulator is the Gnielinski correlation, which takes Re and Pr only; nothing was fitted. Its
split-conformal interval, nominal 90 %, has half-width 19.2 % and was calibrated on 40 synthetic
replicates of the 40 fully developed reads (x/D ≥ 10) under the digitisation's declared noise
model (3 % paper reproducibility, 5 % digitisation floor, in quadrature). Synthetic replicates
because the 40 reads are 5 values, one per Reynolds curve, and 5 exchangeable units cannot
calibrate a 90 % interval (it needs 9) — the first kill criterion fired and this is its named
fallback. On fresh test replicates of the fully developed reads the interval covers 34 of 40
(binomial band 32–39 at 90 %); on the 45 entrance reads, 36 of 45 (band 36–44), per curve in
each panel and in `data/uq_1_naca_counts.csv`. x/D is not an emulator input, so every entrance
point is in-distribution to the interval and to the input-based detectors, which fire on 0;
PhysMAP's W-SURR-05 flags 45 of 45 (orange rings). The points the interval covers in the
entrance region are numerically close, but not supported by validation evidence for this region.

- Files: [`uq_1_naca_coverage.svg`](uq_1_naca_coverage.svg) · [`uq_1_naca_coverage.png`](uq_1_naca_coverage.png)
- Plotted values: [`data/uq_1_naca_coverage.csv`](data/uq_1_naca_coverage.csv); counts: [`data/uq_1_naca_counts.csv`](data/uq_1_naca_counts.csv); the interval: [`data/uq_1_naca_interval.csv`](data/uq_1_naca_interval.csv); the data-trained attempts: [`data/uq_1_naca_calibration_attempts.csv`](data/uq_1_naca_calibration_attempts.csv)
- Source data: [`data/naca/cross_validated_fig10.csv`](../../../data/naca/cross_validated_fig10.csv)

## The interval that does not move, and the term that opens (Lewis 35A)

![The interval that does not move, and the term that opens](uq_2_lewis_materiality.png)

Design M's surrogate, a Gaussian process on gravity-off CFD, carries an emulation interval of
±0.45 %: split conformal at nominal 90 % with one unit per held-out run, over the 12 DOE runs
each refitted without (`data/uq_2_lewis_heldout_runs.csv`). The interval depends on Re, Pr and
x/D only; those are identical with gravity off and on, so the interval is identical, and the
gravity-off control sits inside it at every station. What opens with gravity on is W-SURR-06's
materiality from the matched ablation, shown at the illustrative θ = 0.10: 0.111 at x/D 67.55,
0.154 at x/D 101.69, 0.195 at x/D 135.84, the bank's values. θ is not locked; no flag here is a
verdict. Hollow markers are the three stations Lewis disowns. Materiality comes from the matched
CFD pair, not from the measurement; the remaining gap to the measurement is the base model's.

- Files: [`uq_2_lewis_materiality.svg`](uq_2_lewis_materiality.svg) · [`uq_2_lewis_materiality.png`](uq_2_lewis_materiality.png)
- Plotted values: [`data/uq_2_lewis_stations.csv`](data/uq_2_lewis_stations.csv); the interval: [`data/uq_2_lewis_interval.csv`](data/uq_2_lewis_interval.csv); held-out runs: [`data/uq_2_lewis_heldout_runs.csv`](data/uq_2_lewis_heldout_runs.csv)
- Source data: [`results/lewis35A_head_to_head/stress_test_lewis_reuse.json`](../../../results/lewis35A_head_to_head/stress_test_lewis_reuse.json), [`docs/uq/data/uq_2_lewis_emulation_heldout.json`](../data/uq_2_lewis_emulation_heldout.json)
