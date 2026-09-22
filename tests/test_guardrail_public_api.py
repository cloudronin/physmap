"""CredibilityGuardrail public-API tests — one per spec Verification bullet.

These exercise the SHIPPED public surface (physmap.CredibilityGuardrail). They do
NOT touch the locked phase1_gate / assessment_v06 tests, which keep guarding the
internals byte-for-byte.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from physmap import (
    Assessment,
    ClosureValidityDetectorConfig,
    ColumnMap,
    CredibilityGuardrail,
    DistanceDetectorConfig,
    Disposition,
    GPVarianceDetectorConfig,
    Observability,
    Regime,
    Verdict,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
# Checkout-only fixture. NACA TN-1451 (1947) is a US Government work in the public
# domain; the digitisation is a two-reader cross-validated visual read of Fig 10.
NACA_CSV = REPO_ROOT / "data" / "naca" / "cross_validated_fig10.csv"
COORDS = ["Re", "Pr", "x_over_D"]
X_OVER_D_CUTOFF = 10.0


# ── data helpers ──────────────────────────────────────────────────────────────

def _load_naca():
    rows = []
    with open(NACA_CSV) as f:
        for r in csv.DictReader(line for line in f if not line.lstrip().startswith("#")):
            rows.append({k: float(v) if _isnum(v) else v for k, v in r.items()})
    return rows


def _isnum(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _split_naca():
    rows = _load_naca()
    train = [r for r in rows if r["x_over_D"] >= X_OVER_D_CUTOFF]
    test = [r for r in rows if r["x_over_D"] < X_OVER_D_CUTOFF]
    Xtr = np.array([[r[c] for c in COORDS] for r in train])
    ytr = np.array([r["Nu_meas"] for r in train])
    Xte = np.array([[r[c] for c in COORDS] for r in test])
    yte = np.array([r["Nu_meas"] for r in test])
    return train, test, Xtr, ytr, Xte, yte


# ── 1. Locked NACA reproduction through the public API ────────────────────────

def test_naca_reproduction_unobservable_reject():
    _, _, Xtr, ytr, Xte, _ = _split_naca()
    g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    assert g.mode == "physics_active"
    assert g.observability_classification["x_over_D"] is Observability.UNOBSERVABLE
    assert g.observability_classification["reynolds_number"] is Observability.OBSERVABLE
    g.fit(Xtr, train_y=ytr, columns=ColumnMap(inputs=COORDS))
    res = g.assess(Xte, columns=ColumnMap(inputs=COORDS))

    assert len(res) == 45                                  # matches locked gate split
    assert all(a.verdict is Verdict.REJECT for a in res)   # corpus catches entrance points
    assert all(a.fired_bound_variable == "x_over_D" for a in res)
    assert all(a.observability is Observability.UNOBSERVABLE for a in res)
    # closure_validity fired and baselines silent on the entrance region
    from physmap import DetectorKind
    a = res[0]
    assert a.signals[DetectorKind.CLOSURE_VALIDITY].fired
    assert not a.signals[DetectorKind.GP_VARIANCE].fired
    assert "gnielinski-1976" in a.rationale and "x_over_D" in a.rationale


def test_naca_reproduction_steelman_set_matches_gate_semantics():
    """Pin the steelman baseline set (the phase1_gate detectors) through the
    public API; the UNOBSERVABLE→REJECT headline holds independent of the set."""
    _, _, Xtr, ytr, Xte, _ = _split_naca()
    g = CredibilityGuardrail(
        surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE,
        detectors=[GPVarianceDetectorConfig(), DistanceDetectorConfig(),
                   ClosureValidityDetectorConfig()],
    )
    g.fit(Xtr, train_y=ytr, columns=ColumnMap(inputs=COORDS))
    res = g.assess(Xte, columns=ColumnMap(inputs=COORDS))
    assert all(a.verdict is Verdict.REJECT for a in res)
    assert all(a.fired_bound_variable == "x_over_D" for a in res)


# ── 2. Data-shape validation (fail loudly at fit, not silent no-fire) ─────────

def test_fit_without_bound_variable_raises():
    g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    X = np.array([[5e4, 5.0], [6e4, 4.0]])
    with pytest.raises(ValueError, match="x_over_D"):
        g.fit(X, train_y=np.array([100.0, 110.0]), columns=ColumnMap(inputs=["Re", "Pr"]))


# ── 3. Closure-validity detector: graded margin + governing variable ──────────

def test_detector_graded_margin_and_fired_variable():
    from physmap.pipeline.validity_signal import ValidityRangeDistanceDetector
    det = ValidityRangeDistanceDetector(
        closure_id="gnielinski-1976", feature_names=["log10_Re", "Pr", "x_over_D"])
    X = np.array([[np.log10(5e4), 5.0, 2.0],     # x/D past bound
                  [np.log10(5e4), 5.0, 50.0]])    # inside
    per = det.evaluate_bounds(X)
    g0 = det.governing_bound(per[0])
    assert g0 is not None and g0.coord == "x_over_D" and g0.margin > 0 and g0.side == "below"
    assert det.governing_bound(per[1]) is None    # inside every bound
    # the detector reports the bound; it does NOT carry observability
    assert not hasattr(g0, "observability")


# ── 4. Forrest do-no-harm: OBSERVABLE ⇒ verdict == statistical-only ───────────

def _synthetic_rect_channel():
    rng = np.random.default_rng(7)
    # train inside modified-sparrow Re∈[10000,70000], Pr∈[2.2,5.4]
    Re_tr = rng.uniform(15000, 65000, 40)
    Pr_tr = rng.uniform(3.0, 5.0, 40)
    Xtr = np.column_stack([Re_tr, Pr_tr])
    ytr = 0.023 * Re_tr ** 0.8 * Pr_tr ** 0.4            # synthetic Nu
    # test: half sub-critical (Re far below range AND far from train), half in-range
    Re_te = np.concatenate([rng.uniform(3000, 7000, 15), rng.uniform(20000, 60000, 15)])
    Pr_te = rng.uniform(3.0, 5.0, 30)
    Xte = np.column_stack([Re_te, Pr_te])
    return Xtr, ytr, Xte


def test_forrest_do_no_harm_observable_equals_statistical_only():
    Xtr, ytr, Xte = _synthetic_rect_channel()
    cm = ColumnMap(inputs=["Re", "Pr"])

    phys = CredibilityGuardrail(
        surrogate_inputs=["Re", "Pr"],
        regime=Regime.INTERNAL_FORCED_CONVECTION_RECT_CHANNEL)
    stat = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.UNLISTED)
    assert phys.mode == "physics_active" and stat.mode == "statistical_only"
    # Re is an observable surrogate input → the corpus axis is redundant
    assert phys.observability_classification["reynolds_number"] is Observability.OBSERVABLE

    phys.fit(Xtr, train_y=ytr, columns=cm)
    stat.fit(Xtr, train_y=ytr, columns=cm)
    rp = phys.assess(Xte, columns=cm)
    rs = stat.assess(Xte, columns=cm)
    # do-no-harm: identical verdicts (corpus never double-counted on an observable axis)
    assert [a.verdict for a in rp] == [a.verdict for a in rs]
    assert [a.disposition for a in rp] == [a.disposition for a in rs]


# ── 5. PARTIAL defers honestly (aggregator branch; end-to-end deferred) ───────

def test_partial_branch_defers_to_review():
    from physmap.guardrail.aggregator_observability import ObservabilityWeightedAggregator
    from physmap.pipeline.validity_signal import PerBoundMargin
    from physmap.pipeline.core import DetectorResult as CoreResult

    agg = ObservabilityWeightedAggregator()
    fb = PerBoundMargin("richardson_number", "Ri", 0.4, "claimed", "above")
    cv = CoreResult("closure_validity", 0.4, True, None, "fired")
    out = agg.combine(
        decision_signals={"closure_validity": cv},
        observability={"richardson_number": Observability.PARTIAL},
        fired_bound=fb, severities={})
    assert out.verdict is Verdict.UNCERTAIN
    assert out.disposition is Disposition.REVIEW


def test_classifier_marks_buoyancy_partial():
    from physmap.guardrail.classify import classify_observability, load_default_corpus_index
    obs = classify_observability(
        ["Re", "Pr"], Regime.MIXED_CONVECTION_HORIZONTAL_TUBE, load_default_corpus_index())
    assert obs["richardson_number"] is Observability.PARTIAL


# ── 6. UNLISTED regime: statistical-only, no crash ────────────────────────────

def test_unlisted_statistical_only_runs():
    Xtr, ytr, Xte = _synthetic_rect_channel()
    cm = ColumnMap(inputs=["Re", "Pr"])
    g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.UNLISTED)
    assert g.mode == "statistical_only"
    assert g.observability_classification == {}
    assert g.resolved_closures == []
    g.fit(Xtr, train_y=ytr, columns=cm)
    res = g.assess(Xte, columns=cm)
    assert len(res) == len(Xte)
    from physmap import DetectorKind
    assert all(DetectorKind.CLOSURE_VALIDITY not in a.signals for a in res)


# ── 7. Determinism — same inputs → identical rationale ────────────────────────

def test_determinism_identical_rationale():
    _, _, Xtr, ytr, Xte, _ = _split_naca()
    g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    g.fit(Xtr, train_y=ytr, columns=ColumnMap(inputs=COORDS))
    r1 = g.assess(Xte, columns=ColumnMap(inputs=COORDS))
    r2 = g.assess(Xte, columns=ColumnMap(inputs=COORDS))
    assert [a.rationale for a in r1] == [a.rationale for a in r2]


# ── 8. graph=True → SHACL-conformant v0.6 subgraph ────────────────────────────

def _find_shacl():
    import os
    cands = []
    if os.environ.get("UOFA_REPO"):
        cands.append(Path(os.environ["UOFA_REPO"]) / "packs/disposition/shapes/disposition_shapes.ttl")
    cur = REPO_ROOT
    for _ in range(8):
        cur = cur.parent
        cands.append(cur / "uofa" / "packs/disposition/shapes/disposition_shapes.ttl")
        if cur.parent == cur:
            break
    # No hardcoded developer paths: this test is skipped unless UOFA_REPO is set
    # or a `uofa` checkout sits beside this one. `uofa` is an OPTIONAL extra here
    # ([jsonld], for evidence export), so its absence is the normal case.
    return next((c for c in cands if c.exists()), None)


def test_to_graph_shacl_conforms():
    shacl = _find_shacl()
    if shacl is None:
        pytest.skip("disposition SHACL pack not found (set UOFA_REPO or checkout sibling uofa)")
    import pyshacl
    import rdflib

    _, _, Xtr, ytr, Xte, _ = _split_naca()
    g = CredibilityGuardrail(
        surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE,
        surrogate=lambda X: np.full(len(X), 120.0))   # predictions for the Discrepancy node

    # train via the same temp CSVs so truth flows from the file (graph needs truth)
    import tempfile
    rows = _load_naca()
    d = Path(tempfile.mkdtemp())
    fields = list(rows[0].keys())
    for stem, pred in (("train", lambda r: r["x_over_D"] >= 10), ("test", lambda r: r["x_over_D"] < 10)):
        with open(d / f"{stem}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields); w.writeheader()
            w.writerows([r for r in rows if pred(r)])
    cm = ColumnMap(inputs=COORDS, truth="Nu_meas")
    g.fit(d / "train.csv", columns=cm)
    res = g.assess(d / "test.csv", columns=cm, graph=True)

    shacl_graph = rdflib.Graph(); shacl_graph.parse(shacl, format="turtle")
    ctx = (REPO_ROOT / "physmap" / "fixtures" / "context" / "v0.6.jsonld").as_uri()
    for a in res[:5]:
        doc = a.to_graph(); doc["@context"] = ctx
        dg = rdflib.Graph(); dg.parse(data=json.dumps(doc), format="json-ld")
        conforms, _, text = pyshacl.validate(dg, shacl_graph=shacl_graph, inference="rdfs")
        assert conforms, f"SHACL failed:\n{text}"


def test_graph_true_requires_truth():
    _, _, Xtr, ytr, Xte, _ = _split_naca()
    g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    g.fit(Xtr, train_y=ytr, columns=ColumnMap(inputs=COORDS))
    with pytest.raises(ValueError, match="truth"):
        g.assess(Xte, columns=ColumnMap(inputs=COORDS), graph=True)   # ndarray has no truth


# ── 9. Polymorphism — ndarray == Path; companion+Path raises; missing col ─────

def test_polymorphism_ndarray_equals_path(tmp_path):
    rows = _load_naca()
    fields = list(rows[0].keys())
    train_rows = [r for r in rows if r["x_over_D"] >= 10]
    test_rows = [r for r in rows if r["x_over_D"] < 10]
    Xtr = np.array([[r[c] for c in COORDS] for r in train_rows])
    ytr = np.array([r["Nu_meas"] for r in train_rows])
    Xte = np.array([[r[c] for c in COORDS] for r in test_rows])

    g_arr = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    g_arr.fit(Xtr, train_y=ytr, columns=ColumnMap(inputs=COORDS))
    res_arr = g_arr.assess(Xte, columns=ColumnMap(inputs=COORDS))

    for stem, sub in (("train", train_rows), ("test", test_rows)):
        with open(tmp_path / f"{stem}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(sub)
    cm = ColumnMap(inputs=COORDS, truth="Nu_meas")
    g_path = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    g_path.fit(tmp_path / "train.csv", columns=cm)
    res_path = g_path.assess(tmp_path / "test.csv", columns=cm)

    assert [a.verdict for a in res_arr] == [a.verdict for a in res_path]
    assert [a.fired_bound_variable for a in res_arr] == [a.fired_bound_variable for a in res_path]
    from physmap import DetectorKind
    for a, b in zip(res_arr, res_path):
        assert a.signals[DetectorKind.CLOSURE_VALIDITY].score == pytest.approx(
            b.signals[DetectorKind.CLOSURE_VALIDITY].score)


def test_path_with_companion_array_raises(tmp_path):
    rows = _load_naca()
    with open(tmp_path / "d.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    with pytest.raises(ValueError, match="path is given"):
        g.fit(tmp_path / "d.csv", train_y=np.array([1.0]), columns=ColumnMap(inputs=COORDS, truth="Nu_meas"))


def test_missing_column_raises(tmp_path):
    rows = _load_naca()
    with open(tmp_path / "d.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    with pytest.raises(ValueError, match="not found"):
        g.fit(tmp_path / "d.csv", columns=ColumnMap(inputs=["Re", "Pr", "NOPE"], truth="Nu_meas"))


# ── 10. save / load round-trip + corpus-version warn + no surrogate ───────────

def test_save_load_roundtrip(tmp_path):
    _, _, Xtr, ytr, Xte, _ = _split_naca()
    cm = ColumnMap(inputs=COORDS)
    g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    g.fit(Xtr, train_y=ytr, columns=cm)
    res = g.assess(Xte, columns=cm)

    bundle = tmp_path / "g.physmap"
    g.save(bundle)
    import zipfile
    members = zipfile.ZipFile(bundle).namelist()
    assert "manifest.json" in members
    assert not any("surrogate" in m for m in members)        # surrogate never serialized

    g2 = CredibilityGuardrail.load(bundle)
    res2 = g2.assess(Xte, columns=cm)
    assert [a.verdict for a in res] == [a.verdict for a in res2]
    assert [a.rationale for a in res] == [a.rationale for a in res2]


def test_load_warns_on_corpus_mismatch(tmp_path, monkeypatch):
    _, _, Xtr, ytr, _, _ = _split_naca()
    g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    g.fit(Xtr, train_y=ytr, columns=ColumnMap(inputs=COORDS))
    bundle = tmp_path / "g.physmap"
    g.save(bundle)
    # after saving the real fingerprint, force a mismatch at load
    monkeypatch.setattr(
        "physmap.guardrail.io.corpus_fingerprint",
        lambda *a, **k: {"version": "9.9.9", "sha256": "dead" * 16, "n_entries": 0})
    with pytest.warns(UserWarning, match="corpus"):
        CredibilityGuardrail.load(bundle)
