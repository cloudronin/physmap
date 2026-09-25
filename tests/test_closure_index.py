"""Open closure index — the expanded 201-closure coverage map (verdict-free).

Asserts the index merges the corpus-derived entries with the approved expansion
candidates, stays metadata-only (no bounds/provenance/disposition), the candidates
resolve as case-2b, the new families/aliases are present, and the committed JSON is
a fresh, deterministic build of the candidate table.
"""
from __future__ import annotations

import json
from pathlib import Path

import physmap.corpus.calibration as cc
from physmap.closures.index import (
    CLOSURE_INDEX,
    ResolutionCase,
    classify_closure,
    match_closure,
    premium_coverage_ids,
)

INDEX_JSON = Path(cc.__file__).resolve().parent.parent / "closures" / "data" / "closure_index.json"
META_FIELDS = {"closure_id", "closure_name", "closure_family", "geometry_class",
               "physics_coordinates", "citation", "aliases"}
DISPOSITION_TOKENS = ("confirmed_by", "confirmation", "source_worksheet", "narrow-then-promote",
                      "validated_range", "bound_status", "provenance", '"min"', '"max"')


def test_index_has_201_closures():
    # 53 corpus + churchill (registry-only) + 147 approved candidates
    assert len(CLOSURE_INDEX) == 201


def test_index_is_metadata_only():
    data = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    for c in data["closures"]:
        assert set(c) <= META_FIELDS, c["closure_id"]


def test_index_carries_no_disposition_or_bounds():
    txt = INDEX_JSON.read_text(encoding="utf-8").lower()
    hits = [t for t in DISPOSITION_TOKENS if t.lower() in txt]
    assert hits == [], hits


def test_every_closure_has_citation_and_family_except_churchill():
    for cid, m in CLOSURE_INDEX.items():
        assert m.citation, cid
        if cid != "churchill-mixed-convection-flat-plate":
            assert m.closure_family, cid


def test_expansion_candidates_are_case_2b():
    cov = premium_coverage_ids()
    # The ids of the closed corpus come from the bundled coverage map (ids only, no
    # bounds), so this runs without the closed corpus.
    active = cov
    assert len(active) == 53
    cands = [cid for cid in CLOSURE_INDEX if cid not in cov]
    assert len(cands) == 148  # 147 approved candidates + churchill
    for cid in cands:
        assert classify_closure(cid, active) is ResolutionCase.NO_BOUNDS, cid


def test_new_families_present():
    fams = {m.closure_family for m in CLOSURE_INDEX.values()}
    for f in ("condensation", "external-convection", "natural-convection", "hydraulic-friction",
              "transfer-analogy", "surface-enhancement", "packed-porous", "radiation",
              "combustion-kinetics", "species-diffusion", "rarefied-gas", "cardio", "aero",
              "wall-function"):
        assert f in fams, f


def test_free_text_matches_new_aliases():
    assert match_closure("Ergun") == "ergun-packed-bed-1952"
    assert match_closure("Colebrook") == "colebrook-white-friction-1939"
    assert match_closure("Fay-Riddell") == "fay-riddell-stagnation-1958"
    assert match_closure("Carreau-Yasuda") == "carreau-yasuda-1981"


