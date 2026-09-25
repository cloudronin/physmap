"""PhysMAP Benchmark v0.4 — the cross-domain matrix through the REAL library API.

Binding methodology requirement (spec v0.4): every cell is produced by the
shipped public API `physmap.guardrail.CredibilityGuardrail` (construct -> fit ->
assess), with the DETECTOR as the only swapped variable — NOT the gate_core /
AnyFired experiment harness. The baseline column is the library's statistical /
input-space detectors (distance + GP-variance); the PhysMAP column is the
corpus / closure-validity detector (ValidityRangeDistanceDetector); the ensemble
verdict comes from the shipped observability-weighted aggregator.

Per the verified design (a Plan-agent investigation ran the library and confirmed
it): the per-detector decisions are read from the RAW `Assessment.signals[...]`
.fired (always honest, detector-independent), and the observability-weighted
`verdict` is used only for the narrative. The Pareto lift (clean_lift = corpus
fires & baselines quiet & surrogate WRONG) is then computed exactly as
gate_core.pareto_verdict does, but on the public API's output.

This runner reproduces the already-landed outcomes (reproduce-or-explain):
  NACA / Velazquez / Casper -> PHYSMAP_WINS (Casper & NACA UNOBSERVABLE pole;
    Velazquez PARTIAL-calibrated middle), Forrest -> DO_NO_HARM, Marineau ->
    NEGATIVE_CONTROL, dirker -> PARTIAL[provisional].

CLI:  python -m physmap.benchmarks.benchmark_v0_4
"""
from __future__ import annotations

import csv as _csv
import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from physmap.guardrail.guardrail import CredibilityGuardrail
from physmap.guardrail.classify import coord_to_meta_key, input_to_feature
from physmap.guardrail.configs import (
    ClosureValidityDetectorConfig,
    ColumnMap,
    DistanceDetectorConfig,
    GPVarianceDetectorConfig,
)
from physmap.guardrail.enums import DetectorKind, Observability, Regime, Verdict
from physmap.pipeline.observability import vehicle_observability
from physmap.pipeline.surrogate import ThresholdCalibration
from physmap.pipeline.vehicle_spec import vehicle_spec
from physmap.substrate.engine import build_substrate
from physmap.substrate.vehicle_config import (
    _vehicles_dir,
    load_named_vehicle,
    load_vehicle_config,
)


OPERATING_PERCENTILES = (50, 75, 90, 95, 99, 100)   # matches phase1_gate / vehicle_gate_sweep
MIN_TRAIN_FOR_DETECTORS = 3
REFERENCE_PCT = 99.0                                 # pct used for the "fires in region" narrative

# The detector set is FIXED at the steelman input-space baselines + the corpus
# detector. distance is explicitly included and novelty_density is excluded so the
# baseline matches gate_core's (distance, gp_variance) union (the banked baseline).
_DETECTORS = (
    DistanceDetectorConfig(),
    GPVarianceDetectorConfig(),
    ClosureValidityDetectorConfig(),
)
_BASELINE_KINDS = (DetectorKind.DISTANCE_TO_TRAINING, DetectorKind.GP_VARIANCE)
_CORPUS_KIND = DetectorKind.CLOSURE_VALIDITY

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "benchmark_v0_4"

#: The current bank. 0.4.1 corrects the NACA source data: the 0.4 bank's NACA row came from
#: an automated read of NACA TN-1451 Fig 10 later found invalid (see
#: data/naca/CORRECTION_v0_4_1.md). Every other cell is identical. The 0.4 bank is kept,
#: unchanged, for audit -- it is history, not current evidence.
BANK_VERSION = "0.4.1"
BANK_DIR = ("data", "benchmarks", "v0_4_1")
HISTORICAL_BANKS = {"0.4": ("data", "benchmarks", "v0_4")}


@dataclass(frozen=True)
class BenchSpec:
    """Per-vehicle benchmark cell config, DERIVED from the vehicle YAML's `benchmark`
    block (no hardcoded table).

    `surrogate_inputs` are the SHORT data names the guardrail maps to baseline
    features (Re->log10_Re, M->M, ...). `column_inputs` (= surrogate_inputs + the
    failure driver, deduped) is the ColumnMap superset the closure-validity detector
    reads. `expected_observability_class` is the a-priori INTENT (guarded against the
    COMPUTED class); the cell OUTCOME is computed from raw signals, never declared.
    """
    vehicle_id: str
    domain: str
    regime: Regime
    surrogate_inputs: tuple[str, ...]
    column_inputs: tuple[str, ...]
    calib: ThresholdCalibration
    expected_observability_class: str
    failure_driver: str
    architecture_axis: bool = False
    caveat: str = ""


def bench_spec_from_config(cfg) -> "BenchSpec | None":
    """Build a BenchSpec from a vehicle's `benchmark` block, or None if the vehicle
    has no block or opts out (`include != true`). The cell config is DERIVED, not
    tabled: `column_inputs` = surrogate_inputs + the failure driver (deduped — a
    driver that IS a surrogate input, e.g. Forrest's Re, adds nothing); calib from
    the block's `threshold_calibration` or the library default."""
    b = cfg.benchmark
    if b is None or not b.include:
        return None
    surrogate_inputs = tuple(b.surrogate_inputs)
    column_inputs = surrogate_inputs + (
        (b.failure_driver,) if b.failure_driver not in surrogate_inputs else ())
    calib = (
        ThresholdCalibration(paper_uncertainty_pct=float(b.threshold_calibration[0]),
                             digitization_uncertainty_pct=float(b.threshold_calibration[1]))
        if b.threshold_calibration is not None else ThresholdCalibration()
    )
    return BenchSpec(
        vehicle_id=cfg.vehicle_id, domain=b.domain, regime=Regime[b.regime],
        surrogate_inputs=surrogate_inputs, column_inputs=column_inputs, calib=calib,
        expected_observability_class=b.expected_observability_class,
        failure_driver=b.failure_driver, architecture_axis=b.architecture_axis,
        caveat=b.caveat,
    )


def discover_benchmark_vehicles() -> list[BenchSpec]:
    """The ONLY source of the benchmark vehicle list: every `physmap/vehicles/*.yaml`
    carrying a `benchmark: {include: true}` block. Re-scanned on each call, so adding
    a YAML makes its cell appear on the next run with NO runner edit (and removing it
    removes the cell). No hardcoded vehicle name lives in this module."""
    specs: list[BenchSpec] = []
    for path in sorted(_vehicles_dir().glob("*.yaml")):
        spec = bench_spec_from_config(load_vehicle_config(path))
        if spec is not None:
            specs.append(spec)
    return specs


# Import-time snapshot (convenience for tests / the architecture axis); `run_matrix`
# RE-discovers on each run so a newly-registered YAML appears without reimport.
VEHICLE_BENCH: tuple[BenchSpec, ...] = tuple(discover_benchmark_vehicles())


# ── CSV emit (the Path+ColumnMap branch carries truth; the ndarray path does not) ──

def _write_csv(rows, column_inputs: tuple[str, ...], path: Path) -> None:
    """Write one CSV with the ColumnMap input columns + truth + prediction.

    truth = Row.cfd_truth (measured), prediction = Row.surrogate_prediction (the
    vehicle's native surrogate). solver_truth on the returned Assessment is only
    populated on this Path branch (guardrail.py ndarray path hardcodes truth=None).
    """
    header = list(column_inputs) + ["truth", "prediction"]
    with path.open("w", newline="") as fh:
        w = _csv.writer(fh)
        w.writerow(header)
        for r in rows:
            line = [r.meta[c] for c in column_inputs]
            line += [r.cfd_truth, r.surrogate_prediction]
            w.writerow(line)


# ── Pareto from Assessments (mirrors gate_core.pareto_verdict, on public API output) ──

def _pareto_at_pct(assessments, calib: ThresholdCalibration) -> dict:
    """clean_lift / misaligned + per-detector fire counts from the public API's
    Assessments. Per row: baseline = distance OR gp_variance raw .fired (counted
    separately too, so a divergence is self-documenting); corpus = closure_validity
    raw .fired; WRONG/ACCURATE from prediction vs truth and the calib lift/accuracy
    thresholds (gate_core.pareto_verdict logic, verbatim)."""
    clean_lift = misaligned = n_wrong = n_base = n_dist = n_gp = n_corpus = 0
    verdicts: dict[str, int] = {}
    for a in assessments:
        d = a.signals.get(DetectorKind.DISTANCE_TO_TRAINING)
        g = a.signals.get(DetectorKind.GP_VARIANCE)
        dist_fired = bool(d.fired) if d is not None else False
        gp_fired = bool(g.fired) if g is not None else False
        base_fired = dist_fired or gp_fired
        cv = a.signals.get(_CORPUS_KIND)
        corpus_fired = bool(cv.fired) if cv is not None else False
        pred, truth = a.surrogate_prediction, a.solver_truth
        rel_pct = (abs(pred - truth) / abs(truth) * 100.0) if truth else 0.0
        is_wrong = rel_pct > calib.lift_threshold_pct
        is_accurate = rel_pct <= calib.accuracy_threshold_pct
        n_wrong += int(is_wrong)
        n_base += int(base_fired); n_dist += int(dist_fired); n_gp += int(gp_fired)
        n_corpus += int(corpus_fired)
        if corpus_fired and not base_fired and is_wrong:
            clean_lift += 1
        if corpus_fired and not base_fired and is_accurate:
            misaligned += 1
        verdicts[a.verdict.value] = verdicts.get(a.verdict.value, 0) + 1
    return {
        "clean_lift": clean_lift, "misaligned": misaligned, "n_wrong": n_wrong,
        "n_baseline_fired": n_base, "n_distance_fired": n_dist,
        "n_gp_var_fired": n_gp, "n_corpus_fired": n_corpus,
        "n_test": len(assessments), "verdicts": verdicts,
    }


# ── cell-outcome classification (reproduce-or-explain) ────────────────────────

def _classify(failure_obs, clean_lift_max: int, n_wrong_max: int) -> str:
    """Empirical cell outcome, keyed on the failure coord's OBSERVABILITY-POSITION
    (the spec's primary axis) + the Pareto clean-lift over the sweep:

      * Gate-2 fail (surrogate accurate in deploy)            -> NO_FAILURE
      * OBSERVABLE failure axis (baseline-visible pole)       -> BASELINE_VISIBLE
        (the role — DO_NO_HARM vs NEGATIVE_CONTROL — is a-priori; both are
         "baseline sees it", not a corpus win)
      * UNOBSERVABLE/PARTIAL + clean_lift>0 (corpus catches wrong rows the FULL
        steelman baseline misses, at some operating pct)      -> PHYSMAP_WINS / PARTIAL
      * UNOBSERVABLE/PARTIAL + NO clean_lift (surrogate wrong but the full
        steelman baseline already fires on every wrong row)   -> BASELINE_CATCHES_NO_LIFT
        (the honest non-win: e.g. Casper's gp_variance catches the quiet cluster)
    """
    if n_wrong_max == 0:
        return "NO_FAILURE"
    if failure_obs is Observability.OBSERVABLE:
        return "BASELINE_VISIBLE"
    if clean_lift_max > 0:
        return "PHYSMAP_WINS" if failure_obs is Observability.UNOBSERVABLE else "PARTIAL"
    return "BASELINE_CATCHES_NO_LIFT"


def _observability_score(vehicle_id: str, failure_obs) -> tuple[float, str]:
    """Numeric observability in [0,1] for the figure's x-axis. Prefer the MEASURED
    cv_r2_knn estimator (`vehicle_observability`); fall back to the STRUCTURAL pole
    from the class (UNOBSERVABLE->0.0, OBSERVABLE->1.0, PARTIAL->0.5) when the
    estimator is unavailable/degenerate (e.g. a constant failure-var deploy region)."""
    try:
        score = float(vehicle_observability(vehicle_id).score)
        if score == score:                       # not NaN
            return score, "measured"
    except Exception:
        pass
    pole = {Observability.UNOBSERVABLE: 0.0, Observability.OBSERVABLE: 1.0,
            Observability.PARTIAL: 0.5}.get(failure_obs)
    return (pole if pole is not None else float("nan")), "structural_pole"


def run_cell(spec: BenchSpec) -> dict:
    """Run one vehicle through the real CredibilityGuardrail API over the
    operating-pct sweep and return the cell record. The OUTCOME is computed from raw
    signals; the YAML's `expected_observability_class` is an intent GUARD only."""
    cfg = load_named_vehicle(spec.vehicle_id)
    rows, _ref, _meta = build_substrate(cfg)
    vspec = vehicle_spec(cfg)

    # YAML<->substrate consistency (hard invariant: a mis-declared cell fails loudly
    # rather than being silently benchmarked).
    if spec.failure_driver != vspec.failure_var:
        raise ValueError(
            f"{spec.vehicle_id}: benchmark.failure_driver={spec.failure_driver!r} != "
            f"vehicle_spec.failure_var={vspec.failure_var!r}")
    feats = {input_to_feature(s) for s in spec.surrogate_inputs}
    if not feats.issubset(set(vspec.baseline_feature_names)):
        raise ValueError(
            f"{spec.vehicle_id}: benchmark.surrogate_inputs map to features "
            f"{sorted(feats)}, not a subset of vehicle_spec.baseline_feature_names "
            f"{sorted(vspec.baseline_feature_names)}")

    train = [r for r in rows if vspec.split.train_predicate(r.meta)]
    test = [r for r in rows if vspec.split.test_predicate(r.meta)]

    # Failure-coord observability (pct-independent; set at __init__, no fit needed).
    probe = CredibilityGuardrail(
        surrogate_inputs=list(spec.surrogate_inputs), regime=spec.regime,
        detectors=_DETECTORS,
    )
    obs_map = probe.observability_classification
    failure_coord = next(
        (c for c in obs_map if coord_to_meta_key(c) == vspec.failure_var), None)
    failure_obs = obs_map.get(failure_coord)
    # Observability GUARD (spec Step 1): the computed class must match the declared
    # intent; a mismatch is surfaced (run/CLI exits non-zero), never silently absorbed.
    obs_guard = (failure_obs is not None
                 and failure_obs.name == spec.expected_observability_class)
    obs_score, obs_source = _observability_score(spec.vehicle_id, failure_obs)

    base = {
        "vehicle_id": spec.vehicle_id, "domain": spec.domain,
        "regime": spec.regime.value, "failure_var": vspec.failure_var,
        "failure_observability": failure_obs.value if failure_obs else None,
        "expected_observability_class": spec.expected_observability_class,
        "observability_guard_passed": bool(obs_guard),
        "observability_score": obs_score, "observability_source": obs_source,
        "caveat": spec.caveat, "surrogate_inputs": list(spec.surrogate_inputs),
        "n_train": len(train), "n_test": len(test),
        "calib": {"lift_threshold_pct": spec.calib.lift_threshold_pct,
                  "accuracy_threshold_pct": spec.calib.accuracy_threshold_pct},
    }
    if not test:
        return {**base, "empirical_outcome": "NO_DATA",
                "rationale": "no failure-region (deploy) points"}
    if len(train) < MIN_TRAIN_FOR_DETECTORS:
        # Observable degenerate pole (Forrest): the failure axis IS a surrogate input,
        # so the baseline is sufficient by construction — DO_NO_HARM. Too few
        # in-distribution rows to fit detectors (thin n; matches degenerate_short_circuit).
        if failure_obs is Observability.OBSERVABLE:
            return {**base, "empirical_outcome": "DO_NO_HARM", "clean_lift_max": 0,
                    "rationale": (f"observable degenerate pole; only {len(train)} train "
                                  f"rows (thin) — baseline-sufficient by construction, "
                                  f"no detector fit (matches degenerate_short_circuit)")}
        return {**base, "empirical_outcome": "INSUFFICIENT_TRAIN",
                "rationale": f"{len(train)} train rows < {MIN_TRAIN_FOR_DETECTORS}"}

    colmap = ColumnMap(inputs=list(spec.column_inputs), truth="truth", prediction="prediction")
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        train_csv, test_csv = tdp / "train.csv", tdp / "test.csv"
        _write_csv(train, spec.column_inputs, train_csv)
        _write_csv(test, spec.column_inputs, test_csv)
        per_pct: dict[str, dict] = {}
        ref_row = None
        for pct in OPERATING_PERCENTILES:
            guard = CredibilityGuardrail(
                surrogate_inputs=list(spec.surrogate_inputs), regime=spec.regime,
                detectors=_DETECTORS, operating_pct=float(pct),
            )
            guard.fit(train_csv, columns=colmap)
            assessments = guard.assess(test_csv, columns=colmap)
            row = _pareto_at_pct(assessments, spec.calib)
            per_pct[str(pct)] = row
            if float(pct) == REFERENCE_PCT:
                ref_row = row

    ref_row = ref_row or per_pct[str(OPERATING_PERCENTILES[-1])]
    clean_lift_max = max(r["clean_lift"] for r in per_pct.values())
    n_wrong_max = max(r["n_wrong"] for r in per_pct.values())
    min_base = min(r["n_baseline_fired"] for r in per_pct.values())
    empirical = _classify(failure_obs, clean_lift_max, n_wrong_max)
    return {
        **base,
        "clean_lift_max": clean_lift_max,
        "misaligned_min": min(r["misaligned"] for r in per_pct.values()),
        "n_wrong_max": n_wrong_max,
        "min_baseline_fired_over_sweep": min_base,
        "ref_pct": REFERENCE_PCT,
        "ref_n_baseline_fired": ref_row["n_baseline_fired"],
        "ref_n_distance_fired": ref_row["n_distance_fired"],
        "ref_n_gp_var_fired": ref_row["n_gp_var_fired"],
        "ref_n_corpus_fired": ref_row["n_corpus_fired"],
        "ref_verdicts": ref_row["verdicts"],
        "empirical_outcome": empirical,
        "per_pct": per_pct,
    }


def run_matrix(write: bool = True) -> dict:
    """Discover the benchmark vehicles from the registry (no hardcoded list) and run
    each cell. `all_guards_passed` = every cell's computed observability class matched
    its declared intent."""
    cells = [run_cell(s) for s in discover_benchmark_vehicles()]
    matrix = {
        "benchmark": f"PhysMAP Benchmark v{BANK_VERSION} (cross-domain, real-API, registry-driven)",
        "bank_version": BANK_VERSION,
        "api": "physmap.guardrail.CredibilityGuardrail (fit/assess, observability-weighted)",
        "detectors": "baseline=(distance, gp_variance); corpus=closure_validity (raw signals read)",
        "operating_percentiles": list(OPERATING_PERCENTILES),
        "cells": cells,
        "all_guards_passed": all(c.get("observability_guard_passed", False) for c in cells),
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        out = RESULTS_DIR / "matrix.json"
        out.write_text(json.dumps(matrix, indent=2))
        matrix["_path"] = str(out)
    return matrix


def load_banked_matrix() -> dict | None:
    """The previously-banked matrix.json (the reproduce-or-explain baseline), or None."""
    p = RESULTS_DIR / "matrix.json"
    return json.loads(p.read_text()) if p.exists() else None


def reproduce_regressions(new_matrix: dict, banked: dict | None) -> list[str]:
    """Vehicles present in BOTH whose computed `empirical_outcome` changed vs the
    banked baseline — the reproduce-or-explain gate. A NEW vehicle (absent from the
    baseline) is NOT a regression: it is reported and becomes the baseline once
    reviewed."""
    if not banked:
        return []
    prior = {c["vehicle_id"]: c.get("empirical_outcome") for c in banked.get("cells", [])}
    return [
        f"{c['vehicle_id']}: {prior[c['vehicle_id']]} -> {c.get('empirical_outcome')}"
        for c in new_matrix.get("cells", [])
        if c["vehicle_id"] in prior and c.get("empirical_outcome") != prior[c["vehicle_id"]]
    ]


def _print_table(matrix: dict) -> None:
    print(f"\n{matrix['benchmark']}")
    print(f"API: {matrix['api']}")
    hdr = (f"{'vehicle':<32}{'domain':<12}{'obs_class':<13}{'obs':>5}{'clean':>6}"
           f"{'dist':>5}{'gpv':>5}{'corp':>5}  {'empirical':<26}{'exp_obs':<13}{'guard':>6}")
    print(hdr); print("-" * len(hdr))
    for c in matrix["cells"]:
        os_ = c.get("observability_score")
        print(f"{c['vehicle_id']:<32}{c['domain']:<12}"
              f"{str(c.get('failure_observability')):<13}"
              f"{(f'{os_:.2f}' if isinstance(os_, (int, float)) else '-'):>5}"
              f"{c.get('clean_lift_max', '-'):>6}"
              f"{c.get('ref_n_distance_fired', '-'):>5}{c.get('ref_n_gp_var_fired', '-'):>5}"
              f"{c.get('ref_n_corpus_fired', '-'):>5}  "
              f"{c['empirical_outcome']:<26}{c.get('expected_observability_class', ''):<13}"
              f"{'Y' if c.get('observability_guard_passed') else 'N':>6}")
    print(f"\nall observability guards passed: {matrix['all_guards_passed']}")
    print("(obs = numeric observability; dist/gpv/corp = #deploy rows each detector "
          "fires on at ref pct; clean = max clean Pareto lift over the sweep)")


def main(argv=None) -> int:
    banked = load_banked_matrix()
    matrix = run_matrix(write=True)
    _print_table(matrix)
    regressions = reproduce_regressions(matrix, banked)
    if regressions:
        print("\nREPRODUCE-OR-EXPLAIN REGRESSION (existing cells changed):")
        for r in regressions:
            print(f"  {r}")
    if matrix.get("_path"):
        print(f"\nbanked: {matrix['_path']}")
    return 0 if (matrix["all_guards_passed"] and not regressions) else 1


if __name__ == "__main__":
    raise SystemExit(main())
