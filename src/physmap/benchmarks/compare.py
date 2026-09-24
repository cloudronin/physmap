"""Compare a fresh benchmark run against the banked matrix.

Exact equality is the wrong test, and a clean-clone check proved it: on numpy 2.5 /
scikit-learn 1.9, `dirker_water.observability_score` came back 0.4912044133088568 where
the matrix banked 0.49120441330885667. That is a relative difference of 2.6e-16 -- one
unit in the last place, from a different BLAS reduction order. Nothing about the result
changed.

So floats are compared with a tolerance and everything else is compared exactly. The
split matters, because the fields that decide an outcome are not floats:

  * outcomes, verdicts, observability classes  -- strings, exact
  * every count (n_train, n_test, n_wrong, clean_lift, fire counts) -- ints, exact
  * scores and calibrated thresholds -- floats, within tolerance

A tolerance loose enough to absorb ULP noise (1e-9 relative) is still roughly seven
orders of magnitude tighter than any change that would mean something. And a match that
needed the tolerance is reported as such rather than as "identical", because those are
different statements.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

__all__ = ["MatrixComparison", "compare_matrices", "compare_records", "DEFAULT_REL_TOL"]

#: Relative tolerance for float fields. Absorbs last-bit differences between numpy /
#: BLAS builds; far tighter than any numerically meaningful change.
DEFAULT_REL_TOL = 1e-9


@dataclass
class MatrixComparison:
    #: Real differences: any non-float mismatch, or a float beyond tolerance.
    drift: list[str] = field(default_factory=list)
    #: Float fields that differ but are within tolerance. Not drift; worth reporting.
    within_tolerance: list[str] = field(default_factory=list)
    rel_tol: float = DEFAULT_REL_TOL
    #: Optional per-field tolerance, `path -> (rel_tol, abs_tol)`, overriding `rel_tol`. For
    #: records whose floats are not all alike -- a difference of two near-equal numbers needs
    #: an absolute tolerance, where everything else is compared relatively.
    tolerance: Callable[[str], tuple[float, float]] | None = None
    #: How a summary describes `tolerance`.
    tolerance_note: str = ""

    @property
    def matches(self) -> bool:
        return not self.drift

    @property
    def bit_identical(self) -> bool:
        return not self.drift and not self.within_tolerance

    def summary(self) -> str:
        if self.drift:
            return f"DRIFT in {len(self.drift)} field(s)"
        if self.within_tolerance:
            if self.tolerance is not None:
                return (
                    f"matches within {self.tolerance_note} "
                    f"({len(self.within_tolerance)} float field(s) differ, all by less than that)"
                )
            return (
                f"matches within {self.rel_tol:g} relative "
                f"({len(self.within_tolerance)} float field(s) differ in their last bits)"
            )
        return "bit-identical"

    def drifting_vehicles(self) -> list[str]:
        return sorted({d.split(".")[0] for d in self.drift})


def _close(a: float, b: float, rel_tol: float, abs_tol: float = 0.0) -> bool:
    if a == b:
        return True
    scale = max(abs(a), abs(b))
    return abs(a - b) <= max(rel_tol * scale, abs_tol)


def _walk(fresh, banked, path: str, cmp: MatrixComparison) -> None:
    if isinstance(fresh, bool) or isinstance(banked, bool):
        # bool is an int subclass; compare it exactly, never numerically
        if fresh != banked:
            cmp.drift.append(f"{path}: fresh={fresh!r} banked={banked!r}")
        return
    if isinstance(fresh, dict) and isinstance(banked, dict):
        for k in sorted(set(fresh) | set(banked)):
            if k not in fresh:
                cmp.drift.append(f"{path}.{k}: missing from the fresh run")
            elif k not in banked:
                cmp.drift.append(f"{path}.{k}: missing from the banked matrix")
            else:
                _walk(fresh[k], banked[k], f"{path}.{k}", cmp)
        return
    if isinstance(fresh, list) and isinstance(banked, list):
        if len(fresh) != len(banked):
            cmp.drift.append(f"{path}: length {len(fresh)} vs {len(banked)}")
            return
        for i, (x, y) in enumerate(zip(fresh, banked)):
            _walk(x, y, f"{path}[{i}]", cmp)
        return
    if isinstance(fresh, float) or isinstance(banked, float):
        if not isinstance(fresh, (int, float)) or not isinstance(banked, (int, float)):
            cmp.drift.append(f"{path}: fresh={fresh!r} banked={banked!r}")
        elif fresh == banked:
            return
        elif _close(float(fresh), float(banked),
                    *(cmp.tolerance(path) if cmp.tolerance else (cmp.rel_tol, 0.0))):
            cmp.within_tolerance.append(f"{path}: fresh={fresh!r} banked={banked!r}")
        else:
            cmp.drift.append(f"{path}: fresh={fresh!r} banked={banked!r}")
        return
    if fresh != banked:
        cmp.drift.append(f"{path}: fresh={fresh!r} banked={banked!r}")


def compare_matrices(fresh: dict, banked: dict, *, rel_tol: float = DEFAULT_REL_TOL) -> MatrixComparison:
    """Compare two matrices cell by cell and field by field."""
    cmp = MatrixComparison(rel_tol=rel_tol)

    f_cells = {c["vehicle_id"]: c for c in fresh.get("cells", [])}
    b_cells = {c["vehicle_id"]: c for c in banked.get("cells", [])}
    for vid in sorted(set(f_cells) | set(b_cells)):
        if vid not in f_cells:
            cmp.drift.append(f"{vid}: absent from the fresh run")
        elif vid not in b_cells:
            cmp.drift.append(f"{vid}: absent from the banked matrix")
        else:
            _walk(f_cells[vid], b_cells[vid], vid, cmp)

    for key in ("benchmark", "api", "detectors", "operating_percentiles",
                "all_guards_passed"):
        _walk(fresh.get(key), banked.get(key), key, cmp)
    return cmp


def compare_records(fresh: dict, banked: dict, *, rel_tol: float = DEFAULT_REL_TOL,
                    tolerance: Callable[[str], tuple[float, float]] | None = None,
                    tolerance_note: str = "") -> MatrixComparison:
    """Compare any two nested records under the same rule as the matrix: floats within
    tolerance -- `rel_tol`, or per field via `tolerance` -- and everything else exactly. For
    banked results that are not a vehicle matrix -- the stress tests -- so they drift-check
    the same way `benchmark run` does."""
    cmp = MatrixComparison(rel_tol=rel_tol, tolerance=tolerance, tolerance_note=tolerance_note)
    _walk(fresh, banked, "record", cmp)
    return cmp

