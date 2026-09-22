"""PhysMAP Evidence Corpus — schema, validators, loader, query CLI.

The justification-side companion to the calibration corpus. Calibration → decision
signals (does a bound fire). Evidence → justification signals (which source, what
measured divergence, what conditions — the auditable "why").

Claim-centric, three flat tables, atomic provenance:
  sources.jsonl   one row per paper/handbook/data sheet
  claims.jsonl    one row per (source asserts something about a closure's validity)
  (closures)      joined from calibration_corpus.corpus.jsonl via closure_id

A `claims` row IS a v0.6 `CredibilityFactor` (claim_type→factorType, status→
factorStatus, source's standard→factorStandard) with PROV-DM `wasDerivedFrom` to
the Source. Same vocabulary as the assessment; the corpus is a reusable library
of factors-about-closures-in-general.

Spec: PhysMAP_Evidence_Corpus_Build_Spec_v0_1.md
Storage: two JSONL files, line-diffable.
Mirror of `calibration_corpus.py`'s structural patterns (dataclasses, validators
named gates, CLI subcommands).

Provenance discipline (gate 9): a measured_divergence row MUST cite the primary
source directly. Lifting a value from a calibration-corpus provenance note is
provenance laundering and is disallowed. The valid extraction_method values are
'primary-source' and 'visual-estimate-rendered-pdf' only.

Visual-estimate divergence rows (gate 10) MUST also populate
magnitude_uncertainty_pct, n_points, and resolvability_ratio so the coarser tier
is self-documenting downstream.

Torch-free; depends only on the standard library and the calibration corpus
module (for the closure_id join validator).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Lazy import inside the join validator to avoid hard coupling at module load.

# ── controlled vocabularies ───────────────────────────────────────────────────

SOURCE_TYPES = {
    "originating-paper",
    "validation-study",
    "correction-paper",
    "handbook",
}

SOURCE_STATUSES = {"populated", "stub"}

CLAIM_TYPES = {
    "originating-bound",
    "validated-bound",
    "correction",
    "consensus-bound",
}

ROLES = {"originate", "validate", "correct", "synthesize"}

# Aligned with calibration_corpus.BOUND_STATUSES plus spec's "contested".
CLAIM_STATUSES = {
    "confirmed",
    "confirmed-contested",
    "claimed",
    "extrapolated",
    "contested",
}

MEASURES = {"MAE", "median_gap", "resolvability_ratio", "mean_relative_pct"}

# Provenance discipline: there is NO 'calibration-provenance-lift' path.
# A divergence row must trace to its primary source or to a visual digitization
# of the rendered PDF. Anything else is laundered and fails gate 9.
EXTRACTION_METHODS = {"primary-source", "visual-estimate-rendered-pdf"}

# v0.6 vocab projection (claim_type → CredibilityFactor.factorType).
_V06_FACTOR_TYPE_BY_CLAIM_TYPE = {
    "originating-bound": "OriginatingBound",
    "validated-bound": "ValidatedBound",
    "correction": "Correction",
    "consensus-bound": "ConsensusBound",
}

# ── open-core evidence resolution (env -> premium -> bundled seed) ────────────
#
# The evidence corpus carries the SAME firewall as the calibration corpus. The
# published files are the seed: a claim ships only if its closure is one of the
# 15 seed closures, and a source ships only if a surviving claim cites it. The
# firewall is an allowlist; see dev/tools/split_evidence_corpus.py, which derives
# these files deterministically and has a --check mode that fails on drift.
#
# Resolution order mirrors resolve_corpus_path() in calibration.py so both halves
# of the corpus move together:
#   1. $PHYSMAP_EVIDENCE_DIR      -- explicit override
#   2. the optional physmap_corpus_premium package
#   3. the bundled seed           -- always present
import importlib.resources as _ir_e
import importlib.util as _iu_e
import os as _os_e

PHYSMAP_EVIDENCE_ENV = "PHYSMAP_EVIDENCE_DIR"
_EVIDENCE_SEED_PACKAGE = "physmap.corpus.data"
_PREMIUM_PACKAGE_E = "physmap_corpus_premium"


def _evidence_path(premium_name: str, seed_name: str) -> Path:
    env = _os_e.environ.get(PHYSMAP_EVIDENCE_ENV)
    if env:
        return Path(env).expanduser() / premium_name
    if _iu_e.find_spec(_PREMIUM_PACKAGE_E) is not None:
        try:
            p = Path(str(_ir_e.files(_PREMIUM_PACKAGE_E) / premium_name))
            if p.is_file():
                return p
        except (FileNotFoundError, ModuleNotFoundError, NotADirectoryError):
            pass
    return Path(str(_ir_e.files(_EVIDENCE_SEED_PACKAGE) / seed_name))


DEFAULT_SOURCES_PATH = _evidence_path("sources.jsonl", "evidence_sources_seed.jsonl")
DEFAULT_CLAIMS_PATH = _evidence_path("claims.jsonl", "evidence_claims_seed.jsonl")

# The premium calibration corpus. Absent from this repository by design; see the
# note above DEFAULT_PATH in calibration.py.
from physmap.corpus.calibration import DEFAULT_PATH as DEFAULT_CALIBRATION_PATH  # noqa: E402


# ── schema dataclasses ────────────────────────────────────────────────────────


@dataclass
class Source:
    """One paper / handbook / data sheet."""

    source_id: str  # immutable kebab-case slug, e.g. "forrest-2014"
    citation: str  # full citation
    doi: str | None  # null when no DOI
    year: int
    source_type: str  # ∈ SOURCE_TYPES
    source_status: str  # ∈ SOURCE_STATUSES — populated vs stub (no claims against stubs)
    notes: str  # e.g. "tested 5 closures simultaneously"


@dataclass
class Range:
    """Numeric range used for re_range / pr_range in Conditions."""

    min: float | None
    max: float | None


@dataclass
class Bound:
    """The claim's asserted boundary on one physics coordinate."""

    variable: str  # "reynolds_number" | "prandtl_number" | "x_over_D" | ...
    valid_above: float | None
    valid_below: float | None
    condition: str  # human-readable condition string


@dataclass
class MeasuredDivergence:
    """Quantitative gap between closure prediction and measurement.

    Required when the parent claim's role == 'validate' (gate 4). Forbidden
    otherwise. extraction_method discipline is enforced by gates 9, 10, 11.
    """

    magnitude_pct: float  # signed; e.g. +82 (over-prediction) or -3.5
    region: str  # e.g. "sub-critical laminar (Re~3900, Pr=5.4)"
    measure: str  # ∈ MEASURES
    extraction_method: str  # ∈ EXTRACTION_METHODS
    page_or_table: str  # gate 11 — anchor to a specific table/figure/page
    magnitude_uncertainty_pct: float | None = None  # required when visual-estimate
    n_points: int | None = None  # required when visual-estimate
    resolvability_ratio: float | None = None  # required when visual-estimate


@dataclass
class Conditions:
    """The (Re, Pr, geometry, fluid) under which the claim's bound applies."""

    re_range: Range
    pr_range: Range
    geometry_class: str  # "circular-pipe" | "narrow-rect-channel-one-sided" | ...
    fluid: str  # "air" | "water" | "R12" | ...


@dataclass
class Claim:
    """One atomic (source, closure, bound) assertion."""

    claim_id: str  # e.g. "gnielinski-1976-originate-re"
    closure_id: str  # → calibration_corpus
    source_id: str  # → sources.jsonl (atomic provenance; exactly one)
    claim_type: str  # ∈ CLAIM_TYPES
    role: str  # ∈ ROLES
    bound: Bound
    measured_divergence: MeasuredDivergence | None
    conditions: Conditions
    status: str  # ∈ CLAIM_STATUSES
    supersedes_claim_id: str | None  # wasRevisionOf edge
    contradicts_claim_id: str | None  # sources-disagree edge
    notes: str = ""  # free-form context


# ── (de)serialization ─────────────────────────────────────────────────────────


def _range_from_dict(d: dict) -> Range:
    return Range(min=d.get("min"), max=d.get("max"))


def source_from_dict(d: dict) -> Source:
    return Source(**d)


def claim_from_dict(d: dict) -> Claim:
    """Build a Claim from a JSON-loaded dict (handles nested dataclasses)."""
    bound = Bound(**d["bound"])

    md_raw = d.get("measured_divergence")
    md = MeasuredDivergence(**md_raw) if md_raw is not None else None

    cond_raw = d["conditions"]
    conditions = Conditions(
        re_range=_range_from_dict(cond_raw["re_range"]),
        pr_range=_range_from_dict(cond_raw["pr_range"]),
        geometry_class=cond_raw["geometry_class"],
        fluid=cond_raw["fluid"],
    )

    payload = {**d, "bound": bound, "measured_divergence": md, "conditions": conditions}
    return Claim(**payload)


def source_to_dict(s: Source) -> dict:
    return asdict(s)


def claim_to_dict(c: Claim) -> dict:
    return asdict(c)


# ── per-claim validators (gates 1, 4-12) ──────────────────────────────────────


def validate_claim(
    claim: Claim,
    source_index: dict[str, Source],
    calibration_closure_ids: set[str],
    claim_ids_in_corpus: set[str],
) -> list[str]:
    """Return human-readable errors for one claim; empty list = valid.

    The corpus-wide gates (2, 3, 7, claim_id uniqueness) need the surrounding
    indexes; this function accepts them as arguments rather than reaching out
    to the filesystem itself.
    """
    errs: list[str] = []
    cid = claim.claim_id or "<no claim_id>"

    # Gate 1 — atomic provenance: exactly one source_id (non-empty string).
    if not claim.source_id or not isinstance(claim.source_id, str):
        errs.append(f"{cid}: source_id missing (gate 1 — atomic provenance)")

    # Gate 2 — source_id resolves in sources.jsonl AND is not a stub.
    if claim.source_id and claim.source_id not in source_index:
        errs.append(
            f"{cid}: source_id '{claim.source_id}' not found in sources.jsonl "
            f"(gate 2)"
        )
    elif claim.source_id:
        src = source_index[claim.source_id]
        if src.source_status == "stub":
            errs.append(
                f"{cid}: source_id '{claim.source_id}' is a stub "
                f"(no claims allowed against stub sources — gate 2)"
            )

    # Gate 3 — closure_id resolves in calibration corpus (join validator).
    if claim.closure_id not in calibration_closure_ids:
        errs.append(
            f"{cid}: closure_id '{claim.closure_id}' not found in calibration "
            f"corpus (gate 3 — join validator)"
        )

    # Gate 4 — measured_divergence populated iff role == 'validate'.
    if claim.role == "validate" and claim.measured_divergence is None:
        errs.append(
            f"{cid}: role='validate' but measured_divergence is null "
            f"(gate 4 — validate claims must carry measured divergence)"
        )
    if claim.role != "validate" and claim.measured_divergence is not None:
        errs.append(
            f"{cid}: role='{claim.role}' but measured_divergence is populated "
            f"(gate 4 — non-validate claims must NOT carry measured divergence)"
        )

    # Gate 5 — role ∈ ROLES.
    if claim.role not in ROLES:
        errs.append(
            f"{cid}: role '{claim.role}' not in {sorted(ROLES)} (gate 5)"
        )

    # Gate 6 — claim_type ∈ CLAIM_TYPES.
    if claim.claim_type not in CLAIM_TYPES:
        errs.append(
            f"{cid}: claim_type '{claim.claim_type}' not in {sorted(CLAIM_TYPES)} "
            f"(gate 6)"
        )

    # Gate 7 — supersedes/contradicts resolve in own claims table.
    for fk_name, fk_value in (
        ("supersedes_claim_id", claim.supersedes_claim_id),
        ("contradicts_claim_id", claim.contradicts_claim_id),
    ):
        if fk_value is not None and fk_value not in claim_ids_in_corpus:
            errs.append(
                f"{cid}: {fk_name} '{fk_value}' does not resolve in claims.jsonl "
                f"(gate 7)"
            )

    # Gate 8 — status ∈ CLAIM_STATUSES.
    if claim.status not in CLAIM_STATUSES:
        errs.append(
            f"{cid}: status '{claim.status}' not in {sorted(CLAIM_STATUSES)} "
            f"(gate 8)"
        )

    # Gates 9, 10, 11 — measured_divergence sub-checks.
    md = claim.measured_divergence
    if md is not None:
        # Gate 9 — no provenance-laundered divergence.
        if md.extraction_method not in EXTRACTION_METHODS:
            errs.append(
                f"{cid}: measured_divergence.extraction_method "
                f"'{md.extraction_method}' not in {sorted(EXTRACTION_METHODS)} "
                f"(gate 9 — no provenance laundering; 'calibration-provenance-lift' "
                f"is disallowed by design)"
            )

        # Gate 10 — uncertainty discipline for visual-estimate claims.
        if md.extraction_method == "visual-estimate-rendered-pdf":
            for fname, fval in (
                ("magnitude_uncertainty_pct", md.magnitude_uncertainty_pct),
                ("n_points", md.n_points),
                ("resolvability_ratio", md.resolvability_ratio),
            ):
                if fval is None:
                    errs.append(
                        f"{cid}: visual-estimate measured_divergence missing "
                        f"required field '{fname}' "
                        f"(gate 10 — coarser tier must be self-documenting)"
                    )

        # Gate 11 — page_or_table populated on every MeasuredDivergence.
        if not md.page_or_table:
            errs.append(
                f"{cid}: measured_divergence.page_or_table empty "
                f"(gate 11 — must anchor to a specific table/figure/page)"
            )

        # Shape — measure ∈ MEASURES.
        if md.measure not in MEASURES:
            errs.append(
                f"{cid}: measured_divergence.measure '{md.measure}' not in "
                f"{sorted(MEASURES)}"
            )

    return errs


def validate_source(source: Source) -> list[str]:
    """Return human-readable errors for one source row."""
    errs: list[str] = []
    sid = source.source_id or "<no source_id>"

    if not source.source_id or " " in source.source_id or source.source_id != source.source_id.lower():
        errs.append(f"{sid}: source_id must be a lowercase kebab-case slug (no spaces)")
    if not source.citation:
        errs.append(f"{sid}: citation missing")
    if source.source_type not in SOURCE_TYPES:
        errs.append(
            f"{sid}: source_type '{source.source_type}' not in {sorted(SOURCE_TYPES)}"
        )
    if source.source_status not in SOURCE_STATUSES:
        errs.append(
            f"{sid}: source_status '{source.source_status}' not in "
            f"{sorted(SOURCE_STATUSES)}"
        )
    if not isinstance(source.year, int) or source.year < 1800 or source.year > 2100:
        errs.append(f"{sid}: year {source.year!r} not a plausible integer")
    return errs


# ── corpus-wide invariants ────────────────────────────────────────────────────


def validate_corpus(
    sources: list[Source],
    claims: list[Claim],
    calibration_closure_ids: set[str],
) -> dict[str, list[str]]:
    """Per-claim/source errors keyed by id; '__corpus__' for cross-row issues.

    Implements gates 1-11 per claim, plus:
      - Gate 12 (corpus-wide): claim_id is unique across claims.jsonl.
      - Source-level shape checks via validate_source.
      - Source-id uniqueness.
    """
    out: dict[str, list[str]] = {}

    # Source shape + uniqueness.
    seen_sources: dict[str, int] = {}
    for s in sources:
        errs = validate_source(s)
        if errs:
            out[s.source_id or "<no source_id>"] = errs
        seen_sources[s.source_id] = seen_sources.get(s.source_id, 0) + 1
    dup_sources = [sid for sid, n in seen_sources.items() if n > 1]
    if dup_sources:
        out.setdefault("__corpus__", []).append(
            f"duplicate source_id values in sources.jsonl: {sorted(dup_sources)}"
        )

    source_index = {s.source_id: s for s in sources}
    claim_ids_in_corpus = {c.claim_id for c in claims}

    # Gate 12 (corpus-wide) — claim_id uniqueness.
    seen_claims: dict[str, int] = {}
    for c in claims:
        seen_claims[c.claim_id] = seen_claims.get(c.claim_id, 0) + 1
    dup_claims = [cid for cid, n in seen_claims.items() if n > 1]
    if dup_claims:
        out.setdefault("__corpus__", []).append(
            f"duplicate claim_id values in claims.jsonl (gate 12): "
            f"{sorted(dup_claims)}"
        )

    # Per-claim gates 1-11.
    for c in claims:
        errs = validate_claim(
            c, source_index, calibration_closure_ids, claim_ids_in_corpus
        )
        if errs:
            out[c.claim_id or "<no claim_id>"] = errs

    return out


# ── loader API ────────────────────────────────────────────────────────────────


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"{path.name} JSONL parse error at line {lineno}: {e}"
                ) from e
    return rows


def load_sources(path: str | Path = DEFAULT_SOURCES_PATH) -> list[Source]:
    rows = _load_jsonl(Path(path))
    out: list[Source] = []
    for i, d in enumerate(rows, start=1):
        try:
            out.append(source_from_dict(d))
        except TypeError as e:
            raise ValueError(
                f"sources.jsonl schema mismatch at row {i} "
                f"(source_id={d.get('source_id', '?')!r}): {e}"
            ) from e
    return out


def load_claims(path: str | Path = DEFAULT_CLAIMS_PATH) -> list[Claim]:
    rows = _load_jsonl(Path(path))
    out: list[Claim] = []
    for i, d in enumerate(rows, start=1):
        try:
            out.append(claim_from_dict(d))
        except (TypeError, KeyError) as e:
            raise ValueError(
                f"claims.jsonl schema mismatch at row {i} "
                f"(claim_id={d.get('claim_id', '?')!r}): {e}"
            ) from e
    return out


def load_calibration_closure_ids(
    path: str | Path = DEFAULT_CALIBRATION_PATH,
) -> set[str]:
    """Read the calibration corpus and return the set of closure_id values
    (the join domain for evidence-corpus gate 3)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"calibration corpus not found: {p}")
    ids: set[str] = set()
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            d = json.loads(stripped)
            cid = d.get("closure_id")
            if cid:
                ids.add(cid)
    return ids


# ── query helpers (the 5 spec value-test queries) ─────────────────────────────


def query_validity_story(claims: list[Claim], closure_id: str) -> list[Claim]:
    """All claims about one closure — the multi-source picture (spec query 1)."""
    return [c for c in claims if c.closure_id == closure_id]


def query_source_contributions(claims: list[Claim], source_id: str) -> list[Claim]:
    """All claims established by one source (spec query 2)."""
    return [c for c in claims if c.source_id == source_id]


def query_disagreements(claims: list[Claim]) -> list[Claim]:
    """Contested claims OR claims that explicitly contradict another (spec query 3)."""
    return [
        c
        for c in claims
        if c.status == "contested" or c.contradicts_claim_id is not None
    ]


def query_unsupported_bounds(
    claims: list[Claim],
    calibration_path: str | Path = DEFAULT_CALIBRATION_PATH,
) -> list[tuple[str, str]]:
    """Calibration bounds with no backing evidence claim (spec query 4).

    Returns (closure_id, coord) tuples for every CoordinateBound in the
    calibration corpus that has zero matching evidence claims on the same
    closure_id + bound.variable. This is the cross-corpus quality check that
    justifies the separation between calibration and evidence.
    """
    p = Path(calibration_path)
    # (closure_id, variable) tuples that DO have a backing claim.
    backed: set[tuple[str, str]] = {(c.closure_id, c.bound.variable) for c in claims}

    flagged: list[tuple[str, str]] = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            d = json.loads(stripped)
            cid = d.get("closure_id")
            for bound in d.get("validated_range", []):
                coord = bound.get("coord")
                if cid and coord and (cid, coord) not in backed:
                    flagged.append((cid, coord))
    return flagged


def query_provenance_for_assessment(
    claims: list[Claim],
    closure_id: str,
    re_value: float | None = None,
    pr_value: float | None = None,
) -> list[Claim]:
    """Claims for the closure whose Conditions envelope contains the (Re, Pr)
    point of a fired detector (spec query 5).

    A claim is included if (a) it pertains to closure_id, and (b) each provided
    operating value falls inside the claim's re_range / pr_range (open-side
    None bounds count as 'unbounded on that side')."""
    out: list[Claim] = []
    for c in claims:
        if c.closure_id != closure_id:
            continue
        if re_value is not None and not _in_range(re_value, c.conditions.re_range):
            continue
        if pr_value is not None and not _in_range(pr_value, c.conditions.pr_range):
            continue
        out.append(c)
    return out


def _in_range(value: float, r: Range) -> bool:
    if r.min is not None and value < r.min:
        return False
    if r.max is not None and value > r.max:
        return False
    return True


# ── v0.6 JSON-LD export ───────────────────────────────────────────────────────


def claim_to_v06_jsonld(claim: Claim, source: Source) -> dict:
    """Project a Claim into v0.6 vocab terms (CredibilityFactor + PROV-DM).

    Spec mapping: claim_type→factorType, status→factorStatus, source→factorStandard
    (via wasDerivedFrom). Emits a single JSON-LD-shaped dict that uses the v0.6
    context at physmap/fixtures/context/v0.6.jsonld.
    """
    out: dict = {
        "@context": "physmap/fixtures/context/v0.6.jsonld",
        "@type": "CredibilityFactor",
        "id": f"evidence-corpus:{claim.claim_id}",
        "factorType": _V06_FACTOR_TYPE_BY_CLAIM_TYPE.get(claim.claim_type, claim.claim_type),
        "factorStatus": claim.status,
        "factorStandard": source.doi or source.citation,
        "wasDerivedFrom": f"source:{source.source_id}",
        "description": (
            f"{claim.role} claim on closure {claim.closure_id}: "
            f"{claim.bound.variable} {claim.bound.condition}"
        ),
    }
    if claim.measured_divergence is not None:
        md = claim.measured_divergence
        out["hasEvidence"] = {
            "@type": "Discrepancy",
            "discrepancyMagnitude": md.magnitude_pct,
            "discrepancyRegion": md.region,
            "measureType": md.measure,
            "sourceReference": f"{source.source_id}#{md.page_or_table}",
        }
    return out


# ── CLI ───────────────────────────────────────────────────────────────────────


def _print_errors(errs_by_id: dict[str, list[str]]) -> int:
    if not errs_by_id:
        return 0
    total = sum(len(v) for v in errs_by_id.values())
    print(
        f"evidence corpus validation FAILED — {total} errors across "
        f"{len(errs_by_id)} ids:"
    )
    for cid in sorted(errs_by_id):
        print(f"  [{cid}]")
        for err in errs_by_id[cid]:
            print(f"      • {err}")
    return 1


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        sources = load_sources(args.sources_path)
        claims = load_claims(args.claims_path)
        calibration_ids = load_calibration_closure_ids(args.calibration_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"FAILED to load corpus: {e}", file=sys.stderr)
        return 2

    errs_by_id = validate_corpus(sources, claims, calibration_ids)
    if not errs_by_id:
        print(
            f"evidence corpus validation PASSED — {len(sources)} sources, "
            f"{len(claims)} claims clean"
        )
        # Status summary by role/status (audit signal).
        role_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        for c in claims:
            role_counts[c.role] = role_counts.get(c.role, 0) + 1
            status_counts[c.status] = status_counts.get(c.status, 0) + 1
        print(f"  by role:")
        for r in sorted(role_counts):
            print(f"    {r:>12s} : {role_counts[r]}")
        print(f"  by status:")
        for s in sorted(status_counts):
            print(f"    {s:>20s} : {status_counts[s]}")
        return 0
    return _print_errors(errs_by_id)


def _cmd_summary(args: argparse.Namespace) -> int:
    sources = load_sources(args.sources_path)
    claims = load_claims(args.claims_path)

    pop = sum(1 for s in sources if s.source_status == "populated")
    stub = sum(1 for s in sources if s.source_status == "stub")
    print(f"sources : {len(sources)}  (populated={pop}, stub={stub})")
    print(f"claims  : {len(claims)}")

    # Claims by closure.
    by_closure: dict[str, list[Claim]] = {}
    for c in claims:
        by_closure.setdefault(c.closure_id, []).append(c)
    print(f"  by closure:")
    for cid in sorted(by_closure):
        roles = ", ".join(sorted({c.role for c in by_closure[cid]}))
        print(f"    {cid:>55s} : {len(by_closure[cid]):>2d}  ({roles})")

    # Claims by source.
    by_source: dict[str, int] = {}
    for c in claims:
        by_source[c.source_id] = by_source.get(c.source_id, 0) + 1
    print(f"  by source:")
    for sid in sorted(by_source):
        print(f"    {sid:>30s} : {by_source[sid]}")

    # Extraction-method tally for validate claims.
    em_counts: dict[str, int] = {}
    for c in claims:
        if c.measured_divergence is not None:
            em_counts[c.measured_divergence.extraction_method] = (
                em_counts.get(c.measured_divergence.extraction_method, 0) + 1
            )
    print(f"  by extraction_method (validate claims):")
    for em in sorted(em_counts):
        print(f"    {em:>40s} : {em_counts[em]}")
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    claims = load_claims(args.claims_path)
    sub = args.query_name

    if sub == "validity-story":
        if not args.closure_id:
            print("--closure-id required for validity-story", file=sys.stderr)
            return 2
        rows = query_validity_story(claims, args.closure_id)
        print(f"validity story for closure '{args.closure_id}' — {len(rows)} claims:")
        for c in rows:
            md = c.measured_divergence
            md_str = (
                f"  divergence={md.magnitude_pct:+.1f}% [{md.measure}, "
                f"{md.extraction_method}, {md.page_or_table}]"
                if md is not None
                else ""
            )
            print(
                f"  [{c.role:>10s}] {c.claim_id}  status={c.status}  "
                f"source={c.source_id}  bound={c.bound.variable}{md_str}"
            )
        return 0

    if sub == "source-contributions":
        if not args.source_id:
            print("--source-id required for source-contributions", file=sys.stderr)
            return 2
        rows = query_source_contributions(claims, args.source_id)
        print(f"contributions of source '{args.source_id}' — {len(rows)} claims:")
        for c in rows:
            print(
                f"  {c.claim_id}  closure={c.closure_id}  role={c.role}  "
                f"status={c.status}"
            )
        return 0

    if sub == "unsupported-bounds":
        rows = query_unsupported_bounds(claims, args.calibration_path)
        print(
            f"calibration bounds with no backing evidence claim — {len(rows)} flagged:"
        )
        for cid, coord in sorted(rows):
            print(f"  {cid} :: {coord}")
        return 0

    if sub == "disagreements":
        rows = query_disagreements(claims)
        print(f"disagreements — {len(rows)} claims:")
        for c in rows:
            print(
                f"  {c.claim_id}  status={c.status}  "
                f"contradicts={c.contradicts_claim_id}"
            )
        return 0

    print(f"unknown query: {sub}", file=sys.stderr)
    return 2


def _cmd_export_jsonld(args: argparse.Namespace) -> int:
    sources = load_sources(args.sources_path)
    claims = load_claims(args.claims_path)
    source_index = {s.source_id: s for s in sources}

    rows = query_validity_story(claims, args.closure_id)
    if args.re is not None or args.pr is not None:
        rows = query_provenance_for_assessment(rows, args.closure_id, args.re, args.pr)

    out = []
    for c in rows:
        src = source_index.get(c.source_id)
        if src is None:
            continue
        out.append(claim_to_v06_jsonld(c, src))
    print(json.dumps(out, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PhysMAP Evidence Corpus — validator, summary, and query CLI"
    )
    parser.add_argument(
        "--sources-path", type=Path, default=DEFAULT_SOURCES_PATH,
        help=f"path to sources.jsonl (default: {DEFAULT_SOURCES_PATH})",
    )
    parser.add_argument(
        "--claims-path", type=Path, default=DEFAULT_CLAIMS_PATH,
        help=f"path to claims.jsonl (default: {DEFAULT_CLAIMS_PATH})",
    )
    parser.add_argument(
        "--calibration-path", type=Path, default=DEFAULT_CALIBRATION_PATH,
        help=f"path to calibration corpus.jsonl (default: {DEFAULT_CALIBRATION_PATH})",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate", help="run the 12 QC gates + corpus invariants")
    sub.add_parser("summary", help="print a status summary of the corpus")

    q = sub.add_parser("query", help="run one of the spec value-test queries")
    q.add_argument(
        "query_name",
        choices=[
            "validity-story",
            "source-contributions",
            "unsupported-bounds",
            "disagreements",
        ],
    )
    q.add_argument("--closure-id", type=str, default=None)
    q.add_argument("--source-id", type=str, default=None)

    e = sub.add_parser(
        "export-jsonld",
        help="export v0.6-shaped JSON-LD for a closure's claims (optionally filtered "
        "to a (Re, Pr) operating point)",
    )
    e.add_argument("--closure-id", type=str, required=True)
    e.add_argument("--re", type=float, default=None)
    e.add_argument("--pr", type=float, default=None)

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        return _cmd_validate(args)
    if args.cmd == "summary":
        return _cmd_summary(args)
    if args.cmd == "query":
        return _cmd_query(args)
    if args.cmd == "export-jsonld":
        return _cmd_export_jsonld(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
