"""The benchmark reproduces its own banked matrix from a clean checkout.

This is the claim the public release rests on, so it is asserted rather than
described. Every field of every cell is compared -- not just the headline outcome --
because an outcome can survive a change that moved every count underneath it.

Slow: it fits detectors for all seven vehicles. Roughly a minute.
"""

from __future__ import annotations

import warnings

import pytest

from physmap.benchmarks.registry import VEHICLES


def _deep_diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}: missing in fresh")
            elif k not in b:
                out.append(f"{path}.{k}: missing in banked")
            else:
                out += _deep_diff(a[k], b[k], f"{path}.{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} vs {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b))
                for d in _deep_diff(x, y, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} vs {b!r}"]


@pytest.fixture(scope="module")
def fresh_matrix():
    from physmap.benchmarks.benchmark_v0_4 import run_matrix

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # write=False: the run must never overwrite the bank it is compared against.
        return run_matrix(write=False)


@pytest.fixture(scope="module")
def banked_matrix():
    from physmap.benchmarks.report import load_banked_matrix

    return load_banked_matrix()


def test_all_seven_vehicles_are_discovered():
    from physmap.benchmarks.benchmark_v0_4 import discover_benchmark_vehicles

    found = {v[0] if isinstance(v, tuple) else getattr(v, "vehicle_id", v)
             for v in discover_benchmark_vehicles()}
    assert found == {v.vehicle_id for v in VEHICLES}


def test_every_cell_matches_the_banked_matrix_field_for_field(fresh_matrix, banked_matrix):
    fresh = {c["vehicle_id"]: c for c in fresh_matrix["cells"]}
    banked = {c["vehicle_id"]: c for c in banked_matrix["cells"]}
    assert set(fresh) == set(banked)

    diffs = []
    for vid in sorted(banked):
        diffs += _deep_diff(fresh[vid], banked[vid], vid)
    assert diffs == [], "benchmark drifted from its banked matrix:\n" + "\n".join(diffs[:40])


def test_matrix_level_fields_match(fresh_matrix, banked_matrix):
    for key in ("benchmark", "api", "detectors", "operating_percentiles",
                "all_guards_passed"):
        assert _deep_diff(fresh_matrix.get(key), banked_matrix.get(key), key) == []


def test_observability_guards_pass(fresh_matrix):
    assert fresh_matrix["all_guards_passed"] is True


def test_the_run_is_deterministic(fresh_matrix):
    """Two runs of the same checkout must agree. A benchmark that wanders between
    runs cannot be evidence of anything."""
    from physmap.benchmarks.benchmark_v0_4 import run_matrix

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        second = run_matrix(write=False)
    assert _deep_diff(fresh_matrix, second, "matrix") == []


def test_running_does_not_overwrite_the_banked_matrix(fresh_matrix):
    """`run_matrix(write=False)` is load-bearing: the monorepo's main() wrote the
    matrix BEFORE comparing, so a divergent run silently rewrote its own baseline."""
    import hashlib
    from physmap._paths import checkout_path

    p = checkout_path("data", "benchmarks", "v0_4", "matrix_full_seven.json",
                      what="the banked matrix")
    before = hashlib.sha256(p.read_bytes()).hexdigest()

    from physmap.benchmarks.benchmark_v0_4 import run_matrix

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run_matrix(write=False)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == before
