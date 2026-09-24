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

__all__ = ["repo_root", "checkout_path", "have_checkout", "CheckoutRequired"]

_MARKERS = ("pyproject.toml", ".git")
REPO_URL = "https://github.com/cloudronin/physmap"


class CheckoutRequired(FileNotFoundError):
    """Checkout-only data was needed from an installed wheel.

    A FileNotFoundError, so every existing handler still catches it. The CLI catches it by
    name and prints this one sentence instead of a traceback.
    """

    def __init__(self, what: str):
        self.what = what
        super().__init__(
            f"this needs {what} from the repository checkout, and a pip-installed wheel "
            f"does not include that data. Clone {REPO_URL} and run `pip install -e .` inside "
            f"the clone to use it."
        )


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
        raise CheckoutRequired(what)
    p = root.joinpath(*parts)
    if not p.exists():
        raise FileNotFoundError(
            f"{what} not found at {p}. Expected it in the checkout at "
            f"{'/'.join(parts)}."
        )
    return p
