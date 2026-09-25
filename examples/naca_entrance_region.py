"""The pipe-entrance case, end to end.

A heated pipe's Nusselt number is predicted from (Re, Pr) alone, by the Gnielinski
correlation for fully developed flow, then asked about the entrance region. It has
never seen x/D -- the variable that governs the entrance -- so it cannot represent
what changes there. Neither can an input-based OOD detector: it sees the same two
columns, and in those two columns the entrance points look perfectly ordinary.

PhysMAP reads the bound variable from the test coordinates instead, checks it
against the closure's validated range, and knows at fit time that x/D is
structurally invisible to this surrogate. The result is a refusal with a reason.

The last block scores the correlation against the measurements, so the failure is
shown rather than asserted: at the benchmark's own NACA error threshold it is right
on every fully developed point and wrong on some entrance points, mostly near the
inlet. The closure check flags every entrance point, so it also flags the ones the
correlation gets right.

Data: NACA TN-1451 (1947), Fig 10, bellmouth entrance. US Government work,
public domain; two-reader cross-validated digitisation.

Run:  python examples/naca_entrance_region.py
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import numpy as np

from physmap import (
    ColumnMap,
    CredibilityGuardrail,
    DetectorKind,
    Observability,
    Regime,
    Verdict,
)

CSV = Path(__file__).resolve().parents[1] / "data" / "naca" / "cross_validated_fig10.csv"
COORDS = ["Re", "Pr", "x_over_D"]
FULLY_DEVELOPED = 10.0   # x/D at which the entrance effect has died out


def load():
    with open(CSV) as f:
        reader = csv.DictReader(line for line in f if not line.lstrip().startswith("#"))
        return [{k: (float(v) if _num(v) else v) for k, v in row.items()} for row in reader]


def _num(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def main() -> None:
    rows = load()
    train = [r for r in rows if r["x_over_D"] >= FULLY_DEVELOPED]
    test = [r for r in rows if r["x_over_D"] < FULLY_DEVELOPED]

    Xtr = np.array([[r[c] for c in COORDS] for r in train])
    ytr = np.array([r["Nu_meas"] for r in train])
    Xte = np.array([[r[c] for c in COORDS] for r in test])

    print(f"train: {len(train)} fully-developed points   test: {len(test)} entrance points\n")

    # The surrogate only ever saw Re and Pr.
    guard = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)

    print("observability, decided at construction time:")
    for var, obs in guard.observability_classification.items():
        print(f"  {var:24s} {obs.name}")
    print()

    guard.fit(Xtr, train_y=ytr, columns=ColumnMap(inputs=COORDS))
    results = guard.assess(Xte, columns=ColumnMap(inputs=COORDS))

    print("verdicts:", dict(Counter(a.verdict.name for a in results)))
    print("bound variable that fired:", {a.fired_bound_variable for a in results})
    print()

    a = results[0]
    print("one assessment:")
    print(f"  verdict          {a.verdict.name}")
    print(f"  observability    {a.observability.name}")
    print(f"  closure_validity fired={a.signals[DetectorKind.CLOSURE_VALIDITY].fired}")
    # Both input-based OOD detectors in the default set, so the silence is shown, not claimed.
    print(f"  novelty_density  fired={a.signals[DetectorKind.NOVELTY_DENSITY].fired}  <- input-based OOD detector")
    print(f"  gp_variance      fired={a.signals[DetectorKind.GP_VARIANCE].fired}  <- input-based OOD detector")
    print(f"  rationale        {a.rationale}")

    ood = sum(1 for x in results
              if x.signals[DetectorKind.NOVELTY_DENSITY].fired or x.signals[DetectorKind.GP_VARIANCE].fired)
    print(f"  input-based OOD detectors fired on {ood} of {len(results)} entrance points")
    assert ood == 0, "an input-based OOD detector fired -- the demo's claim no longer holds"
    assert all(x.verdict is Verdict.REJECT for x in results)
    assert all(x.observability is Observability.UNOBSERVABLE for x in results)
    print()
    score_the_correlation(train, test, results)


def score_the_correlation(train, test, results) -> None:
    """Where the correlation behind the prediction actually fails, against the measurement.
    Wrong means the benchmark's own NACA threshold -- the naca_tn1451 vehicle's lift
    threshold -- so nothing here is chosen for this example."""
    from scipy.stats import fisher_exact

    from physmap.benchmarks.benchmark_v0_4 import bench_spec_from_config
    from physmap.closures.registry import get_closure
    from physmap.substrate.vehicle_config import load_named_vehicle

    threshold = bench_spec_from_config(load_named_vehicle("naca_tn1451")).calib.lift_threshold_pct
    gn = get_closure("gnielinski-1976")

    def err(r):
        pred = float(gn.fn(Re=np.array([r["Re"]]), Pr=np.array([r["Pr"]]))[0])
        return abs(pred - r["Nu_meas"]) / r["Nu_meas"] * 100.0

    home = [err(r) for r in train]
    entrance = [err(r) for r in test]
    home_wrong = sum(e > threshold for e in home)
    wrong = [(r, e) for r, e in zip(test, entrance) if e > threshold]
    flagged_right = sum(1 for a, e in zip(results, entrance)
                        if a.signals[DetectorKind.CLOSURE_VALIDITY].fired and e <= threshold)
    _, p = fisher_exact([[len(wrong), len(test) - len(wrong)],
                         [home_wrong, len(train) - home_wrong]], alternative="greater")
    worst_r, worst = max(zip(test, entrance), key=lambda t: t[1])
    print(f"where gnielinski-1976 actually fails (wrong = off the measurement by more than "
          f"{threshold:.1f}%, the benchmark's NACA threshold):")
    print(f"  fully developed (home): {home_wrong} of {len(train)} wrong")
    print(f"  entrance:               {len(wrong)} of {len(test)} wrong, all at x/D <= "
          f"{max(r['x_over_D'] for r, _ in wrong):g}; worst {worst:.0f}% at x/D "
          f"{worst_r['x_over_D']:g}")
    print(f"  entrance worse than home: one-sided Fisher exact p = {p:.1g}")
    print(f"  the closure check flagged all {len(test)} entrance points; the correlation is "
          f"within the threshold on {flagged_right} of them")
    assert home_wrong == 0, "the correlation is wrong at home -- the demo's baseline no longer holds"


if __name__ == "__main__":
    main()
