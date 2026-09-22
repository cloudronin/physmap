# `physmap.pipeline` — D3 detection + adjudication

The architecture refactor's pipeline side: a substrate's rows flow through a
**linear sequence of stages**, two roles of signal (decision vs justification),
one aggregator, one per-point `Assessment` (Phase 1) or v0.6-conformant
subgraph (Phase 2).

```
rows -> Detectors (decision) -> Aggregator -> Verdict
                              \
                               -> JustificationStages -> evidence dict
                                                       \
                                                        -> Assessment
                                                          /
       Phase-2: Assessment -> v0.6 subgraph -> DefeasibleAdjudicator
                                            -> Disposition (controlled vocab)
                                            -> (SHACL-conformant)
```

## Modules

| Module | Role |
|---|---|
| [`core.py`](core.py) | The Pipeline class + protocols (`Detector`, `JustificationStage`, `Aggregator`) + `DetectorResult` / `Verdict` / `Assessment` dataclasses + `DetectorAdapter` wrapper + five `make_*_adapter()` factories. |
| [`detectors.py`](detectors.py) | Inner detector classes (`DistanceDetector`, `GPVarianceDetector`, `EnsembleVarianceDetector`, `CorpusDetector`). Locked parameters: Mahalanobis k=3, Matérn-5/2 neutral-mean GP, polynomial-bootstrap ensemble. |
| [`validity_signal.py`](validity_signal.py) | `ValidityRangeDistanceDetector` — **the differentiator**. Reads the corpus's per-coord validated range and fires on L2-distance > 0. No training-data dependence. |
| [`surrogate.py`](surrogate.py) | `Surrogate` (GP with neutral mean, Matérn-5/2) + `ThresholdCalibration` + `SurrogateError`. Used by the gates. |
| [`aggregators.py`](aggregators.py) | Phase-1 aggregators: `AnyFired` (the locked ensemble metric), `CorpusGated` (corpus catches what baselines miss), `WeightedVote`. |
| [`defeasible_aggregator.py`](defeasible_aggregator.py) | Phase-2 `DefeasibleAdjudicator` + offset rules + `AdjudicationResult`. Maps surviving weakeners to one of the 5 v0.6 `actionClass` strings (`accept-residual-risk`, `restrict-cou`, `characterize-region`, `acquire-validation`, `change-cou`). |
| [`assessment_v06.py`](assessment_v06.py) | Phase-1 `Assessment` -> v0.6 subgraph mapper. Five typed nodes (`DiscrepancyNode`, `CredibilityFactorNode`, `WeakenerAnnotationNode`, `OffsetRationaleNode`, `DispositionNode`) + JSON-LD serializer. Controlled-vocab dataclasses fail closed on off-vocab strings. |
| [`evidence_stage.py`](evidence_stage.py) | `EvidenceEnrichmentStage` — JustificationStage that attaches per-closure claim provenance from `corpus.evidence` when a gating signal fires. |
| [`phase1_gate.py`](phase1_gate.py) | CLI: runs NACA through the Phase-1 architecture (engine + DetectorAdapters + AnyFired) and reports detection lift + explanation correctness. |
| [`phase2_gate.py`](phase2_gate.py) | CLI: runs the full Phase-1+2 pipeline, emits v0.6 JSON-LD per point, adjudicates dispositions, optionally runs pyshacl validation against uofa's disposition pack. |

## Two ROLES of signal

* **Decision** — the aggregator weighs these to produce the verdict.
  Includes the four locked detectors (distance, GP variance, ensemble
  variance, corpus error magnitude) and the validity detector.
* **Justification** — rides along to explain/audit; NEVER weighed for
  the verdict. Evidence provenance, sources, corrections.

The aggregator consumes ONLY decision signals; the justification stages
attach to the `Assessment` for downstream audit. This is the load-bearing
discipline that the spec calls out (Part 2): detection and explanation
flow through one pipeline but are cleanly separated.

## How to use — Phase 1

```python
from physmap.pipeline import (
    Pipeline, AnyFired, make_distance_adapter, make_gp_variance_adapter,
    make_closure_validity_adapter,
)

# adapters wrap the locked detectors; thresholds calibrated against training
distance = make_distance_adapter(train_X, threshold=tau_distance)
gp_var   = make_gp_variance_adapter(train_X, train_y, threshold=tau_gp)
validity = make_closure_validity_adapter(
    closure_id="gnielinski-1976",
    feature_names=("log10_Re", "Pr", "x_over_D"),
)

# Pipeline orchestrates: run detectors on test rows, aggregate, emit Assessments
pipe = Pipeline(
    feature_extractor=...,
    decision_stages=[distance, gp_var, validity],
    aggregator=AnyFired(),
)
assessments = pipe.run(test_rows)   # list[Assessment]; one per row
```

Or just run the gate:
```bash
python -m physmap.pipeline.phase1_gate cross_validated_fig10
# -> banks results/physmap_d3_phase1_gate/cross_validated_fig10.json
```

## How to use — Phase 2 (v0.6 + defeasible)

```python
from physmap.pipeline import DefeasibleAdjudicator
from physmap.pipeline.assessment_v06 import assessment_to_v06_subgraph

adj = DefeasibleAdjudicator()  # defaults; offset rules disabled

for a in assessments:           # from Phase-1 above
    sub = assessment_to_v06_subgraph(
        a,
        surrogate_prediction=row.surrogate_prediction,
        solver_truth=row.cfd_truth,
        adjudicator=adj,
    )
    jsonld = sub.to_jsonld()    # SHACL-conformant v0.6 doc
```

Or just run the gate:
```bash
python -m physmap.pipeline.phase2_gate cross_validated_fig10 --shacl-validate
# -> banks results/physmap_d3_phase2_gate/cross_validated_fig10.json
# -> v0.6 JSON-LD bundle + Disposition counts + SHACL conformance
```

## The defeasible adjudicator's action-class table

| Surviving weakeners | Disposition |
|---|---|
| None | `accept-residual-risk` + rationale |
| Literature alone (`OutOfValidatedRange`) | `characterize-region` (the NACA misaligned-bound case) |
| Novelty alone (distance / GP variance) | `acquire-validation` |
| Novelty + literature | `restrict-cou` |
| Corpus-error alone | `accept-residual-risk` + rationale |
| Complex / multi-pattern fallback | `change-cou` |

Plus pluggable `OffsetRule` callables (e.g. `AGREEMENT_NON_DISPOSITIVE`)
that emit `OffsetRationale` nodes against specific factors.

## Tests pinning the pipeline

* `tests/test_d3_pipeline.py` — adapter wrap fidelity, Pipeline role
  discipline, aggregator logic, integration on a toy training set.
* `tests/test_assessment_v06.py` — 16 tests covering mapping correctness,
  controlled-vocab fail-closed, SHACL conformance against uofa's
  disposition pack, end-to-end on the Phase-1 gate output.
* `tests/test_defeasible_aggregator.py` — 16 tests covering each of the
  6 action-class branches, the accept-residual-risk-requires-justification
  guard, and the agreement-non-dispositive offset rule.
* `tests/test_phase1_gate.py` — `PARETO_LIFT_misaligned` reproduced on all
  4 banked NACA CSVs + structural invariant (validity fires on every
  entrance row) + v0.6-mapping seed contract.
* `tests/test_phase2_gate.py` — SHACL passes on all 4 NACA gate outputs +
  disposition mix matches the NACA finding (~80% characterize-region,
  ~20% restrict-cou).
