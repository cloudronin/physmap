"""PhysMAP Corpus Rung 2 — real-truth test. Torch-free.

The five gates:
  G-divergence-exists (HARD PRECONDITION) gates the headline's interpretation:
    pass requires BOTH a numeric divergence AND a substrate that carries closure-
    reality divergence (not closure-vs-correlation).
  G-corpus-beats-causal (HEADLINE) is reported as NOT-INFORMATIVE when divergence
    fails, NOT-EMITTED at EMPIRICAL-INCOMPLETE status, else PASS/FAIL on the gap.
"""

from __future__ import annotations

import inspect

import pytest

from physmap.substrate import corpus_real as cr
from physmap.substrate.stage1_ingest import (
    Mechanism,
    Row,
    load_rows,
)


# ── independence + leak (rung-1 carryover) ───────────────────────────────────

def test_independence_guard_propagated_from_stage1():
    """load_rows() hard-fails on truth_source='same-closure'; visible from corpus_real."""
    circular = [
        Row(operating_point=(1.0, 1.0), surrogate_prediction=0.5, cfd_truth=0.5,
            truth_source="same-closure",
            guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
            mechanisms=[Mechanism("a", "a-c", 1.0, 0.0, 2.0, 0.5),
                        Mechanism("b", "b-c", 1.0, 0.0, 2.0, 0.5)]),
    ]
    with pytest.raises(ValueError):
        load_rows(circular)


def test_no_leak_signature():
    """G-no-leak (signature): corpus_verdict has no truth-suggestive parameter names."""
    from physmap.infra.corpus_runtime import corpus_verdict
    params = list(inspect.signature(corpus_verdict).parameters.keys())
    for forbidden in ("hi_true", "truth", "y_true"):
        assert forbidden not in params, f"sig leaks truth: {forbidden}"


# ── pipe adapter correctness ─────────────────────────────────────────────────

# ── divergence detector ──────────────────────────────────────────────────────

def test_divergence_exists_detector_hand_built():
    """Hand-built rows: one row with closure ≈ truth → not divergent;
    one with |closure−truth|>tol AND causal not flagging → divergent."""
    meta = cr.SubstrateMeta(
        name="hand", divergent_truth_substrate=True, reason="hand",
        norm_strategy="per_row_truth", bound_for_pde=None, magnitude_bridge_ok=True,
    )
    # row A: clean (closure = truth)
    rowA = Row(operating_point=(1.0,), surrogate_prediction=1.0, cfd_truth=1.0,
               truth_source="experimental",
               guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
               mechanisms=[Mechanism("a", "a-c", 0.5, 0.0, 1.0, 0.5),
                           Mechanism("b", "b-c", 0.5, 0.0, 1.0, 0.5)])
    # row B: |closure-truth| big AND causal trustworthy (both mechanisms in-cal)
    rowB = Row(operating_point=(2.0,), surrogate_prediction=0.5, cfd_truth=1.0,
               truth_source="experimental",
               guardrail_signals={"ood": 0.0, "residual": 0.0, "variance": 0.0},
               mechanisms=[Mechanism("a", "a-c", 0.5, 0.0, 1.0, 0.5),
                           Mechanism("b", "b-c", 0.5, 0.0, 1.0, 0.5)])
    d = cr.divergence_exists([rowA, rowB], meta, tol=0.05, theta_mat=0.20)
    assert d["n_divergent"] == 1
    assert d["divergent_ops"][0]["op"] == [2.0]
    assert d["numeric_criterion_passed"] is True


# ── LOO mechanics on a hand-built small set ──────────────────────────────────

# ── status logic ─────────────────────────────────────────────────────────────

# ── gates: headline interpretation ───────────────────────────────────────────

# ── artifacts + additive invariant ───────────────────────────────────────────

def test_torch_free():
    """Importing the corpus_real module must not pull in torch. Checked in a CLEAN
    subprocess so the result is independent of full-suite import ordering — torch may
    be installed, and other tests may import it first, so a global
    `'torch' in sys.modules` check on the shared interpreter is order-fragile. The
    subprocess imports ONLY this module and reports whether torch came along."""
    import subprocess
    import sys

    probe = (
        "import sys, physmap.substrate.corpus_real; "
        "sys.exit(1 if 'torch' in sys.modules else 0)"
    )
    result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
    assert result.returncode == 0, (
        "importing physmap.substrate.corpus_real pulled in torch "
        f"(stderr={result.stderr.strip()!r})"
    )
