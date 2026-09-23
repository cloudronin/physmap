"""The surrogate fit and its generalisation residual."""

from __future__ import annotations

import pytest

from physmap.materiality.surrogate_fit import (
    fit_and_verify,
    fit_power_law,
    residuals,
)


def _exact(c, n, res):
    return {re: c * re**n for re in res}


def test_recovers_an_exact_power_law():
    fit = fit_power_law(_exact(3.5, 0.25, (400, 800, 1200, 1600)))
    assert fit.coefficient == pytest.approx(3.5, rel=1e-9)
    assert fit.exponent == pytest.approx(0.25, rel=1e-9)


def test_exact_data_gives_zero_residual_on_both_splits():
    fit, f, h = fit_and_verify(_exact(3.5, 0.25, (400, 800, 1600)),
                               _exact(3.5, 0.25, (600, 1200)))
    assert f.max_abs_rel == pytest.approx(0.0, abs=1e-12)
    assert h.max_abs_rel == pytest.approx(0.0, abs=1e-12)


def test_held_out_residual_is_reported_separately_and_can_be_worse():
    fit_c = _exact(3.5, 0.25, (400, 800, 1600))
    held = _exact(3.5, 0.25, (600, 1200))
    held[1200] *= 1.10                       # a condition the fit does not capture
    _, f, h = fit_and_verify(fit_c, held)
    assert f.max_abs_rel < 1e-9
    assert h.max_abs_rel == pytest.approx(0.10 / 1.10, rel=1e-6)
    assert h.n == 2


def test_overlapping_conditions_are_refused():
    """The leak this module exists to prevent: a shared condition makes the held-out
    residual a fitted residual under another name, and says nothing when unchecked."""
    with pytest.raises(ValueError, match="both the fit and the held-out set"):
        fit_and_verify(_exact(3.5, 0.25, (400, 800)), _exact(3.5, 0.25, (800, 1600)))


def test_a_one_condition_fit_is_refused():
    with pytest.raises(ValueError, match="at least 2 conditions"):
        fit_power_law({400: 8.0})


def test_conditions_are_keyed_by_re_so_a_duplicate_cannot_be_smuggled_in():
    """Keying on Re makes a repeated condition impossible by construction, which is why
    the `unidentifiable` guard inside fit_power_law is unreachable through this API. It
    is kept as a cheap assertion for any future caller that builds the mapping
    differently; it is not exercised here because it cannot be reached."""
    conditions = {400: 8.0}
    conditions[400.0] = 9.0
    assert conditions == {400: 9.0}
    with pytest.raises(ValueError, match="at least 2 conditions"):
        fit_power_law(conditions)


def test_report_carries_signed_and_absolute_residuals():
    fit = fit_power_law(_exact(3.5, 0.25, (400, 1600)))
    biased = {re: nu * 1.05 for re, nu in _exact(3.5, 0.25, (600, 1200)).items()}
    r = residuals(fit, biased, "held out")
    assert r.mean_signed_rel < 0            # prediction sits below the biased truth
    assert r.max_abs_rel > 0
    assert "held out" in r.summary() and "n=2" in r.summary()


def test_empty_held_out_set_reports_nothing_rather_than_zero():
    fit = fit_power_law(_exact(3.5, 0.25, (400, 1600)))
    r = residuals(fit, {}, "held out")
    assert r.n == 0 and r.max_abs_rel is None
    assert "no conditions" in r.summary()
