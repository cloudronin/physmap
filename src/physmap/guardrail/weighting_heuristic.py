"""Config-time observability weighting heuristic — the derived (not tuned) rule.

Spec: docs/specs/PhysMAP_Ensemble_ConfigTime_Observability_Heuristic_Spec_v0_1.md

Given ONLY config-time-legal inputs — the surrogate's declared inputs, the regime's
resolved closures + their bound-variables, the Layer-2a observability_class, and (when
a real vehicle has calibrated it) the Layer-2c partial_degree — assign each bound
variable a detector-weight decision:

    OBSERVABLE   → trust the BASELINE  (failure axis is a surrogate input; corpus redundant)
    UNOBSERVABLE → trust the CORPUS    (baseline structurally blind; its silence is *expected*)
    PARTIAL      → depends on degree_status:
        uncalibrated, no lean → DEFER  (honest UNCERTAIN; no weight invented)
        uncalibrated + lean   → LEAN   (qualitative physics default, NOT a measured weight)
        calibrated            → GRADED (interpolate from the calibrated Layer-2c degree)

The poles are fully determined from structure today; the PARTIAL middle is honestly
deferred until a real vehicle calibrates its (regime, variable) degree, then graduates
to a graded weight WITHOUT any rule change — the same heuristic just reads a richer corpus.

DISCIPLINE (load-bearing): this module NEVER computes or estimates an observability
score/degree. The graded weight comes ONLY from a calibrated Layer-2c degree read via
`partial_degree_for()`; deriving a degree from structural inputs would fabricate an
empirical quantity (the same error the mapping spec forbids). There is deliberately NO
import of the cv_r2_knn estimator (`pipeline.observability`) anywhere in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from physmap.corpus.calibration import ClosureEntry
from physmap.guardrail.classify import coord_input_aliases, load_default_corpus_index
from physmap.guardrail.corpus_regimes import (
    KNOWN_PARTIAL,
    REGIME_TO_CLOSURES,
    observability_class_for,
    partial_degree_for,
)
from physmap.guardrail.enums import Observability, Regime


# Half-width of the near-pole "collapse" zone on the observability axis. A JUDGMENT
# CHOICE, not a fitted/tuned number: a calibrated degree within POLE_BAND of a pole is
# treated AS that pole (corpus-trust near 0, baseline-trust near 1); strictly between,
# the corpus fire is a calibrated SOFT-flag whose weight is scaled by (1 - degree).
# Chosen deliberately coarse (0.15) so a single mid-range calibration cannot masquerade
# as a hard pole; it is the one knob here and is meant to be revisited (not re-fit) as
# the corpus accumulates more calibrated degrees.
POLE_BAND = 0.15

# weight_target vocabulary — the per-variable decision the aggregator consumes.
WEIGHT_BASELINE = "baseline"
WEIGHT_CORPUS = "corpus"
WEIGHT_DEFER = "defer"
WEIGHT_LEAN = "lean"
WEIGHT_GRADED = "graded"

# graded sub-lean — which pole behavior a calibrated degree resolves to.
LEAN_CORPUS_TRUST = "corpus-trust"
LEAN_BASELINE_TRUST = "baseline-trust"
LEAN_SOFT_FLAG = "soft-flag"

# Structural-lean hook (spec-optional). A qualitative physics-knowledge default for an
# UNCALIBRATED known-partial cell — explicitly a LEAN pending confirmation, never a
# measured weight, and overridden the instant a calibrated degree lands. EMPTY today
# (no lean encoded) → the heuristic defers. When a real lean is authored it belongs
# alongside the other corpus prerequisites in corpus_regimes.py.
STRUCTURAL_LEAN_OVERRIDES: dict[tuple[str, str], str] = {}


def structural_lean_for(closure_id: str, coord: str) -> str | None:
    """The qualitative physics-knowledge lean for an uncalibrated known-partial cell,
    or None (→ DEFER). Never a measured weight."""
    return STRUCTURAL_LEAN_OVERRIDES.get((closure_id, coord))


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)


def graded_weights(degree: float) -> tuple[float, float]:
    """(w_baseline, w_corpus) for a calibrated partial degree.

    POLARITY (load-bearing — guard against sign inversion): the observability degree
    runs 0 = baseline blind (unobservable end) → 1 = baseline sees the axis (observable
    end). So a HIGHER degree means MORE baseline weight:

        w_baseline = degree,   w_corpus = 1 - degree

    At the endpoints this reproduces the poles exactly:
        graded_weights(0.0) == (0.0, 1.0)   # all corpus  (unobservable)
        graded_weights(1.0) == (1.0, 0.0)   # all baseline (observable)
    """
    d = _clamp01(degree)
    return d, 1.0 - d


def graded_lean(degree: float) -> str:
    """Which pole behavior a calibrated degree resolves to (the continuous-blend rule).

    corpus-trust near the unobservable pole (degree <= POLE_BAND), baseline-trust near
    the observable pole (degree >= 1 - POLE_BAND), else a calibrated soft-flag in between.
    """
    d = _clamp01(degree)
    if d <= POLE_BAND:
        return LEAN_CORPUS_TRUST
    if d >= 1.0 - POLE_BAND:
        return LEAN_BASELINE_TRUST
    return LEAN_SOFT_FLAG


@dataclass(frozen=True)
class BoundWeightDecision:
    """The config-time weight decision for one regime bound-variable. Inspectable: it
    carries the class, the target, the (poles + graded) weights, the degree_status, and
    the provenance, so the derived rule can be audited end-to-end."""
    closure_id: str
    coord: str
    observability: Observability
    weight_target: str             # baseline | corpus | defer | lean | graded
    w_baseline: float | None       # set for poles + graded; None for defer/lean
    w_corpus: float | None
    degree_status: str             # n/a | uncalibrated | calibrated
    partial_degree: float | None   # regime-resolved calibrated degree (graded only)
    structural_lean: str | None    # corpus_lean | baseline_lean | neutral (lean target only)
    calibrated_by: tuple[str, ...]
    rationale: str


def resolve_partial(
    closure_id: str, coord: str, *, regime_value: str | None = None,
) -> BoundWeightDecision:
    """Weight decision for a PARTIAL (known-partial, absent) bound — the ONLY branch
    that consults Layer-2c. Reads `partial_degree_for()`; never derives a degree.

    The calibrated degree is regime-resolved: a degree calibrated for one regime must
    not weight a deployment in a different regime, so a calibrated cell with no entry
    for `regime_value` falls back to the honest uncalibrated behavior for this deployment.
    """
    degree_map, degree_status, calibrated_by = partial_degree_for(closure_id, coord)

    degree: float | None = None
    if degree_status == "calibrated" and degree_map:
        degree = degree_map.get(regime_value) if regime_value is not None else None
        if degree is None:
            degree_status, calibrated_by = "uncalibrated", []  # not calibrated for THIS regime

    if degree_status == "calibrated" and degree is not None:
        w_b, w_c = graded_weights(degree)
        lean = graded_lean(degree)
        return BoundWeightDecision(
            closure_id, coord, Observability.PARTIAL, WEIGHT_GRADED,
            w_b, w_c, "calibrated", float(degree), None, tuple(calibrated_by),
            f"partial graded: degree={degree:g} → (w_baseline={w_b:g}, w_corpus={w_c:g}), "
            f"{lean}; calibrated_by={list(calibrated_by)}",
        )

    lean = structural_lean_for(closure_id, coord)
    if lean is not None:
        return BoundWeightDecision(
            closure_id, coord, Observability.PARTIAL, WEIGHT_LEAN,
            None, None, "uncalibrated", None, lean, (),
            f"partial uncalibrated: applying labeled structural_lean={lean!r} "
            f"(qualitative physics default, not a measured weight)",
        )
    return BoundWeightDecision(
        closure_id, coord, Observability.PARTIAL, WEIGHT_DEFER,
        None, None, "uncalibrated", None, None, (),
        "partial uncalibrated: DEFER (UNCERTAIN) — no calibrated degree, no weight invented",
    )


def config_time_weights(
    surrogate_inputs: Sequence[str],
    regime: Regime,
    corpus_index: dict[str, ClosureEntry] | None = None,
) -> list[BoundWeightDecision]:
    """The full per-bound weight table for a deployment — the inspectable derived rule.

    Mirrors `classify_observability`'s structural step (same `coord_input_aliases` +
    `observability_class_for` primitives, so the OBSERVABLE/PARTIAL/UNOBSERVABLE split
    cannot diverge from the canonical classifier) and additionally attaches the weight
    decision + provenance per bound. PARTIAL delegates to `resolve_partial` (the only
    Layer-2c read). UNLISTED (or no resolved closures) → [] → statistical-only.
    """
    if corpus_index is None:
        corpus_index = load_default_corpus_index()
    out: list[BoundWeightDecision] = []
    if regime is Regime.UNLISTED:
        return out
    inputs = set(surrogate_inputs)
    for closure_id in REGIME_TO_CLOSURES.get(regime, ()):
        entry = corpus_index.get(closure_id)
        if entry is None:
            continue
        for bound in entry.validated_range:
            coord = bound.coord
            if any(a in inputs for a in coord_input_aliases(coord)):
                out.append(BoundWeightDecision(
                    closure_id, coord, Observability.OBSERVABLE, WEIGHT_BASELINE,
                    1.0, 0.0, "n/a", None, None, (),
                    "observable: failure axis is a surrogate input → baseline sees the "
                    "failure region; corpus redundant",
                ))
            elif observability_class_for(closure_id, coord) == KNOWN_PARTIAL:
                out.append(resolve_partial(closure_id, coord, regime_value=regime.value))
            else:
                out.append(BoundWeightDecision(
                    closure_id, coord, Observability.UNOBSERVABLE, WEIGHT_CORPUS,
                    0.0, 1.0, "n/a", None, None, (),
                    "unobservable: failure axis absent + structural-binary → baseline "
                    "blind; trust corpus (its silence is expected, not reassuring)",
                ))
    return out
