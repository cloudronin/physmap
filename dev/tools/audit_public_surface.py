#!/usr/bin/env python3
"""Audit the checkout before it goes public. Run it in CI and before every tag.

    python dev/tools/audit_public_surface.py

Checks things a reviewer would otherwise have to remember, and that fail quietly if
nobody looks: private identifiers left in the tree, a PDF slipping in, a performance
metric appearing in a build that claims to make none, and the release state disagreeing
with what the command line actually exposes.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: Identifiers from the private monorepo and its neighbours. A hit is not always a
#: leak, but it is always worth a human look before publishing.
#:
#: `physmap-wall` is deliberately NOT on this list. It is the name of the vanished CFD
#: working tree, and the known-results declaration has to name it: recording exactly
#: which inputs are missing is the point of that document. A marker list that blocks
#: honest provenance would get itself disabled the first time it fired.
PRIVATE_MARKERS = re.compile(
    r"\b(kgfm|assurify|credenza|uofa-lab|vvettrivel)\b", re.I
)

#: Names that would mean a performance metric is being COMPUTED.
BANNED_IDENTIFIERS = {
    "precision", "recall", "f1", "f1_score", "precision_score", "recall_score",
    "precision_recall_fscore_support", "fbeta_score",
}


def _tracked() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def check_no_pdfs(problems: list[str]) -> None:
    for f in _tracked():
        if f.lower().endswith(".pdf"):
            problems.append(f"tracked PDF: {f}")


def check_no_private_markers(problems: list[str]) -> None:
    allowed = {"LICENSE-CORPUS", "dev/tools/audit_public_surface.py"}
    for f in _tracked():
        if f in allowed:
            continue
        p = REPO / f
        try:
            text = p.read_text("utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if PRIVATE_MARKERS.search(line):
                problems.append(f"private marker: {f}:{i}: {line.strip()[:100]}")


def check_no_metric_computation(problems: list[str]) -> None:
    """AST, not grep. Prose that explains no claim is made must not trip this."""
    from physmap.release import emits_performance_metrics

    if emits_performance_metrics():
        return  # a NAFEMS_REPRODUCTION build is allowed to compute them

    for path in (REPO / "src").rglob("*.py"):
        tree = ast.parse(path.read_text("utf-8"), filename=str(path))
        for node in ast.walk(tree):
            name = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
            elif isinstance(node, ast.arg):
                name = node.arg
            if name in BANNED_IDENTIFIERS:
                problems.append(
                    f"performance metric computed: {path.relative_to(REPO)}:"
                    f"{node.lineno}: {name}"
                )


def check_release_state_matches_surface(problems: list[str]) -> None:
    from physmap.cli import build_parser
    from physmap.release import CURRENT_RELEASE_STATE, has_reproduce_command

    choices = build_parser()._subparsers._group_actions[0].choices
    present = "reproduce" in choices
    if present != has_reproduce_command():
        problems.append(
            f"release state {CURRENT_RELEASE_STATE.value} says reproduce should be "
            f"{'present' if has_reproduce_command() else 'absent'}, but it is "
            f"{'present' if present else 'absent'}"
        )


def check_no_expected_metrics(problems: list[str]) -> None:
    from physmap.release import emits_performance_metrics

    if emits_performance_metrics():
        return
    for f in _tracked():
        if f.endswith("expected_metrics.json"):
            problems.append(f"expected metrics in a non-reproduction build: {f}")


def main() -> int:
    problems: list[str] = []
    for check in (
        check_no_pdfs,
        check_no_private_markers,
        check_no_metric_computation,
        check_release_state_matches_surface,
        check_no_expected_metrics,
    ):
        check(problems)

    from physmap.release import CURRENT_RELEASE_STATE

    print(f"public-surface audit  (release state: {CURRENT_RELEASE_STATE.value})")
    if problems:
        print("\nFAILED:")
        for p in problems:
            print(f"  {p}")
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
