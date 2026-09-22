# Redistribution determinations

One row per source dataset. **No data file enters this repository without a determination
here.** A citation is attribution; it is not permission, and a provenance manifest does not
create a right that does not exist.

Status as of 2026-09-22.

| Dataset | Source | How values were produced | Terms | Determination |
|---|---|---|---|---|
| `naca_tn1451` | NACA TN-1451 (1947) | Two-reader visual digitisation, Fig 10 | US Government work, public domain | **CLEAR — shipped** |
| `velazquez_sco2` | Velázquez et al. (2026), *Appl. Therm. Eng.* 285:129206 | Exact transcription from the supplementary tables, plus our own CoolProp-derived columns | **CC BY 4.0 on the version of record**, publisher-deposited | **CLEAR — not yet shipped** |
| `forrest` | Forrest et al., *J. Heat Transfer* 138(2):021704 | Visual estimates from Fig 5 of the **version of record** | ASME holds copyright. VoR is free-to-read with no reuse licence. A CC-BY accepted manuscript exists on OSTI PAGES | **BLOCKED as digitised** — see decision 1 |
| `casper_hypersonic_transition` | Casper MS thesis (DTIC ADA504177) **and** AIAA 2009-4054 | Figure digitisation, 600-DPI segmentation, two readers | Thesis: unlimited distribution. **The rows carrying the result are from the AIAA paper** | **SPLIT** — see decision 2 |
| `marineau_hypersonic_transition` | Marineau et al., AIAA 2014-3108 | Transcribed from Table 3 | Unverified. Copyright line unread; source PDF not banked | **UNRESOLVED** — see decision 3 |
| `dirker_water` | Dirker, Meyer & Reid (2018), *Exp. Therm. Fluid Sci.* 98 | Figure digitisation from Figs 17–20 | Closed access. Crossref carries **only** the Elsevier TDM licence | **BLOCKED pending policy** — see decision 4 |
| `jin_sco2_buoyancy` | Jin et al. (2023), *Ann. Nucl. Energy* 188:109825 | Figure digitisation, two readers; Bu and Bo* recomputed | Closed access, no open copy anywhere. TDM licence only | **BLOCKED pending policy** — see decision 4 |

## What was verified directly

Crossref licence records were queried directly for all three Elsevier DOIs:

- `10.1016/j.applthermaleng.2025.129206` returns `creativecommons.org/licenses/by/4.0`
  at `content-version=vor`, delay 0. This is an affirmative, publisher-deposited grant on
  the published article.
- `10.1016/j.expthermflusci.2018.06.017` returns the Elsevier TDM user licence only.
- `10.1016/j.anucene.2023.109825` returns the TDM licence plus STM article-sharing
  policies. No Creative Commons licence on either.

The [AIAA rights and permissions policy](https://aiaa.org/publications/publish-with-aiaa/rights-and-permissions/)
states that no part of ARC content may be used to train, fine-tune, develop or improve any
artificial intelligence or machine learning model, including text-and-data-mining tools,
without prior written permission, commercial or not.

Whether that clause reaches these two datasets turns on a question of fact that is worth
separating out: **it is a site term, and it binds users of ARC.** The Casper paper was
obtained from OSTI, a government repository. The Marineau PDF's origin is not recorded. If
neither came from ARC, the site terms are not the operative restriction and the question
falls back to ordinary copyright in the underlying paper.

## The Elsevier exemption does not reach the digitised sets

Elsevier's permissions guidance exempts "creating an original figure or table from data or
factual information that was **not previously in figure or table format**". Both Dirker and
Jin were read off published figures, so the one clause that could exempt them is worded to
exclude exactly this case. The TDM licence under which the articles are deposited forbids
systematic redistribution of the dataset outright.

`velazquez_sco2` is different in kind, not merely in degree: those values were transcribed
from the authors' own supplementary tables under a CC BY grant, never read off a plot.

## Citation corrections to apply before any of these ship

Found while establishing provenance. All are factual errors in the current metadata:

- Casper ADA504177 is a **Master's thesis**, not a PhD thesis.
- Forrest is **2015/2016** (DOI `10.1115/1.4031646`); the recorded 2014 is the SAND report
  year. No DOI is recorded in the vehicle spec.
- Marineau's paper number **AIAA 2014-3108** is recorded nowhere, and the seed corpus
  carries a wrong title for it.
- Dirker records a ScienceDirect pii but not the DOI `10.1016/j.expthermflusci.2018.06.017`.

## Consequence for the public benchmark

Two of the seven benchmark vehicles are currently clear: `naca_tn1451` and
`velazquez_sco2`. A public v0.4 matrix built today would carry two cells, not seven, and
would have to say so rather than presenting itself as the benchmark described in the
runbook.
