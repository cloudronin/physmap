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
    "VehicleRecord",
    "VEHICLES",
    "rerunnable_ids",
    "banked_only_ids",
]


class Redistribution(str, Enum):
    #: Source data ships. The vehicle can be recomputed from this checkout.
    CLEAR = "clear"
    #: Cleared-status undetermined or negative by project decision.
    EXCLUDED_BY_DECISION = "excluded_by_decision"
    #: No reuse licence exists. Not a decision -- a finding.
    BLOCKED_NO_LICENCE = "blocked_no_licence"


@dataclass(frozen=True)
class VehicleRecord:
    vehicle_id: str
    domain: str
    failure_variable: str
    source: str
    how_values_were_produced: str
    redistribution: Redistribution
    redistribution_reason: str

    @property
    def rerunnable(self) -> bool:
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
        Redistribution.EXCLUDED_BY_DECISION,
        "ASME holds copyright in the version of record that was digitised. A CC-BY "
        "accepted manuscript exists but was not the source used. The values are also "
        "marked in their own header as placeholders pending redigitisation.",
    ),
    VehicleRecord(
        "casper_hypersonic_transition", "aerospace", "freestream_noise_pct",
        "Casper MS thesis (DTIC ADA504177) and AIAA 2009-4054",
        "Figure digitisation, 600-DPI segmentation, two readers",
        Redistribution.EXCLUDED_BY_DECISION,
        "The rows carrying the result come from the AIAA paper. AIAA prohibits using "
        "their content to develop machine-learning models without written permission.",
    ),
    VehicleRecord(
        "marineau_hypersonic_transition", "aerospace", "st_xsw_ratio",
        "Marineau et al., AIAA 2014-3108 / SAND2014-4326C",
        "Transcribed from Table 3",
        Redistribution.BLOCKED_NO_LICENCE,
        "No reuse licence exists. The OSTI copy carries no copyright notice and is marked "
        "public-release-unlimited, but that is a security determination, not a licence; "
        "OSTI expressly disclaims granting one.",
    ),
    VehicleRecord(
        "dirker_water", "thermal-fluids", "Ri",
        "Dirker, Meyer & Reid (2018), Exp. Therm. Fluid Sci. 98",
        "Figure digitisation from Figs 17-20",
        Redistribution.EXCLUDED_BY_DECISION,
        "Closed access under the Elsevier TDM licence, which forbids systematic "
        "redistribution. The one permissions exemption is drafted to exclude data that "
        "was previously in figure format.",
    ),
    VehicleRecord(
        "jin_sco2_buoyancy", "thermal-fluids", "Bu",
        "Jin et al. (2023), Ann. Nucl. Energy 188:109825",
        "Figure digitisation, two readers; Bu and Bo* recomputed",
        Redistribution.EXCLUDED_BY_DECISION,
        "Closed access with no open copy anywhere, same Elsevier terms as Dirker. The "
        "authors were asked for raw data and declined.",
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
