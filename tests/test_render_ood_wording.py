"""The rendered explanations name the baseline ONE way: "input-based OOD detector".

The talk says that phrase while the live demo shows these strings on screen, so the two must
agree. The older wordings were not just inconsistent: "novelty detector" is wrong for the
seven-vehicle benchmark, which excludes novelty density and uses distance-to-training plus GP
variance. These tests pin the rendered sentences so the wording cannot drift back silently.
"""
from physmap.guardrail.render import (
    render_baseline, render_partial, render_unobservable)
from physmap.pipeline.validity_signal import PerBoundMargin

_BOUND = PerBoundMargin(coord="x_over_D", feature_name="x_over_D", margin=0.5,
                        bound_status="confirmed", side="low")
_STALE = ("statistical baseline", "statistical detector", "novelty detector")


def _clean(text: str) -> None:
    low = text.lower()
    for stale in _STALE:
        assert stale not in low, f"stale wording {stale!r} in: {text}"


def test_unobservable_rationale_names_the_input_based_ood_detector():
    quiet = render_unobservable(closure_id="gnielinski-1976", fired_bound=_BOUND,
                                bound_interval=(10.0, None), baseline_fired=False,
                                claims_for_closure=(), sources_index={})
    assert "unobservable to input-based OOD detectors" in quiet
    assert "Input-based OOD detectors are silent because they cannot observe x_over_D." in quiet
    _clean(quiet)

    loud = render_unobservable(closure_id="gnielinski-1976", fired_bound=_BOUND,
                               bound_interval=(10.0, None), baseline_fired=True,
                               claims_for_closure=(), sources_index={})
    assert "An input-based OOD detector also fired." in loud
    _clean(loud)


def test_baseline_and_partial_rationales_use_the_same_name():
    _clean(render_baseline(baseline_fired_names=(), all_quiet=True))
    assert render_baseline(baseline_fired_names=(), all_quiet=True).startswith(
        "All input-based OOD detectors are quiet")
    fired = render_baseline(baseline_fired_names=("gp_variance",), all_quiet=False)
    assert fired.startswith("Input-based OOD detector(s) fired (gp_variance)")
    _clean(fired)
    _clean(render_partial(closure_id="aung-worku-mixed-convection-1986",
                          fired_bound=PerBoundMargin(coord="richardson_number",
                                                     feature_name="Ri", margin=0.2,
                                                     bound_status="claimed", side="high"),
                          bound_interval=(0.1, 10.0)))
