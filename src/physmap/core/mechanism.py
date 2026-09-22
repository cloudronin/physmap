"""A mechanism and its calibration window. Domain-neutral on purpose.

Nothing here mentions Nusselt numbers, Reynolds numbers or heat transfer. The causal
method is a statement about mechanisms, quantities of interest and calibration windows;
the moment a heat-transfer field appears in this layer, the method stops being general
and starts being a convection tool wearing a general name.

Adapted from the substrate ingest in the monorepo, with the heat-transfer fields
removed and `contribution` deliberately dropped -- see physmap.materiality for why a
contribution fraction is not a materiality.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CalibrationWindow", "Mechanism"]


@dataclass(frozen=True)
class CalibrationWindow:
    """The range of a governing variable over which a mechanism was calibrated.

    An open end is None, not an infinity: "no upper bound was stated" and "the upper
    bound is very large" are different claims about the evidence.
    """

    variable: str
    low: float | None = None
    high: float | None = None

    def __post_init__(self) -> None:
        if self.low is not None and self.high is not None and self.low > self.high:
            raise ValueError(
                f"calibration window for {self.variable!r} is inverted: "
                f"low={self.low} > high={self.high}"
            )

    def contains(self, value: float) -> bool:
        if self.low is not None and value < self.low:
            return False
        if self.high is not None and value > self.high:
            return False
        return True

    def describe(self) -> str:
        if self.low is None and self.high is None:
            return f"{self.variable} (no stated bound)"
        if self.low is None:
            return f"{self.variable} <= {self.high:g}"
        if self.high is None:
            return f"{self.variable} >= {self.low:g}"
        return f"{self.low:g} <= {self.variable} <= {self.high:g}"


@dataclass(frozen=True)
class Mechanism:
    """One mechanism at one operating point."""

    mechanism_id: str
    name: str
    window: CalibrationWindow
    operating_value: float

    def in_calibration(self) -> bool:
        return self.window.contains(self.operating_value)

    def outside_calibration(self) -> bool:
        return not self.in_calibration()
