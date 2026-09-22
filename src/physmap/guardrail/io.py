"""save / load — a .physmap bundle that is both fitted-state reuse and an
inspectable audit artifact.

The bundle is a zip: a readable JSON manifest (config + observability
classification + resolved closures + corpus version/hash + package version + fit
timestamp) and the fitted baseline models (joblib). The surrogate is NOT
serialized (re-supply on load); the corpus is NOT serialized (the manifest
records its version + content hash, and load WARNS on mismatch). The closure-
validity detectors carry no fit state — they are rebuilt from the installed
corpus deterministically.

Only the fitted INNER detectors are pickled: the DetectorAdapter wraps a
non-picklable rationale closure, so load rewraps the inner with the factory's
rationale builder + the saved threshold.
"""

from __future__ import annotations

import json
import warnings
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import physmap
from physmap.corpus.evidence import load_claims, load_sources
from physmap.guardrail.configs import (
    ClosureValidityDetectorConfig,
    DistanceDetectorConfig,
    GPVarianceDetectorConfig,
    NoveltyDetectorConfig,
)
from physmap.guardrail.corpus_regimes import corpus_fingerprint
from physmap.guardrail.enums import AggregatorKind, DensityMethod, Device, DetectorKind, Regime
from physmap.pipeline.validity_signal import ValidityRangeDistanceDetector


def _detector_to_dict(spec) -> dict:
    if isinstance(spec, DetectorKind):
        return {"type": "kind", "kind": spec.value}
    if isinstance(spec, NoveltyDetectorConfig):
        return {"type": "NoveltyDetectorConfig", "method": spec.method.value,
                "components": spec.components, "warn_pct": spec.warn_pct,
                "reject_pct": spec.reject_pct, "device": spec.device.value}
    if isinstance(spec, DistanceDetectorConfig):
        return {"type": "DistanceDetectorConfig", "k": spec.k, "device": spec.device.value}
    if isinstance(spec, GPVarianceDetectorConfig):
        return {"type": "GPVarianceDetectorConfig", "kernel": spec.kernel,
                "device": spec.device.value}
    if isinstance(spec, ClosureValidityDetectorConfig):
        return {"type": "ClosureValidityDetectorConfig", "graded": spec.graded,
                "status_weighting": spec.status_weighting}
    raise TypeError(f"cannot serialize detector spec of type {type(spec).__name__}")


def _detector_from_dict(d: dict):
    t = d["type"]
    if t == "kind":
        return DetectorKind(d["kind"])
    if t == "NoveltyDetectorConfig":
        return NoveltyDetectorConfig(method=DensityMethod(d["method"]), components=d["components"],
                                     warn_pct=d["warn_pct"], reject_pct=d["reject_pct"],
                                     device=Device(d["device"]))
    if t == "DistanceDetectorConfig":
        return DistanceDetectorConfig(k=d["k"], device=Device(d["device"]))
    if t == "GPVarianceDetectorConfig":
        return GPVarianceDetectorConfig(kernel=d["kernel"], device=Device(d["device"]))
    if t == "ClosureValidityDetectorConfig":
        return ClosureValidityDetectorConfig(graded=d["graded"], status_weighting=d["status_weighting"])
    raise ValueError(f"unknown detector spec type {t!r}")


def save_guardrail(guard, path) -> None:
    if not guard._fitted:
        raise RuntimeError("save() called before fit(); nothing fitted to persist.")
    import joblib

    fp = corpus_fingerprint()   # {version, sha256, n_entries, tier} of the active corpus
    manifest = {
        "physmap_version": physmap.__version__,
        "fit_timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "surrogate_inputs": guard.surrogate_inputs,
            "regime": guard.regime.value,
            "aggregator": guard.aggregator_kind.value,
            "operating_pct": guard.operating_pct,
            "detectors": [_detector_to_dict(s) for s in guard.detectors],
        },
        "observability_classification": {k: v.value for k, v in guard._observability.items()},
        "resolved_closures": list(guard._resolved_closures),
        "baseline_feature_names": list(guard._baseline_feature_names),
        "validity_feature_names": list(guard._validity_feature_names),
        "graded": guard._graded,
        "status_weighting": guard._status_weighting,
        "corpus": fp,
        # Top-level audit field: which corpus TIER produced this artifact. The
        # tier also lives in corpus.tier; surfaced here so audit tooling can read
        # it without reaching into the fingerprint.
        "corpus_tier": fp["tier"],
        "thresholds": {
            "distance": guard._distance.threshold if guard._distance else None,
            "gp_variance": guard._gp.threshold if guard._gp else None,
        },
    }

    with zipfile.ZipFile(Path(path), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        if guard._distance is not None:
            buf = BytesIO(); joblib.dump(guard._distance.inner, buf)
            z.writestr("models/distance.joblib", buf.getvalue())
        if guard._gp is not None:
            buf = BytesIO(); joblib.dump(guard._gp.inner, buf)
            z.writestr("models/gp.joblib", buf.getvalue())
        if guard._density is not None:
            buf = BytesIO(); joblib.dump(guard._density, buf)
            z.writestr("models/density.joblib", buf.getvalue())


def load_guardrail(cls, path, *, surrogate=None):
    import joblib
    from physmap.pipeline.core import DetectorAdapter, _distance_rationale, _gp_rationale

    with zipfile.ZipFile(Path(path), "r") as z:
        manifest = json.loads(z.read("manifest.json"))
        cfg = manifest["config"]
        guard = cls(
            surrogate_inputs=cfg["surrogate_inputs"],
            regime=Regime(cfg["regime"]),
            detectors=[_detector_from_dict(d) for d in cfg["detectors"]],
            aggregator=AggregatorKind(cfg["aggregator"]),
            surrogate=surrogate,
            operating_pct=cfg["operating_pct"],
        )

        saved = manifest["corpus"]
        cur = corpus_fingerprint()
        saved_tier = manifest.get("corpus_tier") or saved.get("tier", "unknown")
        cur_tier = cur.get("tier", "unknown")
        if cur["version"] != saved["version"] or cur["sha256"] != saved["sha256"]:
            tier_note = ""
            if saved_tier != cur_tier and "unknown" not in (saved_tier, cur_tier):
                # Tier drift is a WARN, not an error: a seed-fitted guard loaded
                # in a premium env is fully valid (seed closures ⊂ premium); a
                # premium-fit guard in a seed env loses premium-only bounds (the
                # validity-detector rebuild below drops them gracefully).
                tier_note = (
                    f" Tier changed: fit on the '{saved_tier}' corpus, loaded in a "
                    f"'{cur_tier}' environment."
                )
            warnings.warn(
                f"corpus version/content differs from the saved guard "
                f"(saved {saved['version']}/{saved['sha256'][:8]} vs installed "
                f"{cur['version']}/{cur['sha256'][:8]}); validity bounds may have "
                f"changed since this guard was fit.{tier_note}",
                stacklevel=2,
            )

        th = manifest["thresholds"]
        names = set(z.namelist())
        if "models/distance.joblib" in names:
            inner = joblib.load(BytesIO(z.read("models/distance.joblib")))
            guard._distance = DetectorAdapter(
                name="distance", inner=inner, threshold=th.get("distance"),
                rationale_fn=_distance_rationale(getattr(inner, "k", 3)))
        if "models/gp.joblib" in names:
            inner = joblib.load(BytesIO(z.read("models/gp.joblib")))
            guard._gp = DetectorAdapter(
                name="gp_variance", inner=inner, threshold=th.get("gp_variance"),
                rationale_fn=_gp_rationale())
        if "models/density.joblib" in names:
            guard._density = joblib.load(BytesIO(z.read("models/density.joblib")))

    guard._graded = manifest["graded"]
    guard._status_weighting = manifest["status_weighting"]
    if "closure_validity" in guard._detector_configs and guard._resolved_closures:
        # Rebuild validity detectors from the ACTIVE corpus, skipping any closure
        # whose bounds are absent (a premium-fit guard loaded in a seed env). This
        # degrades gracefully — warn, not error — per the case-2a semantics.
        rebuilt = []
        for cid in guard._resolved_closures:
            try:
                rebuilt.append((cid, ValidityRangeDistanceDetector(
                    closure_id=cid, feature_names=guard._validity_feature_names)))
            except ValueError:
                pass
        guard._validity_detectors = rebuilt
    saved_resolved = list(manifest.get("resolved_closures", []))
    dropped = [c for c in saved_resolved if c not in guard._resolved_closures]
    if dropped:
        warnings.warn(
            f"closure-validity bounds for {dropped} resolved at fit time but are "
            f"not in the active corpus now (likely a premium-fit guard loaded in a "
            f"seed environment); those validity detectors are dropped. The guard "
            f"still loads and runs on its remaining detectors.",
            stacklevel=2,
        )
    guard._claims = load_claims()
    guard._sources_index = {s.source_id: s for s in load_sources()}
    guard._fitted = True
    return guard
