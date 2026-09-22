"""PhysMAP D3 — literature-derived validity-range-distance signal.

Per user directive after the sweep finding:
  "Track B's signal was never the physics-validity signal PhysMAP claims —
   that signal (literature validity-range distance) still needs to be
   built and tested against genuinely-quiet baselines on real data."

This module implements the ACTUAL PhysMAP physics-validity claim: a signal
that depends ONLY on the literature-derived closure validated_range from
`corpus.jsonl`, NOT on training data. That's the structural property that
differentiates PhysMAP from input-distribution novelty detectors.

Signal definition:
  Given a test point (Re, Pr, ...) and a matched closure_id, look up the
  closure's `validated_range` from corpus.jsonl. For each coordinate in
  the range, compute the relative distance from the test point's value to
  the [min, max] interval:
    - 0 if min <= value <= max
    - (min - value) / min if value < min
    - (value - max) / max if value > max
  Combine across coordinates as L2 norm. Signal > 0 iff test point is
  outside the validated rectangle on at least one coordinate.

Key property: this signal has NO training-data dependence. It catches
out-of-validity points regardless of how training is distributed.
That's the structural mechanism that lets PhysMAP differentiate from
novelty detectors, IF such a differentiator cell exists in the data.

Important: just because this signal fires doesn't mean it differentiates
from baselines. Baselines fire when test points are far from training.
A clean differentiator requires test points that are:
  - INSIDE the training distribution (baselines genuinely quiet)
  - OUTSIDE the closure's validated range (validity-distance fires)
These conditions can only co-occur if training data includes points
outside the closure's validated range — i.e., a practitioner trained on
data spanning the closure's validity boundary.

For Forrest:
  Modified Sparrow-Cur validated_range: Re [10000, 70000], Pr [2.2, 5.4].
  Forrest data includes:
    - Sub-critical Re<4000  (OUTSIDE validated Re range)
    - Transition  Re 4000-10000  (OUTSIDE validated Re range)
    - Benign      Re>=10000     (INSIDE validated range)
  If training includes any sub-critical or transition points, the closure's
  validity boundary cuts THROUGH the training distribution. Test points on
  the wrong side of that internal boundary would be baseline-quiet but
  validity-loud — the genuine differentiator cell.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np

from physmap.corpus.calibration import resolve_corpus_path


# Map D3 feature names to corpus.jsonl coordinate names.
# Geometry features (Dh, alpha_star, etc.) are NOT in corpus validated_range
# (yet); they're in regime_context as prose. So those features don't
# contribute to validity-distance — they're for baselines only.
#
# x_over_D added after the Track-C-extension for Gnielinski. The validity
# signal now fires on entrance-region (x/D < 10) test points where the
# bare correlation is invalid per textbook (Bergman/Incropera 7th ed §8.5).
FEATURE_TO_CORPUS_COORD = {
    "log10_Re": "reynolds_number",   # validated_range stores raw Re
    "Pr": "prandtl_number",
    "x_over_D": "x_over_D",          # straight passthrough
    "log10_x_over_D": "x_over_D",    # for log-scale axial-position features
    "Ri": "richardson_number",       # buoyancy validity ceiling (Stage-3 middle).
                                     # raw Ri (NOT log) — signal() compares the raw
                                     # value to the corpus min/max directly.
    "ratio_mu_w_b": "viscosity_ratio_wall_bulk",  # property-variation bound (Velazquez sCO2)
    "Bu": "liu_buoyancy_parameter",               # buoyancy validity bound (Jin sCO2 vertical tube;
                                                  # raw Bu vs corpus max 1.3e-5 directly)
    # aerospace / hypersonic-transition validity coords (raw passthrough — the
    # signal() comparison uses the raw value vs corpus min/max directly):
    "freestream_noise_pct": "freestream_noise_rms_pitot_pct",  # Casper (Pate-Stainback bound)
    "st_xsw_ratio": "entropy_layer_shock_ratio",               # Marineau (entropy-layer/shock bound)
}


# Status weighting for picking the GOVERNING (dispositive) fired bound when a
# point is past multiple bounds at once: a confirmed bound outranks a claimed
# one at equal margin. Mirrors the corpus bound_status vocabulary.
_STATUS_WEIGHT = {
    "confirmed": 1.0,
    "confirmed-contested": 0.9,
    "extrapolated": 0.6,
    "claimed": 0.4,
}
_DEFAULT_STATUS_WEIGHT = 0.4


@dataclass(frozen=True)
class PerBoundMargin:
    """One bound's graded distance-past-bound for one test point.

    `margin` is the same per-coordinate relative distance `signal()` squares into
    its L2 norm: 0 inside [min, max], > 0 outside. `side` ∈ {below, above, inside}.
    This is the graded, un-collapsed signal (the Tier-1 finding: graded margin
    ensembles better than binary fire-at-bound). The detector reports which bound
    was violated and by how much; it does NOT decide observability — that routing
    lives in the aggregator.
    """
    coord: str               # corpus bound variable, e.g. "x_over_D"
    feature_name: str        # the feature column read, e.g. "x_over_D" or "log10_Re"
    margin: float            # graded distance-past-bound (0 inside; >0 outside)
    bound_status: str        # confirmed | confirmed-contested | extrapolated | claimed
    side: str                # below | above | inside


@dataclass
class ValidityRangeDistanceDetector:
    """PhysMAP's literature-derived physics-validity signal.

    Reads the matched closure's validated_range from corpus.jsonl. At each
    test point, computes distance from the test point's coordinates to the
    validated rectangle. Signal > 0 iff test point is outside the
    rectangle on at least one coordinate.

    NO training-data dependence. Pure literature lookup.
    """
    closure_id: str
    feature_names: Sequence[str]
    # Resolves the ACTIVE corpus (env → premium → bundled seed) at construction
    # time; a dev/editable tree gets the full premium corpus unchanged, a core-only
    # install gets the bundled seed. Pass an explicit path to override.
    corpus_path: Path = field(default_factory=resolve_corpus_path)

    valid_ranges: dict[str, tuple[float, float]] = field(default_factory=dict, init=False)
    # bound_status[coord] mirrors the corpus bound_status; used by governing_bound's
    # status weighting. Populated alongside valid_ranges; signal() never reads it.
    bound_status: dict[str, str] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.valid_ranges = self._load_validated_ranges()
        if not self.valid_ranges:
            raise ValueError(
                f"closure_id '{self.closure_id}' has no usable validated_range "
                f"in corpus.jsonl (or closure_id not found)"
            )
        self.bound_status = self._load_bound_status()

    def _load_validated_ranges(self) -> dict[str, tuple[float, float]]:
        ranges = {}
        with open(self.corpus_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("closure_id") != self.closure_id:
                    continue
                for vr in entry.get("validated_range", []):
                    coord = vr["coord"]
                    vmin = float(vr["min"])
                    vmax = float(vr["max"])
                    ranges[coord] = (vmin, vmax)
                break
        return ranges

    def signal(self, test_X: np.ndarray) -> np.ndarray:
        """Per-test-point validity-distance to the closure's validated range.

        For each test point and each feature that maps to a corpus coord,
        compute the relative distance to the [min, max] interval and
        combine as L2 norm. Geometry features (not in corpus) contribute 0.
        """
        n_test = len(test_X)
        scores = np.zeros(n_test, dtype=float)
        for i, x in enumerate(test_X):
            sq_dist = 0.0
            for j, fname in enumerate(self.feature_names):
                coord = FEATURE_TO_CORPUS_COORD.get(fname)
                if coord is None or coord not in self.valid_ranges:
                    continue
                # Convert feature value back to physical units for coord lookup
                if fname == "log10_Re":
                    value = 10.0 ** float(x[j])
                elif fname == "log10_x_over_D":
                    value = 10.0 ** float(x[j])
                else:
                    value = float(x[j])
                vmin, vmax = self.valid_ranges[coord]
                if value < vmin:
                    rel = (vmin - value) / max(vmin, 1e-9)
                    sq_dist += rel ** 2
                elif value > vmax:
                    rel = (value - vmax) / max(vmax, 1e-9)
                    sq_dist += rel ** 2
                # else: in [min, max], contributes 0
            scores[i] = float(np.sqrt(sq_dist))
        return scores

    # ── graded per-bound margins + governing fired bound (additive) ───────────
    # signal() above is left byte-identical (the locked phase1_gate depends on
    # it). These methods expose the SAME per-coordinate relative distances
    # un-collapsed, plus which bound governs — what the observability-weighted
    # aggregator needs to route on the fired bound VARIABLE.

    def _load_bound_status(self) -> dict[str, str]:
        """{coord: bound_status} for the matched closure. A separate read keeps
        _load_validated_ranges() and signal() byte-identical."""
        statuses: dict[str, str] = {}
        with open(self.corpus_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("closure_id") != self.closure_id:
                    continue
                for vr in entry.get("validated_range", []):
                    statuses[vr["coord"]] = vr.get("bound_status", "")
                break
        return statuses

    def evaluate_bounds(self, test_X: np.ndarray) -> list[list[PerBoundMargin]]:
        """Per test point, the graded per-bound margins — the un-collapsed terms
        signal() L2-combines. One PerBoundMargin per (feature → corpus coord) the
        detector can evaluate; margin > 0 means the point is past that bound. The
        per-coordinate math mirrors signal() exactly."""
        out: list[list[PerBoundMargin]] = []
        for x in test_X:
            row: list[PerBoundMargin] = []
            for j, fname in enumerate(self.feature_names):
                coord = FEATURE_TO_CORPUS_COORD.get(fname)
                if coord is None or coord not in self.valid_ranges:
                    continue
                if fname in ("log10_Re", "log10_x_over_D"):
                    value = 10.0 ** float(x[j])
                else:
                    value = float(x[j])
                vmin, vmax = self.valid_ranges[coord]
                if value < vmin:
                    margin = (vmin - value) / max(vmin, 1e-9)
                    side = "below"
                elif value > vmax:
                    margin = (value - vmax) / max(vmax, 1e-9)
                    side = "above"
                else:
                    margin = 0.0
                    side = "inside"
                row.append(PerBoundMargin(
                    coord=coord, feature_name=fname, margin=float(margin),
                    bound_status=self.bound_status.get(coord, ""), side=side,
                ))
            out.append(row)
        return out

    def governing_bound(
        self, per_bound: Sequence[PerBoundMargin], *, status_weighting: bool = True,
    ) -> PerBoundMargin | None:
        """The governing (dispositive) fired bound for one point: the most-
        violated, status-weighted when `status_weighting` (a confirmed bound
        outranks a claimed one at equal margin). None if the point is inside
        every bound."""
        fired = [b for b in per_bound if b.margin > 0.0]
        if not fired:
            return None

        def _key(b: PerBoundMargin) -> float:
            w = (_STATUS_WEIGHT.get(b.bound_status, _DEFAULT_STATUS_WEIGHT)
                 if status_weighting else 1.0)
            return w * b.margin

        return max(fired, key=_key)
