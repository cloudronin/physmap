# `physmap.corpus` — calibration + evidence

Two corpora, queried independently, joined at `closure_id`. They live in
separate JSONL files under `physmap/results/{calibration_corpus,evidence_corpus}/`;
this package is the loader + validator for each.

The split is load-bearing: the calibration table feeds **decision** signals
(the validity detector reads its numerical bounds); the evidence corpus feeds
**justification** signals (the EvidenceEnrichmentStage attaches its claim
provenance). They have different correctness standards — a wrong bound is a
false alarm (tolerable signal error), a wrong citation is false provenance
(reputationally serious). So they're held to different bars.

> **A corpus entry fires in production — a wrong bound is worse than a missing
> one.** Any change to either corpus goes through PR review against the
> [Corpus PR Review Guide](PR_Review_Guide.md) before it is
> merged into the live corpus. See [PR review](#pr-review) below.

## Modules

| Module | Role |
|---|---|
| [`calibration.py`](calibration.py) | Calibration-table loader + validator + CLI. `ClosureEntry`/`CoordinateBound` dataclasses; 7 QC gates; `load_corpus()`, `is_in_calibration()`, `get_validated_range()`. The validity detector reads `corpus.jsonl` directly (faster than going through the loader), but this module owns the schema. |
| [`evidence.py`](evidence.py) | Claim-centric evidence corpus + validator + CLI. `Source`/`Claim`/`Bound`/`MeasuredDivergence`/`Conditions` dataclasses; 12 QC gates (gate 9 disallows calibration-provenance laundering; gate 10 requires the visual-estimate uncertainty triple; gate 11 anchors every MeasuredDivergence). `claim_to_v06_jsonld()` projects a claim into v0.6 vocab terms. |

## The two JSONL files

Both live under `physmap/results/` (entry counts are current-as-of, not fixed —
the corpus grows as bounds are mined and promoted):

```
results/calibration_corpus/
  corpus.jsonl                                  closure calibration entries (36 as of last update)
  SCHEMA.md                                     schema documentation
  calibration_bound_confirmation_worksheet.csv  the worksheet that fed the corpus

results/evidence_corpus/
  sources.jsonl                                 sources (populated + stubbed)
  claims.jsonl                                  atomic claims across closures
  README.md                                     evidence-corpus README
```

## How to use — calibration

```python
from physmap.corpus.calibration import load_corpus, index_by_id, is_in_calibration

idx = index_by_id(load_corpus())
ok = is_in_calibration(idx, "gnielinski-1976", "reynolds_number", 10_000.0)
# -> True

# CLI: validate the committed corpus
# python -m physmap.corpus.calibration validate
```

## How to use — evidence

```python
from physmap.corpus.evidence import load_claims, load_sources
from physmap.pipeline.evidence_stage import make_evidence_enrichment_stage

# Direct API
claims = load_claims()       # list[Claim]
sources = load_sources()     # list[Source]

# Or the JustificationStage factory (loads + indexes for you)
stage = make_evidence_enrichment_stage("gnielinski-1976")
# -> ready to plug into Pipeline.justification_stages

# CLI: validate the committed evidence corpus
# python -m physmap.corpus.evidence validate
# CLI: export a claim to v0.6 JSON-LD
# python -m physmap.corpus.evidence export-v06 --claim-id gnielinski-1976-originate-re
```

## Why two corpora not one

The spec (Part 3) lays this out: graph **deferred** from the signal path
(two flat tables; the calibration table is what the validity detector
queries). The Phase-2 v0.6 graph in `pipeline.assessment_v06` is the
OUTPUT structure, not the detection substrate — a different thing.

So:
* **Calibration table** = queryable numerical bounds. Job: detection.
  Quality metric: signal behavior. (Tolerable false alarms.)
* **Evidence table** = papers, divergences, conditions, corrections,
  citations. Job: auditable justification. Quality metric: "would a
  reviewer accept this provenance." Higher correctness bar.

## Cross-check

The substrate engine + validity detector enforce the join by reading
`closure_id` from a vehicle's `matched_closure_id` and looking up both
the calibration bound (for the detector's L2 distance) and the evidence
claim (for the justification payload). Mismatched IDs surface as silent
gaps in `EvidenceEnrichmentStage.enrich()` output (`claim_count: 0`).

## PR review

Every change to either corpus (new closure, new bound, new evidence claim)
goes through PR review **before** it is merged into the live corpus. The full
checklist — for both the human reviewer and the agent preparing the PR — is in
the **[Corpus PR Review Guide](PR_Review_Guide.md)**.

The two checks that matter most are the ones the validators **cannot** do, and
both correspond to error classes already encountered:

1. **Numbers match the primary, in context.** Read the cited primary source and
   confirm each value IS the value in the paper and means what the entry claims.
   The validator checks schema and gates; it cannot check the entry against the
   source.
2. **Right physical quantity (same-name-different-physics).** Confirm each bound's
   variable is the actual physical group the corpus uses, not a same-named
   different group. Numerically-faithful-but-physically-wrong is invisible to the
   validator.

### The two named traps (they recur; the guide details both)

- **Misattribution** — a real, correct bound banked against the **wrong closure**
  (e.g. a μ/μ_s range attached to the turbulent correlation when it belonged to
  the laminar combined-entry one). Verify the JOIN by reading the source, not the
  candidate description.
- **Same-name-different-physics** — a bound keyed to a **different physical group
  of the same name** (e.g. a gradient-Richardson stability criterion vs the
  corpus's flow Gr/Re² `richardson_number`). Numerically faithful, physically
  wrong, validator-invisible. Confirm WHICH exact quantity (watch Richardson,
  Mach, Pohlhausen, Nusselt variants — any group with multiple definitions).

Both are caught only by reading the primary and applying physics judgment, which
is why human review (and an agent that reads the actual source, not the candidate
description) is the gate — not the validator. The validators are necessary but
not sufficient: they enforce schema and the gate rules, but the two error classes
above pass every automated check.

### Promotion discipline (carried by the guide)

- Single-source bounds are `status: claimed`; `confirmed` requires primary-source
  verification and is **human-promoted** at merge, never set by the agent.
- Provenance authority is the **primary** source; handbooks/textbooks are the
  **discovery path**, recorded but never laundered as the authority.
- Persisted fields carry **paraphrased facts + citation pointers**, never verbatim
  copyrighted sentences (the verbatim scan enforces this; eyeball it anyway).
- Corpus diffs are **additive** — existing entries untouched; the post-merge state
  re-validates clean and the `regime_observability.py` projection regenerates
  (drift test passes).
- A new closure is **inert until mapped** (regime/facet-tags + observability
  override are deferred human physics judgments); the PR surfaces those TODOs so
  "banked but never fires" is never a silent state.