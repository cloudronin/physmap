"""Packaging regressions that fail SILENTLY if they are not asserted.

Every check here guards a failure mode whose symptom is a wrong answer rather
than an exception.
"""

from __future__ import annotations

import pytest


def test_closure_index_is_not_empty():
    """The index loads tolerantly, so a packaging break yields an EMPTY index.

    Nothing raises. Imports succeed. `CLOSURE_INDEX` is just {}, and every
    registered closure starts reporting as unregistered. Under the src/ layout
    this happens the moment `where = ["src"]` is dropped from pyproject.toml.
    """
    from physmap.closures.index import (
        CLOSURE_INDEX,
        EXPECTED_INDEX_SIZE,
        verify_index_loaded,
    )

    assert verify_index_loaded() == EXPECTED_INDEX_SIZE
    assert len(CLOSURE_INDEX) == EXPECTED_INDEX_SIZE == 201


def test_seed_corpus_resolves_and_is_the_seed():
    """A public checkout must land on the 15-closure seed, never on a premium file."""
    from physmap.corpus.calibration import active_tier, resolve_corpus_path

    p = resolve_corpus_path()
    assert p.is_file(), f"corpus did not resolve to a file: {p}"
    assert p.name == "corpus_seed.jsonl", f"expected the bundled seed, got {p}"
    assert active_tier() == "seed"


def test_evidence_corpus_is_firewalled_to_seed_closures():
    """A claim may only ship if its closure is in the seed. The firewall is an
    allowlist: no per-claim judgement calls about what "really" leaks."""
    import json

    from physmap.corpus.calibration import resolve_corpus_path
    from physmap.corpus.evidence import load_claims, load_sources

    seed_ids = {
        json.loads(line)["closure_id"]
        for line in resolve_corpus_path().read_text("utf-8").splitlines()
        if line.strip()
    }
    claims = load_claims()
    assert claims, "evidence claims failed to load"

    outside = sorted({c.closure_id for c in claims} - seed_ids)
    assert outside == [], f"claims ship for non-seed closures: {outside}"

    cited = {c.source_id for c in claims if c.source_id}
    shipped = {s.source_id for s in load_sources()}
    assert shipped <= cited, f"sources ship that no surviving claim cites: {sorted(shipped - cited)}"


def test_issue_url_points_at_this_repository():
    from physmap.closures.index import ISSUE_REPO

    assert ISSUE_REPO == "cloudronin/physmap"
