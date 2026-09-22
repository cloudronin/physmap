"""Repo-checkout paths, resolved once and failing loudly.

Several artifacts in this project live in the CHECKOUT, not in the installed
package: the digitised NACA fixture, the regime/observability mapping, the
registry-expansion table, and the benchmark substrate CSVs. They are deliberately
outside the wheel -- see the note on redistribution in LICENSE-CORPUS, and the
README's warning that the benchmark requires an editable install.

The trap this module exists to close: code that derives such a path with
``Path(__file__).parents[n]`` silently produces a WRONG path under the src/
layout rather than an error, and a caller that catches FileNotFoundError then
degrades quietly. A missing corpus becomes an empty corpus, and an empty corpus
still runs -- it just answers nothing. Every resolver here raises instead.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["repo_root", "checkout_path", "have_checkout"]

_MARKERS = ("pyproject.toml", ".git")


def repo_root() -> Path | None:
    """The checkout root, or None when running from an installed wheel."""
    for parent in Path(__file__).resolve().parents:
        if any((parent / m).exists() for m in _MARKERS):
            return parent
    return None


def have_checkout() -> bool:
    return repo_root() is not None


def checkout_path(*parts: str, what: str) -> Path:
    """A path inside the checkout. Raises unless it exists.

    `what` names the artifact in the error, so a failure says which file is
    missing and why it is not in the wheel.
    """
    root = repo_root()
    if root is None:
        raise FileNotFoundError(
            f"{what} lives in the repository checkout and is not shipped in the "
            f"wheel. Install from a clone with `pip install -e .` to use it."
        )
    p = root.joinpath(*parts)
    if not p.exists():
        raise FileNotFoundError(
            f"{what} not found at {p}. Expected it in the checkout at "
            f"{'/'.join(parts)}."
        )
    return p
