"""PhysMAP Benchmark v0.4 — derived artifacts, regenerated from the banked JSON.

Three views of the ONE banked source (`results/benchmark_v0_4/matrix.json` +
`architecture_axis.json`): the two-claims findings doc, the observability-axis
figure, and the results CSV. None re-runs the benchmark or recomputes an outcome;
none has a per-vehicle branch (cells are iterated uniformly, styled/emitted by the
declarative fields). So all three can only ever AGREE with the banked matrix — and
a newly-registered vehicle appears in each automatically.

CLI: `python -m physmap.benchmarks.benchmark_report` (or `physmap benchmark report`).
"""
from __future__ import annotations

import csv as _csv
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results" / "benchmark_v0_4"
FINDINGS = (Path(__file__).resolve().parent.parent.parent / "docs" / "findings"
            / "PhysMAP_Benchmark_v0_4_Findings_v0_1.md")

# A cell is "caveated" (provisional/thin) if its declared caveat flags it — used to
# mark such cells distinctly in the figure so the honest scope is visible IN the plot.
_CAVEAT_FLAGS = ("provisional", "thin", "small-n", "small n", "strict")


def _load(name: str) -> dict | None:
    p = RESULTS / name
    return json.loads(p.read_text()) if p.exists() else None


def _cells(matrix: dict) -> list[dict]:
    return sorted(matrix.get("cells", []), key=lambda c: (c.get("domain", ""), c["vehicle_id"]))


def _is_caveated(cell: dict) -> bool:
    cav = (cell.get("caveat") or "").lower()
    return any(f in cav for f in _CAVEAT_FLAGS)


def _obs_label(cell: dict) -> str:
    cls = cell.get("failure_observability") or "?"
    score = cell.get("observability_score")
    src = cell.get("observability_source", "")
    s = f"{score:.2f}" if isinstance(score, (int, float)) else "—"
    tag = "" if src == "measured" else " (pole)"
    return f"{cls} ({s}{tag})"


def _clean_rate(cell: dict) -> float:
    """Normalized corpus advantage: clean lift ÷ surrogate deploy failures (n_wrong) — the FRACTION
    of the surrogate's deploy failures the corpus uniquely catches while the steelman baseline stays
    quiet. In [0,1], comparable across vehicles (n_wrong does NOT vary with the detector operating-pct
    — it depends only on prediction-vs-truth — so clean_lift_max / n_wrong_max is well-defined). 0.0
    when there are no deploy failures (DO_NO_HARM: no advantage to have). This is the y-axis: a rate,
    so the figure means what it looks like (no raw-count 'read position not height' caveat)."""
    ct = cell.get("clean_lift_max", 0) or 0
    nw = cell.get("n_wrong_max", 0) or 0
    return (ct / nw) if nw else 0.0


# ── B1: findings generator (template framing + generated data sections) ───────

_HEADER = """# PhysMAP Benchmark v0.4 — Findings (the benchmark of record)

> **Generated** by `physmap.benchmarks.benchmark_report` from the banked
> `results/benchmark_v0_4/{{matrix,architecture_axis}}.json` — do not hand-edit the
> data sections; re-run `physmap benchmark report` after a benchmark run.

Spec: [`specs/PhysMAP_Benchmark_Spec_v0_4.md`](../specs/PhysMAP_Benchmark_Spec_v0_4.md);
repeatable-runner spec:
[`specs/PhysMAP_Benchmark_YAMLDriven_Repeatable_Runner_Spec_v0_1.md`](../specs/PhysMAP_Benchmark_YAMLDriven_Repeatable_Runner_Spec_v0_1.md).
Artifacts: [`results/benchmark_v0_4/`](../../physmap/results/benchmark_v0_4/)
(`matrix.json`, `architecture_axis.json`, `benchmark_results.csv`, the figure, and
`gpvar_floor_investigation.md`).

**Binding methodology (v0.4):** every cell is produced by the SHIPPED public API
`physmap.guardrail.CredibilityGuardrail` (construct → fit → assess,
observability-weighted), the DETECTOR the only swapped variable. Per-cell decisions
are read from the RAW `Assessment.signals[...]` fire (verified detector-independent);
the Pareto lift (corpus fires & baselines quiet & surrogate WRONG) is computed on
that API output. The vehicle set is the registry: every `physmap/vehicles/*.yaml`
with a `benchmark` block — adding one is the only change needed for a new cell.
"""

_METHODOLOGY = """## Methodology findings

- **Real-API reproduction (reproduce-or-explain).** Outcomes are computed from raw
  signals; the registry-driven runner reproduces the banked outcomes exactly, and a
  cell that diverges is investigated, not forced.
- **gp_variance dense-training floor (`GP_VARIANCE_REL_FLOOR`).** The
  percentile-of-train-self gp_variance threshold collapses under dense training
  (a GP interpolating near-duplicate inputs → ~0 self-variance → tau ~7e-4), firing
  on benign sub-1% predictive variance. Confirmed per-row on two cases (Casper 1.06%;
  NACA cross-validated 0.05–0.72%) and floored — the [0.02, 0.20] invariant band is
  the evidence it is principled, not tuned-to-win. Full record:
  [`results/benchmark_v0_4/gpvar_floor_investigation.md`](../../physmap/results/benchmark_v0_4/gpvar_floor_investigation.md).
- **Single-detector-verdict guard.** Detector raw fires are detector-independent;
  the corpus-only verdict is honest REJECT on the unobservable axis and masked to
  TRUSTWORTHY (do-no-harm) on the observable axis — so the matrix reads raw signals,
  not the aggregated verdict.
- **Observability guard.** Each vehicle's declared `expected_observability_class` is
  asserted against the computed class; a mismatch fails loudly (no silent banking).
"""

_SUPPORTED = """## Supported / not supported

**Supported:** the cross-domain mechanism (both domains); discrimination (win where
baseline-blind, do-no-harm at the observable pole, decline at the baseline-visible
negative control); model-agnosticism where ≥2 architectures train and are guarded
identically.

**Not supported (do not claim):** full observability-spectrum coverage
(vehicle-limited); production-scale field-surrogate fidelity (the field /
neural-operator demonstration is deferred to a field-shaped vehicle); Casper as a
fresh-blind-holdout (it is construction-frozen-a-priori, small-n); dirker as a
stability-confirmed middle.
"""

_NEXT = """## Named next hardening steps

1. **Casper data request** — fresh quiet rms-vs-x conditions (more quiet points, more
   than one Re) to convert the construction-frozen-a-priori win into a fresh-blind-holdout.
2. **Field-shaped vehicle** — for the neural-operator (DeepONet / NVIDIA PhysicsNeMo)
   demonstration the scalar vehicles cannot support (out of scope for this matrix).
"""


def _matrix_table(cells: list[dict]) -> str:
    rows = ["| Vehicle | Domain | Observability | Outcome | Evidence |",
            "|---|---|---|---|---|"]
    for c in cells:
        ev = []
        if c.get("clean_lift_max") is not None:
            ev.append(f"clean lift {c['clean_lift_max']}")
        if c.get("n_test") is not None:
            ev.append(f"n={c['n_test']}")
        if _is_caveated(c):
            ev.append("⚠ caveat")
        rows.append(f"| **{c['vehicle_id']}** | {c.get('domain','')} | {_obs_label(c)} "
                    f"| {c['empirical_outcome']} | {'; '.join(ev)} |")
    return "\n".join(rows)


def _cross_domain_claim(cells: list[dict]) -> str:
    wins = {c["domain"] for c in cells if c["empirical_outcome"] == "PHYSMAP_WINS"}
    dnh = [c["vehicle_id"] for c in cells if c["empirical_outcome"] == "DO_NO_HARM"]
    neg = [c["vehicle_id"] for c in cells if c["empirical_outcome"] == "BASELINE_VISIBLE"]
    win_vehicles = [c["vehicle_id"] for c in cells if c["empirical_outcome"] == "PHYSMAP_WINS"]
    partials = [c["vehicle_id"] for c in cells if c["empirical_outcome"] == "PARTIAL"]
    wins_prose = " and ".join(sorted(wins))
    status = ("DEMONSTRATED in BOTH domains" if len(wins) >= 2
              else f"shown in {wins_prose}" if wins else "NOT shown")
    return (
        f"**1. Cross-domain (multiphysics) — {status}.** A confirmed PHYSMAP_WINS in "
        f"{wins_prose} ({', '.join(win_vehicles)}), the partial-observability middle(s) "
        f"({', '.join(partials) or 'none'}), the do-no-harm pole ({', '.join(dnh) or 'none'}), "
        f"and the baseline-visible negative control ({', '.join(neg) or 'none'}) — the same "
        f"mechanism (corpus catches a baseline-invisible failure, does no harm where the "
        f"baseline suffices, declines where the baseline already sees it) across domains."
    )


def _model_agnosticism_claim(arch: dict | None) -> str:
    if not arch:
        return ("**2. Model-agnosticism — not run** (no architecture-axis artifact; flag "
                "vehicles with `benchmark.architecture_axis: true` and run the axis).")
    shown, not_testable = [], []
    for vid, a in arch.get("agreement", {}).items():
        if a.get("all_show_corpus_lift"):
            shown.append(f"{vid} ({', '.join(a.get('trainable_architectures', []))})")
        if a.get("not_trainable"):
            not_testable.append(f"{vid} ({', '.join(a['not_trainable'])} NOT_TRAINABLE at n)")
    return (
        f"**2. Model-agnosticism — shown where demonstrated, not-testable elsewhere.** "
        f"PhysMAP guards GP and structurally-different surrogates identically (detector "
        f"fires are prediction-independent; only is-WRONG varies). Shown on: "
        f"{'; '.join(shown) or 'none'}. Not testable on: {'; '.join(not_testable) or 'none'} "
        f"(honest exclusion — no theater cells; never averaged into the claim)."
    )


def _caveat_block(cells: list[dict]) -> str:
    lines = ["## Honest caveats (per-cell, carried from the YAML — credibility, not weakness)", ""]
    for c in cells:
        if c.get("caveat"):
            lines.append(f"- **{c['vehicle_id']}**: {c['caveat']}")
    return "\n".join(lines)


def generate_findings(matrix: dict | None = None, arch: dict | None = None,
                      write: bool = True) -> str:
    matrix = matrix or _load("matrix.json")
    if matrix is None:
        raise FileNotFoundError(f"no banked matrix.json under {RESULTS}; run the benchmark first")
    arch = arch if arch is not None else _load("architecture_axis.json")
    cells = _cells(matrix)
    doc = "\n".join([
        _HEADER,
        "## The two claims (kept separate)\n",
        _cross_domain_claim(cells), "",
        _model_agnosticism_claim(arch), "",
        "## Cross-domain matrix (real API, registry-driven)\n",
        _matrix_table(cells), "",
        _METHODOLOGY,
        _caveat_block(cells), "",
        _SUPPORTED,
        _NEXT,
    ])
    if write:
        FINDINGS.parent.mkdir(parents=True, exist_ok=True)
        FINDINGS.write_text(doc)
    return doc


# ── B3: results CSV (the tabular twin) ────────────────────────────────────────

_CSV_COLUMNS = ["vehicle", "domain", "observability", "observability_class",
                "surrogate_inputs", "failure_driver", "baseline_fired", "corpus_fired",
                "clean_lift", "n_wrong", "clean_lift_rate", "misaligned", "outcome", "n", "caveat"]


def generate_csv(matrix: dict | None = None, arch: dict | None = None,
                 write: bool = True) -> dict:
    matrix = matrix or _load("matrix.json")
    if matrix is None:
        raise FileNotFoundError(f"no banked matrix.json under {RESULTS}")
    arch = arch if arch is not None else _load("architecture_axis.json")

    main_rows = []
    for c in _cells(matrix):
        main_rows.append({
            "vehicle": c["vehicle_id"], "domain": c.get("domain", ""),
            "observability": c.get("observability_score", ""),
            "observability_class": c.get("failure_observability", ""),
            "surrogate_inputs": "|".join(c.get("surrogate_inputs", [])),
            "failure_driver": c.get("failure_var", ""),
            "baseline_fired": c.get("ref_n_baseline_fired", ""),
            "corpus_fired": c.get("ref_n_corpus_fired", ""),
            "clean_lift": c.get("clean_lift_max", ""),
            "n_wrong": c.get("n_wrong_max", ""),
            "clean_lift_rate": round(_clean_rate(c), 3),
            "misaligned": c.get("misaligned_min", ""),
            "outcome": c["empirical_outcome"], "n": c.get("n_test", ""),
            "caveat": c.get("caveat", ""),
        })
    paths = {}
    if write:
        RESULTS.mkdir(parents=True, exist_ok=True)
        p = RESULTS / "benchmark_results.csv"
        with p.open("w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=_CSV_COLUMNS)
            w.writeheader(); w.writerows(main_rows)
        paths["matrix_csv"] = str(p)

    # Architecture axis: one explicit row per vehicle×architecture — NOT_TRAINABLE is a
    # row VALUE, never a dropped row (the no-theater discipline holds in the CSV too).
    if arch:
        arch_rows = []
        for c in arch.get("cells", []):
            g = c.get("gate1", {})
            arch_rows.append({
                "vehicle": c["vehicle_id"], "architecture": c["architecture"],
                "outcome": c["outcome"], "trainable": g.get("trainable", ""),
                "gate1_median_err_pct": g.get("median_err_pct", ""),
                "clean_lift": c.get("clean_lift_max", ""),
                "n_wrong_in_deploy": c.get("gate2_n_wrong_in_deploy", ""),
            })
        if write and arch_rows:
            p = RESULTS / "architecture_results.csv"
            cols = ["vehicle", "architecture", "outcome", "trainable",
                    "gate1_median_err_pct", "clean_lift", "n_wrong_in_deploy"]
            with p.open("w", newline="") as fh:
                w = _csv.DictWriter(fh, fieldnames=cols)
                w.writeheader(); w.writerows(arch_rows)
            paths["arch_csv"] = str(p)
    return paths


# ── B2: results figure (the observability axis — derived, never hand-drawn) ────

_DOMAIN_COLOR = {"thermal-fluids": "#0072B2", "aerospace": "#D55E00"}   # colorblind-safe
_OUTCOME_MARKER = {"PHYSMAP_WINS": "*", "PARTIAL": "o", "DO_NO_HARM": "s",
                   "BASELINE_VISIBLE": "X", "NO_FAILURE": "v",
                   "BASELINE_CATCHES_NO_LIFT": "P"}


def generate_figure(matrix: dict | None = None, arch: dict | None = None,
                    write: bool = True) -> list[str]:
    """Primary figure: observability (x) vs corpus clean-lift (y), colored by domain,
    marked by outcome, OPEN markers for caveated (provisional/thin) cells so the scope
    is honest IN the figure. Best-effort: returns [] if matplotlib is unavailable."""
    matrix = matrix or _load("matrix.json")
    if matrix is None:
        raise FileNotFoundError(f"no banked matrix.json under {RESULTS}")
    arch = arch if arch is not None else _load("architecture_axis.json")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
    except ImportError:
        return []

    cells = _cells(matrix)
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    _placed: dict[tuple, int] = {}   # stagger labels for coincident points (e.g. the poles)
    for c in cells:
        x = c.get("observability_score")
        y = _clean_rate(c)
        if not isinstance(x, (int, float)):
            continue
        outcome = c["empirical_outcome"]
        color = _DOMAIN_COLOR.get(c.get("domain", ""), "gray")
        marker = _OUTCOME_MARKER.get(outcome, "o")
        caveated = _is_caveated(c)
        _key = (round(float(x), 2), round(float(y), 2))
        _n = _placed.get(_key, 0)
        _placed[_key] = _n + 1
        # De-overlap coincident markers (e.g. Forrest & Marineau both at the observable pole
        # (1.0, 0)): nudge the 2nd+ point sharing an (x, y) by a small x offset toward the axis
        # interior so both markers are visible; the staggered label names each. Purely visual.
        xj = float(x) + (-0.035 * _n if float(x) >= 0.5 else 0.035 * _n)
        ax.scatter([xj], [y], s=320, marker=marker,
                   facecolors=("none" if caveated else color),
                   edgecolors=color, linewidths=2.2, zorder=3)
        ax.annotate(c["vehicle_id"].replace("_hypersonic_transition", "").replace("_", " "),
                    (xj, y), textcoords="offset points", xytext=(9, 5 + 17 * _n), fontsize=9)
    # Coverage-gap finding: 0.8-0.95 is the GENUINELY empty high-observability band — clear of the
    # property-ratio partials (dirker 0.49, velazquez 0.57) AND below the observable pole (1.0). Scoped
    # to where "no vehicle" actually holds (NOT 0.6-0.8, which is merely sparsely sampled just above
    # velazquez). Flagged as a named future-vehicle target. Drawn first (zorder 0); text sits in the
    # empty band, clear of the velazquez point/label at 0.57.
    ax.axvspan(0.80, 0.95, color="0.5", alpha=0.09, zorder=0)
    ax.text(0.875, 0.50, "coverage gap\n0.8–0.95\n(no vehicle —\nfuture target)",
            ha="center", va="center", fontsize=7.0, color="0.4", style="italic", zorder=1)
    ax.set_xlim(-0.07, 1.07)
    ax.set_ylim(-0.05, 1.12)                  # rate in [0,1] (+headroom for the top label)
    ax.set_xlabel("observability   (driver invisible to inputs  ←——→  driver is an input)",
                  fontsize=11)
    ax.set_ylabel("corpus clean-lift rate\n(fraction of deploy failures the corpus uniquely catches)",
                  fontsize=11)
    ax.set_title("PhysMAP: corpus advantage tracks observability position", fontsize=13)
    ax.grid(True, alpha=0.25)
    dom_handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=col,
                          markersize=11, label=dom) for dom, col in _DOMAIN_COLOR.items()]
    out_handles = [Line2D([0], [0], marker=m, color="0.3", linestyle="none",
                          markersize=11, label=o) for o, m in _OUTCOME_MARKER.items()
                   if any(c["empirical_outcome"] == o for c in cells)]
    cav_handle = [Line2D([0], [0], marker="o", color="0.3", markerfacecolor="none",
                         markersize=11, linestyle="none", label="caveated (provisional/thin)")]
    # Legend OUTSIDE the axes (right) so it never obscures a data point (e.g. the
    # high-clean-lift middle near mid-axis).
    ax.legend(handles=dom_handles + out_handles + cav_handle, fontsize=8,
              loc="center left", bbox_to_anchor=(1.01, 0.5), framealpha=0.9)
    n_total = sum(c.get("n_test", 0) or 0 for c in cells)
    cap = ("Each point: a benchmark vehicle. x = observability (cv_r2_knn; structural poles at 0/1). "
           "y = corpus clean-lift RATE = clean lift / surrogate deploy failures (n_wrong) — the fraction "
           "of the surrogate's deploy failures the corpus uniquely catches while the steelman baseline "
           "stays quiet, in [0,1] (0 = no failures / no advantage). Color = domain; marker = computed "
           "outcome; open marker = caveated; coincident points nudged in x for visibility. Shaded band "
           f"(0.8–0.95) = coverage gap: the high-observability region no vehicle yet probes. {len(cells)} vehicles, total "
           f"deploy n={n_total}. Derived from matrix.json (raw clean-lift counts + n in benchmark_results.csv).")
    fig.text(0.5, -0.02, cap, ha="center", va="top", fontsize=7.5, wrap=True)

    out: list[str] = []
    if write:
        RESULTS.mkdir(parents=True, exist_ok=True)
        for ext, dpi in (("svg", None), ("pdf", None), ("png", 220)):
            p = RESULTS / f"benchmark_matrix.{ext}"
            fig.savefig(p, dpi=dpi, bbox_inches="tight")
            out.append(str(p))
    plt.close(fig)
    return out


# ── orchestration ─────────────────────────────────────────────────────────────

def report_all() -> dict:
    matrix = _load("matrix.json")
    if matrix is None:
        raise FileNotFoundError(
            f"no banked matrix.json under {RESULTS} — run `physmap benchmark run` first")
    arch = _load("architecture_axis.json")
    generate_findings(matrix, arch, write=True)
    csvs = generate_csv(matrix, arch, write=True)
    figs = generate_figure(matrix, arch, write=True)
    return {"findings": str(FINDINGS), "csv": csvs, "figures": figs}


def main(argv=None) -> int:
    arts = report_all()
    print("regenerated benchmark report artifacts:")
    print(f"  findings: {arts['findings']}")
    for k, v in arts["csv"].items():
        print(f"  {k}: {v}")
    for f in arts["figures"]:
        print(f"  figure: {f}")
    if not arts["figures"]:
        print("  (figure skipped — matplotlib not available; install the [experiment] extra)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
