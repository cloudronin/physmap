# NACA TN-1451 Fig 10 — the benchmark's source data, corrected (bank v0.4.1)

Recorded 2026-09-25. The benchmark's `naca_tn1451` vehicle read a dataset that does not
represent the figure it was taken from. From bank v0.4.1 it reads the two-reader record of
the same figure. The original file and the original bank are kept unchanged, for audit; they
are history, not current evidence.

## What was wrong

Bank v0.4 read [`wpd_fig10.csv`](wpd_fig10.csv). Its rows are labelled "algorithmic
WPD-equivalent": an automated read of a render of NACA TN-1451 (1948), page 37, Figure 10,
recording each point's pixel position. Mapped back onto that render (4717 × 2840 px), the read
fails in two independent ways.

- **Its axis calibration is wrong.** It places fc = 0 and x/D = 0 correctly (pixel y 2547.5,
  pixel x 1379), but it anchors x/D = 17 at pixel x 3214 — which is the figure's x/D = 13
  gridline; x/D = 17 is at x 3782 — and fc = 20 at pixel y 246, above the plotted grid; fc = 20
  is at y 1134. Measured from the figure's own gridlines: the true x/D is 0.76 × the recorded
  value (plus 0.03), and the true fc is 1.63 × the recorded value.
- **Its points are not on the data.** Placed on the figure, the recorded points sit on gridline
  crossings and on the legend's text, not on the plotted symbols. Row 76 — recorded x/D 16.924,
  fc 1.16, Nu 11.02 — is the gridline crossing at x/D 13, fc 2. Rows 1–5 — recorded x/D ≈ 1.4,
  fc 17.18 down to 11.10, the "entrance peaks" — are gridline crossings at x/D 1, fc 28 down to
  18, above every plotted curve.

Its own notes add a third hazard: each point's Reynolds number is assigned by the rank of its
fc value.

## How it was verified

- **The original figure.** On page 37, the Re = 55,570 curve (symbol ρ) levels off at fc ≈ 10–11
  for x/D ≥ 10, which is Nu ≈ 95–104. Nothing is plotted near fc = 1.2 at x/D 17. The page
  render and the automated read's overlay on it are kept with the research records; they are
  not redistributed here, under this repository's numbers-only rule.
- **Both independent digitisation records of the same figure.** The two-reader record,
  [`cross_validated_fig10.csv`](cross_validated_fig10.csv) — two readers reading
  independently, their values agreed within visual precision — and an earlier single-reader
  per-marker read, kept with the research records. Both put Re = 55,570 at fc 11.0–11.7 for
  x/D ≥ 10, which is Nu 104–111.

So the recorded Nu = 11.02 is not a measurement, and the rest of the automated read cannot be
trusted either: its calibration and its choice of points are both wrong, so it cannot be
patched row by row.

## The correction

From bank v0.4.1, [`../vehicles/naca_tn1451.yaml`](../vehicles/naca_tn1451.yaml) reads
`cross_validated_fig10.csv`: 85 rows, five Reynolds-number curves at x/D 1–17 — 40 fully
developed rows (x/D ≥ 10) and 45 entrance rows. It is the same record the x/D example
(`examples/naca_entrance_region.py`) has always used. The noise model is unchanged — 3 %
paper reproducibility, 5 % digitisation floor — and so are the thresholds derived from it.

## What changed in the bank

Only the NACA cell. The other six cells of the matrix are identical to v0.4, and a test holds
them so (`tests/test_home_baseline.py`).

| NACA, at percentile 99 | v0.4 (automated read) | v0.4.1 (two-reader read) |
|---|---|---|
| training rows / test rows | 29 / 47 | 40 / 45 |
| wrong predictions, caught only by PhysMAP | 20 of 20 | 9 of 9 |
| accurate predictions flagged anyway | 24 | 19 |
| home error (Gnielinski, never fitted to these rows) | 13 of 29 | 0 of 40 |
| deployment error | 20 of 47 | 9 of 45 |
| outcome class | PHYSMAP_WINS | PHYSMAP_WINS |

Every figure, table and sentence in the README and the talk package was regenerated from
v0.4.1.

## What was kept, unchanged

- [`wpd_fig10.csv`](wpd_fig10.csv) — the automated read. Not current evidence.
- [`../benchmarks/v0_4/`](../benchmarks/v0_4/) — the original matrix (2026-09-22), and the home
  baseline and architecture axis derived from it (2026-09-25). Their fingerprints are pinned
  by `tests/test_home_baseline.py`. To rerun them exactly, check out release `v0.2.4`.
