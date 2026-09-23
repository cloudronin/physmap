"""The surrogate fit, its generalisation residual, and the case-loss failure mode.

The earlier version of this suite took `{Re: Nu}` and had a test that *demonstrated*
last-write-wins on a repeated `Re`. That pinned the bug instead of preventing it: on a
2-D (Re, Gr*) grid, several cases share an Re, and a dict silently kept one. These tests
now require that cases survive ingestion and that a repeated Re cannot straddle the split.
"""

from __future__ import annotations

import pytest

from physmap.materiality.surrogate_fit import (
    Case,
    fit_and_verify,
    fit_power_law,
    ingest,
    irreducible_spread,
    residuals,
    split_by_re,
)


def _law(c, n, res, tag="c", **cond):
    return [Case(f"{tag}{i}", re, c * re**n, cond) for i, re in enumerate(res, 1)]


# ── ingestion keeps every case ───────────────────────────────────────────────

def test_two_cases_at_one_re_both_survive():
    """The failure the old API had: same Re, different Gr, one case silently lost."""
    cases = [
        Case("a", 800, 8.0, {"Gr": 1.0e6}),
        Case("b", 800, 9.5, {"Gr": 5.0e6}),
        Case("c", 1600, 10.0, {"Gr": 1.0e6}),
    ]
    kept = ingest(cases)
    assert len(kept) == 3
    assert {c.case_id for c in kept} == {"a", "b", "c"}


def test_duplicate_case_ids_raise():
    with pytest.raises(ValueError, match="duplicate case id"):
        ingest([Case("a", 800, 8.0), Case("a", 1600, 9.0)])


def test_conditions_the_surrogate_cannot_see_are_retained():
    c = ingest([Case("a", 800, 8.0, {"Gr": 5e6, "L_over_D": 20, "direction": "up"})])[0]
    assert c.conditions["Gr"] == 5e6 and c.conditions["direction"] == "up"


@pytest.mark.parametrize("re,nu", [(0, 8.0), (-1, 8.0), (800, 0), (800, -2)])
def test_non_positive_values_are_refused(re, nu):
    with pytest.raises(ValueError, match="must be positive"):
        Case("a", re, nu)


# ── repeated Re: kept, fitted, and its floor reported ────────────────────────

def test_repeated_re_puts_a_floor_on_the_residual_and_it_is_reported():
    cases = [Case("a", 800, 8.0), Case("b", 800, 9.6), Case("c", 1600, 10.0)]
    spread = irreducible_spread(cases)
    assert 800 in spread and 1600 not in spread
    assert spread[800] == pytest.approx((9.6 - 8.0) / 8.8, rel=1e-9)
    fit = fit_power_law(cases)
    assert fit.n_cases == 3 and fit.n_distinct_re == 2
    assert fit.irreducible_spread[800] > 0


def test_a_fit_needs_two_distinct_re_not_merely_two_cases():
    with pytest.raises(ValueError, match="2 distinct Re"):
        fit_power_law([Case("a", 800, 8.0), Case("b", 800, 9.0)])


# ── the fit itself ───────────────────────────────────────────────────────────

def test_recovers_an_exact_power_law():
    fit = fit_power_law(_law(3.5, 0.25, (400, 800, 1200, 1600)))
    assert fit.coefficient == pytest.approx(3.5, rel=1e-9)
    assert fit.exponent == pytest.approx(0.25, rel=1e-9)


def test_exact_data_gives_zero_residual_on_both_splits():
    _, f, h = fit_and_verify(_law(3.5, 0.25, (400, 800, 1600)),
                             _law(3.5, 0.25, (600, 1200), tag="h"))
    assert f.max_abs_rel == pytest.approx(0.0, abs=1e-12)
    assert h.max_abs_rel == pytest.approx(0.0, abs=1e-12)


def test_held_out_residual_is_separate_and_can_be_worse():
    held = _law(3.5, 0.25, (600, 1200), tag="h")
    held[1] = Case(held[1].case_id, held[1].Re, held[1].Nu * 1.10)
    _, f, h = fit_and_verify(_law(3.5, 0.25, (400, 800, 1600)), held)
    assert f.max_abs_rel < 1e-9
    assert h.max_abs_rel == pytest.approx(0.10 / 1.10, rel=1e-6)
    assert h.n == 2


# ── the split must not straddle an Re ────────────────────────────────────────

def test_an_re_on_both_sides_is_refused():
    with pytest.raises(ValueError, match="Re values appear on both sides"):
        fit_and_verify(_law(3.5, 0.25, (400, 800)),
                       _law(3.5, 0.25, (800, 1600), tag="h"))


def test_split_by_re_keeps_every_case_at_one_re_together():
    cases = [Case("a", 800, 8.0, {"Gr": 1e6}), Case("b", 800, 9.5, {"Gr": 5e6}),
             Case("c", 1600, 10.0), Case("d", 400, 6.0)]
    fit_side, held = split_by_re(cases, holdout_re=[800])
    assert {c.case_id for c in held} == {"a", "b"}      # both, not one
    assert {c.case_id for c in fit_side} == {"c", "d"}
    assert not (set(c.Re for c in fit_side) & set(c.Re for c in held))


def test_holding_out_every_re_is_refused():
    with pytest.raises(ValueError, match="nothing left to fit"):
        split_by_re(_law(3.5, 0.25, (400, 800)), holdout_re=[400, 800])


def test_unknown_holdout_re_is_refused():
    with pytest.raises(ValueError, match="not present in the cases"):
        split_by_re(_law(3.5, 0.25, (400, 800)), holdout_re=[999])


# ── reporting ────────────────────────────────────────────────────────────────

def test_report_is_per_case_and_carries_signed_residuals():
    fit = fit_power_law(_law(3.5, 0.25, (400, 1600)))
    biased = [Case(c.case_id, c.Re, c.Nu * 1.05) for c in _law(3.5, 0.25, (600, 1200), tag="h")]
    r = residuals(fit, biased, "held out")
    assert r.mean_signed_rel < 0
    assert [cid for cid, _, _ in r.per_case] == ["h1", "h2"]
    assert "held out" in r.summary() and "n=2" in r.summary()


def test_empty_held_out_set_reports_nothing_rather_than_zero():
    fit = fit_power_law(_law(3.5, 0.25, (400, 1600)))
    r = residuals(fit, [], "held out")
    assert r.n == 0 and r.max_abs_rel is None
    assert "no cases" in r.summary()
