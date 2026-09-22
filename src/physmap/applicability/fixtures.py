"""Declarative screening fixtures. Stated cases, not measured ones.

Two cases were screened out of the original study. They are reproduced here as
DECLARATIVE fixtures: their preconditions are asserted from the case description, not
read from data, because the evidence inputs and provenance for them are not available.

What they demonstrate is the refusal logic and its reason codes. What they are not is
executable evidence-backed cases, and nothing in the output lets them read as such --
every result carries `evidence_state = DECLARATIVE`, and the CLI prints it.

They become measured cases only when their evidence inputs and provenance arrive. Until
then a fixture that claimed otherwise would be the exact error this project is about:
a stated thing wearing the clothes of a measured one.
"""

from __future__ import annotations

from physmap.applicability.screen import ScreenResult, screen_case
from physmap.release import EvidenceState

__all__ = ["FIXTURE_IDS", "conjugate_heat_transfer", "fda_blood_pump", "get_fixture"]

FIXTURE_IDS = ("conjugate-heat-transfer", "fda-blood-pump")


def conjugate_heat_transfer() -> ScreenResult:
    """Solid-fluid conjugate heat transfer, QoI = peak solid temperature.

    Screened out because the QoI does not decompose over fluid-side mechanisms. Peak
    solid temperature is set by conduction through the solid coupled to the fluid-side
    heat flux; removing a fluid-side convection mechanism changes the coupled boundary
    condition rather than subtracting a term. There is no "the same case with buoyancy
    off" whose peak temperature differs only by the buoyancy contribution.
    """
    return screen_case(
        "conjugate-heat-transfer", "peak_solid_temperature",
        qoi_decomposes=False,
        mechanisms_separable=False,
        has_calibration_window=True,
        ablation_available=None,
        evidence_state=EvidenceState.DECLARATIVE,
        notes=(
            "Preconditions are asserted from the case description, not measured.",
            "Reported to demonstrate refusal logic only.",
        ),
    )


def fda_blood_pump() -> ScreenResult:
    """FDA benchmark centrifugal blood pump, QoI = haemolysis index.

    Screened out because the mechanisms are not separable. The haemolysis index
    integrates a damage model along pathlines through a rotating machine; shear
    generation, turbulence and residence time are coupled through the same flow field.
    Switching one off does not hold the others fixed -- it produces a different flow.
    """
    return screen_case(
        "fda-blood-pump", "haemolysis_index",
        qoi_decomposes=True,
        mechanisms_separable=False,
        has_calibration_window=True,
        ablation_available=None,
        evidence_state=EvidenceState.DECLARATIVE,
        notes=(
            "Preconditions are asserted from the case description, not measured.",
            "Reported to demonstrate refusal logic only.",
        ),
    )


_FIXTURES = {
    "conjugate-heat-transfer": conjugate_heat_transfer,
    "fda-blood-pump": fda_blood_pump,
}


def get_fixture(case_id: str) -> ScreenResult:
    try:
        return _FIXTURES[case_id]()
    except KeyError:
        raise KeyError(
            f"unknown screening fixture {case_id!r}; available: {list(FIXTURE_IDS)}"
        ) from None
