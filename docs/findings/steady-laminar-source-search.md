# Searching for a demonstrably steady laminar experiment

**Why this search exists.** The Lewis assessment establishes that a run can be well measured
or demonstrably laminar, but the two run opposite. A source is needed that gives individually
identified operating conditions, measured heat transfer, **and positive evidence of steady
laminar flow** — not laminarity assumed from a Reynolds number.

**Verification status is marked per source.** Two were read directly; the rest come from a
literature sweep and are marked unverified. An unverified entry is a lead, not a finding.

## The seam the literature splits along

Nobody has published a vertical-tube, uniform-heat-flux, buoyancy-aided experiment that
simultaneously tabulates per-run `Re`/`Pr`/`Ra`, reports measured `Nu`, **and** demonstrates
steadiness with data. Sources have either the steadiness evidence or the reproducible tables.

There is a physical reason, and it is the same one the Lewis work ran into: the vertical
aiding-flow geometry is the one that loses steadiness partway down the tube.

## Read directly

### Hallman, NASA TN D-1104 (1961) — the closest geometric match

*Experimental Study of Combined Forced and Free Laminar Convection in a Vertical Tube.*
NASA TN D-1104, Lewis Research Center, December 1961.
<https://ntrs.nasa.gov/citations/19980235517>

**Verified by reading the PDF.** Vertical circular tube, water, uniform wall heat flux by AC
resistance heating, L/D ≈ 192, preceded by a 115-diameter approach section so the inlet
profile is fully developed. Both aiding and opposing flow. US Government work.

It does the one thing Lewis does not — **it separates its steady runs from its unsteady ones**:

> The data which are believed to be fully developed and which were steady (nonfluctuating)
> are shown in figure 9.

and characterises the departure directly:

> A transition from steady laminar flow to a slow, apparently random, eddy flow was observed
> on some runs. This was evidenced by wall temperature fluctuations appearing on the upper
> portions of the heated tube.

It also states an uncertainty: `Nu = 6.12 ± 0.25`, about 4 %, from a detailed error analysis
on one run.

**What blocks it: there is no run table.** Runs are named and plotted with local Rayleigh
numbers annotated, but the tabulated conditions live in Hallman's 1958 Purdue thesis, which
was not reachable. Per-run `Re` and `Pr` would have to be digitised from the figure abscissa.

**Its transition correlation does not transfer to Lewis.** See the Lewis assessment: it is
stated valid for `1 < Re·Pr/(2x/D) < 20` and Lewis's stations sit at 30–488.

### Barozzi, PhD thesis, City University (1993) — the most complete package

*Combined convection and other effects in heat transfer in horizontal flows.*
<https://openaccess.city.ac.uk/id/eprint/16971/>

**Verified by reading the PDF** — title, institution, and the steadiness criterion below were
checked against the document. Same City Research Online policy as Lewis.

Horizontal circular duct, 3 m long, 16 mm bore copper, uniform peripheral electrical heating,
water, wall temperatures at 12 axial stations. Ten named runs (PA–PE, FA–FE) with entry and
exit values of `Re`, `Pr`, `Ra_q`, `Gr_q` tabulated. Local `Nu` at every station with the
reduction rule stated. Built deliberately to generate CFD comparison data.

**Its steadiness evidence is quantified, which makes it the strongest found:**

> steady state conditions are stated to be reached when four complete measurement cycles of
> wall and fluid temperatures, executed at intervals of two minutes or more (up to 5), give
> unchanged results within 0.1 °C, the maximum deviation from the average of the four
> readings is within 0.03 °C, and the wall temperature variations are randomly positive and
> negative from one sample to another

An accepted data-logger sequence is reproduced. Stated uncertainty: ±16 % at 95 % coverage
for the generality of results, rising to ±28 % near the entrance.

**Two honest caveats.** The *temporal steadiness* is measured; *laminarity* is argued from
`Re ≤ ~1000` plus an assumed stability limit near `Ra_q ~ 6e5` — and runs FC and FD sit at
`Ra_q ≈ 5e6`, roughly eight times above it, with `Nu` rising downstream. And the geometry is
**horizontal**: buoyancy acts across the flow and drives secondary circulation rather than
aiding acceleration, so it is a different mechanism from the NAFEMS case.

## Leads, not yet verified

| Source | Why it is interesting | Why it is not settled |
|---|---|---|
| **Barozzi, Dumas & Collins (1984)**, *Int. J. Heat Fluid Flow* 5(4):235–241, doi 10.1016/0142-727X(84)90060-2 | The vertical-tube water counterpart to the 1993 thesis, same author. Its abstract reports **a transition criterion derived from measured local `Nu`** in exactly the target geometry — the single thing most needed | Paywalled, not retrieved. **Highest-value item to obtain.** Note this is the correct citation for what earlier notes called "Barozzi, Dumas & Stieglitz" |
| **Morcos (1974)**, Iowa State PhD, Retrospective Theses 5996 | ~140 heat-transfer runs fully tabulated with Run/ṁ/q/`Nu`/`Ra`/`Pr`/`Re` — the richest data package found. Flat `Nu`-vs-`x` means no tail-up at the measuring station | Horizontal. **Laminarity is assumed from `Re ≤ ~1756`** with no fluctuation record or transition criterion. What was verified is fully-developed flow, not laminar flow |
| **Lagana & Baliga (2012)** HEFAT, and Lagana (1996) McGill MEng | Dye visualisation over the entire heated length — the only such evidence in this literature. Reports that the **vertical** runs pass through a wave-like unsteady zone, which is direct support for the Lewis finding | **Reports no Nusselt number**, and the thesis states the inner-wall heat flux cannot be reduced without further work. Unusable as truth |
| **Everts et al. (2020)**, *Appl. Therm. Eng.* 179:115696 | Vertical tube, water, constant flux, both directions, L/D 886, with a proper 95 % `Nu` uncertainty analysis | Laminarity asserted from Reynolds number; range extends to `Re` 2300; results given as continuous curves rather than named runs |

**Cleared off the list:** Kemeny & Somers (1962) — wall temperatures fluctuate downstream,
transition above bulk `Re` 200. Zeldin & Schmidt (1972) — velocity profiles only, `Nu` is
predicted not measured, isothermal wall, essentially one condition. Scheele & Hanratty (1962)
— a transition criterion, not a `Nu` source. Mohammed (2008) — paywalled, and no laminar
verification of any kind.

## Where this leaves the benchmark

**Lewis is retained as a documented limitation, not deleted.** The assessment stands: it has
the richest per-run conditions of anything reachable, and its value is now partly that it
shows *how* the vertical geometry fails the steadiness requirement.

**No source is strong on all criteria**, so nothing here changes the metrics position: they
stay closed. The two moves that would change it are obtaining Barozzi, Dumas & Collins
(1984), whose measured-`Nu` transition criterion is exactly the missing screen, and deciding
whether the horizontal geometry of Barozzi's thesis is an acceptable substitute — which is a
question about whether a cross-flow buoyancy mechanism tests the same thing, and is the
owner's call, not a technical one.
