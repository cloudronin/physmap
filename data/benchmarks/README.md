# Benchmark banks

Each folder is one version of the seven-vehicle benchmark's committed result. The code reads
exactly one of them — `BANK_VERSION` in `src/physmap/benchmarks/benchmark_v0_4.py` — and
`physmap benchmark run` recomputes every cell and checks it against that one.

| Version | Folder | Status | What it is |
|---|---|---|---|
| **0.4.1** | [`v0_4_1/`](v0_4_1/) | **current** | The matrix, its home baseline and its architecture axis, with the NACA vehicle reading the two-reader record of Fig 10 |
| 0.4 | [`v0_4/`](v0_4/) | historical, kept for audit | The original matrix (2026-09-22), and the home baseline and architecture axis derived from it (2026-09-25). Its NACA row came from an automated read later found invalid |

Why 0.4.1 exists, what it changed and how it was checked:
[`../naca/CORRECTION_v0_4_1.md`](../naca/CORRECTION_v0_4_1.md). Only the NACA cell differs;
the other six cells are identical, and `tests/test_home_baseline.py` holds them so and pins
the 0.4 files' fingerprints. A historical bank is never edited: it is the record of what was
claimed, and when.

Each folder holds:

- `matrix_full_seven.json` — per vehicle: counts, verdicts and thresholds. No third-party
  measurement values.
- `home_baseline.json` — derived beside the matrix: how often each vehicle's surrogate is wrong
  at home and when deployed, labelled by how the home error was obtained.
- `architecture_axis.json` — three model types per flagged vehicle, each gated on its held-out
  error; `physmap benchmark architectures` recomputes it (PyTorch, about 20 minutes).
