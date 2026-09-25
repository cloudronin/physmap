"""D3 pipeline + aggregator tests.

Three layers of pinning:

  1. ADAPTER WRAP FIDELITY. Each `make_*_adapter` factory wraps an existing
     detector and emits scores byte-equal to the inner detector's `signal()`
     output. Thresholds and rationales are layered on top without perturbing
     the math.

  2. PIPELINE STRUCTURE. Decision-stages-only Pipeline + Aggregator drives
     batched evaluation, emits one Assessment per row, and rejects role
     misconfigurations (decision stage tagged as justification, etc.).

  3. AGGREGATOR LOGIC. AnyFired / CorpusGated / WeightedVote each produce
     the expected verdict + a rationale that names which detectors fired.
     Edge cases (empty signals, missing detector, dead overrides) raise.

Integration test at the end runs the full pipeline end-to-end on a
synthetic 2-feature training set and confirms per-row Assessments match
the expected structure.
"""

from __future__ import annotations

import numpy as np
import pytest

from physmap.pipeline.aggregators import AnyFired, CorpusGated, WeightedVote
from physmap.pipeline.detectors import (
    DistanceDetector,
    EnsembleVarianceDetector,
    GPVarianceDetector,
    extract_features_batch,
)
from physmap.pipeline.core import (
    Assessment,
    DetectorAdapter,
    DetectorResult,
    Pipeline,
    Verdict,
    make_closure_validity_adapter,
    make_distance_adapter,
    make_ensemble_variance_adapter,
    make_gp_variance_adapter,
)
from physmap.substrate.stage1_ingest import Mechanism, Row


# ── helpers ─────────────────────────────────────────────────────────────────

RNG_SEED = 20260605


def _toy_train(n: int = 20, d: int = 2, seed: int = RNG_SEED):
    rng = np.random.default_rng(seed)
    train_X = rng.normal(size=(n, d))
    # toy "Nu" target that's a polynomial of features
    train_y = 50.0 + 3.0 * train_X[:, 0] + 2.0 * train_X[:, 1] ** 2
    train_closure_pred = train_y + rng.normal(scale=0.5, size=n)
    return train_X, train_y, train_closure_pred


def _toy_rows(n: int = 5, seed: int = RNG_SEED + 1) -> list[Row]:
    """Build Row stand-ins for pipeline.run() input. Mech contributions are
    placeholders — pipeline doesn't care; it reads meta + operating_point."""
    rng = np.random.default_rng(seed)
    rows: list[Row] = []
    for i in range(n):
        re = float(10 ** rng.uniform(3, 5))
        pr = float(rng.uniform(0.5, 6.0))
        rows.append(Row(
            operating_point=(i, round(re, 2)),
            surrogate_prediction=100.0,
            cfd_truth=100.0,
            truth_source="experimental",
            cfd_uncertainty=1.0,
            guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
            mechanisms=[Mechanism(
                name="m", closure_id="gnielinski-1976",
                operating_value=re, calib_lo=3000.0, calib_hi=5.0e6,
                contribution=1.0,
            )],
            meta={"Re": re, "Pr": pr},
        ))
    return rows


# ── 1. ADAPTER WRAP FIDELITY ────────────────────────────────────────────────

def test_distance_adapter_signal_byte_equal_to_inner():
    train_X, _, _ = _toy_train()
    adapter = make_distance_adapter(train_X, threshold=2.0)
    inner = DistanceDetector(train_X=train_X)
    test_X = np.array([[0.5, 0.5], [3.0, -1.0]])
    assert np.array_equal(adapter.signal(test_X), inner.signal(test_X))


def test_gp_adapter_signal_byte_equal_to_inner():
    train_X, train_y, _ = _toy_train()
    adapter = make_gp_variance_adapter(train_X, train_y, threshold=0.1)
    inner = GPVarianceDetector(train_X=train_X, train_y=train_y)
    test_X = np.array([[0.5, 0.5], [3.0, -1.0]])
    np.testing.assert_array_equal(adapter.signal(test_X), inner.signal(test_X))


def test_ensemble_adapter_signal_byte_equal_to_inner():
    train_X, train_y, _ = _toy_train()
    adapter = make_ensemble_variance_adapter(train_X, train_y, threshold=0.1)
    inner = EnsembleVarianceDetector(train_X=train_X, train_y=train_y)
    test_X = np.array([[0.5, 0.5], [3.0, -1.0]])
    np.testing.assert_array_equal(adapter.signal(test_X), inner.signal(test_X))


def test_adapter_fired_flag_and_rationale():
    train_X, _, _ = _toy_train()
    adapter = make_distance_adapter(train_X, threshold=0.5)
    # Pick a test point far from training -> score > threshold -> fired
    test_X = np.array([[10.0, 10.0]])
    results = adapter.evaluate(test_X)
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, DetectorResult)
    assert r.fired is True
    assert r.score > 0.5
    assert "FIRED" in r.rationale
    assert "Mahalanobis" in r.rationale


def test_adapter_threshold_none_fires_on_positive_only():
    """Literature-only path: threshold=None -> fired iff score > 0."""
    class _Stub:
        def signal(self, x):
            return np.array([0.0, 0.5, 1e-6])
    adapter = DetectorAdapter(name="stub", inner=_Stub(), threshold=None)
    results = adapter.evaluate(np.zeros((3, 1)))
    assert [r.fired for r in results] == [False, True, True]
    assert all(r.threshold is None for r in results)
    assert "literature-only" in results[1].rationale


def test_adapter_rejects_inner_without_signal_method():
    with pytest.raises(TypeError, match="must expose .signal"):
        DetectorAdapter(name="bad", inner=object())


# ── 2. PIPELINE STRUCTURE ───────────────────────────────────────────────────

class _AlwaysFireDetector:
    """Test fixture: returns the same score for every test point."""
    def __init__(self, name: str, score: float = 1.0,
                 role: str = "decision", threshold: float | None = 0.5):
        self.name = name
        self.role = role
        self._score = score
        self.threshold = threshold

    def evaluate(self, test_X: np.ndarray) -> list[DetectorResult]:
        return [
            DetectorResult(
                detector_name=self.name, score=self._score,
                fired=(self._score > (self.threshold or 0.0)),
                threshold=self.threshold,
                rationale=f"{self.name}: stub score={self._score}",
                role=self.role,
            )
            for _ in range(len(test_X))
        ]


class _RecordingJustifier:
    """Test justification stage; records the decision_signals it saw."""
    def __init__(self, name: str = "rec"):
        self.name = name
        self.role = "justification"
        self.calls: list[dict] = []

    def enrich(self, row_meta, decision_signals):
        self.calls.append({"meta": row_meta, "signals": list(decision_signals)})
        return {"closure_id": "stub-closure", "sources": ["stub-source"]}


def test_pipeline_requires_decision_stages():
    with pytest.raises(ValueError, match="at least one decision stage"):
        Pipeline(
            feature_extractor=lambda metas: np.zeros((len(metas), 1)),
            decision_stages=[],
            aggregator=AnyFired(),
        )


def test_pipeline_rejects_decision_with_justification_role():
    with pytest.raises(ValueError, match="role='decision'"):
        Pipeline(
            feature_extractor=lambda metas: np.zeros((len(metas), 1)),
            decision_stages=[_AlwaysFireDetector("bad", role="justification")],
            aggregator=AnyFired(),
        )


def test_pipeline_rejects_justification_with_decision_role():
    with pytest.raises(ValueError, match="role='justification'"):
        good_dec = _AlwaysFireDetector("good", role="decision")

        class _BadJustifier:
            name = "bad_just"
            role = "decision"
            def enrich(self, *a, **k): return {}

        Pipeline(
            feature_extractor=lambda metas: np.zeros((len(metas), 1)),
            decision_stages=[good_dec],
            aggregator=AnyFired(),
            justification_stages=[_BadJustifier()],
        )


def test_pipeline_empty_rows_returns_empty():
    pipe = Pipeline(
        feature_extractor=lambda metas: np.zeros((len(metas), 1)),
        decision_stages=[_AlwaysFireDetector("d1", score=2.0)],
        aggregator=AnyFired(),
    )
    assert pipe.run([]) == []


def test_pipeline_emits_one_assessment_per_row():
    rows = _toy_rows(n=4)
    pipe = Pipeline(
        feature_extractor=lambda metas: extract_features_batch(metas, ["log10_Re", "Pr"]),
        decision_stages=[
            _AlwaysFireDetector("d1", score=2.0, threshold=0.5),
            _AlwaysFireDetector("d2", score=0.1, threshold=0.5),
        ],
        aggregator=AnyFired(),
    )
    assessments = pipe.run(rows)
    assert len(assessments) == 4
    for a, r in zip(assessments, rows):
        assert isinstance(a, Assessment)
        assert a.operating_point == r.operating_point
        assert set(a.decision_signals.keys()) == {"d1", "d2"}
        assert a.verdict == "fire"     # d1 always fires
        assert "d1" in a.rationale


def test_pipeline_justification_stage_runs_and_attaches():
    rows = _toy_rows(n=3)
    just = _RecordingJustifier(name="evidence_stub")
    pipe = Pipeline(
        feature_extractor=lambda metas: extract_features_batch(metas, ["log10_Re", "Pr"]),
        decision_stages=[_AlwaysFireDetector("d1", score=1.0, threshold=0.5)],
        justification_stages=[just],
        aggregator=AnyFired(),
    )
    out = pipe.run(rows)
    assert len(just.calls) == 3
    for a in out:
        assert "evidence_stub" in a.justification_signals
        assert a.justification_signals["evidence_stub"]["closure_id"] == "stub-closure"


# ── 3. AGGREGATOR LOGIC ─────────────────────────────────────────────────────

def _result(name: str, fired: bool, score: float = 1.0,
            threshold: float | None = 0.5) -> DetectorResult:
    return DetectorResult(
        detector_name=name, score=score, fired=fired,
        threshold=threshold,
        rationale=f"{name}: {'FIRED' if fired else 'quiet'} score={score}",
        role="decision",
    )


# ── AnyFired ─────────────────────────────────────────────────────────────────

def test_any_fired_all_quiet_returns_quiet():
    sigs = {"a": _result("a", False), "b": _result("b", False)}
    v = AnyFired().combine(sigs)
    assert v.label == "quiet"
    assert "all detectors quiet" in v.rationale


def test_any_fired_one_fires_returns_fire():
    sigs = {"a": _result("a", False), "b": _result("b", True)}
    v = AnyFired().combine(sigs)
    assert v.label == "fire"
    assert "b: FIRED" in v.rationale


def test_any_fired_multiple_fire_returns_fire_naming_all():
    sigs = {"a": _result("a", True), "b": _result("b", True)}
    v = AnyFired().combine(sigs)
    assert v.label == "fire"
    assert "a: FIRED" in v.rationale and "b: FIRED" in v.rationale


def test_any_fired_empty_signals_raises():
    with pytest.raises(ValueError, match="no decision signals"):
        AnyFired().combine({})


# ── CorpusGated ─────────────────────────────────────────────────────────────

def _gated() -> CorpusGated:
    return CorpusGated(
        baseline_names=("distance", "gp_variance"),
        corpus_names=("closure_validity",),
    )


def test_corpus_gated_baselines_quiet_corpus_fires_returns_fire():
    sigs = {
        "distance":         _result("distance",          False),
        "gp_variance":      _result("gp_variance",       False),
        "closure_validity": _result("closure_validity",  True, threshold=None),
    }
    v = _gated().combine(sigs)
    assert v.label == "fire"
    assert "corpus catches what baselines missed" in v.rationale


def test_corpus_gated_baseline_fires_returns_quiet():
    sigs = {
        "distance":         _result("distance",          True),
        "gp_variance":      _result("gp_variance",       False),
        "closure_validity": _result("closure_validity",  False, threshold=None),
    }
    v = _gated().combine(sigs)
    assert v.label == "quiet"
    assert "baseline fired" in v.rationale.lower() or "corpus quiet" in v.rationale.lower()


def test_corpus_gated_both_fire_returns_quiet():
    sigs = {
        "distance":         _result("distance",          True),
        "gp_variance":      _result("gp_variance",       True),
        "closure_validity": _result("closure_validity",  True, threshold=None),
    }
    v = _gated().combine(sigs)
    assert v.label == "quiet"
    assert "baselines AND corpus" in v.rationale.lower() or "both" in v.rationale.lower()


def test_corpus_gated_all_quiet_returns_quiet():
    sigs = {
        "distance":         _result("distance",          False),
        "gp_variance":      _result("gp_variance",       False),
        "closure_validity": _result("closure_validity",  False, threshold=None),
    }
    v = _gated().combine(sigs)
    assert v.label == "quiet"
    assert "all detectors quiet" in v.rationale


def test_corpus_gated_missing_detector_raises():
    with pytest.raises(KeyError, match="missing required detectors"):
        _gated().combine({"distance": _result("distance", False)})


# ── WeightedVote ────────────────────────────────────────────────────────────

def test_weighted_vote_threshold_met_returns_fire():
    wv = WeightedVote(weights={"a": 0.6, "b": 0.5}, vote_threshold=1.0)
    sigs = {"a": _result("a", True), "b": _result("b", True)}
    v = wv.combine(sigs)
    assert v.label == "fire"
    assert "1.1" in v.rationale     # 0.6 + 0.5 = 1.1


def test_weighted_vote_threshold_not_met_returns_quiet():
    wv = WeightedVote(weights={"a": 0.4, "b": 0.5}, vote_threshold=1.0)
    sigs = {"a": _result("a", True), "b": _result("b", True)}
    v = wv.combine(sigs)
    assert v.label == "quiet"


def test_weighted_vote_empty_weights_raises():
    with pytest.raises(ValueError, match="non-empty"):
        WeightedVote(weights={})


def test_weighted_vote_negative_weight_raises():
    with pytest.raises(ValueError, match="cannot be negative"):
        WeightedVote(weights={"a": -0.1, "b": 1.0})


def test_weighted_vote_nonpositive_threshold_raises():
    with pytest.raises(ValueError, match="must be > 0"):
        WeightedVote(weights={"a": 1.0}, vote_threshold=0.0)


def test_weighted_vote_unit_weights_degenerates_to_any_fired_for_unit_threshold():
    """Sanity: weights all 1.0 and vote_threshold=1.0 == AnyFired."""
    wv = WeightedVote(weights={"a": 1.0, "b": 1.0}, vote_threshold=1.0)
    sigs_one_fired = {"a": _result("a", False), "b": _result("b", True)}
    sigs_none = {"a": _result("a", False), "b": _result("b", False)}
    assert wv.combine(sigs_one_fired).label == "fire"
    assert wv.combine(sigs_none).label == "quiet"


# ── 4. INTEGRATION (Pipeline + adapters + aggregator end-to-end) ────────────

def test_pipeline_with_real_distance_and_gp_adapters_runs():
    """Smoke test with REAL adapters wrapping the locked detectors.
    Confirms the wiring; doesn't pin numeric outputs (those are pinned by
    test_closures_registry + test_d3_detectors)."""
    train_X, train_y, _ = _toy_train(n=20)
    # Calibrate thresholds at the 75th percentile of training self-scores
    # (mirrors the locked recipe in d3_ensemble_rescore.py:194).
    distance_inner = DistanceDetector(train_X=train_X)
    gp_inner = GPVarianceDetector(train_X=train_X, train_y=train_y)
    tau_dist = float(np.quantile(distance_inner.signal(train_X), 0.75))
    tau_gp = float(np.quantile(gp_inner.signal(train_X), 0.75))

    decision_stages = [
        make_distance_adapter(train_X, threshold=tau_dist),
        make_gp_variance_adapter(train_X, train_y, threshold=tau_gp),
    ]

    pipe = Pipeline(
        feature_extractor=lambda metas: np.array([
            [float(np.log10(m["Re"])), float(m["Pr"])] for m in metas
        ]),
        decision_stages=decision_stages,
        aggregator=AnyFired(),
    )

    rows = _toy_rows(n=6)
    out = pipe.run(rows)
    assert len(out) == 6
    for a in out:
        assert a.verdict in ("fire", "quiet")
        assert set(a.decision_signals) == {"distance", "gp_variance"}
        for r in a.decision_signals.values():
            assert r.role == "decision"
            assert r.detector_name in ("distance", "gp_variance")


def test_closure_validity_adapter_fires_outside_validated_range():
    """Real validity adapter on Gnielinski's corpus entry. A point with
    Re < 3000 is outside the validated [3000, 5e6] range and should fire."""
    # Build the feature vector in the same shape ValidityRangeDistanceDetector
    # expects: a 2D array whose columns correspond to feature_names.
    adapter = make_closure_validity_adapter(
        closure_id="gnielinski-1976",
        feature_names=("log10_Re", "Pr"),
    )
    # Point INSIDE the rectangle: Re=1e4 (>= 3000), Pr=1.0 (>= 0.5)
    inside = np.array([[float(np.log10(1.0e4)), 1.0]])
    inside_results = adapter.evaluate(inside)
    assert inside_results[0].fired is False
    assert inside_results[0].score == 0.0
    assert "INSIDE" in inside_results[0].rationale

    # Point OUTSIDE on Re: Re=100 (< 3000)
    outside = np.array([[float(np.log10(100.0)), 1.0]])
    outside_results = adapter.evaluate(outside)
    assert outside_results[0].fired is True
    assert outside_results[0].score > 0.0
    assert outside_results[0].threshold is None
    assert "OUTSIDE" in outside_results[0].rationale
    assert "gnielinski-1976" in outside_results[0].rationale
