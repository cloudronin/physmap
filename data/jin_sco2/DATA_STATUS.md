# Jin sCO₂-Buoyancy Vehicle — DATA STATUS (single source of truth for provenance tier)

**Rule (updated 2026-06-10):** **author raw data is NOT forthcoming** — figure-digitization is the **final data** for
this vehicle. The truth ceiling is therefore **human-confirmed two-reader digitization** at figure-read precision —
the same standard the project accepted for Casper and Velázquez. The Fig-17 A6(ii) cell is the **human-confirmed
cell**; the q/G families are reader-2-verified. The build runs at this precision and the banked evidence Claim stays
**bound-only / `claimed`** (the agent never sets `confirmed`/`human_confirmed`; promotion would need an independent
measured source). `AUTHOR_DATA_REQUEST.md` is **RETIRED**.

## Tier 1 — HUMAN-CONFIRMED (figure-digitization tier)
- **`jin_fig17_htc_reconciled.csv`** — Fig 17(b), the A6(ii) cell (upward vs downward HTC at matched G=443, P=7.8,
  T_in=22, q=43.9). Agent reader-1 + agent reader-2 (17/17 agree, max diff 0.40) + **human visual confirmation**
  (user vs Fig 17b, 2026-06-10). The differentiator signal — up/down divergence 6.2× at matched inputs — is robust.
  Still a published-plot digitization (±0.3 read-uncertainty), not author-supplied per-point data.

## Tier 2 — READER-2-VERIFIED, PROVISIONAL (figure-digitization tier)
- **`jin_fig7_10_families_htc_corrected.csv`** — Fig 7(b) q-family extremes (q=29 benign, q=60.3 deploy) + Fig 10(b)
  G-family extremes (G=452 benign, G=347 deploy). Agent single-reader pass **FAILED** verification; rebuilt from the
  user's reads and **re-checked by the user** (2026-06-10, holds; 2 within-tolerance micro-flags applied). Provisional
  placeholders — usable to scaffold/sanity-check the gates, **not** as confirmed truth.
- Superseded failed pass: `jin_fig7_10_families_htc_reader1.csv` (marked DO-NOT-USE; kept as the audit trail).

## Tier 3 — NOT ACQUIRED (and not needed for the differentiator)
Author data is not forthcoming, so these are simply not used. **None is required for the built differentiator:**
- **Bo\* / Bu are RECOMPUTED, not acquired** — derived from the operating point (Jin Eqs. 20–21) + CoolProp and
  **cross-checked against the paper's own Fig 8/10c-d values** (`g5g6g7_corpus_bound.py`; q=29 8.2 vs ~8e-7, q=60.3
  17 vs ~15e-7, G=347 20.5 vs ~20e-7). Computing Bo\*/Bu from the operating point is the corpus's own job per the
  construction spec; author-supplied Bo\*/Bu would only have been a redundant cross-check.
- Fig 11 low-G family + the tangled middle curves (Fig 7 q=35.6/39.4/47.7; Fig 10 G=377.6/417.4) — not reliably
  eye-digitizable; **NOT needed** (the differentiator is built on the tier-1 direction cell + the tier-2 family extremes).
- Precise per-point truth at the authors' ±9.3% would only **sharpen** the G3 magnitude, not change any gate verdict
  (the 6.2× signal dwarfs the figure-read ±0.3).

## Gate consequence — BUILT
G1 is **complete for the differentiator**: the A6(ii) direction cell is human-confirmed (tier-1) and the benign/deploy
family extremes are reader-2-verified (tier-2), which is sufficient to train the surrogate on benign and test on deploy.
**G2–G7 all PASS at figure-digitization precision → `BUILT_DIFFERENTIATOR` (digitization-tier)** (`g2g3_result.json`,
`g4_result.json`, `g5g6g7_result.json`; summary in `GATES_DRY_RUN.md`). The result is final at this precision; only the
quantitative magnitude carries figure-read uncertainty, and the banked Claim stays bound-only/`claimed`.
