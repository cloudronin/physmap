"""Bundled open-tier corpus data (package resources).

Holds the sanitized SEED corpus (`corpus_seed.jsonl`) and the premium COVERAGE
map (`premium_coverage.json`, closure_ids only — no bounds). Both are generated
by `dev/tools/split_corpus.py` and shipped in the core wheel as package data;
the loader resolves them via `importlib.resources` when neither an explicit
`$PHYSMAP_CORPUS` override nor a premium corpus is present.

This package carries NO moat content: the seed is firewalled (every bound
collapsed to status "seed", all confirmation/disposition stripped) and the
coverage map is ids-only.
"""
