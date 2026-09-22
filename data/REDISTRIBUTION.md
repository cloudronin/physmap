# Redistribution determinations

One row per source dataset. **No data file enters this repository without a determination
here.** A citation is attribution; it is not permission, and a provenance manifest does not
create a right that does not exist.

Status as of 2026-09-22.

| Dataset | Source | How values were produced | Terms | Determination |
|---|---|---|---|---|
| `naca_tn1451` | NACA TN-1451 (1947) | Two-reader visual digitisation, Fig 10 | US Government work, public domain | **CLEAR — shipped** |
| `velazquez_sco2` | Velázquez et al. (2026), *Appl. Therm. Eng.* 285:129206 | Exact transcription from supplementary Appendix D, plus our own CoolProp-derived columns | **CC BY 4.0**, publisher-deposited, and Elsevier states the article licence extends to supplementary files | **CLEAR — ships** |
| `forrest` | Forrest et al., *J. Heat Transfer* 138(2):021704 | Visual estimates from Fig 5 | ASME holds copyright and requires permission. The CC BY route **does not exist** — see below | **SHIPS AGAINST PUBLISHER TERMS**, and **NOT benchmark-grade** |
| `casper_hypersonic_transition` | Casper MS thesis (DTIC ADA504177) **and** AIAA 2009-4054 | Figure digitisation, 600-DPI segmentation, two readers | The rows carrying the result are AIAA's, and AIAA prohibits using their content to develop ML models | **SHIPS AGAINST PUBLISHER TERMS** — risk accepted |
| `marineau_hypersonic_transition` | Marineau et al., AIAA 2014-3108 / SAND2014-4326C | Transcribed from Table 3 | No licence — and **no prohibition**. Public-release marked, government-funded, government-hosted | **SHIPS, NOT LICENSED** — facts basis |
| `dirker_water` | Dirker, Meyer & Reid (2018), *Exp. Therm. Fluid Sci.* 98 | Figure digitisation from Figs 17–20 | Elsevier TDM licence **forbids** systematic redistribution | **SHIPS AGAINST PUBLISHER TERMS** — risk accepted |
| `jin_sco2_buoyancy` | Jin et al. (2023), *Ann. Nucl. Energy* 188:109825 | Figure digitisation, two readers; Bu and Bo* recomputed | Same Elsevier terms. No open copy. Authors asked for raw data and **declined** | **SHIPS AGAINST PUBLISHER TERMS** — risk accepted |

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

## Forrest — the CC BY route was checked and does not exist

Worth recording, because it looked available and is not.

ASME's open-access policy does say *"Inclusion will be with ASME © and a CC-BY reuse
license"* — but that sentence sits in their section on **institutional** repositories. The
Forrest accepted manuscript is deposited on OSTI, a **funder** repository. ASME's page does
not extend the grant there.

The deposited PDF settles it. All 57 pages were downloaded and searched: **zero**
occurrences of "creative commons", "CC-BY", "licen", "copyright" or the © symbol. There is
no marking to rely on. Crossref deposits no licence for `10.1115/1.4031646`, and the OSTI
record has no rights field.

So Forrest ships on the same footing as the other unlicensed datasets, not on a CC BY
grant. Anyone repeating this check will find the same absence.

### Forrest also has a data problem, which is not a licensing problem

Its own header:

> `VISUAL ESTIMATES from claude-pair reading the rendered Forrest 2014 Fig 5.`
> `NOT digitized by WebPlotDigitizer. Use ONLY as a resolvability triage check.`

And its benchmark cell is degenerate: `n_train=1`, `n_test=4`, recorded in the matrix as
*"baseline-sufficient by construction, no detector fit"*. The `DO_NO_HARM` outcome is
short-circuited rather than earned — with one training row there is no detector to do
harm with.

It is published so both weaknesses are inspectable rather than hidden behind an outcome
nobody can check. **Re-digitise Fig 5 properly with WebPlotDigitizer before treating this
cell as evidence.** Being legal to publish and being fit to benchmark on are separate
questions, and the registry tracks them on separate axes for that reason.

## Casper — weaker than Marineau, not equal to it

The OSTI copy of AIAA 2009-4054 ([record](https://www.osti.gov/biblio/1142576),
[PDF](https://www.osti.gov/servlets/purl/1142576)) was downloaded and searched across all
20 pages: no copyright notice, **and no public-release marking either**. Marineau carried
"Approved for public release; distribution is unlimited" on all 24 of its pages. Casper
carries neither marking — just silence, which establishes nothing in either direction.

AIAA's prohibition on using their content to develop machine-learning models sits on top,
and a public ML benchmark is squarely what it describes. Shipped as an accepted risk.

## Five datasets ship without a licence. Say so plainly.

**Shipping is not licensing**, and the repository does not pretend otherwise. Two of the
seven shipped datasets carry affirmative permission. Five do not, and they are labelled
that way in the registry, in the benchmark report and here.

### What is actually being redistributed

**Numbers only.** No paper, no figure, no table image, no PDF. Two audits enforce it — one
on the built wheel, one on the checkout — and no document-shaped file is tracked anywhere
in this repository. Copyright bites hardest on expression, and none of the expression
moves.

### Marineau — no permission, and no prohibition

These are measured values transcribed from a published table. Facts are not copyrightable;
nobody owns the fact that transition began at a given station. The document carries no
copyright notice, is marked approved for public release by the controlling office, was
publicly funded, and is hosted on a government server. No term anywhere forbids this.

Ships on the facts basis. The cleanest of the three by a distance.

### Dirker and Jin — shipped against an express term

This is a risk the project accepted, not a determination that the term does not apply. The
distinction matters and is recorded rather than blurred.

Elsevier's TDM licence forbids substantially or systematically reproducing or
redistributing the dataset. That is a **contract** term, so copyrightability is the wrong
axis for it: whether measured values are facts does not release anyone from an agreement
made to obtain access. The clause says "substantially or systematically" precisely to
catch the argument that each extracted number is individually free. Separately, the EU
database right protects substantial extraction from a database built with real investment
— which exists *because* facts are not copyrightable, and which an experimental campaign
is the paradigm case for.

Two further facts, recorded because they are uncomfortable rather than despite it:

- The provenance files describe 500-DPI crops, two independent readers, per-marker reads
  and ±18% read uncertainty. That is documented systematic extraction. It would be
  inconsistent to publish provenance that precise and characterise the same act as casual
  recall.
- Jin's authors were asked for the raw data and declined.

Mitigations that are real but partial: only numbers are redistributed; for Jin, `Bu` and
`Bo*` are recomputed from the paper's own equations, so part of that file is derived work
rather than extraction; and both are removed on objection.

### Removal on objection

Any rights holder who objects gets the data removed. Open an issue at
<https://github.com/cloudronin/physmap/issues>; see NOTICE. This is a genuine commitment
and it is also, honestly, the fallback the decision rests on.

## Velázquez — the supplementary file is covered

The question was whether the article's CC BY grant reaches the supplementary file the
values were taken from, rather than only the article text. It does, and Elsevier says so
in terms:

> "If you provide your data as supplementary files to your paper and the paper is Open
> Access, the data will follow the same license as you choose for the article."
> — [Elsevier support](https://www.elsevier.support/publishing/answer/which-license-should-i-select-when-posting-my-research-data)

Supporting facts:

- Crossref deposits `creativecommons.org/licenses/by/4.0` at `content-version=vor` for
  `10.1016/j.applthermaleng.2025.129206`, delay 0.
- `mmc1.docx` carries the article's own title and author list, and is served from
  Elsevier's CDN under the article's pii — it is a component of the published article,
  not a separate work.
- The values are transcribed verbatim from Appendix D, Tables D1–D28: 28 tests × 20
  stations = 560 points, the authors' own reduced data with their stated per-point
  uncertainties. Nothing was read off a plot.
- The file itself carries no licence marking, which is why the determination rests on the
  publisher's stated scope rather than on the file.

**CLEAR under CC BY 4.0.** Ships with attribution and a CC BY notice.

## Marineau — CORRECTED to blocked

**An earlier version of this file recorded Marineau as CLEAR. That was wrong, and the
reasoning behind it was wrong in a way worth naming.**

It rested on the document carrying no copyright notice and being stamped "Approved for
public release; distribution is unlimited" on all 24 pages. Those facts are true — 77,283
characters were searched and there are zero copyright assertions. But they do not do the
work that was asked of them.

**A public-release marking is a security and export determination, not a copyright
licence.** It says the controlling office does not object to the document being seen. It
says nothing about who may copy it. And since Berne, copyright has not required notice, so
the absence of one establishes nothing either.

OSTI states the position directly:

> "public access does not connote that the materials on this or other DOE websites are in
> the public domain"

and provides access "under the authority of the government's retained license to
distribute publications" — a distribution right held by OSTI, not a licence granted to
readers — while users remain "solely responsible for complying with applicable copyright
law restrictions, including seeking the permission of the copyright owners."
([OSTI disclaimer](https://www.osti.gov/disclaim))

The remaining routes were checked and all close:

- **17 USC §105 (US Government work).** Does not apply. Sandia was operated by a wholly
  owned Lockheed Martin subsidiary under DOE contract `AC04-94AL85000`, and several AEDC
  authors are Aerospace Testing Alliance, a contractor. Contractor-authored works are not
  government works.
- **An explicit marking.** OSTI honours a "U.S. Government Work" designation where one
  exists. This document does not carry one, and the OSTI record has no rights or licence
  field at all.
- **Facts are not copyrightable.** Available in principle, but this is the same position
  rejected for Dirker and Jin. Using it here and not there would not be a determination;
  it would be a preference dressed as one.

**BLOCKED.** Excluded from this release. The route to clearing it is written permission
from Sandia and AEDC, which is not a four-week task.

## The Elsevier exemption does not reach the digitised sets

The copy at **OSTI 1145775** ([record](https://www.osti.gov/biblio/1145775),
[PDF](https://www.osti.gov/servlets/purl/1145775)) was downloaded and searched in full:
77,283 characters across 24 pages.

- **Zero** occurrences of "copyright", "©", "(c) 20" or "all rights reserved".
- **"Approved for public release; distribution is unlimited"** on every one of the 24
  pages, including page 1 above the title.
- Crossref has no licence deposited for `10.2514/6.2014-3108`, which is consistent with
  AIAA never having asserted one over this version.
- Funded by the OSD TRMC HSST program, with Sandia under DOE/NNSA contract DE-AC04-94AL85000.

The banked CSV columns — `ST_m`, `dST_m`, `ReinfN`, `ST_Xsw`, `ReinfST`, `ReST`,
`RethetaST` — match Table 3 "Transition Parameters at 0-deg AoA" on page 8 exactly, and
the values are transcribed from that table rather than read off a plot.

**Why the AIAA site terms do not reach this.** AIAA's prohibition on using content to
train or develop machine-learning models is a term of use for *their* platform, ARC. This
copy was obtained from a US Government repository, and it asserts no copyright of its own
while affirmatively authorising unlimited distribution on every page.

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
- Marineau's paper number **AIAA 2014-3108** (DOI `10.2514/6.2014-3108`, SAND2014-4326C)
  is recorded nowhere, and the seed corpus carries a wrong title. The correct title is
  *Mach 10 Boundary-Layer Transition Experiments on Sharp and Blunted Cones*; Crossref
  appends "(Invited)". Authors: Marineau, Moraru, Lewis, Norris, Lafferty (AEDC White
  Oak); Wagnild, Smith (Sandia).
- Dirker records a ScienceDirect pii but not the DOI `10.1016/j.expthermflusci.2018.06.017`.

## Consequence for the public benchmark

**All seven benchmark vehicles ship.** Two under a licence — `naca_tn1451` (public domain)
and `velazquez_sco2` (CC BY 4.0). Five without one: `marineau_hypersonic_transition` on a
facts basis with no prohibition attached, and `forrest`, `casper_hypersonic_transition`,
`dirker_water` and `jin_sco2_buoyancy` against express publisher terms.

One further caveat that is not about licensing: **`forrest` is not benchmark-grade**, by
its own header and by the degeneracy of its cell.

The full seven-vehicle result is still reported — every vehicle's outcome and provenance
appears in the benchmark report and on the slides. What changes is what the public
checkout can *rerun*. The report names the two it reruns and the five it does not, and the
command must never be presented as reproducing all seven.
