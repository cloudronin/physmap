"""PhysMAP Stage 1 (Part B) — row ingestion + the independence guard.

The data-ready contract for real-CFD validation. A Row is the single unit the harness
reasons over; when the dependency wall (CFD oracle + PhysicsNeMo) clears, a `cfd_rows()`
loader produces Rows from the data and NOTHING downstream changes — the Step 0 algebraic
oracle is wired in here as a STAND-IN fixture (`step0_fixture_rows`) so the whole harness
runs end-to-end now.

INDEPENDENCE GUARD (the guard that matters most): the entire value of Stage 1 is that the
truth label is INDEPENDENT of the closure-based materiality the causal method uses. If a
row's `cfd_truth` were produced by the same closure the causal method checks, the
experiment is circular (Step 0 in CFD clothing) and any lift is fake. `load_rows`
HARD-FAILS (raises) on `truth_source == "same-closure"`. The fixture uses its own marked
value `"fixture-algebraic"` (exempt → STAND-IN status, never EMPIRICAL).

Torch-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# truth_source controlled vocabulary
TRUTH_INDEPENDENT = {"experimental", "independent-hifi-model"}   # OK for an EMPIRICAL verdict
TRUTH_FIXTURE = "fixture-algebraic"                              # the Step 0 stand-in (→ STAND-IN)
TRUTH_CIRCULAR = "same-closure"                                 # hard-fail: circular, refused at load
TRUTH_PENDING = "pending"                                       # coarse run; independent truth not yet stood up
TRUTH_SOURCES = TRUTH_INDEPENDENT | {TRUTH_FIXTURE, TRUTH_CIRCULAR, TRUTH_PENDING}


@dataclass
class Mechanism:
    """One closure/mechanism at an operating point. materiality + in_cal are DERIVED
    (contribution fraction; operating_value within [calib_lo, calib_hi])."""
    name: str
    closure_id: str
    operating_value: float
    calib_lo: float
    calib_hi: float
    contribution: float            # closure-side contribution magnitude to the QoI

    def in_calibration(self) -> bool:
        return self.calib_lo <= self.operating_value <= self.calib_hi


@dataclass
class Row:
    """One operating point: the surrogate prediction, the (independent) truth, the
    guardrail signals, and the per-mechanism closure structure."""
    operating_point: tuple
    surrogate_prediction: float
    cfd_truth: float
    truth_source: str
    guardrail_signals: dict                 # {"ood": float, "residual": float, "variance": float}
    mechanisms: list                        # list[Mechanism]
    cfd_uncertainty: float = 0.0            # CFD's own numerical-error band (0 for the fixture)
    meta: dict = field(default_factory=dict)

    def materialities(self) -> np.ndarray:
        c = np.array([m.contribution for m in self.mechanisms], float)
        total = c.sum()
        return c / total if total > 0 else np.zeros_like(c)


def _validate(row: Row) -> None:
    if row.truth_source not in TRUTH_SOURCES:
        raise ValueError(f"Row {row.operating_point}: unknown truth_source {row.truth_source!r} "
                         f"(allowed: {sorted(TRUTH_SOURCES)})")
    if not row.mechanisms:
        raise ValueError(f"Row {row.operating_point}: no mechanisms")
    for k in ("ood", "residual", "variance"):
        if k not in row.guardrail_signals:
            raise ValueError(f"Row {row.operating_point}: guardrail_signals missing {k!r}")


def load_rows(rows: list) -> list:
    """Validate + enforce the INDEPENDENCE GUARD. Hard-fails (raises) on any row whose
    truth comes from the same closure the causal method checks — circular, refused at the
    door so it can never reach a lift verdict."""
    circular = [r for r in rows if r.truth_source == TRUTH_CIRCULAR]
    if circular:
        ids = [r.operating_point for r in circular][:5]
        raise ValueError(
            f"INDEPENDENCE GUARD: {len(circular)} row(s) have truth_source='same-closure' "
            f"(e.g. {ids}) — the truth is produced by the closure the causal method checks, so "
            f"causal-vs-truth is circular (Step 0 in CFD clothing). Refused at ingestion. The "
            f"truth must be experimental or an independent hi-fi model.")
    for r in rows:
        _validate(r)
    return rows


def truth_is_independent(rows: list) -> bool:
    """True iff every row's truth is from an independent source (real-data EMPIRICAL gate)."""
    return all(r.truth_source in TRUTH_INDEPENDENT for r in rows)


def is_fixture(rows: list) -> bool:
    """True iff all rows are the algebraic stand-in (→ STAND-IN status)."""
    return all(r.truth_source == TRUTH_FIXTURE for r in rows)


# ── Step 0 algebraic oracle as the STAND-IN fixture ───────────────────────────

def _maha(P, mu, inv):
    d = np.asarray(P, float) - mu
    return np.sqrt(np.einsum("ij,jk,ik->i", d, inv, d))


def step0_fixture(seed: int = 0) -> tuple:
    """Build the Step 0 grid as Stage-1 Rows + the TRAINING-distribution reference signals
    (for the harness's 95th-pct self-calibration — the production-correct calibration set,
    NOT the query rows). Returns (rows, reference). truth_source='fixture-algebraic'
    (exempt from the independence guard, → STAND-IN); cfd_uncertainty=0.

    Calibrating on the FULL-ENVELOPE training reference reproduces Step 0's deployed behavior:
    the surrogate is confident across the trained envelope, so the extrapolation region's
    signals are not extreme vs the training reference → guardrails MISS the blind spot."""
    from physmap.infra import blindspot_oracle as bo

    ds = bo.build_dataset(seed=seed)
    X, Xtr = ds.X, ds.X_train
    mu, cov = Xtr.mean(axis=0), np.cov(Xtr.T)
    inv = np.linalg.inv(cov)
    # per-query-point signals
    maha_q = _maha(X, mu, inv)
    residual_q = np.abs(ds.hi_sur - ds.hi_clo)
    variance_q = ds.surrogate.ensemble_variance(X)
    # training-distribution reference (the calibration set)
    reference = {
        "ood": _maha(Xtr, mu, inv),
        "residual": np.abs(ds.surrogate.predict(Xtr) - ds.closures.hi_clo(Xtr[:, 0], Xtr[:, 1])),
        "variance": ds.surrogate.ensemble_variance(Xtr),
    }
    rows = []
    for i in range(len(X)):
        tau, t = float(X[i, 0]), float(X[i, 1])
        mechs = [
            Mechanism("shear", "closure-shear", tau, bo.TAU_LO, bo.TAU_CAL_S, float(ds.c_s[i])),
            Mechanism("exposure", "closure-exposure", t, bo.T_LO, bo.T_CAL_E, float(ds.c_e[i])),
        ]
        rows.append(Row(
            operating_point=(tau, t),
            surrogate_prediction=float(ds.hi_sur[i]),
            cfd_truth=float(ds.hi_true[i]),
            truth_source=TRUTH_FIXTURE,
            cfd_uncertainty=0.0,
            guardrail_signals={"ood": float(maha_q[i]), "residual": float(residual_q[i]),
                               "variance": float(variance_q[i])},
            mechanisms=mechs,
        ))
    return rows, reference


def step0_fixture_rows(seed: int = 0) -> list:
    """Just the rows (convenience for callers that don't need the calibration reference)."""
    return step0_fixture(seed=seed)[0]


# ── real-data loader (the doc's swap-in; torch-free) ──────────────────────────

def cfd_rows(path) -> list:
    """Load Stage-1 Rows from a JSON payload an external producer wrote (e.g. the real
    PhysicsNeMoAdapter running in a torch env). The payload is {"rows": [ {...}, ... ]}
    where each row dict carries operating_point / surrogate_prediction / cfd_truth /
    truth_source / cfd_uncertainty / guardrail_signals / mechanisms[...]. Torch-free — this
    is the production swap-in for step0_fixture_rows when real CFD data arrives.
    Validation + the independence guard are applied via load_rows()."""
    import json
    from pathlib import Path
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []
    for d in payload["rows"]:
        mechs = [Mechanism(**m) for m in d["mechanisms"]]
        rows.append(Row(
            operating_point=tuple(d["operating_point"]),
            surrogate_prediction=float(d["surrogate_prediction"]),
            cfd_truth=float(d["cfd_truth"]),
            truth_source=d["truth_source"],
            cfd_uncertainty=float(d.get("cfd_uncertainty", 0.0)),
            guardrail_signals=d["guardrail_signals"],
            mechanisms=mechs,
            meta=d.get("meta", {}),
        ))
    return load_rows(rows)
