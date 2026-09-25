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
    """Counts, outcomes, verdicts and classes exactly; floats within 1e-9 relative.

    Exact float equality is not portable and a clean-clone check proved it: on
    numpy 2.5 / sklearn 1.9, dirker_water's observability_score differed from the
    banked value by one unit in the last place. The comparator keeps the fields that
    decide an outcome -- all of which are ints or strings -- on exact equality.
    """
    from physmap.benchmarks.compare import compare_matrices

    cmp = compare_matrices(fresh_matrix, banked_matrix)
    assert cmp.matches, (
        "benchmark drifted from its banked matrix:\n" + "\n".join(cmp.drift[:40])
    )


def test_outcome_bearing_fields_are_compared_exactly():
    """The tolerance must not be able to absorb a changed count or verdict."""
    from physmap.benchmarks.compare import compare_matrices

    a = {"cells": [{"vehicle_id": "v", "n_wrong": 8, "empirical_outcome": "PHYSMAP_WINS",
                    "observability_score": 0.5}]}
    for mutate in ({"n_wrong": 9}, {"empirical_outcome": "DO_NO_HARM"}):
        b = {"cells": [{**a["cells"][0], **mutate}]}
        assert not compare_matrices(a, b).matches, mutate

    # ...while a last-bit float difference is not drift
    b = {"cells": [{**a["cells"][0], "observability_score": 0.5000000000000001}]}
    cmp = compare_matrices(a, b)
    assert cmp.matches and cmp.within_tolerance


def test_observability_guards_pass(fresh_matrix):
    assert fresh_matrix["all_guards_passed"] is True


def test_the_run_is_deterministic(fresh_matrix):
    """Two runs of the same checkout must agree. A benchmark that wanders between
    runs cannot be evidence of anything."""
    from physmap.benchmarks.benchmark_v0_4 import run_matrix

    from physmap.benchmarks.compare import compare_matrices

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        second = run_matrix(write=False)
    cmp = compare_matrices(fresh_matrix, second)
    # Same interpreter, same build: this one really should be bit-identical.
    assert cmp.bit_identical, "\n".join((cmp.drift + cmp.within_tolerance)[:20])


def test_running_does_not_overwrite_the_banked_matrix(fresh_matrix):
    """`run_matrix(write=False)` is load-bearing: the monorepo's main() wrote the
    matrix BEFORE comparing, so a divergent run silently rewrote its own baseline."""
    import hashlib
    from physmap._paths import checkout_path

    from physmap.benchmarks.benchmark_v0_4 import BANK_DIR
    p = checkout_path(*BANK_DIR, "matrix_full_seven.json",
                      what="the banked matrix")
    before = hashlib.sha256(p.read_bytes()).hexdigest()

    from physmap.benchmarks.benchmark_v0_4 import run_matrix

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run_matrix(write=False)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == before
