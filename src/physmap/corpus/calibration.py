"""PhysMAP Calibration-Boundary Corpus — schema, validators, loader, CLI.

The data asset that makes the causal-layer guardrail real: a geometry-agnostic
catalog of CFD closure validity envelopes, indexed by `closure_id`, with per-bound
provenance and a `confirmed/claimed/extrapolated` status that is the asset.

Spec: docs/specs/PhysMAP_CalibrationBoundary_Corpus_Spec_v0_1.md
Storage: a single JSONL file (one closure entry per line, line-diffable).
This module: schema (dataclasses + controlled vocabs), validators (the 7 QC gates +
corpus-wide invariants), loader API (load / index_by_id / get_validated_range /
is_in_calibration), and a CLI (`python -m physmap.corpus.calibration validate`).

The integration seam: `Mechanism.in_calibration()` in stage1_ingest.py uses hardcoded
`calib_lo/hi`. The corpus-backed replacement is `is_in_calibration(corpus_index,
closure_id, coord, operating_value)`. The swap is mechanical once the corpus has
Tier 1 coverage — deliberately not done yet.

Discipline: correct-and-partial beats complete-and-unverified. A `confirmed` bound
requires a primary-source citation (gate 7); the validator REJECTS any `confirmed`
without it. Mass-loading training-knowledge entries as `claimed` is allowed and
expected; passing them off as `confirmed` is forbidden.

Torch-free; depends only on the standard library.
"""

from __future__ import annotations

import argparse
import importlib.resources as _ir
import importlib.util as _iu
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

# ── controlled vocabularies (mirror stage1_ingest.TRUTH_SOURCES pattern) ──────

CLOSURE_FAMILIES = {
    # two-phase / boiling
    "flow-boiling", "pool-boiling", "chf-dnb",
    "rpi-sub-closure", "interfacial-force",
    # single-phase
    "single-phase-convection", "rans-turbulence", "wall-function",
    # medical
    "hemolysis",
    # multiphysics
    "cavitation", "condensation",
    "combustion-kinetics", "radiation",
    "non-newtonian-rheology", "porous-media", "species-diffusion",
    # hypersonic / high-speed
    "boundary-layer-transition",
}

BOUND_STATUSES = {"confirmed", "confirmed-contested", "claimed", "extrapolated"}

# The open SEED tier collapses every bound to this single status (the firewall
# strips the confirmed/claimed narration). It is NOT a premium status — the
# strict validator rejects it unless seed_tier=True is passed (opt-in), so the
# premium corpus's confirmed-citation discipline stays byte-identical.
SEED_BOUND_STATUS = "seed"

SOLVER_NAMES = {"openfoam", "fluent", "starccm+", "cfx", "none"}

# Geometry descriptors that MUST NOT appear in physics_coordinates per gate 6
# (geometry lives only in regime_context as traceability, never as a coord).
_FORBIDDEN_COORD_NAMES = {
    "geometry", "shape", "diameter", "length", "channel_width",
    "pipe_diameter", "channel_height", "aspect_ratio_geometry",
}

# Provenance shape requirement: a `confirmed` bound MUST carry both a primary_source
# flag AND a non-empty citation (gate 7 — handbook restatement ≠ primary confirmation).
# `provenance` is a dict; the expected keys are documented here, not strict-validated
# beyond the gate-7 requirement so curators can carry extra context fields.
_PROVENANCE_PRIMARY_KEY = "primary_source"
_PROVENANCE_CITATION_KEYS = ("citation", "doi", "page", "table", "figure", "url", "year")

# DEFAULT_PATH is the CANONICAL PREMIUM location and DOES NOT EXIST IN THIS
# REPOSITORY. The premium corpus is the commercial moat and is not published
# here, so resolution below always falls through to the bundled 15-closure seed
# unless $PHYSMAP_CORPUS points somewhere else. That is the intended public
# behaviour, not a misconfiguration. The path is kept so a premium holder can
# drop the file in and have it picked up with no code change.
# DEFAULT_PATH is the CANONICAL PREMIUM location — the full moat corpus in the
# dev/editable tree. It is NOT shipped in the core wheel (the package-data glob
# excludes results/calibration_corpus). Curation tooling and dev tests operate
# on this path directly; runtime loading goes through resolve_corpus_path().
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "results" / "calibration_corpus" / "corpus.jsonl"


# ── open-core corpus resolution (env → premium → bundled seed) ─────────────────
PHYSMAP_CORPUS_ENV = "PHYSMAP_CORPUS"
_PREMIUM_PACKAGE = "physmap_corpus_premium"       # optional private package (full corpus)
_PREMIUM_FILENAME = "corpus_premium.jsonl"
_SEED_PACKAGE = "physmap.corpus.data"             # bundled in the core wheel
_SEED_FILENAME = "corpus_seed.jsonl"


def _seed_path() -> Path:
    """The bundled, firewalled SEED corpus (always present in the core wheel)."""
    return Path(str(_ir.files(_SEED_PACKAGE) / _SEED_FILENAME))


def _premium_package_path() -> Path | None:
    """Full corpus from the optional `physmap_corpus_premium` package, or None."""
    if _iu.find_spec(_PREMIUM_PACKAGE) is None:
        return None
    try:
        p = Path(str(_ir.files(_PREMIUM_PACKAGE) / _PREMIUM_FILENAME))
        return p if p.is_file() else None
    except (FileNotFoundError, ModuleNotFoundError, NotADirectoryError):
        return None


def resolve_corpus_path() -> Path:
    """Resolve the active calibration corpus, in precedence order:

      1. ``$PHYSMAP_CORPUS`` — explicit path override.
      2. Premium if present — the canonical dev/editable file (DEFAULT_PATH), or
         the installed ``physmap_corpus_premium`` package.
      3. The bundled seed — ``physmap/corpus/data/corpus_seed.jsonl``.

    No network calls, no license checks: tier detection is purely "is the
    premium file present". In an editable/dev checkout step 2 hits DEFAULT_PATH,
    so every existing consumer sees the full corpus unchanged; in a core-only
    wheel install the canonical file is absent and resolution falls to the seed.
    """
    env = os.environ.get(PHYSMAP_CORPUS_ENV)
    if env:
        return Path(env).expanduser()
    if DEFAULT_PATH.is_file():
        return DEFAULT_PATH
    pkg = _premium_package_path()
    if pkg is not None:
        return pkg
    return _seed_path()


def active_tier(path: str | Path | None = None) -> str:
    """Return "seed" or "premium" for the resolved (or given) corpus.

    Content-based: the seed firewall collapses EVERY bound to status "seed", so
    a corpus whose first entry is all-"seed" is the seed tier. This is correct
    even for an explicit ``$PHYSMAP_CORPUS`` override regardless of filename.
    """
    p = Path(path) if path is not None else resolve_corpus_path()
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                statuses = {b.get("bound_status")
                            for b in json.loads(line).get("validated_range", [])}
                return "seed" if statuses == {SEED_BOUND_STATUS} else "premium"
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return "premium"


# ── schema dataclasses ────────────────────────────────────────────────────────

@dataclass
class CoordinateBound:
    """One per coordinate of a closure's validity envelope."""
    coord: str                                  # e.g. "mass_flux", "reynolds_number"
    min: float | None                           # None = unbounded below
    max: float | None                           # None = unbounded above
    unit: str                                   # SI preferred; "dimensionless" for Re/Pr
    bound_status: str                           # ∈ BOUND_STATUSES
    provenance: dict                            # see _PROVENANCE_* constants above
    contested_note: str | None = None           # if sources disagree on this coord


@dataclass
class ClosureEntry:
    """One named closure: validity envelope + provenance + status + scope filter."""
    closure_id: str                             # immutable slug: family-name-year
    closure_family: str                         # ∈ CLOSURE_FAMILIES
    closure_name: str                           # human name
    physics_coordinates: list[str]              # ordered list of coord names
    validated_range: list[CoordinateBound]      # one per coord; order matches
    fluid_context: list[str]                    # ["water","R12","blood","air",...]
    regime_context: str | None                  # traceability only; geometry-OK here
    contested: bool                             # whole-entry disagreement flag
    solver_availability: list[str]              # ⊂ SOLVER_NAMES
    weakener_link: list[str]                    # UofA weakener-pattern ids
    last_reviewed: str                          # ISO date YYYY-MM-DD
    reviewer: str                               # who curated/verified


# ── (de)serialization ─────────────────────────────────────────────────────────

def entry_from_dict(d: dict) -> ClosureEntry:
    """Build a ClosureEntry from a JSON-loaded dict (handles nested CoordinateBound)."""
    bounds_raw = d.get("validated_range", [])
    bounds = [CoordinateBound(**b) for b in bounds_raw]
    payload = {**d, "validated_range": bounds}
    return ClosureEntry(**payload)


def entry_to_dict(entry: ClosureEntry) -> dict:
    return asdict(entry)


# ── per-entry validation (the 7 QC gates) ─────────────────────────────────────

def validate(entry: ClosureEntry, *, seed_tier: bool = False) -> list[str]:
    """Return a list of human-readable error strings; empty list = entry is valid.

    Implements the spec's 7 per-entry QC gates plus shape checks.

    seed_tier=True (opt-in) validates a sanitized SEED file: it additionally
    accepts bound_status "seed". Everything else is unchanged, so premium
    validation is byte-identical to before (gate 7 only ever fires on
    confirmed/confirmed-contested, which the seed never carries).
    """
    errs: list[str] = []
    allowed_statuses = BOUND_STATUSES | {SEED_BOUND_STATUS} if seed_tier else BOUND_STATUSES
    eid = entry.closure_id or "<no closure_id>"

    # Shape: closure_id present, immutable slug
    if not entry.closure_id or not isinstance(entry.closure_id, str):
        errs.append(f"{eid}: closure_id missing or not a string")
    elif " " in entry.closure_id or entry.closure_id != entry.closure_id.lower():
        errs.append(f"{eid}: closure_id must be a lowercase slug (no spaces)")

    # Controlled vocab: family
    if entry.closure_family not in CLOSURE_FAMILIES:
        errs.append(
            f"{eid}: closure_family '{entry.closure_family}' not in CLOSURE_FAMILIES "
            f"({sorted(CLOSURE_FAMILIES)})"
        )

    # Shape: closure_name present
    if not entry.closure_name:
        errs.append(f"{eid}: closure_name missing")

    # Shape: physics_coordinates and validated_range length match
    if len(entry.physics_coordinates) != len(entry.validated_range):
        errs.append(
            f"{eid}: physics_coordinates ({len(entry.physics_coordinates)}) and "
            f"validated_range ({len(entry.validated_range)}) length mismatch"
        )

    # Shape + Gate 6: coord names in validated_range match physics_coordinates list,
    # and no geometry descriptors appear (geometry lives only in regime_context).
    for coord_name in entry.physics_coordinates:
        if coord_name.lower() in _FORBIDDEN_COORD_NAMES:
            errs.append(
                f"{eid}: physics_coordinates contains forbidden geometry descriptor "
                f"'{coord_name}' (gate 6 — geometry lives only in regime_context)"
            )
    coord_names_in_bounds = {b.coord for b in entry.validated_range}
    coord_names_declared = set(entry.physics_coordinates)
    if coord_names_in_bounds != coord_names_declared:
        only_in_bounds = coord_names_in_bounds - coord_names_declared
        only_in_decl = coord_names_declared - coord_names_in_bounds
        errs.append(
            f"{eid}: physics_coordinates vs validated_range.coord mismatch "
            f"(only in bounds: {sorted(only_in_bounds)}; only in declaration: "
            f"{sorted(only_in_decl)})"
        )

    # Per-bound gates 1, 2, 3, 7
    for b in entry.validated_range:
        # Gate 1: every bound carries a provenance
        if not isinstance(b.provenance, dict) or not b.provenance:
            errs.append(
                f"{eid}: coord '{b.coord}' missing provenance "
                f"(gate 1 — every bound carries a citation)"
            )
        else:
            # Gate 7: confirmed (and confirmed-contested) bounds require
            # primary_source + a non-handbook citation. confirmed-contested
            # is still a confirmation — source(s) disagree, but the primary-
            # source provenance discipline applies the same way.
            if b.bound_status in ("confirmed", "confirmed-contested"):
                if not b.provenance.get(_PROVENANCE_PRIMARY_KEY):
                    errs.append(
                        f"{eid}: coord '{b.coord}' is '{b.bound_status}' but provenance "
                        f"missing primary_source=true "
                        f"(gate 7 — handbook restatement ≠ primary confirmation)"
                    )
                has_citation = any(
                    b.provenance.get(k) for k in _PROVENANCE_CITATION_KEYS
                )
                if not has_citation:
                    errs.append(
                        f"{eid}: coord '{b.coord}' is '{b.bound_status}' but provenance "
                        f"carries no citation (one of {_PROVENANCE_CITATION_KEYS})"
                    )

        # Gate 2: bound_status ∈ BOUND_STATUSES (claimed default until upgraded);
        # seed_tier additionally allows the collapsed "seed" status.
        if b.bound_status not in allowed_statuses:
            errs.append(
                f"{eid}: coord '{b.coord}' bound_status '{b.bound_status}' not in "
                f"{sorted(allowed_statuses)} (gate 2)"
            )

        # Gate 3: a contested_note on a bound means contested=True at entry level
        if b.contested_note and not entry.contested:
            errs.append(
                f"{eid}: coord '{b.coord}' has contested_note but entry.contested=False "
                f"(gate 3 — record disagreement, do NOT silently average)"
            )

        # Shape: unit present
        if not b.unit:
            errs.append(f"{eid}: coord '{b.coord}' missing unit")

        # Shape: at least one of min/max set
        if b.min is None and b.max is None:
            errs.append(
                f"{eid}: coord '{b.coord}' has both min and max unset "
                f"(at least one bound must be declared)"
            )
        if b.min is not None and b.max is not None and b.min > b.max:
            errs.append(f"{eid}: coord '{b.coord}' min ({b.min}) > max ({b.max})")

    # Gate 4: solver_availability set; if {"none"} alone, require handbook adoption note
    if not entry.solver_availability:
        errs.append(f"{eid}: solver_availability empty (gate 4 — scope filter)")
    else:
        for s in entry.solver_availability:
            if s not in SOLVER_NAMES:
                errs.append(
                    f"{eid}: solver_availability includes '{s}' not in "
                    f"{sorted(SOLVER_NAMES)}"
                )
        if entry.solver_availability == ["none"]:
            # Gate 4 requires an explicit handbook-ADOPTION marker, not just any mention
            # of "handbook" — otherwise "no handbook reference here" trivially passes.
            adoption_markers = (
                "handbook-adopted", "handbook adoption",
                "handbook-canonical", "canonical handbook",
                "widely re-cited", "widely cited", "widely adopted",
            )
            ctx = (entry.regime_context or "").lower()
            if not any(marker in ctx for marker in adoption_markers):
                errs.append(
                    f"{eid}: solver_availability=['none'] requires an explicit handbook-"
                    f"adoption marker in regime_context (one of: "
                    f"{', '.join(repr(m) for m in adoption_markers)}); gate 4 — keeps "
                    f"the count at thousands not hundreds-of-thousands"
                )

    # Gate 5: weakener_link populated
    if not entry.weakener_link:
        errs.append(
            f"{eid}: weakener_link empty (gate 5 — bridge to UofA weakener vocabulary)"
        )

    # Shape: last_reviewed parseable ISO date
    if not entry.last_reviewed:
        errs.append(f"{eid}: last_reviewed missing")
    else:
        try:
            date.fromisoformat(entry.last_reviewed)
        except ValueError as e:
            errs.append(
                f"{eid}: last_reviewed '{entry.last_reviewed}' not parseable ISO date "
                f"({e})"
            )

    # Shape: reviewer present
    if not entry.reviewer:
        errs.append(f"{eid}: reviewer missing")

    return errs


# ── corpus-wide invariants ────────────────────────────────────────────────────

def validate_corpus(entries: list[ClosureEntry], *, seed_tier: bool = False) -> dict[str, list[str]]:
    """Per-entry errors keyed by closure_id, plus '__corpus__' for cross-entry issues.

    Cross-entry checks: unique closure_id. seed_tier is forwarded to validate()."""
    out: dict[str, list[str]] = {}
    for e in entries:
        errs = validate(e, seed_tier=seed_tier)
        if errs:
            out[e.closure_id or "<no closure_id>"] = errs

    # Unique closure_id across the corpus
    seen: dict[str, int] = {}
    for e in entries:
        seen[e.closure_id] = seen.get(e.closure_id, 0) + 1
    dups = [cid for cid, n in seen.items() if n > 1]
    if dups:
        out.setdefault("__corpus__", []).append(
            f"duplicate closure_id values: {sorted(dups)}"
        )

    return out


# ── loader API (minimal; future-causal-layer-integration-ready) ───────────────

def load_corpus(path: str | Path | None = None) -> list[ClosureEntry]:
    """Parse the JSONL file into a list of ClosureEntry. Raises on parse errors;
    schema validity must be checked separately via validate_corpus().

    path=None resolves the active corpus via resolve_corpus_path() (env → premium
    → bundled seed). In a dev/editable tree that is the canonical premium file, so
    behaviour is unchanged; in a core-only install it is the bundled seed."""
    p = Path(path) if path is not None else resolve_corpus_path()
    if not p.exists():
        raise FileNotFoundError(f"corpus file not found: {p}")
    entries: list[ClosureEntry] = []
    with open(p, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                d = json.loads(stripped)
            except json.JSONDecodeError as e:
                raise ValueError(f"corpus JSONL parse error at line {lineno}: {e}") from e
            try:
                entries.append(entry_from_dict(d))
            except TypeError as e:
                raise ValueError(
                    f"corpus schema mismatch at line {lineno} "
                    f"(closure_id={d.get('closure_id', '?')!r}): {e}"
                ) from e
    return entries


def index_by_id(entries: list[ClosureEntry]) -> dict[str, ClosureEntry]:
    return {e.closure_id: e for e in entries}


def get_validated_range(
    entries_index: dict[str, ClosureEntry], closure_id: str, coord: str,
) -> CoordinateBound | None:
    """Return the CoordinateBound for (closure_id, coord), or None if unknown."""
    entry = entries_index.get(closure_id)
    if entry is None:
        return None
    for b in entry.validated_range:
        if b.coord == coord:
            return b
    return None


def is_in_calibration(
    entries_index: dict[str, ClosureEntry], closure_id: str, coord: str, value: float,
) -> bool | None:
    """Return True/False if the value is inside [min, max] for the (closure_id, coord)
    bound, or None if the closure_id or coord is not in the corpus. None signals the
    caller to fall back to its own bounds (Mechanism.calib_lo/hi today)."""
    b = get_validated_range(entries_index, closure_id, coord)
    if b is None:
        return None
    if b.min is not None and value < b.min:
        return False
    if b.max is not None and value > b.max:
        return False
    return True


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print_errors(errs_by_id: dict[str, list[str]]) -> int:
    """Print errors grouped by closure_id; return non-zero exit code if any."""
    if not errs_by_id:
        return 0
    total = sum(len(v) for v in errs_by_id.values())
    print(f"corpus validation FAILED — {total} errors across {len(errs_by_id)} entries:")
    for cid in sorted(errs_by_id):
        print(f"  [{cid}]")
        for err in errs_by_id[cid]:
            print(f"      • {err}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PhysMAP Calibration-Boundary Corpus — validator + summary CLI",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="run the 7 QC gates + corpus invariants")
    p_val.add_argument("--path", type=Path, default=None,
                       help="path to corpus.jsonl (default: the active corpus via "
                            "resolve_corpus_path — env → premium → bundled seed)")
    p_val.add_argument("--tier", choices=("auto", "seed", "premium"), default="auto",
                       help="validation tier; 'auto' detects 'seed' (all-seed bounds) "
                            "and applies the seed-tier gates")

    p_sum = sub.add_parser("summary", help="print a status summary of the corpus")
    p_sum.add_argument("--path", type=Path, default=None)

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        path = args.path or resolve_corpus_path()
        try:
            entries = load_corpus(path)
        except (FileNotFoundError, ValueError) as e:
            print(f"FAILED to load corpus: {e}", file=sys.stderr)
            return 2
        seed_tier = args.tier == "seed" or (args.tier == "auto" and active_tier(path) == "seed")
        errs_by_id = validate_corpus(entries, seed_tier=seed_tier)
        if not errs_by_id:
            tier = "seed" if seed_tier else "premium"
            print(f"corpus validation PASSED — {len(entries)} entries clean "
                  f"[{tier}] ({path})")
            # Status summary by bound_status (useful audit signal)
            status_counts: dict[str, int] = {}
            for e in entries:
                for b in e.validated_range:
                    status_counts[b.bound_status] = status_counts.get(b.bound_status, 0) + 1
            total_bounds = sum(status_counts.values())
            print(f"  total bounds: {total_bounds}")
            display_statuses = sorted(BOUND_STATUSES | ({SEED_BOUND_STATUS} if seed_tier else set()))
            for s in display_statuses:
                print(f"    {s:>12s} : {status_counts.get(s, 0)}")
            print(f"  contested entries: "
                  f"{sum(1 for e in entries if e.contested)}/{len(entries)}")
            return 0
        return _print_errors(errs_by_id)

    if args.cmd == "summary":
        path = args.path or resolve_corpus_path()
        entries = load_corpus(path)
        family_counts: dict[str, int] = {}
        for e in entries:
            family_counts[e.closure_family] = family_counts.get(e.closure_family, 0) + 1
        print(f"corpus: {len(entries)} entries  [{active_tier(path)}] ({path})")
        for fam in sorted(family_counts):
            print(f"  {fam:>26s} : {family_counts[fam]}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
