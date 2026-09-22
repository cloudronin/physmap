"""Cross-cutting infrastructure shared across the architecture refactor and
the broader physmap system. Grouped under one subpackage during R7 of
the cleanup.

Modules:
  corpus_runtime    — Entry + corpus_error_magnitude (used by
                       pipeline.detectors.CorpusDetector)
  gate_runner       — generic gate-running orchestration
  gates             — gate definitions
  ledger            — append-only run ledger (12 consumers — load-bearing)
  metrics           — generic metrics helpers
  physics_causal    — physics-side causal/non-causal split
  physics_synth     — physics synthesis
  schema            — shared schema definitions
  stage1_adapter    — Stage-1 adapter
  stage1_harness    — Stage-1 harness

These modules are kept INSIDE the package (not archived) because they
have widely-distributed consumers. The infra subpackage isolates them
from the architecture refactor's canonical surface so a reader can tell
"new architecture" (pipeline / substrate / corpus / closures) from
"shared old infrastructure" (this subpackage) at a glance.
"""
