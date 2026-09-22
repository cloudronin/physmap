"""The seven benchmark vehicles, and which of them this checkout can rerun.

Two different things are tracked here and they must not collapse into one:

  **The result** — all seven vehicles ran, and every outcome is reported. The banked
  matrix in `data/benchmarks/v0_4/` holds counts, verdicts and thresholds computed from
  our own runs. It contains no third-party measurement values.

  **The rerun** — only vehicles whose source data is cleared for redistribution ship
  their CSV, so only those can be recomputed from this checkout.

A reader must be able to see, per vehicle, both the outcome and whether the number in
front of them was recomputed here or read from the bank. The public command reruns two
of seven and says so; it is never described as reproducing the benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "Redistribution",
    "DataQuality",
    "triage_only_ids",
    "licensed_ids",
    "unlicensed_shipped_ids",
    "VehicleRecord",
    "VEHICLES",
    "rerunnable_ids",
    "banked_only_ids",
]


class Redistribution(str, Enum):
    """Why each vehicle's source data does or does not ship.

    Three of these mean "it ships", and they are kept apart on purpose. A reader
    deciding whether to reuse this data needs to know whether it rests on a licence,
    on the absence of a prohibition, or on a risk the project chose to carry. Folding
    them into one CLEAR would hide exactly the distinction that matters.
    """

    #: Affirmative permission exists: public domain, or an explicit open licence.
    CLEAR = "clear"

    #: No permission and no prohibition. Shipped on the position that measured values
    #: are facts. Defensible, and not backed by a grant.
    NO_LICENCE_FACTS_BASIS = "no_licence_facts_basis"

    #: Shipped DESPITE an express publisher term forbidding redistribution. A risk the
    #: project accepted with its eyes open, not a determination that the term does not
    #: apply. Removed on objection.
    AGAINST_PUBLISHER_TERMS = "against_publisher_terms"

    #: Does not ship, by project decision.
    EXCLUDED_BY_DECISION = "excluded_by_decision"


class DataQuality(str, Enum):
    """How good the source values are. INDEPENDENT of whether they may be redistributed.

    A dataset can be perfectly legal to publish and still be unfit to benchmark on.
    Collapsing the two would let a licence clearance launder a data-quality problem.
    """

    #: Properly digitised or transcribed, with stated uncertainty.
    BENCHMARK_GRADE = "benchmark_grade"
    #: The file itself says not to trust it as truth. Published so the weakness is
    #: inspectable rather than hidden behind an outcome nobody can check.
    TRIAGE_ONLY = "triage_only"


@dataclass(frozen=True)
class VehicleRecord:
    vehicle_id: str
    domain: str
    failure_variable: str
    source: str
    how_values_were_produced: str
    redistribution: Redistribution
    redistribution_reason: str
    quality: DataQuality = DataQuality.BENCHMARK_GRADE
    quality_note: str = ""

    SHIPS = frozenset({
        Redistribution.CLEAR,
        Redistribution.NO_LICENCE_FACTS_BASIS,
        Redistribution.AGAINST_PUBLISHER_TERMS,
    })

    @property
    def rerunnable(self) -> bool:
        return self.redistribution in VehicleRecord.SHIPS

    @property
    def licensed(self) -> bool:
        """True only where affirmative permission exists. Shipping is not licensing."""
        return self.redistribution is Redistribution.CLEAR


VEHICLES: tuple[VehicleRecord, ...] = (
    VehicleRecord(
        "naca_tn1451", "thermal-fluids", "x_over_D",
        "NACA TN-1451 (1947), Fig 10, bellmouth entrance",
        "Two-reader visual digitisation",
        Redistribution.CLEAR,
        "US Government work, public domain.",
    ),
    VehicleRecord(
        "velazquez_sco2", "thermal-fluids", "ratio_mu_w_b",
        "Velazquez et al. (2026), Appl. Therm. Eng. 285:129206",
        "Verbatim transcription of supplementary Appendix D, Tables D1-D28",
        Redistribution.CLEAR,
        "CC BY 4.0, publisher-deposited. Elsevier states the article licence extends to "
        "supplementary files.",
    ),
    VehicleRecord(
        "forrest", "thermal-fluids", "Re",
        "Forrest et al., J. Heat Transfer 138(2):021704",
        "Visual estimates from Fig 5 of the version of record",
        Redistribution.AGAINST_PUBLISHER_TERMS,
        "ASME holds copyright and requires written permission to reproduce. The CC-BY "
        "route does not apply: ASME grants it for accepted manuscripts in INSTITUTIONAL "
        "repositories, the OSTI deposit is a FUNDER repository, and the deposited PDF "
        "carries no Creative Commons marking at all. Shipped anyway, as an accepted "
        "risk. Numbers only.",
        DataQuality.TRIAGE_ONLY,
        "The file's own header: 'VISUAL ESTIMATES ... NOT digitized by WebPlotDigitizer. "
        "Use ONLY as a resolvability triage check.' Its benchmark cell is also "
        "degenerate -- 1 training row, no detector fit -- so its DO_NO_HARM outcome is "
        "short-circuited rather than earned. Published so both weaknesses are visible; "
        "re-digitise Fig 5 properly before treating this cell as evidence.",
    ),
    VehicleRecord(
        "casper_hypersonic_transition", "aerospace", "freestream_noise_pct",
        "Casper MS thesis (DTIC ADA504177) and AIAA 2009-4054",
        "Figure digitisation, 600-DPI segmentation, two readers",
        Redistribution.AGAINST_PUBLISHER_TERMS,
        "The rows carrying the result come from the AIAA paper, and AIAA prohibits using "
        "their content to develop machine-learning models without written permission -- "
        "which is what a public ML benchmark is. Shipped anyway, as an accepted risk. "
        "Weaker than Marineau, not equal to it: the OSTI copy carries no copyright "
        "notice AND no public-release marking, just silence. Numbers only.",
    ),
    VehicleRecord(
        "marineau_hypersonic_transition", "aerospace", "st_xsw_ratio",
        "Marineau et al., AIAA 2014-3108 / SAND2014-4326C",
        "Transcribed from Table 3",
        Redistribution.NO_LICENCE_FACTS_BASIS,
        "No reuse licence exists, and no prohibition either. The OSTI copy carries no "
        "copyright notice and is marked public-release-unlimited by the controlling "
        "office -- a security determination, not a licence, and OSTI expressly disclaims "
        "granting one. Ships on the position that measured values transcribed from a "
        "published table are facts. Government-funded, government-hosted, transcribed "
        "rather than digitised: the cleanest of the unlicensed three.",
    ),
    VehicleRecord(
        "dirker_water", "thermal-fluids", "Ri",
        "Dirker, Meyer & Reid (2018), Exp. Therm. Fluid Sci. 98",
        "Figure digitisation from Figs 17-20",
        Redistribution.AGAINST_PUBLISHER_TERMS,
        "Elsevier's TDM licence forbids substantially or systematically redistributing "
        "the dataset, and the one permissions exemption is drafted to exclude data that "
        "was previously in figure format -- which this was. Shipped anyway, as an "
        "accepted risk. Values are numbers only; no figure, text or PDF is "
        "redistributed. Weakest of the three: read off plots rather than transcribed.",
    ),
    VehicleRecord(
        "jin_sco2_buoyancy", "thermal-fluids", "Bu",
        "Jin et al. (2023), Ann. Nucl. Energy 188:109825",
        "Figure digitisation, two readers; Bu and Bo* recomputed",
        Redistribution.AGAINST_PUBLISHER_TERMS,
        "Same Elsevier terms as Dirker, with no open copy anywhere, and the authors were "
        "asked for raw data and declined. Shipped anyway, as an accepted risk. Bu and "
        "Bo* are recomputed from the paper's own equations, so part of this file is "
        "derived work rather than extraction.",
    ),
)

_BY_ID = {v.vehicle_id: v for v in VEHICLES}


def get(vehicle_id: str) -> VehicleRecord:
    try:
        return _BY_ID[vehicle_id]
    except KeyError:
        raise KeyError(
            f"unknown vehicle {vehicle_id!r}; known: {sorted(_BY_ID)}"
        ) from None


def rerunnable_ids() -> tuple[str, ...]:
    """The vehicles this checkout can recompute. Everything else is banked-only."""
    return tuple(v.vehicle_id for v in VEHICLES if v.rerunnable)


def banked_only_ids() -> tuple[str, ...]:
    return tuple(v.vehicle_id for v in VEHICLES if not v.rerunnable)


def licensed_ids() -> tuple[str, ...]:
    """Vehicles whose data ships under affirmative permission."""
    return tuple(v.vehicle_id for v in VEHICLES if v.licensed)


def unlicensed_shipped_ids() -> tuple[str, ...]:
    """Vehicles that ship WITHOUT a licence. Removed on objection; see NOTICE."""
    return tuple(
        v.vehicle_id for v in VEHICLES
        if v.rerunnable and not v.licensed
    )


def triage_only_ids() -> tuple[str, ...]:
    """Vehicles whose source values are not benchmark-grade by their own account."""
    return tuple(v.vehicle_id for v in VEHICLES if v.quality is DataQuality.TRIAGE_ONLY)
