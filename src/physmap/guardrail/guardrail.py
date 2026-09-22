"""The public CredibilityGuardrail — construct → fit → assess → save.

Surrogate-aware, closure-aware credibility guard. It wraps the shipped pipeline
internals (statistical baselines + the closure-validity corpus detector + the
defeasible adjudicator + the v0.6 assessment graph) behind a clean API, and adds
the one new mechanism: structural observability. The verdict is driven by the
surrogate's INPUT COORDINATES and the closure validity bounds — not by the
prediction value — so predictions are needed only for the audit graph.

Polymorphic fit/assess on ndarray | Path (file or dir) converge to an I/O-free
core (_fit_core / _assess_core) that operates on per-row coordinate dicts. The
fit-time bound-variable check fails loudly if the data lacks a resolved closure's
bound variable — the safety net against a silent dead differentiator.
"""

from __future__ import annotations

import csv
import glob
from pathlib import Path
from typing import Sequence

import numpy as np

from physmap.corpus.calibration import get_validated_range
from physmap.corpus.evidence import load_claims, load_sources, query_validity_story
from physmap.guardrail.aggregator_observability import (
    CORPUS_NAME,
    ObservabilityWeightedAggregator,
)
from physmap.guardrail.classify import (
    classify_observability,
    coord_to_feature,
    coord_to_meta_key,
    input_to_feature,
    load_default_corpus_index,
)
from physmap.guardrail.configs import (
    Assessment,
    ClosureValidityDetectorConfig,
    ColumnMap,
    ConformalResidualDetectorConfig,
    DetectorResult,
    DistanceDetectorConfig,
    GPVarianceDetectorConfig,
    NoveltyDetectorConfig,
)
from physmap.closures.index import (
    CLOSURE_INDEX,
    ClosureResolutionError,
    ResolutionCase,
    classify_closure,
    match_closure,
    resolution_message,
)
from physmap.guardrail.corpus_regimes import REGIME_TO_CLOSURES
from physmap.guardrail.detector_conformal import CONFORMAL_NAME, ConformalResidualDetector
from physmap.guardrail.detector_density import DensityNoveltyDetector
from physmap.guardrail.enums import (
    AggregatorKind,
    Device,
    DetectorKind,
    Observability,
)
from physmap.guardrail.graph import KIND_BY_NAME, NAME_BY_KIND
from physmap.guardrail.render import (
    render_baseline,
    render_partial,
    render_partial_graded,
    render_unobservable,
)
from physmap.guardrail.weighting_heuristic import resolve_partial
from physmap.pipeline.core import (
    DetectorResult as CoreDetectorResult,
    GP_VARIANCE_REL_FLOOR,
    make_distance_adapter,
    make_gp_variance_adapter,
)
from physmap.pipeline.detectors import extract_features_batch
from physmap.pipeline.validity_signal import (
    _STATUS_WEIGHT,
    PerBoundMargin,
    ValidityRangeDistanceDetector,
)


DEFAULT_OPERATING_PCT = 99.0   # percentile of train self-scores for distance/GP thresholds

_DEFAULT_DETECTORS = (
    NoveltyDetectorConfig(),
    GPVarianceDetectorConfig(),
    ClosureValidityDetectorConfig(),
)


def _coerce(v):
    """Best-effort float coercion for CSV cells; leave non-numeric as-is."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def _default_config_for(kind: DetectorKind):
    return {
        DetectorKind.NOVELTY_DENSITY: NoveltyDetectorConfig(),
        DetectorKind.DISTANCE_TO_TRAINING: DistanceDetectorConfig(),
        DetectorKind.GP_VARIANCE: GPVarianceDetectorConfig(),
        DetectorKind.CLOSURE_VALIDITY: ClosureValidityDetectorConfig(),
        DetectorKind.CONFORMAL_RESIDUAL: ConformalResidualDetectorConfig(),
    }[kind]


class CredibilityGuardrail:
    def __init__(
        self,
        *,
        surrogate_inputs: Sequence[str],
        regime,
        closure_id: str | None = None,
        detectors: Sequence = _DEFAULT_DETECTORS,
        aggregator: AggregatorKind = AggregatorKind.OBSERVABILITY_WEIGHTED,
        surrogate=None,
        operating_pct: float = DEFAULT_OPERATING_PCT,
    ):
        if aggregator is not AggregatorKind.OBSERVABILITY_WEIGHTED:
            raise NotImplementedError(
                f"aggregator {aggregator.value!r} is wired but not implemented; "
                f"only OBSERVABILITY_WEIGHTED ships now (it is the product value)."
            )
        self.surrogate_inputs = list(surrogate_inputs)
        self.regime = regime
        self.detectors = tuple(detectors)
        self.aggregator_kind = aggregator
        self.surrogate = surrogate
        self.operating_pct = float(operating_pct)

        self._corpus_index = load_default_corpus_index()
        active_ids = set(self._corpus_index)
        regime_closures = tuple(REGIME_TO_CLOSURES.get(regime, ()))

        # Direct closure naming (closure_id= or free-text matched against the open
        # index aliases) is the higher-fidelity demand signal — it must resolve for
        # case 2b/3 closures too. Resolve it now; honor it in fit().
        self._closure_request = closure_id
        self._resolved_request_id = None
        if closure_id:
            self._resolved_request_id = (
                closure_id if (closure_id in CLOSURE_INDEX or closure_id in active_ids)
                else match_closure(closure_id)
            )

        # Closures usable NOW (bounds in the active corpus): the regime's resolved
        # set plus a directly-named closure if it happens to be active.
        resolved = [c for c in regime_closures if c in active_ids]
        if (self._resolved_request_id and self._resolved_request_id in active_ids
                and self._resolved_request_id not in resolved):
            resolved.append(self._resolved_request_id)
        self._resolved_closures = resolved

        # Resolution disposition (case 2a/2b/3) — computed here so construction is
        # cheap and introspectable (mode/observability work pre-fit); raised in fit().
        self._resolution = self._classify_resolution(active_ids, regime_closures)
        self._observability = classify_observability(
            self.surrogate_inputs, regime, self._corpus_index
        )
        self._detector_configs = self._resolve_detectors(self.detectors)
        self._baseline_feature_names = [input_to_feature(s) for s in self.surrogate_inputs]
        self._validity_feature_names = self._compute_validity_features()
        self._region_keys = self._compute_region_keys()
        self._agg = ObservabilityWeightedAggregator()

        # fitted state (populated by _fit_core / load)
        self._fitted = False
        self._distance = None
        self._gp = None
        self._density = None
        self._conformal = None
        self._validity_detectors: list[tuple[str, ValidityRangeDistanceDetector]] = []
        self._graded = True
        self._status_weighting = True
        self._claims = []
        self._sources_index = {}

    # ── setup helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_detectors(specs) -> dict:
        out = {}
        for spec in specs:
            if isinstance(spec, DetectorKind):
                kind, cfg = spec, _default_config_for(spec)
            else:
                kind, cfg = spec.kind, spec
            out[NAME_BY_KIND[kind]] = cfg
        return out

    def _classify_resolution(self, active_ids: set[str], regime_closures: tuple[str, ...]):
        """Decide whether fit() must raise a resolution error (case 2a/2b/3), or
        None to proceed. Preserves the existing statistical-only behaviour: an
        UNLISTED / unmapped regime with no direct closure never raises."""
        facets = {"regime": getattr(self.regime, "name", str(self.regime))}

        # 1. Direct closure naming takes precedence and must work for 2b/3.
        if self._closure_request:
            if self._resolved_request_id is None:
                return (self._closure_request, ResolutionCase.UNREGISTERED, facets)
            case = classify_closure(self._resolved_request_id, active_ids)
            return None if case is ResolutionCase.ACTIVE else (self._resolved_request_id, case, facets)

        # 2. Regime path. Empty/UNLISTED → statistical-only (no raise, unchanged).
        if not regime_closures:
            return None
        # Any closure already active → normal operation (case 1).
        if any(c in active_ids for c in regime_closures):
            return None
        # None active: all premium-only → 2a; otherwise surface the first
        # registered-but-uncurated (2b) — a seed install hitting a premium regime.
        cases = [(c, classify_closure(c, active_ids)) for c in regime_closures]
        if all(case is ResolutionCase.PREMIUM_ONLY for _, case in cases):
            return (regime_closures[0], ResolutionCase.PREMIUM_ONLY, facets)
        for cid, case in cases:
            if case in (ResolutionCase.NO_BOUNDS, ResolutionCase.PREMIUM_ONLY):
                return (cid, case, facets)
        return None

    def _raise_if_unresolved(self) -> None:
        """fit() entry guard — raise the factual one-line resolution error if the
        requested closure's bounds are not in the active corpus."""
        if self._resolution is None:
            return
        name, case, facets = self._resolution
        raise ClosureResolutionError(resolution_message(name, case, facets=facets), case=case)

    def _compute_validity_features(self) -> list[str]:
        feats = list(self._baseline_feature_names)
        for cid in self._resolved_closures:
            for b in self._corpus_index[cid].validated_range:
                f = coord_to_feature(b.coord)
                if f and f not in feats:
                    feats.append(f)
        return feats

    def _compute_region_keys(self) -> list[str]:
        keys = list(self.surrogate_inputs)
        for cid in self._resolved_closures:
            for b in self._corpus_index[cid].validated_range:
                mk = coord_to_meta_key(b.coord)
                if mk and mk not in keys:
                    keys.append(mk)
        return keys

    # ── I/O-free core ─────────────────────────────────────────────────────────

    def _validate_bound_variables(self, metas: list[dict]) -> None:
        """Fail loudly if the data lacks a resolved closure's bound variable —
        the safety net against a silent dead differentiator."""
        if not metas:
            return
        present = set(metas[0].keys())
        for cid in self._resolved_closures:
            for b in self._corpus_index[cid].validated_range:
                mk = coord_to_meta_key(b.coord)
                if mk is None:
                    continue   # no known data column for this coord; can't check
                if mk not in present:
                    raise ValueError(
                        f"regime {self.regime.name} checks a bound on {b.coord}, but "
                        f"the data does not contain it (expected column {mk!r}); the "
                        f"closure-validity detector cannot evaluate this bound. "
                        f"Include {mk!r} in the assessment coordinates."
                    )

    def _fit_core(self, train_metas, train_y, train_pred) -> "CredibilityGuardrail":
        self._validate_bound_variables(train_metas)
        train_baseline_X = extract_features_batch(train_metas, self._baseline_feature_names)

        if "distance" in self._detector_configs:
            cfg = self._detector_configs["distance"]
            self._check_device(cfg.device)
            probe = make_distance_adapter(train_baseline_X, k=cfg.k)
            tau = float(np.percentile(probe.signal(train_baseline_X), self.operating_pct))
            self._distance = make_distance_adapter(train_baseline_X, threshold=tau, k=cfg.k)

        if "gp_variance" in self._detector_configs:
            if train_y is None:
                raise ValueError(
                    "the GP-variance baseline needs training truth; pass train_y "
                    "(ndarray) or a truth column (Path via ColumnMap.truth)."
                )
            cfg = self._detector_configs["gp_variance"]
            self._check_device(cfg.device)
            probe = make_gp_variance_adapter(train_baseline_X, np.asarray(train_y, dtype=float))
            tau = float(np.percentile(probe.signal(train_baseline_X), self.operating_pct))
            tau = max(tau, GP_VARIANCE_REL_FLOOR)   # floor: percentile-of-self degenerates on dense training
            self._gp = make_gp_variance_adapter(
                train_baseline_X, np.asarray(train_y, dtype=float), threshold=tau
            )

        if "conformal_residual" in self._detector_configs:
            if train_y is None:
                raise ValueError(
                    "the conformal-residual detector (observable-pole mode) needs training "
                    "truth; pass train_y (ndarray) or a truth column (Path via ColumnMap.truth)."
                )
            cfg = self._detector_configs["conformal_residual"]
            self._check_device(cfg.device)
            self._conformal = ConformalResidualDetector(
                train_baseline_X, np.asarray(train_y, dtype=float),
                alpha=cfg.alpha, calib_frac=cfg.calib_frac, random_state=cfg.random_state,
            )

        if "novelty_density" in self._detector_configs:
            cfg = self._detector_configs["novelty_density"]
            self._density = DensityNoveltyDetector(
                train_X=train_baseline_X, components=cfg.components,
                warn_pct=cfg.warn_pct, reject_pct=cfg.reject_pct,
                method=cfg.method, device=cfg.device,
            )

        if "closure_validity" in self._detector_configs and self._resolved_closures:
            cfg = self._detector_configs["closure_validity"]
            self._graded = cfg.graded
            self._status_weighting = cfg.status_weighting
            self._validity_detectors = [
                (cid, ValidityRangeDistanceDetector(
                    closure_id=cid, feature_names=self._validity_feature_names))
                for cid in self._resolved_closures
            ]

        self._claims = load_claims()
        self._sources_index = {s.source_id: s for s in load_sources()}
        self._fitted = True
        return self

    def _governing_per_row(self, test_metas) -> list[tuple[PerBoundMargin | None, str | None]]:
        """Per row, the governing fired bound across ALL resolved closures
        (most-violated, status-weighted), tagged with its closure_id."""
        if not self._validity_detectors:
            return [(None, None)] * len(test_metas)
        X = extract_features_batch(test_metas, self._validity_feature_names)
        per_det = [(cid, det.evaluate_bounds(X)) for cid, det in self._validity_detectors]
        out: list[tuple[PerBoundMargin | None, str | None]] = []
        for i in range(len(test_metas)):
            best, best_cid, best_key = None, None, 0.0
            for cid, rows in per_det:
                gov = self._validity_detectors[0][1].governing_bound(
                    rows[i], status_weighting=self._status_weighting)
                if gov is None:
                    continue
                w = _STATUS_WEIGHT.get(gov.bound_status, 0.4) if self._status_weighting else 1.0
                key = w * gov.margin
                if best is None or key > best_key:
                    best, best_cid, best_key = gov, cid, key
            out.append((best, best_cid))
        return out

    def _assess_core(self, test_metas, test_pred, truth_values) -> list[Assessment]:
        if not self._fitted:
            raise RuntimeError("assess() called before fit(); fit the guard first.")
        self._validate_bound_variables(test_metas)
        n = len(test_metas)
        test_baseline_X = extract_features_batch(test_metas, self._baseline_feature_names)

        dist_results = self._distance.evaluate(test_baseline_X) if self._distance else None
        gp_results = self._gp.evaluate(test_baseline_X) if self._gp else None
        dens_scores = self._density.signal(test_baseline_X) if self._density else None
        conf_results = (self._conformal.evaluate(test_baseline_X, test_pred)
                        if self._conformal is not None else None)
        governing = self._governing_per_row(test_metas)

        assessments: list[Assessment] = []
        for i, meta in enumerate(test_metas):
            decision: dict[str, CoreDetectorResult] = {}
            severities: dict[str, str | None] = {}
            if dist_results is not None:
                decision["distance"] = dist_results[i]
                severities["distance"] = "warn" if dist_results[i].fired else None
            if gp_results is not None:
                decision["gp_variance"] = gp_results[i]
                severities["gp_variance"] = "warn" if gp_results[i].fired else None
            if self._density is not None:
                score = float(dens_scores[i])
                fired = score > self._density.warn_threshold
                sev = ("reject" if score > self._density.reject_threshold
                       else ("warn" if fired else None))
                decision["novelty_density"] = CoreDetectorResult(
                    "novelty_density", score, fired, self._density.warn_threshold,
                    _density_rationale(score, self._density), "decision")
                severities["novelty_density"] = sev
            if conf_results is not None:
                decision[CONFORMAL_NAME] = conf_results[i]
                severities[CONFORMAL_NAME] = "warn" if conf_results[i].fired else None

            gov, gov_cid = governing[i]
            if self._validity_detectors:
                fired_cv = gov is not None
                score_cv = (gov.margin if self._graded else 1.0) if fired_cv else 0.0
                decision[CORPUS_NAME] = CoreDetectorResult(
                    CORPUS_NAME, score_cv, fired_cv, None,
                    _cv_rationale(gov_cid, gov), "decision")

            outcome = self._agg.combine(
                decision_signals=decision, observability=self._observability,
                fired_bound=gov, severities=severities,
                fired_closure_id=gov_cid, regime=self.regime)

            obs = self._observability.get(gov.coord) if gov is not None else None
            rationale = self._render_rationale(outcome, gov, gov_cid, decision)
            signals = {
                KIND_BY_NAME[name]: DetectorResult(
                    KIND_BY_NAME[name], r.score, r.fired, r.threshold, r.rationale)
                for name, r in decision.items()
            }
            pred = float(test_pred[i]) if test_pred is not None and test_pred[i] is not None else None
            truth = (float(truth_values[i])
                     if truth_values is not None and truth_values[i] is not None else None)
            region = ", ".join(
                f"{k}={_fmt(meta[k])}" for k in self._region_keys if k in meta)
            op = tuple(meta[k] for k in self._region_keys if k in meta)
            assessments.append(Assessment(
                verdict=outcome.verdict, disposition=outcome.disposition,
                rationale=rationale, signals=signals, observability=obs,
                fired_bound_variable=(gov.coord if gov is not None else None),
                surrogate_prediction=pred, solver_truth=truth,
                operating_point=op, closure_id=gov_cid, region=region))
        return assessments

    def _render_rationale(self, outcome, gov, gov_cid, decision) -> str:
        baseline_fired_names = [
            n for n, r in decision.items() if n != CORPUS_NAME and r.fired]
        if gov is not None and outcome.rule == "unobservable-corpus-trusted":
            bound = get_validated_range(self._corpus_index, gov_cid, gov.coord)
            interval = (bound.min, bound.max) if bound else (None, None)
            return render_unobservable(
                closure_id=gov_cid, fired_bound=gov, bound_interval=interval,
                baseline_fired=bool(baseline_fired_names),
                claims_for_closure=query_validity_story(self._claims, gov_cid),
                sources_index=self._sources_index)
        if gov is not None and outcome.rule == "partial-defer":
            bound = get_validated_range(self._corpus_index, gov_cid, gov.coord)
            interval = (bound.min, bound.max) if bound else (None, None)
            return render_partial(
                closure_id=gov_cid, fired_bound=gov, bound_interval=interval)
        if gov is not None and outcome.rule in (
                "partial-graded-corpus-trust", "partial-graded-softflag"):
            bound = get_validated_range(self._corpus_index, gov_cid, gov.coord)
            interval = (bound.min, bound.max) if bound else (None, None)
            dec = resolve_partial(gov_cid, gov.coord, regime_value=self.regime.value)
            return render_partial_graded(
                closure_id=gov_cid, fired_bound=gov, bound_interval=interval,
                degree=dec.partial_degree, calibrated_by=dec.calibrated_by,
                soft_flag=(outcome.rule == "partial-graded-softflag"))
        return render_baseline(
            baseline_fired_names=baseline_fired_names,
            all_quiet=not baseline_fired_names)

    @staticmethod
    def _check_device(device: Device) -> None:
        if device is Device.CUDA:
            raise NotImplementedError(
                "CUDA device is wired but not implemented; only CPU is built "
                "(workloads are small — GPU is deferred)."
            )

    # ── polymorphic fit / assess ──────────────────────────────────────────────

    def fit(self, train, train_y=None, train_pred=None, *, columns: ColumnMap | None = None):
        self._raise_if_unresolved()
        if isinstance(train, np.ndarray):
            coord_names = columns.inputs if columns is not None else self.surrogate_inputs
            metas = self._array_to_metas(train, coord_names)
            if train_pred is None and self.surrogate is not None:
                train_pred = self.surrogate(train)
            return self._fit_core(metas, train_y, train_pred)
        if isinstance(train, (str, Path)):
            if train_y is not None or train_pred is not None:
                raise ValueError(
                    "predictions/truth come from the file when a path is given; "
                    "do not also pass train_y/train_pred.")
            metas = self._load_path(train, columns)
            truth = columns.truth if columns is not None else "truth"
            needs_truth = bool(
                {"gp_variance", "conformal_residual"} & set(self._detector_configs))
            train_y = self._column(metas, truth) if needs_truth else None
            return self._fit_core(metas, train_y, None)
        raise TypeError(f"train must be np.ndarray or Path/str, got {type(train).__name__}")

    def assess(self, test, test_pred=None, *, columns: ColumnMap | None = None,
               graph: bool = False) -> list[Assessment]:
        if isinstance(test, np.ndarray):
            coord_names = columns.inputs if columns is not None else self.surrogate_inputs
            metas = self._array_to_metas(test, coord_names)
            if test_pred is None and self.surrogate is not None:
                test_pred = self.surrogate(test)
            truth_values = None
        elif isinstance(test, (str, Path)):
            if test_pred is not None:
                raise ValueError(
                    "predictions/truth come from the file when a path is given; "
                    "do not also pass test_pred.")
            metas = self._load_path(test, columns)
            truth_col = columns.truth if columns is not None else "truth"
            pred_col = columns.prediction if columns is not None else "prediction"
            truth_values = self._column(metas, truth_col, optional=True)
            test_pred = self._column(metas, pred_col, optional=True)
            if test_pred is None and self.surrogate is not None:
                test_pred = self.surrogate(
                    extract_features_batch(metas, self._baseline_feature_names))
        else:
            raise TypeError(f"test must be np.ndarray or Path/str, got {type(test).__name__}")

        if graph and (truth_values is None or any(t is None for t in truth_values)):
            raise ValueError(
                "graph=True requires truth for every row (the v0.6 Discrepancy shape "
                "pins exactly one solverTruth). Provide a truth column via a Path + "
                "ColumnMap.truth, or call assess(..., graph=False) for flat assessments.")
        return self._assess_core(metas, test_pred, truth_values)

    # ── data loading helpers ──────────────────────────────────────────────────

    def _array_to_metas(self, X: np.ndarray, coord_names: Sequence[str]) -> list[dict]:
        X = np.asarray(X)
        if X.ndim != 2 or X.shape[1] != len(coord_names):
            raise ValueError(
                f"array has shape {X.shape} but {len(coord_names)} column names "
                f"{list(coord_names)} were given; pass a ColumnMap whose `inputs` "
                f"names every column (a SUPERSET of surrogate_inputs that includes "
                f"the bound variables).")
        return [{coord_names[j]: float(X[i, j]) for j in range(X.shape[1])}
                for i in range(X.shape[0])]

    @staticmethod
    def _load_path(path, columns: ColumnMap | None) -> list[dict]:
        p = Path(path)
        files = sorted(glob.glob(str(p / "*.csv"))) if p.is_dir() else [str(p)]
        if not files:
            raise FileNotFoundError(f"no CSV files found at {p}")
        metas: list[dict] = []
        for f in files:
            with open(f, newline="") as fh:
                for row in csv.DictReader(r for r in fh if not r.lstrip().startswith("#")):
                    metas.append({k: _coerce(v) for k, v in row.items()})
        if columns is not None:
            missing = [c for c in columns.inputs if metas and c not in metas[0]]
            if missing:
                raise ValueError(f"columns {missing} not found in {p} (have {sorted(metas[0])})")
        return metas

    @staticmethod
    def _column(metas, name, *, optional: bool = False):
        if not metas:
            return None
        if name not in metas[0]:
            if optional:
                return None
            raise ValueError(f"column {name!r} not found (have {sorted(metas[0])})")
        return [m.get(name) for m in metas]

    # ── persistence ───────────────────────────────────────────────────────────

    def save(self, path) -> None:
        from physmap.guardrail.io import save_guardrail
        save_guardrail(self, path)

    @classmethod
    def load(cls, path, *, surrogate=None) -> "CredibilityGuardrail":
        from physmap.guardrail.io import load_guardrail
        return load_guardrail(cls, path, surrogate=surrogate)

    # ── introspection ─────────────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        return "physics_active" if self._resolved_closures else "statistical_only"

    @property
    def observability_classification(self) -> dict:
        return dict(self._observability)

    @property
    def resolved_closures(self) -> list:
        return sorted(self._resolved_closures)


# ── module-level rationale builders (deterministic) ───────────────────────────

def _fmt(v) -> str:
    return f"{v:.4g}" if isinstance(v, (int, float)) else str(v)


def _density_rationale(score: float, det: DensityNoveltyDetector) -> str:
    if score > det.reject_threshold:
        return (f"novelty_density: FIRED (NLL={score:.3g} > reject="
                f"{det.reject_threshold:.3g}; far below training density)")
    if score > det.warn_threshold:
        return (f"novelty_density: FIRED (NLL={score:.3g} > warn="
                f"{det.warn_threshold:.3g})")
    return f"novelty_density: quiet (NLL={score:.3g} <= warn={det.warn_threshold:.3g})"


def _cv_rationale(closure_id: str | None, gov: PerBoundMargin | None) -> str:
    if gov is None or closure_id is None:
        return "closure_validity: quiet (test point INSIDE every validated rectangle)"
    return (f"closure_validity: FIRED (test point OUTSIDE the validated rectangle "
            f"of {closure_id!r} on {gov.coord}; margin={gov.margin:.3g} {gov.side})")
