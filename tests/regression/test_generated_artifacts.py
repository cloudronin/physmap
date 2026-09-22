"""Committed artifacts that are GENERATED must still match their generator.

Both files here are derived, committed, and read by something. A generated file that
has silently drifted from its source is worse than a missing one: it looks authoritative
and it is stale.
"""

from __future__ import annotations

import json
import subprocess
import sys

from physmap._paths import checkout_path, repo_root


def test_regime_observability_mapping_matches_its_generator():
    """mapping.jsonl is a projection of the corpus + the regime table. It was
    regenerated against the 15-closure seed when this repository was built; if the
    seed or the regime table changes without a rebuild, this catches it."""
    r = subprocess.run(
        [sys.executable, "-m", "physmap.guardrail.regime_observability", "validate"],
        capture_output=True, text=True, cwd=repo_root(),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASSED" in r.stdout


def test_evidence_seed_matches_a_fresh_split_when_premium_is_available():
    """The firewalled evidence corpus is derived, not hand-edited. Its generator has a
    --check mode; run it when the premium source is reachable, skip when it is not
    (which is the normal case for a public clone)."""
    import pytest

    src = repo_root().parent / "uofa-lab" / "physmap" / "physmap" / "results" / "evidence_corpus"
    if not src.is_dir():
        pytest.skip("premium evidence corpus not present (normal for a public clone)")

    r = subprocess.run(
        [sys.executable, "dev/tools/split_evidence_corpus.py",
         "--premium-dir", str(src), "--check"],
        capture_output=True, text=True, cwd=repo_root(),
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_banked_matrix_is_valid_json_with_seven_cells():
    p = checkout_path("data", "benchmarks", "v0_4", "matrix_full_seven.json",
                      what="the banked matrix")
    m = json.loads(p.read_text("utf-8"))
    assert len(m["cells"]) == 7
    assert m["all_guards_passed"] is True
    assert len({c["vehicle_id"] for c in m["cells"]}) == 7
