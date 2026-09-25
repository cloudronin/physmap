# NAFEMS Multiphysics 2026 — talk package

Everything needed to give the talk, built from committed evidence and checked against it.
The runbook for the live part — the demo, the order of commands, the pre-talk checklist — stays
in [`../talk-runbook.md`](../talk-runbook.md).

## What is here

| File | What it is | How it is made |
|---|---|---|
| [`narrative.md`](narrative.md) | The talk as a story, in five parts | Written; numbers checked |
| [`slide-sequence.md`](slide-sequence.md) | The main slides in order, then the backup inventory | Written; numbers checked |
| [`speaker-notes.md`](speaker-notes.md) | Plain-English notes for every technical figure | Written; numbers checked |
| [`claims-ledger.md`](claims-ledger.md) | Every headline sentence: wording, command, evidence, limits, and where it may be used | Written; numbers checked |
| [`hostile-questions.md`](hostile-questions.md) | Short answers to the hard questions, fact kept apart from interpretation | Written; numbers checked |
| [`historical-reconciliation.md`](historical-reconciliation.md) | Why the abstract's precision, recall and F1 are not presented as validation | Written; numbers checked |
| [`facts-sheet.md`](facts-sheet.md) | Every number the talk uses, with its source | **Generated** |
| [`numbers.json`](numbers.json) | The registry: each displayed number, its exact display string, its source file | **Generated** |
| [`figures/`](figures/README.md) | Eight figures as SVG (editable) and 1920-pixel PNG, each with a data table and a caption naming its source | **Generated** |
| [`reproduction/`](reproduction/README.md) | `physmap stress-test lewis-reuse` from a clean public clone: command, commit, environment, output, exit status | Captured |

## Rebuild and check

```bash
pip install -e ".[experiment]"          # matplotlib, for the figures
python tools/talk_package.py build      # figures, data tables, captions, facts sheet, registry
python tools/talk_package.py check      # no matplotlib needed
```

`check` passes only if all of these hold:

- every registered number, figure table, caption and the facts sheet still match the committed
  records;
- every figure still shows the numbers it is registered as showing;
- every Lewis number matches what `physmap stress-test lewis-reuse` printed in the clean clone,
  line by line, and the clean clone's record matches the committed bank;
- the benchmark figure matches `physmap benchmark report`, and the x/D figure matches
  `examples/naca_entrance_region.py`;
- every decimal, and every whole-number percentage, in the written documents here is either a
  registered number or a historical value quoted in `protocols/known-results-declaration.md`.

The test suite runs it (`tests/test_talk_package.py`).

## The rules every document here follows

- **The benchmark is the point.** What PhysMAP adds to input-based OOD detection — the failures
  it catches that the detectors cannot see, per dataset, with its false alarms beside them — is
  the headline and what sets PhysMAP apart. Its figure is `bench_3_what_physmap_adds`.
- **Two results, kept apart.** The seven-vehicle benchmark and the x/D example are about
  closure validity and observability. Lewis is about causal materiality — a separate question.
  Neither is evidence for the other.
- **Counts per dataset, never pooled.** No rate across datasets, and never the catches without
  the false alarms.
- **Lewis is one run.** Its stations are positions in that run, not cases. No precision, recall
  or F1 anywhere.
- **θ is unlocked.** Materiality is shown as continuous values. θ = 0.10 appears only as an
  illustration, labelled as one.
- **Input-based OOD detector** is the talk's name for detectors that judge a prediction by its
  inputs alone. The claim sentence quotes the command's own wording, "input-only".
- **Not claimed:** that OOD detectors fail in general; that gravity should be left out; anything
  about NVIDIA PhysicsNeMo; any experimental performance rate; any fixed θ.
- **The abstract's numbers are addressed, not replaced.** See
  [`historical-reconciliation.md`](historical-reconciliation.md).
