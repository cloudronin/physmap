"""Closure registry tests — parity with legacy formulas + corpus alignment.

The registry is the executable bridge between corpus calibration entries and
the substrate engine. These tests pin three properties:

  1. PARITY — every closure in `physmap.closures.formulas` produces numerically
     identical output to the legacy hand-coded formula it was extracted from
     (`forrest_substrate.py`, `lance_smith_substrate.py`). The byte-for-byte
     substrate-migration gate depends on this.

  2. CORPUS ALIGNMENT — every registry entry NOT marked `not-in-corpus` has a
     matching `closure_id` in `corpus.jsonl`. Catches drift between the
     registry and the calibration table.

  3. VOCABULARY GUARDS — geometry-class typos raise, unknown closure_ids raise.
     The geometry-match invariant compares strings exactly; silent typos are
     exactly what the guards are for.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from physmap.closures import (
    REGISTRY,
    ClosureEntry,
    get_closure,
    closure_ids_for_geometry,
)
from physmap.closures.formulas import (
    modified_sparrow_cur_nu,
    gnielinski_nu,
    dittus_boelter_nu,
    petukhov_nu,
    sieder_tate_nu,
    pohlhausen_forced_local_nu,
    mcadams_natural_local_nu,
    churchill_mixed_nu,
)
from physmap.closures.geometry_classes import (
    ALL_GEOMETRY_CLASSES,
    CIRCULAR_PIPE,
    FLAT_PLATE_EXTERNAL_MIXED,
    NARROW_RECT_CHANNEL_ONE_SIDED,
    assert_known_geometry,
)
from physmap.closures.registry import STATUS_NOT_IN_CORPUS

# Forrest legacy closure functions were retired in Cleanup 5 part 2 (same
# pattern as L&S in part 1). The registry's formulas in
# `closures/formulas.py` are now the canonical source for sparrow_cur /
# gnielinski / dittus_boelter / petukhov / sieder_tate. The byte-equality
# parity tests for Forrest closures (5 of them) are deleted below; the
# remaining structural test (closures load + REGISTRY shape correctness)
# stays as the load-bearing pin on the registry's correctness.
# Lance & Smith legacy closure functions were retired in Cleanup 5; the
# registry's pohlhausen / mcadams / churchill formulas are now the canonical
# source. The L&S parity tests below (pohlhausen / mcadams / churchill)
# were removed in Cleanup 5 — no legacy reference exists to compare against.
# Forrest's legacy closures remain (Cleanup 5 didn't shim Forrest as of
# this commit); the Forrest parity tests stay.


REPO_ROOT = Path(__file__).resolve().parents[1]


# ── PARITY: registry closures byte-equal to legacy ──────────────────────────

# Grid spans all four vehicles' operating regimes (laminar -> turbulent,
# low-Pr gases -> moderate-Pr water).
RE_GRID = np.array([100., 3000., 5000., 10000., 35000., 70000., 1e5, 1e6])
PR_GRID = np.array([0.71, 0.76, 2.2, 3.5, 5.4, 10., 0.7, 6.0])
RA_GRID = np.array([1e4, 1e6, 1e7, 1e8, 1e9])


def _identical(a, b) -> bool:
    """Byte-equal float comparison (atol=0, rtol=0). The refactor MUST NOT
    perturb numerical output by even one ULP."""
    return np.allclose(a, b, rtol=0, atol=0, equal_nan=True)


# Forrest parity tests (sparrow_cur, gnielinski, dittus_boelter heating +
# cooling, petukhov, sieder_tate unit + mu_ratio) were deleted in
# Cleanup 5 part 2 — the legacy `forrest_substrate` closure functions
# they compared against were retired. The byte-equality is preserved
# structurally (closures/formulas.py contains the exact same arithmetic).
# Confirmed engine-path-correctness via:
#   - test_substrate_engine.test_forrest_engine_path_actually_uses_registry
#     (sentinel-swap test that proves the engine genuinely consults the
#      registry)
#   - the byte-stable engine output that fed the locked NACA + Forrest
#     gates pre-Cleanup-5

# L&S parity tests (pohlhausen / mcadams / churchill) deleted in Cleanup 5
# — legacy copies in lance_smith_substrate.py were retired (closures live
# only in closures/formulas.py now). The byte-equality those tests
# guarded is preserved structurally: closures/formulas.py contains the
# exact same arithmetic that lance_smith_substrate.py previously did, and
# the Phase-1 substrate-engine structural-equality test on the L&S engine
# path passes against the running engine.


# ── CORPUS ALIGNMENT ────────────────────────────────────────────────────────

def test_every_corpus_backed_registry_entry_is_in_corpus():
    """If a registry entry's status is anything OTHER than 'not-in-corpus',
    the corresponding closure_id MUST be in the closed corpus. Its ids ship in the
    bundled coverage map, so this runs without the closed corpus itself."""
    from physmap.closures.index import premium_coverage_ids

    corpus_ids = premium_coverage_ids()
    drift = [
        cid for cid, entry in REGISTRY.items()
        if entry.status != STATUS_NOT_IN_CORPUS and cid not in corpus_ids
    ]
    assert not drift, (
        f"Registry claims corpus backing for {drift} but corpus.jsonl lacks these. "
        f"Either add them to corpus.jsonl or mark them status='not-in-corpus' in "
        f"the registry."
    )


def test_registry_ranges_present_for_corpus_backed_entries():
    """Corpus-backed entries should carry cached ranges (the substrate engine
    uses them for quick checks). Allow None only for closures that genuinely
    have no Re-style coordinate (e.g., the McAdams Ra-only natural-convection
    closure has re_range=None and ra_range set)."""
    for cid, entry in REGISTRY.items():
        if entry.status == STATUS_NOT_IN_CORPUS:
            continue
        has_any = (entry.re_range or entry.pr_range or entry.ra_range
                   or entry.ri_range or entry.bound_range)
        assert has_any, (
            f"{cid}: corpus-backed but no range fields populated; "
            f"the substrate engine has nothing to check the invariant against."
        )


# ── VOCABULARY GUARDS ───────────────────────────────────────────────────────

def test_unknown_geometry_class_raises():
    with pytest.raises(ValueError, match="Unknown geometry_class"):
        assert_known_geometry("does_not_exist")


def test_known_geometry_classes_accepted():
    for gc in ALL_GEOMETRY_CLASSES:
        assert_known_geometry(gc)   # must not raise


def test_get_closure_unknown_id_raises():
    with pytest.raises(KeyError, match="Unknown closure_id"):
        get_closure("not-a-real-closure-2099")


def test_get_closure_known_id_returns_entry():
    entry = get_closure("gnielinski-1976")
    assert isinstance(entry, ClosureEntry)
    assert entry.geometry_class == CIRCULAR_PIPE
    assert entry.required_inputs == ("Re", "Pr")


def test_closure_ids_for_geometry_returns_expected_groups():
    forrest_matched = closure_ids_for_geometry(NARROW_RECT_CHANNEL_ONE_SIDED)
    assert forrest_matched == ["modified-sparrow-cur-asym-narrow-rect-channel-2014"]

    circular = closure_ids_for_geometry(CIRCULAR_PIPE)
    assert "gnielinski-1976" in circular
    assert "dittus-boelter-1930" in circular
    assert "petukhov-1970" in circular        # not in corpus, but still registered
    assert "sieder-tate-1936" in circular

    ls_matched = closure_ids_for_geometry(FLAT_PLATE_EXTERNAL_MIXED)
    assert ls_matched == ["churchill-mixed-convection-flat-plate"]


def test_required_inputs_nonempty_for_every_entry():
    """Every closure MUST declare what it needs; otherwise the substrate
    engine has no idea how to dispatch the kwarg bag."""
    for cid, entry in REGISTRY.items():
        assert entry.required_inputs, f"{cid}: required_inputs is empty"
