"""The NAFEMS talk package agrees with the committed evidence, and its check can fail.

`tools/talk_package.py check` needs no matplotlib: it recomputes every displayed number from
the committed records and compares the package against them, against the clean-clone CLI
output, and against the written documents. The mutation tests feed it broken copies of the
package, because a check that cannot fail proves nothing.
"""
import importlib.util
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("talk_package", REPO / "tools" / "talk_package.py")
tp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tp)


def test_the_committed_package_passes_its_check(capsys):
    assert tp.check() == 0, capsys.readouterr().out


@pytest.fixture
def copy(tmp_path, monkeypatch):
    """A private copy of docs/talk that the check reads instead of the real one."""
    dst = tmp_path / "talk"
    shutil.copytree(tp.TALK, dst)
    monkeypatch.setattr(tp, "TALK", dst)
    monkeypatch.setattr(tp, "FIG", dst / "figures")
    monkeypatch.setattr(tp, "FIGDATA", dst / "figures" / "data")
    monkeypatch.setattr(tp, "REPRO", dst / "reproduction")
    return dst


def _edit(path: Path, old: str, new: str):
    text = path.read_text()
    assert old in text, (path, old)
    path.write_text(text.replace(old, new, 1))


def _fails_with(capsys, needle: str):
    assert tp.check() == 1
    out = capsys.readouterr().out
    assert needle in out, out


def test_an_unsourced_number_in_the_prose_fails(copy, capsys):
    _edit(copy / "narrative.md", "within 0.06 %", "within 0.0123 %")
    _fails_with(capsys, "'0.0123' is neither a registered number")


def test_a_station_value_that_differs_from_the_cli_output_fails(copy, capsys):
    _edit(copy / "reproduction" / "stdout.txt", "-17.0%", "-17.1%")
    _fails_with(capsys, "CLI printed -17.1")


def test_a_hand_edited_facts_sheet_fails(copy, capsys):
    _edit(copy / "facts-sheet.md", "| 67.55 | yes |", "| 67.55 | no |")
    _fails_with(capsys, "facts-sheet.md is stale")


def test_a_figure_that_stops_showing_its_number_fails(copy, capsys):
    _edit(copy / "figures" / "lewis_2_control_vs_gravity_on.svg", "0.408", "0.409")
    _fails_with(capsys, "does not show lewis.ood.threshold_distance")


def test_a_clean_clone_that_did_not_exit_zero_fails(copy, capsys):
    _edit(copy / "reproduction" / "log.txt", "exit status: 0", "exit status: 1")
    _fails_with(capsys, "did not exit 0")


def test_a_clean_clone_record_that_drifts_from_the_bank_fails(copy, capsys):
    _edit(copy / "reproduction" / "fresh_record.json", '"training_rows": 532',
          '"training_rows": 531')
    _fails_with(capsys, "drifts from the bank")


def test_every_figure_registers_the_numbers_it_shows():
    import json
    saved = json.loads((tp.TALK / "numbers.json").read_text())
    for name in tp.FIGURES:
        assert saved["figures"].get(name), f"{name} registers no numbers"
