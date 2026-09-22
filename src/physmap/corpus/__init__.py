"""Corpus side of the architecture refactor — calibration table + claim-centric
evidence corpus.

Module renames during R5 (dropping the redundant _corpus suffix):
  calibration_corpus.py  ->  calibration.py
  evidence_corpus.py     ->  evidence.py

The two corpora live in separate JSONL files under
`physmap/results/calibration_corpus/` and `physmap/results/evidence_corpus/`;
they are JOINED at closure_id in downstream consumers (the validity
detector + the EvidenceEnrichmentStage).
"""
