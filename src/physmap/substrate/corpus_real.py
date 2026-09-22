"""PhysMAP Corpus Rung 2 — real-truth corpus-vs-causal test on Row-shaped data.

Data-source-agnostic: three adapters feed the same machinery — `pipe` (the vehicle-3
NB Ri sweep at conv_step3_final.json), `pump` (FDA pump fHb measurement; idles at
EMPIRICAL-INCOMPLETE while harvest grows + magnitude bridge lands), `step0_fixture`
(the algebraic stand-in for the plumbing smoke-test). Leave-one-out at the row level;
rung-1's verdict functions are imported.

The HEADLINE is G-corpus-beats-causal, but its interpretation is gated by
G-divergence-exists, which itself has BOTH a numeric criterion AND a substrate
criterion. If the substrate cannot carry a closure-reality divergence claim (Eq13 is a
correlation, not measurement; algebraic truth is closure-derivable by construction),
the headline is NOT-INFORMATIVE — neither pass nor fail. The corpus value test
requires a divergent-truth substrate, which today only the (future) bridged pump is.

Run: python -m physmap.substrate.corpus_real [--dataset pipe|pump|step0_fixture]
Torch-free.
"""

from __future__ import annotations

import argparse
import csv
import inspect
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from physmap.infra.blindspot_oracle import EMAX, SMAX, THETA_MAT
from physmap.infra.corpus_runtime import _bootstrap_ci
from physmap.infra.corpus_runtime import Entry, corpus_verdict, pde_residual_flag
from physmap.substrate.stage1_ingest import (
    TRUTH_FIXTURE,
    TRUTH_INDEPENDENT,
    Mechanism,
    Row,
    cfd_rows,
    step0_fixture,
)

OUT_DIR = Path(__file__).parent.parent / "results" / "physmap_corpus_real"

# Defaults
K_DEFAULT = 5
THETA_ERR = 0.05
TOL = 0.05
GUARDRAIL_PCT = 95
SCALE_STEP0 = SMAX + EMAX

# Pipe knobs
RI_CAL_LO, RI_CAL_HI = 0.1, 10.0
DEFAULT_PIPE_PATH = os.path.expanduser(
    os.environ.get("PHYSMAP_PIPE_DATA", "~/physmap-wall/convection/conv_step3_final.json"))
DEFAULT_PUMP_PATH = os.path.expanduser(
    os.environ.get("PHYSMAP_PUMP_DATA", "~/physmap-wall/pump/pump_rows_step2.json"))


# ── substrate metadata ───────────────────────────────────────────────────────

@dataclass
class SubstrateMeta:
    """Per-substrate declaration of the properties that gate the headline's
    interpretation. `divergent_truth_substrate` is the critical flag — if False, the
    substrate cannot test the corpus's value (closure-vs-correlation is not closure-
    vs-reality), and G-corpus-beats-causal must report NOT-INFORMATIVE."""
    name: str
    divergent_truth_substrate: bool
    reason: str
    norm_strategy: str                 # how to normalize closure/truth to comparable units
    bound_for_pde: float | None        # None = PDE arm inert (no fixed ceiling)
    magnitude_bridge_ok: bool
    extra: dict = field(default_factory=dict)


# ── physics coords (kNN index) ───────────────────────────────────────────────

def physics_coords_row(row: Row, scaling: str = "log") -> np.ndarray:
    """Per-row coord vector for kNN indexing. Mechanism-agnostic: uses each mechanism's
    operating_value. Log scaling is the default — operating values typically span
    orders of magnitude and Euclidean kNN behaves better in log space."""
    vals = np.array([m.operating_value for m in row.mechanisms], float)
    if scaling == "log":
        return np.log(np.maximum(vals, 1e-12))
    if scaling == "raw":
        return vals
    if scaling == "calib_range":
        out = []
        for m in row.mechanisms:
            rng = m.calib_hi - m.calib_lo
            out.append((m.operating_value - m.calib_lo) / max(rng, 1e-12))
        return np.array(out, float)
    raise ValueError(f"unknown scaling: {scaling}")


# ── normalization (closure vs truth on a comparable scale) ───────────────────

def _norm_for(row: Row, meta: SubstrateMeta) -> float:
    """Per-row normalizer so |closure - truth|/norm is unitless and comparable to TOL."""
    if meta.norm_strategy == "per_row_truth":
        return float(row.cfd_truth)
    if meta.norm_strategy == "global_scale":
        return float(SCALE_STEP0)
    if meta.norm_strategy == "per_row_ref_const":
        return float(row.meta.get("RIH2_C5_normalization_reference", 1.0))
    raise ValueError(f"unknown norm_strategy: {meta.norm_strategy}")


def normalize_row(row: Row, meta: SubstrateMeta) -> tuple[float, float, float, float]:
    """Return (closure_norm, truth_norm, error_norm_signed, norm)."""
    norm = _norm_for(row, meta)
    if meta.norm_strategy == "per_row_truth":
        # closure/truth_norm both reported on the per-row truth scale
        closure_norm = float(row.surrogate_prediction) / norm
        truth_norm = 1.0
    else:
        closure_norm = float(row.surrogate_prediction) / norm
        truth_norm = float(row.cfd_truth) / norm
    err = truth_norm - closure_norm
    return closure_norm, truth_norm, err, norm


# ── per-row verdicts (the four real-arm verdicts; pde may be inert) ──────────

def naive_verdict_row(row: Row) -> bool:
    """Untrustworthy iff any mechanism is out of [calib_lo, calib_hi]."""
    return any(not m.in_calibration() for m in row.mechanisms)


def causal_verdict_row(row: Row, theta_mat: float = THETA_MAT) -> bool:
    """Untrustworthy iff any material mechanism (contribution fraction ≥ theta_mat) is
    out of calibration. Mirrors rung 1's causal verdict on the schema's mechanisms."""
    mats = row.materialities()
    for i, m in enumerate(row.mechanisms):
        if (not m.in_calibration()) and (float(mats[i]) >= theta_mat):
            return True
    return False


def guardrails_verdict_row(row: Row, reference: dict, pct: float = GUARDRAIL_PCT) -> bool:
    """Untrustworthy iff any guardrail signal exceeds the pct-th percentile of the
    precomputed reference distribution. Reference signals all-zero (placeholder substrate)
    → guardrail arm is inert (never flags)."""
    for k in ("ood", "residual", "variance"):
        ref = np.asarray(reference.get(k, [0.0]), float)
        thr = float(np.percentile(ref, pct)) if len(ref) else 0.0
        sig = float(row.guardrail_signals.get(k, 0.0))
        if sig > thr:
            return True
    return False


def pde_residual_verdict(closure_norm: float, bound: float | None) -> bool | None:
    """Bound check on the NORMALIZED closure. Returns None if the arm is inert
    (no fixed ceiling for this substrate)."""
    if bound is None:
        return None
    return bool(pde_residual_flag(np.array([closure_norm]), bound=bound)[0])


# ── corpus build + LOO ───────────────────────────────────────────────────────

def row_to_entry(row: Row, meta: SubstrateMeta, scaling: str = "log") -> Entry:
    """Build a rung-1 Entry from a Row, normalized + with materiality fractions."""
    closure_norm, truth_norm, err_norm, _ = normalize_row(row, meta)
    mats = row.materialities()
    s_frac = float(mats[0]) if len(mats) >= 1 else 0.0
    e_frac = float(mats[1]) if len(mats) >= 2 else 0.0
    return Entry(
        coords=physics_coords_row(row, scaling=scaling),
        closure=closure_norm,
        truth=truth_norm,
        error=err_norm,             # signed; corpus_verdict takes |error|
        qoi_contrib_s=s_frac,
        qoi_contrib_e=e_frac,
    )


def divergence_exists(rows: list[Row], meta: SubstrateMeta, tol: float,
                      theta_mat: float) -> dict:
    """Per-row check: is |closure - truth| > tol AND does causal NOT flag it?
    Records the divergence-bearing condition ops explicitly."""
    divergent = []
    for r in rows:
        cl_n, tr_n, _, _ = normalize_row(r, meta)
        if abs(cl_n - tr_n) > tol and not causal_verdict_row(r, theta_mat):
            divergent.append({"op": list(r.operating_point),
                              "closure_norm": round(cl_n, 4),
                              "truth_norm": round(tr_n, 4),
                              "abs_err_norm": round(abs(cl_n - tr_n), 4)})
    return {"n_divergent": len(divergent), "divergent_ops": divergent,
            "numeric_criterion_passed": len(divergent) >= 1}


# ---------------------------------------------------------------------------
# The leave-one-out EXPERIMENT path -- loo_run, metrics_loo, gates, plotting,
# CSV writing, the dataset loaders and the __main__ runner -- is not ported.
#
# None of it is on the benchmark path: outside this module only SubstrateMeta is
# imported. It also computed per-arm recall and false-alarm rates, which a build
# that reports no performance metrics must not carry -- the public-surface audit
# flagged exactly those two lines, and deleting the dead code is the honest fix
# rather than adding an exemption to the guard.
# ---------------------------------------------------------------------------
