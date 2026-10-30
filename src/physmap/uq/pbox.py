"""`physmap uq` -- UQAIS, Uncertainty Quantification for AI Surrogates: the minimal propagation,
Roy and Oberkampf style.

Inputs
    samples      CSV: a `point` column and the aleatory input columns, one row per sample.
                 A point with one row has no declared input variability: its CDF is a step.
    predictions  a callable `module:function`, called as fn(**{column: array}) per point,
                 or a CSV with `point` and `prediction`, one row per sample (or one per point).
    terms        CSV, one row per point, the epistemic terms kept on separate lines, all
                 RELATIVE to the prediction (a fraction, not a percent):
                   emulation            held-out emulation error of the surrogate
                   closure_status       inside | outside the closure's validated range
                   bound_kind           the kind of applicability bound that produced that status:
                                        range, set, point (a single training condition with a
                                        tolerance) or ratio (a derived quantity against a threshold)
                   validation           the declared validation metric (used when inside)
                   extrapolation_band   a declared band past the range (used when outside);
                                        blank means UNBOUNDED, and that is what is reported
                   materiality          the omitted-mechanism materiality from an ablation;
                                        `none` means no mechanism model: NOT ASSESSED
                 Any term may instead be given as `<term>_low` and `<term>_high` (signed).
                 A term that is not declared is an error, not a zero.

Output
    A probability box per point: the aleatory CDF of the prediction, shifted by the total
    epistemic interval, read at named quantiles as [lower, upper]; and a JSON report with each
    term on its own line. Never one number. "unbounded" is a legal, reported outcome.

Arithmetic
    Epistemic intervals add (Minkowski sum). For a sample y and total interval [L, H] with
    L <= 0 <= H, the box edges are y + |y| L and y + |y| H, so the relative box width at every
    quantile is exactly H - L: the sum of the terms' widths. That identity is in the report.
"""

from __future__ import annotations

import csv
import importlib
import json
import math
from dataclasses import asdict, dataclass

import numpy as np

PROCESS = "UQAIS, Uncertainty Quantification for AI Surrogates"
BOUND_KINDS = ("range", "set", "point", "ratio")
TERM_NAMES = ("emulation", "validation", "extrapolation_band", "materiality")
DEFAULT_QUANTILES = (0.05, 0.25, 0.50, 0.75, 0.95)
THETA_NOTE = ("theta is not locked; the value used here is illustrative, and the materiality is "
              "reported as a number beside it")


class UQInputError(ValueError):
    """One sentence about what is missing or malformed. Never a traceback."""


@dataclass(frozen=True)
class Term:
    name: str
    low: float            # relative, <= 0; -inf when unbounded
    high: float           # relative, >= 0; +inf when unbounded
    status: str           # declared | zero | unbounded | not_applied | not_assessed
    note: str

    @property
    def unbounded(self) -> bool:
        return math.isinf(self.low) or math.isinf(self.high)

    @property
    def width(self) -> float:
        return self.high - self.low

    def as_json(self) -> dict:
        d = asdict(self)
        d["interval"] = "unbounded" if self.unbounded else [self.low, self.high]
        d["width"] = "unbounded" if self.unbounded else self.width
        del d["low"], d["high"]
        return d


# ── reading ──────────────────────────────────────────────────────────────────

def read_csv(path) -> tuple[list[dict], list[str]]:
    """Rows as strings, plus any leading `#` comment lines (kept: they say what the file is)."""
    comments, body = [], []
    with open(path, newline="") as fh:
        for line in fh:
            if line.lstrip().startswith("#"):
                comments.append(line.strip().lstrip("#").strip())
            else:
                body.append(line)
    rows = list(csv.DictReader(body))
    if not rows:
        raise UQInputError(f"{path} has no data rows")
    if "point" not in rows[0]:
        raise UQInputError(f"{path} needs a `point` column")
    return rows, comments


def load_samples(path, inputs: list[str] | None = None) -> tuple[dict, list[str], list[str]]:
    rows, comments = read_csv(path)
    cols = inputs or [c for c in rows[0] if c != "point"]
    missing = [c for c in cols if c not in rows[0]]
    if missing:
        raise UQInputError(f"{path} lacks input column(s) {', '.join(missing)}")
    points: dict[str, dict[str, list[float]]] = {}
    for r in rows:
        d = points.setdefault(r["point"], {c: [] for c in cols})
        for c in cols:
            d[c].append(_float(r[c], f"{path}: {c} at point {r['point']}"))
    return ({p: {c: np.asarray(v, dtype=float) for c, v in d.items()} for p, d in points.items()},
            cols, comments)


def resolve_callable(spec: str):
    if ":" not in spec:
        raise UQInputError(f"--predict takes module:function, got {spec!r}")
    mod, _, fn = spec.partition(":")
    try:
        f = getattr(importlib.import_module(mod), fn)
    except (ImportError, AttributeError) as e:
        raise UQInputError(f"cannot import {spec!r}: {e}") from e
    return f


def predictions_from_callable(fn, samples: dict) -> dict:
    out = {}
    for point, cols in samples.items():
        y = np.asarray(fn(**cols), dtype=float).reshape(-1)
        n = len(next(iter(cols.values())))
        if len(y) != n:
            raise UQInputError(f"the callable returned {len(y)} values for {n} samples at {point}")
        out[point] = y
    return out


def predictions_from_csv(path, samples: dict) -> dict:
    rows, _ = read_csv(path)
    if "prediction" not in rows[0]:
        raise UQInputError(f"{path} needs a `prediction` column")
    by_point: dict[str, list[float]] = {}
    for r in rows:
        by_point.setdefault(r["point"], []).append(_float(r["prediction"], f"{path}: {r['point']}"))
    out = {}
    for point, cols in samples.items():
        n = len(next(iter(cols.values())))
        if point not in by_point:
            raise UQInputError(f"{path} has no prediction for point {point}")
        y = by_point[point]
        if len(y) == n:
            out[point] = np.asarray(y, dtype=float)
        elif len(y) == 1:
            out[point] = np.full(n, y[0])
        else:
            raise UQInputError(f"{path} has {len(y)} predictions for the {n} samples of {point}")
    return out


def load_terms(path, samples: dict, defaults: dict | None = None) -> dict:
    rows, comments = read_csv(path)
    defaults = defaults or {}
    by_point = {}
    for r in rows:
        if r["point"] in by_point:
            raise UQInputError(f"{path} lists point {r['point']} twice")
        by_point[r["point"]] = r
    missing = [p for p in samples if p not in by_point]
    if missing:
        raise UQInputError(f"{path} has no terms for point(s) {', '.join(missing[:5])}")
    return {p: _merge_defaults(by_point[p], defaults) for p in samples}, comments


def _merge_defaults(row: dict, defaults: dict) -> dict:
    out = dict(row)
    for k, v in defaults.items():
        if v is not None and not out.get(k, "").strip():
            out[k] = str(v)
    return out


def _float(s: str, where: str) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        raise UQInputError(f"{where}: {s!r} is not a number") from None


# ── terms ────────────────────────────────────────────────────────────────────

def _interval(row: dict, term: str, where: str) -> tuple[float, float] | None:
    """[low, high] from `<term>_low`/`<term>_high`, or symmetric from `<term>`; None if blank."""
    lo, hi, sym = row.get(f"{term}_low", ""), row.get(f"{term}_high", ""), row.get(term, "")
    if lo.strip() or hi.strip():
        if not (lo.strip() and hi.strip()):
            raise UQInputError(f"{where}: {term}_low and {term}_high must both be given")
        lo_v, hi_v = _float(lo, where), _float(hi, where)
        if lo_v > 0 or hi_v < 0:
            raise UQInputError(f"{where}: {term} interval [{lo_v}, {hi_v}] must contain 0")
        return lo_v, hi_v
    if sym.strip():
        if sym.strip().lower() == "none":
            return None
        v = abs(_float(sym, where))
        return -v, v
    raise UQInputError(f"{where}: the {term} term is not declared (declare 0 if it is zero)")


def terms_for_point(point: str, row: dict, theta: float | None) -> list[Term]:
    where = f"terms for {point}"
    terms = []

    e = _interval(row, "emulation", where)
    terms.append(Term("emulation", *e, "zero" if e == (0.0, 0.0) else "declared",
                      "surrogate against the simulation it learned, on held-out runs"
                      if e != (0.0, 0.0) else
                      "declared zero: the emulator is the closure itself, nothing was fitted"))

    status = row.get("closure_status", "").strip().lower()
    if status not in ("inside", "outside"):
        raise UQInputError(f"{where}: closure_status must be inside or outside, got {status!r}")
    kind = row.get("bound_kind", "").strip().lower()
    if kind not in BOUND_KINDS:
        raise UQInputError(f"{where}: bound_kind must be one of {', '.join(BOUND_KINDS)}, "
                           f"got {kind!r} (the kind of applicability bound behind closure_status)")
    if status == "inside":
        v = _interval(row, "validation", where)
        terms.append(Term("model_form_validated", *v, "declared",
                          f"inside the closure's validated range (a {kind} bound): the declared "
                          "validation metric (closure against measurement)"))
        terms.append(Term("model_form_unvalidated", 0.0, 0.0, "not_applied",
                          "the point is inside the validated range (W-SURR-05 quiet)"))
    else:
        terms.append(Term("model_form_validated", 0.0, 0.0, "not_applied",
                          "no validation evidence covers this point"))
        band = row.get("extrapolation_band", "").strip() or row.get("extrapolation_band_low", "").strip()
        if band:
            b = _interval(row, "extrapolation_band", where)
            terms.append(Term("model_form_unvalidated", *b, "declared",
                              "outside the closure's validated range (W-SURR-05): a declared "
                              "extrapolation band, reported as declared, not as validated"))
        else:
            terms.append(Term("model_form_unvalidated", -math.inf, math.inf, "unbounded",
                              f"outside the closure's validated range (W-SURR-05, a {kind} bound) "
                              "and no extrapolation band is declared: UNBOUNDED"))

    m = _interval(row, "materiality", where)
    if m is None:
        terms.append(Term("omitted_mechanism", 0.0, 0.0, "not_assessed",
                          "no mechanism model declared: the omitted-mechanism term is NOT "
                          "ASSESSED and the box does not include it"))
    else:
        size = max(-m[0], m[1])
        if theta is not None and size < theta:
            terms.append(Term("omitted_mechanism", 0.0, 0.0, "not_applied",
                              f"materiality {size:.4g} is below the illustrative theta {theta:g}"
                              f" (W-SURR-06 quiet); {THETA_NOTE}"))
        elif size == 0.0:
            terms.append(Term("omitted_mechanism", 0.0, 0.0, "zero",
                              "materiality 0: the ablation changed nothing"))
        else:
            gate = (f", at or above the illustrative theta {theta:g}; {THETA_NOTE}"
                    if theta is not None else "; no theta was given, so it is applied as is")
            terms.append(Term("omitted_mechanism", *m, "declared",
                              f"omitted mechanism active and material (W-SURR-06): materiality "
                              f"{size:.4g} from a matched ablation{gate}"))
    return terms


def total_interval(terms: list[Term]) -> tuple[float, float]:
    return sum(t.low for t in terms), sum(t.high for t in terms)


# ── the box ──────────────────────────────────────────────────────────────────

def pbox(y: np.ndarray, low: float, high: float, quantiles) -> dict:
    y = np.asarray(y, dtype=float)
    out = {}
    for p in quantiles:
        q = float(np.quantile(y, p))
        if math.isinf(low) or math.isinf(high):
            out[f"{p:g}"] = {"aleatory": q, "lower": "unbounded", "upper": "unbounded"}
        else:
            lo = float(np.quantile(y + np.abs(y) * low, p))
            hi = float(np.quantile(y + np.abs(y) * high, p))
            out[f"{p:g}"] = {"aleatory": q, "lower": lo, "upper": hi}
    return out


def propagate(samples: dict, predictions: dict, terms: dict, *, theta: float | None,
              quantiles=DEFAULT_QUANTILES, inputs_note: list[str] = (), terms_note: list[str] = ()) -> dict:
    points = []
    for point, cols in samples.items():
        y = predictions[point]
        ts = terms_for_point(point, terms[point], theta)
        low, high = total_interval(ts)
        unbounded = math.isinf(low) or math.isinf(high)
        med = float(np.quantile(y, 0.5))
        box = pbox(y, low, high, quantiles)
        width = "unbounded" if unbounded else high - low
        points.append({
            "point": point,
            "n_samples": int(len(y)),
            "closure_status": terms[point].get("closure_status", "").strip().lower(),
            "closure_bound_kind": terms[point].get("bound_kind", "").strip().lower(),
            "inputs": {c: {"min": float(v.min()), "median": float(np.median(v)), "max": float(v.max())}
                       for c, v in cols.items()},
            "aleatory_median": med,
            "terms": [t.as_json() for t in ts],
            "total_epistemic": "unbounded" if unbounded else {"low": low, "high": high},
            "relative_box_width": width,
            "sum_of_term_widths": "unbounded" if unbounded else sum(t.width for t in ts),
            "not_assessed": [t.name for t in ts if t.status == "not_assessed"],
            "pbox": box,
        })
    return {
        "command": "physmap uq",
        "process": PROCESS,
        "accounting": ("Roy and Oberkampf: aleatory input uncertainty propagated by sampling; "
                       "epistemic terms carried as intervals, listed separately, summed, never "
                       "averaged; model form outside a validated range is unbounded unless a "
                       "band is declared"),
        "terms_are_relative_to_the_prediction": True,
        "quantiles": [float(p) for p in quantiles],
        "theta": theta, "theta_note": THETA_NOTE if theta is not None else None,
        "samples_file_notes": list(inputs_note), "terms_file_notes": list(terms_note),
        "never_a_single_number": True,
        "points": points,
    }


# ── rendering ────────────────────────────────────────────────────────────────

def _fmt(v, nd=4) -> str:
    if isinstance(v, str):
        return v
    return f"{v:.{nd}g}"


def render(report: dict) -> str:
    qs = report["quantiles"]
    lo_q, hi_q = f"{qs[0]:g}", f"{qs[-1]:g}"
    lines = [f"physmap uq -- {PROCESS}: a probability box per point, terms relative to the prediction",
             f"  quantiles {', '.join(f'{q:g}' for q in qs)}"]
    if report["theta"] is not None:
        lines.append(f"  theta {report['theta']:g} ({report['theta_note']})")
    for n in report["samples_file_notes"]:
        lines.append(f"  samples: {n}")
    for n in report["terms_file_notes"]:
        lines.append(f"  terms: {n}")
    lines.append("")
    hdr = (f"{'point':<22} {'n':>5} {'median':>10} {'emul':>8} {'valid':>8} {'unvalid':>9} "
           f"{'mechanism':>9} {'total':>12}   box at q{lo_q} .. q{hi_q}")
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for pt in report["points"]:
        t = {x["name"]: x for x in pt["terms"]}

        def w(name):
            x = t[name]
            if x["status"] == "unbounded":
                return "UNBOUNDED"
            if x["status"] == "not_assessed":
                return "not assd"
            return _fmt(x["width"], 3)
        tot = pt["total_epistemic"]
        tot_s = "UNBOUNDED" if tot == "unbounded" else f"[{tot['low']:+.3g},{tot['high']:+.3g}]"
        b = pt["pbox"]
        box = (f"[{_fmt(b[lo_q]['lower'])}, {_fmt(b[lo_q]['upper'])}] .. "
               f"[{_fmt(b[hi_q]['lower'])}, {_fmt(b[hi_q]['upper'])}]")
        lines.append(f"{pt['point']:<22} {pt['n_samples']:>5} {pt['aleatory_median']:>10.4g} "
                     f"{w('emulation'):>8} {w('model_form_validated'):>8} "
                     f"{w('model_form_unvalidated'):>9} {w('omitted_mechanism'):>9} {tot_s:>12}   {box}")
    n_unb = sum(1 for p in report["points"] if p["total_epistemic"] == "unbounded")
    n_na = sum(1 for p in report["points"] if p["not_assessed"])
    lines.append("")
    lines.append(f"{len(report['points'])} point(s); {n_unb} unbounded; {n_na} with a term not assessed. "
                 "Each term is on its own line in the JSON report; nothing here is one number.")
    return "\n".join(lines)


def write_report(report: dict, path) -> None:
    with open(path, "w") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
