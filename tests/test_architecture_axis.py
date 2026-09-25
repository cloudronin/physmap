"""The architecture axis: three model types per vehicle, gated, compared with a bank.

The full recompute takes about twenty minutes and needs PyTorch, so it is a slow test. The
fast tests pin the bank's shape, the agreement it states, the gates on the small vehicles,
and the refusals: no PyTorch at import time, and a one-sentence refusal without it.
"""
from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from physmap._paths import TorchRequired
from physmap.benchmarks import architecture_axis as ax
from physmap.benchmarks.benchmark_v0_4 import discover_benchmark_vehicles

CELL_KEYS = {"vehicle_id", "architecture", "gate1", "outcome", "gate2_n_wrong_in_deploy",
             "n_deploy", "deploy_median_rel_err_pct", "clean_lift_max", "clean_lift_by_pct"}


@pytest.fixture(scope="module")
def bank():
    return ax.load_banked_axis()


def test_the_bank_covers_every_flagged_vehicle_and_model(bank):
    flagged = [s.vehicle_id for s in discover_benchmark_vehicles() if s.architecture_axis]
    assert bank["vehicles"] == flagged
    assert {(c["vehicle_id"], c["architecture"]) for c in bank["cells"]} == {
        (v, a) for v in flagged for a in ax.ARCHITECTURES}


def test_the_stated_agreement_follows_from_the_cells(bank):
    assert ax.agreement(bank["cells"], bank["vehicles"]) == bank["agreement"]


def test_the_bank_carries_no_measured_values(bank):
    """Counts, gate results and our own error percentages -- never a measured value."""
    for c in bank["cells"]:
        assert set(c) <= CELL_KEYS, c


def test_a_model_that_fails_the_gate_is_not_compared(bank):
    for c in bank["cells"]:
        if c["outcome"] == "NOT_TRAINABLE":
            assert not c["gate1"]["trainable"]
            assert "clean_lift_max" not in c


@pytest.mark.parametrize("vid,arch", [("jin_sco2_buoyancy", "gbt"), ("jin_sco2_buoyancy", "gp"),
                                      ("naca_tn1451", "gbt")])
def test_small_vehicle_gates_reproduce_the_bank(bank, vid, arch):
    bench = next(s for s in discover_benchmark_vehicles() if s.vehicle_id == vid)
    _tr, _te, Xtr, ytr, _Xte, _yte = ax._vehicle_data(bench)
    gate = ax.trainability_gate(ax.ARCHITECTURES[arch], Xtr, ytr, bench.calib, loo=True)
    banked = next(c for c in bank["cells"] if c["vehicle_id"] == vid and c["architecture"] == arch)
    assert gate == banked["gate1"]


def test_importing_the_axis_does_not_import_torch():
    probe = ("import sys, physmap.benchmarks.architecture_axis; "
             "sys.exit(1 if 'torch' in sys.modules else 0)")
    assert subprocess.run([sys.executable, "-c", probe]).returncode == 0


def test_without_torch_the_run_refuses_before_any_work(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", None)       # makes `import torch` fail
    called = []
    monkeypatch.setattr(ax, "discover_benchmark_vehicles", lambda: called.append(1) or [])
    with pytest.raises(TorchRequired, match="physmap\\[architectures\\]"):
        ax.run_axis()
    assert called == []


def test_the_banked_view_needs_neither_torch_nor_a_recompute():
    out = subprocess.run(
        [sys.executable, "-m", "physmap.cli", "benchmark", "architectures", "--banked"],
        capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "NOTHING WAS RECOMPUTED" in out.stdout


def test_the_report_summarises_the_axis_per_vehicle(bank):
    lines = "\n".join(ax.summary_lines(bank))
    for vid in bank["vehicles"]:
        assert vid in lines
    assert "fails gate" in lines


@pytest.mark.slow
def test_the_full_axis_recomputes_to_the_bank():
    pytest.importorskip("torch")
    cmp = ax.compare_with_bank(ax.run_axis(write=False))
    assert cmp.matches, cmp.drift[:5]


def test_the_deeponet_trains_and_predicts():
    """A short run of the network: one finite prediction per query row."""
    pytest.importorskip("torch")
    X = np.linspace(0, 1, 20).reshape(-1, 2)
    y = X.sum(1)
    pred = ax._fit_predict_deeponet(X, y, X, epochs=50)
    assert pred.shape == (10,) and np.all(np.isfinite(pred))
