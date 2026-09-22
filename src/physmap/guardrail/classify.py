"""Structural observability — the one genuinely new mechanism.

At fit time, classify each resolved closure's validity-bound variable as
OBSERVABLE / PARTIAL / UNOBSERVABLE by SET MEMBERSHIP against the surrogate's
declared inputs. NOT CV-R²: that estimator is retrospective (needs truth + a
region + a population) and cannot run at deployment. This is pure — a corpus
lookup + a feature-name map + a corpus tag; no truth, no population.

Also houses the coordinate-name bridges the guardrail shares. Three vocabularies
are in play:
  * corpus coords (long):     reynolds_number, prandtl_number, x_over_D, richardson_number
  * surrogate inputs (short): Re, Pr, x_over_D, Ri
  * detector features:        log10_Re, Pr, x_over_D
FEATURE_TO_CORPUS_COORD (from validity_signal) is the canonical feature↔coord
source; the short-name + meta-key bridges are added here.
"""

from __future__ import annotations

from typing import Sequence

from physmap.corpus.calibration import ClosureEntry, index_by_id, load_corpus
from physmap.guardrail.corpus_regimes import (
    KNOWN_PARTIAL,
    REGIME_TO_CLOSURES,
    observability_class_for,
)
from physmap.guardrail.enums import Observability, Regime
from physmap.pipeline.validity_signal import FEATURE_TO_CORPUS_COORD


# Corpus coord → surrogate-input name(s) that would make it observable. These mirror
# FEATURE_TO_CORPUS_COORD; the absent-but-correlated axes (richardson_number/Ri,
# viscosity_ratio_wall_bulk) are listed explicitly so set-membership reads them as
# absent from a (Re, Pr) surrogate and routes them PARTIAL rather than OBSERVABLE.
_COORD_TO_INPUT_ALIASES: dict[str, tuple[str, ...]] = {
    "reynolds_number": ("Re", "log10_Re"),
    "prandtl_number": ("Pr",),
    "x_over_D": ("x_over_D", "log10_x_over_D"),
    "richardson_number": ("Ri", "log10_Ri"),
    "viscosity_ratio_wall_bulk": ("ratio_mu_w_b",),
    # Jin: Liu buoyancy parameter Bu is NOT a (Re, Pr) surrogate input and (MEASURED) not recoverable
    # from them — cv_r2_knn ~ 0 over the deploy region, because Bu carries the wall-temperature/HTD
    # signal the DIRECTION toggle drives, orthogonal to the bulk inputs (the SAME structure as Casper's
    # freestream noise). Its only alias is its own meta key and it is NOT known-partial, so set-
    # membership reads it absent → UNOBSERVABLE (the pole, like Casper). Distinct physical group from
    # richardson_number (Gr/Re^2); the same-name trap is avoided by its own coordinate.
    "liu_buoyancy_parameter": ("Bu",),
    # Casper: tunnel freestream noise is a distinct flow-environment axis, NOT a
    # surrogate input and NOT recoverable from (M, Re/m, x) — its only alias is
    # its own feature, so set-membership reads it absent → UNOBSERVABLE (the
    # PHYSMAP_WINS classification: baselines are structurally blind to it).
    "freestream_noise_rms_pitot_pct": ("freestream_noise_pct",),
    # Marineau: the entropy-layer/shock ratio S_T/X_SW is a deterministic
    # function of nose radius (Rn) and unit Reynolds at fixed Mach — BOTH
    # surrogate inputs — so it is recoverable from the inputs → OBSERVABLE
    # (baseline-visible). The negative control: a real validity bound exists,
    # but the steelman baseline already sees the failure via Rn.
    "entropy_layer_shock_ratio": ("Rn_mm", "Re_per_m"),
}

# Corpus coord → the raw meta key the feature extractor reads (extract_features
# computes log10_Re from meta["Re"], reads meta["Pr"], meta["x_over_D"], …).
_COORD_TO_META_KEY: dict[str, str] = {
    "reynolds_number": "Re",
    "prandtl_number": "Pr",
    "x_over_D": "x_over_D",
    "richardson_number": "Ri",
    "viscosity_ratio_wall_bulk": "ratio_mu_w_b",
    "liu_buoyancy_parameter": "Bu",                             # Jin (sCO2 vertical-tube buoyancy)
    "freestream_noise_rms_pitot_pct": "freestream_noise_pct",   # Casper
    "entropy_layer_shock_ratio": "st_xsw_ratio",                # Marineau
}

# Short surrogate-input name → canonical feature name extract_features understands.
_INPUT_TO_FEATURE: dict[str, str] = {
    "Re": "log10_Re",
    "Pr": "Pr",
    "x_over_D": "x_over_D",
    "Ri": "Ri",
    "Dh_mm": "log10_Dh_mm",
    "alpha_star": "alpha_star",
}


def input_to_feature(name: str) -> str:
    """Surrogate-input name → feature name (pass-through if already a feature)."""
    return _INPUT_TO_FEATURE.get(name, name)


def coord_input_aliases(coord: str) -> tuple[str, ...]:
    """The surrogate-input name(s) whose presence makes `coord` observable."""
    if coord in _COORD_TO_INPUT_ALIASES:
        return _COORD_TO_INPUT_ALIASES[coord]
    return tuple(f for f, c in FEATURE_TO_CORPUS_COORD.items() if c == coord)


def coord_to_feature(coord: str) -> str | None:
    """Corpus coord → canonical baseline feature name, or None if the coord has
    no baseline feature (e.g. richardson_number is not in the feature space)."""
    feats = [f for f, c in FEATURE_TO_CORPUS_COORD.items() if c == coord]
    if not feats:
        return None
    for f in feats:           # prefer the passthrough form (x_over_D over log10_x_over_D)
        if f == coord:
            return f
    return sorted(feats)[0]


def coord_to_meta_key(coord: str) -> str | None:
    """Corpus coord → the raw data column / meta key the extractor needs."""
    return _COORD_TO_META_KEY.get(coord)


def load_default_corpus_index() -> dict[str, ClosureEntry]:
    """Load + index the installed calibration corpus (closure_id → ClosureEntry)."""
    return index_by_id(load_corpus())


def classify_observability(
    surrogate_inputs: Sequence[str],
    regime: Regime,
    corpus_index: dict[str, ClosureEntry],
) -> dict[str, Observability]:
    """Map each resolved closure's bound variable → its structural observability.

    UNLISTED (or no resolved closures) → {} → the guard runs statistical-only.
    A bound variable is OBSERVABLE if the surrogate consumes its axis; PARTIAL if
    it is tagged known-partial (absent-but-correlated); else UNOBSERVABLE.
    """
    if regime is Regime.UNLISTED:
        return {}
    inputs = set(surrogate_inputs)
    out: dict[str, Observability] = {}
    for closure_id in REGIME_TO_CLOSURES.get(regime, ()):
        entry = corpus_index.get(closure_id)
        if entry is None:
            continue
        for bound in entry.validated_range:
            coord = bound.coord
            if any(a in inputs for a in coord_input_aliases(coord)):
                out[coord] = Observability.OBSERVABLE
            elif observability_class_for(closure_id, coord) == KNOWN_PARTIAL:
                out[coord] = Observability.PARTIAL
            else:
                out[coord] = Observability.UNOBSERVABLE
    return out
