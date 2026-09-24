"""A pip-installed physmap has no repository checkout.

Commands that need checkout-only data must say so in one sentence and exit non-zero --
never with a traceback. The commands that need nothing from the checkout must still work.
The checkout is hidden by making `repo_root()` return None, which is exactly what an
installed wheel sees.
"""
import pytest

from physmap import _paths, cli


@pytest.fixture
def no_checkout(monkeypatch):
    monkeypatch.setattr(_paths, "repo_root", lambda: None)


@pytest.mark.parametrize("argv", [
    ["benchmark", "report"],
    ["benchmark", "coverage"],
    ["benchmark", "run"],
    ["explain", "jin_sco2_buoyancy"],
    ["stress-test", "lewis-reuse"],
])
def test_checkout_only_commands_say_so_in_one_sentence(no_checkout, capsys, argv):
    assert cli.main(argv) == 1
    out = capsys.readouterr()
    assert "repository checkout" in out.err and "pip install -e ." in out.err
    assert "Traceback" not in out.err
    assert "Recomputing" not in out.out, "it must not claim to recompute what it cannot"


def test_commands_that_need_no_checkout_still_work(no_checkout, capsys):
    assert cli.main(["screen", "conjugate-heat-transfer", "--qoi", "peak_solid_temperature"]) == 0
    assert cli.main(["stress-test", "--list"]) == 0
    assert cli.main(["explain", "--list"]) == 0
    assert "NOT APPLICABLE" in capsys.readouterr().out
