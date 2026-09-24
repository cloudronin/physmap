"""One version number, written in three places, must agree everywhere.

The release workflow refuses a tag that differs from pyproject.toml; this catches the other two
before a release is even attempted -- `physmap --version` and the citation. (A regex, not
tomllib: tomllib is not in Python 3.10, which the project supports.)
"""
import re
from pathlib import Path

import physmap

REPO = Path(__file__).resolve().parents[1]


def test_the_version_agrees_everywhere():
    pyproject = (REPO / "pyproject.toml").read_text()
    version = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M).group(1)
    assert physmap.__version__ == version
    cff = re.search(r"^version:\s*(\S+)", (REPO / "CITATION.cff").read_text(), re.M).group(1)
    assert cff == version
    assert f"## {version} " in (REPO / "CHANGELOG.md").read_text()
