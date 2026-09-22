"""Linear D3 signal pipeline — Detectors -> Aggregator -> Assessment.

Per the v0.2 architecture refactor (Part 2): a point flows through a LINEAR
sequence of stages. Two ROLES of signal distinguished:

  * DECISION signals — the aggregator weighs them to produce the verdict.
    These are the detectors: ClosureValidity (literature-only),
    DistanceToTraining, GPVariance / EnsembleVariance, optional PDEResidual.

  * JUSTIFICATION signals — ride along to explain/audit; NEVER weighed for
    the verdict. Evidence provenance, sources, corrections, validity narrative.

The pipeline accumulates both. The aggregator consumes ONLY decision signals.
Justification signals attach to the Assessment for downstream audit. This keeps
detection and explanation cleanly separated while letting both flow through
one pipeline.

LINEAR, NOT A DAG: a list of decision stages, then a list of justification
stages, then one aggregator. If you find yourself building conditional
routing, you have overshot the design.

WRAP-NOT-REWRITE: the existing detector classes in `d3_detectors.py` and
`d3_validity_signal.py` have a uniform `signal(test_X) -> np.ndarray`
interface. This module provides thin adapters that wrap them, add a
threshold + rationale, and emit a uniform `DetectorResult` schema. The
existing math (locked k=3 Mahalanobis, Matérn-5/2 GP, polynomial
bootstrap, literature L2 distance) stays untouched.

PHASE-1 ASSESSMENT IS FLAT — verdict + signals + flat justification +
rationale. Phase-2 grows the per-detector signals into v0.6
CredibilityFactor / WeakenerAnnotation nodes (gated on NACA showing lift).
The field names here are seeds the Phase-2 mapping will reuse verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any, Callable, Literal, Protocol, Sequence, runtime_checkable,
)

import numpy as np


# ── result schemas ──────────────────────────────────────────────────────────

SignalRole = Literal["decision", "justification"]
Verdict_Label = Literal["fire", "quiet"]


@dataclass(frozen=True)
class DetectorResult:
    """One detector's output for ONE test point.

    `threshold` is None for literature-only detectors (ValidityRangeDistance)
    that fire on `score > 0` with no calibration step. `rationale` is a
    human-readable line that downstream audit + Phase-2 graph nodes will
    use verbatim.
    """
    detector_name: str
    score: float
    fired: bool
    threshold: float | None
    rationale: str
    role: SignalRole = "decision"


@dataclass(frozen=True)
class Verdict:
    """Aggregator output — verdict + rationale for the per-point decision."""
    label: Verdict_Label
    rationale: str


@dataclass(frozen=True)
class Assessment:
    """Per-point assessment — flat in Phase 1.

    Phase-2 mapping (NOT BUILT YET; gated on NACA result):
      `decision_signals[*]`  -> v0.6 CredibilityFactor / WeakenerAnnotation
      `justification_signals[*]` -> v0.6 hasEvidence / hasJustification
      `verdict`              -> Disposition.actionClass
      `rationale`            -> OffsetRationale / residualRiskJustification
    """
    operating_point: tuple
    verdict: Verdict_Label
    decision_signals: dict[str, DetectorResult]
    justification_signals: dict[str, dict[str, Any]]
    rationale: str


# ── protocols ───────────────────────────────────────────────────────────────

@runtime_checkable
class Detector(Protocol):
    """Decision-signal stage. Wraps an underlying `signal(test_X) -> ndarray`
    detector and emits one DetectorResult per test point via `evaluate`."""
    name: str
    role: SignalRole

    def evaluate(self, test_X: np.ndarray) -> list[DetectorResult]: ...


@runtime_checkable
class JustificationStage(Protocol):
    """Justification-signal stage. Attaches provenance / evidence / corrections
    to a per-point assessment. Sees the decision signals but does NOT influence
    the verdict (the aggregator consumes decisions only).
    """
    name: str
    role: SignalRole   # always "justification"

    def enrich(self, row_meta: dict,
               decision_signals: dict[str, DetectorResult]) -> dict[str, Any]: ...


@runtime_checkable
class Aggregator(Protocol):
    """Decision-signal -> Verdict reducer. Phase-1 implementations are
    AnyFired, CorpusGated, WeightedVote (in `d3_aggregators.py`). Phase-2
    plugs in the defeasible-adjudication reasoner."""

    name: str

    def combine(self, decision_signals: dict[str, DetectorResult]) -> Verdict: ...


# ── detector adapters ──────────────────────────────────────────────────────
#
# One generic adapter wraps every existing detector. Differences (name,
# inner instance, rationale verbiage) are passed in at construction. The
# underlying detectors are untouched — adapters only ADD the threshold +
# rationale + role layer.


RationaleFn = Callable[[float, float | None, bool], str]


def _default_rationale(name: str) -> RationaleFn:
    """Generic rationale template. Override per detector for richer language."""
    def _build(score: float, threshold: float | None, fired: bool) -> str:
        if not fired:
            if threshold is None:
                return f"{name}: quiet (score={score:.3g}, no threshold)"
            return f"{name}: quiet (score={score:.3g} <= threshold={threshold:.3g})"
        if threshold is None:
            return f"{name}: FIRED (score={score:.3g} > 0; literature-only)"
        return f"{name}: FIRED (score={score:.3g} > threshold={threshold:.3g})"
    return _build


@dataclass
class DetectorAdapter:
    """Generic adapter — wraps any object with a `signal(test_X) -> ndarray`
    method (every existing detector in d3_detectors.py / d3_validity_signal.py
    satisfies this) and emits DetectorResults.

    `threshold` is None for literature-only detectors. `role` defaults to
    "decision" — pass "justification" only for stages that should ride along
    for audit without feeding the verdict.
    """
    name: str
    inner: Any                  # something with .signal(test_X) -> np.ndarray
    threshold: float | None = None
    role: SignalRole = "decision"
    rationale_fn: RationaleFn | None = None
    extra_meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not hasattr(self.inner, "signal"):
            raise TypeError(
                f"DetectorAdapter inner object must expose .signal(test_X) -> ndarray; "
                f"got {type(self.inner).__name__} which lacks `signal`."
            )
        if self.rationale_fn is None:
            self.rationale_fn = _default_rationale(self.name)

    def signal(self, test_X: np.ndarray) -> np.ndarray:
        """Pass-through to the inner detector. Kept so existing call sites
        that expect `.signal(...)` keep working when handed an adapter."""
        return self.inner.signal(test_X)

    def evaluate(self, test_X: np.ndarray) -> list[DetectorResult]:
        scores = np.asarray(self.signal(test_X), dtype=float)
        results: list[DetectorResult] = []
        for s in scores:
            s_f = float(s)
            if self.threshold is None:
                fired = s_f > 0.0
            else:
                fired = s_f > self.threshold
            rationale = self.rationale_fn(s_f, self.threshold, fired)
            results.append(DetectorResult(
                detector_name=self.name,
                score=s_f,
                fired=bool(fired),
                threshold=self.threshold,
                rationale=rationale,
                role=self.role,
            ))
        return results


# ── concrete adapter factories ──────────────────────────────────────────────
#
# These mirror the four+one existing detectors. Importing the inner classes
# is deferred to the factory body so this module doesn't pull sklearn at
# import time (the test that asserts "no heavy imports" stays green).


def make_distance_adapter(train_X: np.ndarray, *,
                          threshold: float | None = None,
                          k: int = 3,
                          name: str = "distance") -> DetectorAdapter:
    """Mahalanobis k-NN distance baseline. k=3 is locked v0.2."""
    from physmap.pipeline.detectors import DistanceDetector
    inner = DistanceDetector(train_X=train_X, k=k)
    return DetectorAdapter(
        name=name, inner=inner, threshold=threshold,
        rationale_fn=_distance_rationale(k),
        extra_meta={"k": k},
    )


def _distance_rationale(k: int) -> RationaleFn:
    def _build(score: float, threshold: float | None, fired: bool) -> str:
        kind = f"Mahalanobis k={k} mean k-NN distance"
        if not fired:
            return f"distance: quiet ({kind}={score:.3g} <= threshold={threshold:.3g})"
        return f"distance: FIRED ({kind}={score:.3g} > threshold={threshold:.3g})"
    return _build


# GP-variance relative-variance threshold FLOOR. The gp_variance threshold is
# calibrated at a percentile of TRAIN self-scores (guardrail._fit_core and
# gate_core.build_decision_adapters). That percentile-of-self DEGENERATES under
# dense training: a GP that interpolates near-duplicate inputs has near-zero
# posterior std at train points, collapsing the threshold toward 0, so it fires on
# any test point with even a benign relative variance. Floor the calibrated
# threshold at a small absolute relative variance below which the GP is
# definitionally confident.
#
# Justification (documented judgment — Benchmark v0.4; full record in
# results/benchmark_v0_4/gpvar_floor_investigation.md). The pathology is confirmed
# on TWO independent dense-training cases: Casper (benign ~1.06% predictive variance
# tripping a 0.0035 threshold under 159-pt training) and NACA's cross-validated set
# (gp_variance 0.05-0.72%, threshold collapsed to ~7e-4 by ~40 near-duplicate pts).
# Sweeping the floor over the v0.4 cross-domain matrix, any value in [0.02, 0.20] is
# INVARIANT for every cell whose baseline genuinely catches the failure (the NACA
# matrix WIN, the dirker/velazquez middles, and the Marineau negative control are
# all unchanged) and recovers Casper. The WIDTH of that invariant band is the
# evidence the floor is principled, not tuned-to-win: it is not a knob that trades
# cells off against each other; it is the range over which the benchmark does not
# move. 0.05 (5% relative predictive variance) sits centrally in the band.
#
# SCOPE: applied at BOTH gp_variance threshold-calibration sites — the shipped
# public API (guardrail._fit_core) and the Stage-1 harness (gate_core). Effect on
# the frozen path is verdict-NEUTRAL: phase1 stays byte-identical (Pareto counts
# unchanged); only the NACA cross-validated phase2 disposition SUB-mix refines (the
# artifactual restrict-cou rows — gp_variance firing on <1% variance — become
# characterize-region) and is rebanked (results/physmap_d3_phase2_gate). The NACA
# wpd path (gp_variance ~0.36, above floor) is provably unchanged.
GP_VARIANCE_REL_FLOOR = 0.05


def make_gp_variance_adapter(train_X: np.ndarray, train_y: np.ndarray, *,
                             threshold: float | None = None,
                             n_restarts: int = 3,
                             random_state: int = 20260605,
                             name: str = "gp_variance") -> DetectorAdapter:
    """GP with NEUTRAL mean + Matérn-5/2 kernel. Locked v0.2; do not change."""
    from physmap.pipeline.detectors import GPVarianceDetector
    inner = GPVarianceDetector(
        train_X=train_X, train_y=train_y,
        n_restarts=n_restarts, random_state=random_state,
    )
    return DetectorAdapter(
        name=name, inner=inner, threshold=threshold,
        rationale_fn=_gp_rationale(),
    )


def _gp_rationale() -> RationaleFn:
    def _build(score: float, threshold: float | None, fired: bool) -> str:
        kind = "GP posterior std / |mean|"
        if not fired:
            return f"gp_variance: quiet ({kind}={score:.3g} <= threshold={threshold:.3g})"
        return f"gp_variance: FIRED ({kind}={score:.3g} > threshold={threshold:.3g})"
    return _build


def make_ensemble_variance_adapter(train_X: np.ndarray, train_y: np.ndarray, *,
                                   threshold: float | None = None,
                                   n_bootstraps: int = 50,
                                   degree: int = 2,
                                   random_state: int = 20260605,
                                   name: str = "ensemble_variance") -> DetectorAdapter:
    """Bootstrapped degree-2 polynomial ensemble disagreement. Locked v0.2."""
    from physmap.pipeline.detectors import EnsembleVarianceDetector
    inner = EnsembleVarianceDetector(
        train_X=train_X, train_y=train_y,
        n_bootstraps=n_bootstraps, degree=degree, random_state=random_state,
    )
    return DetectorAdapter(
        name=name, inner=inner, threshold=threshold,
        rationale_fn=_ensemble_rationale(n_bootstraps, degree),
    )


def _ensemble_rationale(n_boot: int, degree: int) -> RationaleFn:
    def _build(score: float, threshold: float | None, fired: bool) -> str:
        kind = f"bootstrap deg-{degree} ensemble (n_boot={n_boot}) std/|mean|"
        if not fired:
            return f"ensemble_variance: quiet ({kind}={score:.3g} <= threshold={threshold:.3g})"
        return f"ensemble_variance: FIRED ({kind}={score:.3g} > threshold={threshold:.3g})"
    return _build


def make_closure_validity_adapter(closure_id: str,
                                  feature_names: Sequence[str], *,
                                  name: str = "closure_validity",
                                  corpus_path: Any = None) -> DetectorAdapter:
    """Literature-derived validity-range-distance signal. THE DIFFERENTIATOR.

    No threshold: fires on `score > 0` (i.e., outside the closure's
    corpus-recorded validity rectangle). NO training-data dependence — pure
    literature lookup. This is the detector whose structural property
    differentiates PhysMAP from input-distribution novelty baselines.
    """
    from physmap.pipeline.validity_signal import ValidityRangeDistanceDetector
    kwargs: dict[str, Any] = {
        "closure_id": closure_id,
        "feature_names": list(feature_names),
    }
    if corpus_path is not None:
        kwargs["corpus_path"] = corpus_path
    inner = ValidityRangeDistanceDetector(**kwargs)
    return DetectorAdapter(
        name=name,
        inner=inner,
        threshold=None,                 # literature-only; fires on > 0
        rationale_fn=_validity_rationale(closure_id),
        extra_meta={"closure_id": closure_id, "feature_names": tuple(feature_names)},
    )


def _validity_rationale(closure_id: str) -> RationaleFn:
    def _build(score: float, threshold: float | None, fired: bool) -> str:
        # threshold is always None for the validity detector
        if not fired:
            return (f"closure_validity: quiet (test point INSIDE the validated "
                    f"rectangle of {closure_id!r}; L2-distance=0)")
        return (f"closure_validity: FIRED (test point OUTSIDE the validated "
                f"rectangle of {closure_id!r}; L2-distance={score:.3g})")
    return _build


# ── the pipeline ────────────────────────────────────────────────────────────


@dataclass
class Pipeline:
    """Linear D3 signal pipeline.

    Order of operations per `run(rows)`:
      1. Extract features once via `feature_extractor`.
      2. Each decision stage emits one DetectorResult per row (batch eval).
      3. Each justification stage enriches per-row provenance from row.meta
         (and may consult the just-computed decision signals).
      4. The aggregator reduces ONLY decision signals -> Verdict per row.
      5. Assemble Assessment objects (operating_point, verdict, signals,
         justification, rationale) — one per input row.

    `feature_extractor` is a callable `list[dict] -> np.ndarray`; the
    canonical implementation is `d3_detectors.extract_features_batch`.
    """
    feature_extractor: Callable[[Sequence[dict]], np.ndarray]
    decision_stages: list[Detector]
    aggregator: Aggregator
    justification_stages: list[JustificationStage] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.decision_stages:
            raise ValueError(
                "Pipeline requires at least one decision stage; otherwise the "
                "aggregator has nothing to weigh."
            )
        for stage in self.decision_stages:
            if getattr(stage, "role", "decision") != "decision":
                raise ValueError(
                    f"decision_stages must have role='decision'; stage "
                    f"{stage.name!r} has role={getattr(stage, 'role', '?')!r}. "
                    f"Move it to justification_stages."
                )
        for stage in self.justification_stages:
            if getattr(stage, "role", "justification") != "justification":
                raise ValueError(
                    f"justification_stages must have role='justification'; "
                    f"stage {stage.name!r} has role="
                    f"{getattr(stage, 'role', '?')!r}."
                )

    def run(self, rows: Sequence[Any]) -> list[Assessment]:
        """Score a sequence of stage-1 Row objects through the pipeline.

        `rows` items must expose `.meta` (dict) and `.operating_point` (tuple);
        the canonical `physmap.substrate.stage1_ingest.Row` satisfies this.
        """
        if not rows:
            return []
        metas = [r.meta for r in rows]
        test_X = self.feature_extractor(metas)

        # Step 2 — decision stages, batched
        per_detector: dict[str, list[DetectorResult]] = {}
        for stage in self.decision_stages:
            per_detector[stage.name] = stage.evaluate(test_X)
            if len(per_detector[stage.name]) != len(rows):
                raise RuntimeError(
                    f"detector {stage.name!r} returned "
                    f"{len(per_detector[stage.name])} results for {len(rows)} "
                    f"rows; should be 1-to-1."
                )

        # Step 3 — justification stages, per row (cheap; not vectorized)
        # Step 4 — aggregator per row
        # Step 5 — assemble
        assessments: list[Assessment] = []
        for i, row in enumerate(rows):
            decision = {name: results[i] for name, results in per_detector.items()}
            justification: dict[str, dict[str, Any]] = {}
            for js in self.justification_stages:
                justification[js.name] = js.enrich(row.meta, decision)
            verdict = self.aggregator.combine(decision)
            assessments.append(Assessment(
                operating_point=row.operating_point,
                verdict=verdict.label,
                decision_signals=decision,
                justification_signals=justification,
                rationale=verdict.rationale,
            ))
        return assessments
