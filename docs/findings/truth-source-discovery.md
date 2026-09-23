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

## Brown & Gauvin — a candidate that is **not** interchangeable

| | |
|---|---|
| **Part I (aiding flow)** | Brown, C. K. & Gauvin, W. H. (1965), *Combined free-and-forced convection: I. Heat transfer in aiding flow*, **Can. J. Chem. Eng. 43(6):306–312**, `10.1002/cjce.5450430608` |
| **Part II (opposing flow)** | Same issue, 313–318, `10.1002/cjce.5450430609` |
| Access | **Closed.** Wiley terms of use, no open copy in Unpaywall or Semantic Scholar, no abstract available. Part I is cited 34 times |

**Part I is aiding flow**, which is the right direction for the NAFEMS case.

### Why it needs its own CFD case

Mohammed & Salman cite it directly, and their own description already separates the two
experiments:

> "The average heat transfer results were compared with vertical tube of Brown and Gauvin
> [25] **at constant wall temperature boundary condition** and for **stainless steel tube
> with (L/D = 23)**"

| | Mohammed & Salman | Brown & Gauvin |
|---|---|---|
| Wall boundary condition | **Constant heat flux** | **Constant wall temperature** |
| `L/D` | 30 | **23** |
| Tube | Aluminium, D = 30 mm | Stainless steel |
| Working fluid | Air | **Not established** |

A constant-temperature wall and a constant-flux wall are different boundary-value
problems, and `L/D` differs too. **Brown & Gauvin cannot be substituted into the existing
CFD case.** Using it means building and verifying a second case with its own geometry and
its own wall condition. That is legitimate work, and it is not free.

### What the paper contains is unknown

Whether it reports per-run conditions, measured `Nu` values, or any uncertainty **cannot
be determined without obtaining it**. Two things are worth stating in advance rather than
discovering later:

- Mohammed & Salman quote it as a **correlation**
  (`Nu = 1.75 (μb/μw)^0.14 [Gz + 0.012(Gz·Gr^(1/3))^(4/3)]^(1/3)`), which is evidence the
  paper presents fitted results — not evidence that it lacks tabulated data, but a reason
  not to assume otherwise.
- It is a **1965 paper**. Formal uncertainty analysis was not standard practice then, and
  a stated per-run uncertainty may simply not exist. That is a risk to the plan, not a
  reason to skip the source.

**Status: candidate, unexamined, requires its own CFD case.**

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
