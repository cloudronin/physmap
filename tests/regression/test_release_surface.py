"""What this build is allowed to expose and to say.

The release state is a constant fixed at release time. These tests check that the
CLI surface and the emitted text follow from it, and -- more importantly -- that they
do NOT follow from which files happen to be on disk.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from physmap.release import (
    CURRENT_RELEASE_STATE,
    ReleaseState,
    emits_performance_metrics,
    has_reproduce_command,
)

REPO = Path(__file__).resolve().parents[2]


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "physmap.cli", *args], capture_output=True, text=True
    )


def test_this_build_makes_no_performance_claim():
    assert CURRENT_RELEASE_STATE is not ReleaseState.NAFEMS_REPRODUCTION
    assert not emits_performance_metrics()


def test_reproduce_is_an_unrecognised_command_not_a_missing_data_error():
    assert not has_reproduce_command()
    r = _cli("reproduce", "nafems-2026")
    assert r.returncode != 0
    assert "invalid choice" in r.stderr
    for phrase in ("not found", "missing", "no such file", "does not exist"):
        assert phrase not in r.stderr.lower(), (
            "a preview build must refuse `reproduce` as an unknown command, never as a "
            "runtime data-missing failure"
        )


def test_the_command_surface_is_fixed_by_the_state_not_the_filesystem():
    """Flip the constant in a subprocess and the command appears. Create or remove data
    directories and nothing changes."""
    code = (
        "import physmap.release as r, physmap.cli as c;"
        "r.CURRENT_RELEASE_STATE = r.ReleaseState.NAFEMS_REPRODUCTION;"
        "p = c.build_parser();"
        "print('reproduce' in p._subparsers._group_actions[0].choices)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.stdout.strip() == "True", out.stderr


def test_no_expected_metrics_file_ships():
    hits = list(REPO.rglob("expected_metrics.json"))
    assert hits == [], f"a preview build must not carry expected metrics: {hits}"


@pytest.mark.parametrize("case_id", ["conjugate-heat-transfer", "fda-blood-pump"])
def test_screen_exits_zero_and_marks_output_declarative(case_id):
    r = _cli("screen", case_id)
    assert r.returncode == 0, r.stderr
    assert "NOT APPLICABLE" in r.stdout
    assert "declarative" in r.stdout


def test_no_shipped_module_computes_precision_recall_or_f1():
    """Parse the shipped package and look for a metric being COMPUTED.

    Deliberately an AST walk, not a grep. Several modules discuss precision and recall
    in prose -- explaining that this build makes no such claim is the whole point -- and
    a text search cannot tell an explanation from a computation. This looks only at
    identifiers: names bound, attributes accessed, functions defined, keywords passed.
    String and comment text is invisible to it.
    """
    import ast

    BANNED = {
        "precision", "recall", "f1", "f1_score", "precision_score", "recall_score",
        "precision_recall_fscore_support", "fbeta_score", "true_positives",
        "false_positives", "false_negatives",
    }
    offenders = []

    for path in (REPO / "src").rglob("*.py"):
        tree = ast.parse(path.read_text("utf-8"), filename=str(path))
        for node in ast.walk(tree):
            found = None
            if isinstance(node, ast.Name) and node.id in BANNED:
                found = node.id
            elif isinstance(node, ast.Attribute) and node.attr in BANNED:
                found = node.attr
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in BANNED:
                found = node.name
            elif isinstance(node, ast.arg) and node.arg in BANNED:
                found = node.arg
            elif isinstance(node, ast.keyword) and node.arg in BANNED:
                found = node.arg
            elif isinstance(node, ast.alias) and (node.asname or node.name).split(".")[-1] in BANNED:
                found = node.name
            if found:
                offenders.append(f"{path.relative_to(REPO)}:{getattr(node, 'lineno', '?')}: {found}")

    assert offenders == [], (
        "a preview build must not compute performance metrics:\n" + "\n".join(offenders)
    )
