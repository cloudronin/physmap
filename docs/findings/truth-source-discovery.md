# Truth-source discovery — inputs only

*What an evaluable experimental source must provide, which candidates exist, and their
access status. **No labels, flags, class balance or performance numbers appear here.***

## Why Figure 16 is closed as a route

Figure 16 is a **correlation plot**, not a pointwise benchmark. Its x-coordinate is a
ratio, so even a perfectly calibrated `Ra/Re` cannot separate `Re` from `Gr`; entrance
length is not recoverable per point because the figure aggregates four values of `L/D`;
and the distinct-marker count is indeterminate between roughly 23 and 81. Marker recovery
from it is abandoned. The extraction record is kept in
`surrogate-and-truth-provenance.md` as a finding about the figure, not as data.

## What an evaluable source must provide, per run

| Field | Why |
|---|---|
| Flow direction | Upward/assisting is the case; downward is a different physics problem |
| `Re` | Needed separately, not as part of a ratio |
| `Gr` or `Ra` | Same |
| Geometry and entrance length `L/D` | The entrance region is where the effect lives |
| Measured `Nu` | Local, average, or both — stated which |
| Uncertainty | Per point if it exists; otherwise the stated global figure, labelled as global |

A source missing any of the first four cannot be matched to a CFD condition, however good
its `Nu` values are.

## Candidates

| Source | Regime | Access | Status |
|---|---|---|---|
| **Mohammed & Salman (2008)**, *Exp. Heat Transfer* 21(1):1–23, `10.1080/08916150701647801` | Vertical tube, laminar, upward **and** downward, uniform wall flux, `Re 400–1600`, `Gr 1.1e5–7.4e6` | Closed, T&F, no licence | **The anchor.** Values exist only as figures. Authors contactable — see the drafted request |
| **Mohammed (2008)**, *Energy Conv. & Mgmt* 49(8):2006–2015, `10.1016/j.enconman.2008.02.009` | Companion paper, same rig | Closed, Elsevier TDM | Not yet examined for tabulated data |
| **Behzadmehr, Galanis & Laneville (2003)**, *Int. J. Heat Mass Transfer* 46(25):4823–4833, `10.1016/S0017-9310(03)00323-5` | "Low Reynolds number mixed convection in vertical tubes with uniform wall heat flux" — exactly the regime | Closed, Elsevier TDM | **Unverified whether experimental or numerical.** These authors publish CFD; if numerical it is not independent truth |
| **Joye & Wojnovich (1996)**, *Int. J. Heat Fluid Flow* 17(5):468–473, `10.1016/0142-727X(96)00056-2` | Aiding and opposing mixed convection, vertical tube | Closed, Elsevier TDM | **Boundary condition unverified.** Joye's rigs are typically steam-jacketed, i.e. constant wall *temperature*, not constant flux — which would make it a different case |

No abstract is available for the last two through Crossref, Unpaywall, OpenAlex or
Semantic Scholar, so both flags above are genuinely open questions rather than doubts.

## Routes not yet exhausted

- **NASA NTRS** returned nothing for this regime. **OSTI** returned only modern reactor
  and CO₂ work. A US-government source would solve access *and* redistribution at once, as
  NACA TN-1451 already does in this repository, so it is worth a more careful search than
  one keyword pass.
- The classical vertical-tube mixed-convection literature (Hallman, Scheele & Hanratty,
  Zeldin & Schmidt, Morton) has not been surveyed. Some of it is NACA/NASA-era and may be
  public domain.
- Any source found still needs a redistribution determination before its numbers enter
  this repository.

## Inventory status

**Evaluable measured points in hand: zero.** Unchanged. Nothing above has been obtained,
and no candidate has been confirmed to report per-run conditions with uncertainty.
