"""The pipe-entrance case, end to end.

A surrogate is trained on (Re, Pr) over the fully-developed region of a heated
pipe, then asked about the entrance region. It has never seen x/D -- the
variable that actually governs the entrance -- so it cannot represent what
changed. Neither can an input-space novelty detector: it sees the same two
columns the surrogate does, and in those two columns the new points look
perfectly ordinary.

PhysMAP reads the bound variable from the test coordinates instead, checks it
against the closure's validated range, and knows at fit time that x/D is
structurally invisible to this surrogate. The result is a refusal with a reason,
not a confident wrong number.

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
    print(f"  gp_variance      fired={a.signals[DetectorKind.GP_VARIANCE].fired}  <- the statistical baseline sees nothing")
    print(f"  rationale        {a.rationale}")

    assert all(x.verdict is Verdict.REJECT for x in results)
    assert all(x.observability is Observability.UNOBSERVABLE for x in results)


if __name__ == "__main__":
    main()
