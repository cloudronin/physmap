"""Build and check the UQ figures, their data tables, and the `physmap uq` examples.

    python -m physmap.uq.figures build      # figures (needs matplotlib), tables, examples
    python -m physmap.uq.figures check      # recompute the tables and compare, no matplotlib

Everything lands under docs/uq/. Every number on a figure comes from a table in
docs/uq/figures/data/; the check fails if a committed table differs from what the code gives.
The style is docs/talk/figures': blue is gravity off, orange is gravity on, the only dashed
line is an illustrative threshold, light theme only.
"""

from __future__ import annotations

import csv
import io
import json
import math
import sys
from pathlib import Path

from physmap._paths import checkout_path

UQ = None   # resolved lazily: the checkout's docs/uq
INK = {"surface": "#fcfcfb", "primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781",
       "grid": "#e1e0d9", "axis": "#c3c2b7", "panel": "#f1f0ec", "off": "#2a78d6",
       "on": "#eb6834", "band": "#d9d8d1"}
W, H = 10.0, 5.625
THETA_DASH = (0, (5, 4))
NACA_SAMPLES_PER_POINT = 50
NACA_RE_SPREAD = 0.02           # illustrative relative sd on Re; the source declares none
NACA_SAMPLE_SEED = 3


def _uq() -> Path:
    global UQ
    if UQ is None:
        UQ = checkout_path("docs", "uq", what="the uq docs directory")
    return UQ


def _fig_dir() -> Path:
    return _uq() / "figures"


def _data_dir() -> Path:
    return _uq() / "figures" / "data"


def _ex_dir() -> Path:
    return _uq() / "examples"


def _csv_text(header: list, rows: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def _r(v, nd=6):
    if v is None or isinstance(v, (str, bool)):
        return v
    if isinstance(v, float):
        if math.isinf(v):
            return "unbounded"
        return round(v, nd)
    return v


# ── tables ───────────────────────────────────────────────────────────────────

def naca_tables(N: dict) -> dict[str, str]:
    pts = ["Re", "Pr", "x_over_D", "region", "Nu_measured", "emulator_Nu", "error_pct",
           "within_interval", "test_replicate_Nu", "test_replicate_error_pct",
           "test_replicate_within", "closure_validity_fired", "novelty_density_fired",
           "gp_variance_fired"]
    cnt = list(N["counts"][0].keys())
    att = ["method", "calibration_units", "order_statistic_k", "finite_interval", "half_width", "note"]
    cal = [["nominal", N["nominal"]], ["alpha", round(N["alpha"], 12)],
           ["emulator", N["emulator"]], ["closure", N["closure"]],
           ["fully_developed_from_x_over_D", N["fully_developed_from"]],
           ["n_calibration_replicates", N["n_calibration"]],
           ["order_statistic_k", N["order_statistic_k"]],
           ["half_width", _r(N["half_width"])],
           ["half_width_pct", _r(100 * N["half_width"], 3)],
           ["noise_paper_pct", N["noise_model"]["paper_pct"]],
           ["noise_digitisation_pct", N["noise_model"]["digitisation_pct"]],
           ["noise_combined_relative_sd", _r(N["noise_model"]["combined_relative_sd"])],
           ["seed_calibration", N["seeds"]["calibration"]], ["seed_test", N["seeds"]["test"]],
           ["W_SURR_05_flags_of_entrance", f"{N['flags']['closure_validity']} of {N['flags']['of']}"],
           ["input_based_detectors_fired_of_entrance",
            f"{max(N['flags']['novelty_density'], N['flags']['gp_variance'])} of {N['flags']['of']}"]]
    return {
        "uq_1_naca_coverage.csv": _csv_text(pts, [[_r(p[k]) for k in pts] for p in N["points"]]),
        "uq_1_naca_counts.csv": _csv_text(cnt, [[_r(c[k]) for k in cnt] for c in N["counts"]]),
        "uq_1_naca_calibration_attempts.csv": _csv_text(att, [[_r(a[k]) for k in att] for a in N["attempts"]]),
        "uq_1_naca_interval.csv": _csv_text(["quantity", "value"], cal),
    }


def lewis_tables(L: dict) -> dict[str, str]:
    st = ["x_over_D", "comparable", "why_not", "surrogate_prediction", "control_gravity_off_Nu",
          "experiment_Nu", "control_error_pct", "experimental_error_pct",
          "measurement_relative_to_prediction_pct", "control_relative_to_prediction_pct",
          "statistical_half_width", "statistical_low", "statistical_high",
          "control_within_statistical", "measurement_within_statistical",
          "materiality_gravity_off", "materiality_gravity_on", "flag_at_illustrative_theta",
          "materiality_term_at_theta", "materiality_low", "materiality_high"]
    folds = ["run", "Re", "Pr", "n_rows", "worst_abs_relative_error"]
    e = L["emulation"]
    summary = [["design", L["design"]], ["nominal", L["nominal"]],
               ["theta_illustrative", L["theta_illustrative"]],
               ["emulation_unit", e["unit"]], ["emulation_n_units", e["n_units"]],
               ["emulation_order_statistic_k", e["order_statistic_k"]],
               ["emulation_half_width", _r(e["half_width"], 8)],
               ["emulation_half_width_pct", _r(100 * e["half_width"], 4)],
               ["emulation_row_level_half_width_for_information", _r(e["row_level_half_width_for_information"], 8)],
               ["emulation_n_rows", e["n_rows"]],
               ["inputs_identical_between_gravity_states", L["inputs_identical_between_gravity_states"]],
               ["interval_identical_between_gravity_states", L["interval_identical_between_gravity_states"]],
               ["flagged_stations_at_theta", " ".join(f"{x:g}" for x in L["flagged_stations"])],
               ["flagged_comparable_at_theta", " ".join(f"{x:g}" for x in L["flagged_comparable"])]]
    for x, m in L["materiality_at_three_downstream"].items():
        summary.append([f"materiality_term_at_xD_{x:g}", _r(m)])
    return {
        "uq_2_lewis_stations.csv": _csv_text(st, [[_r(s[k]) for k in st] for s in L["stations"]]),
        "uq_2_lewis_heldout_runs.csv": _csv_text(folds, [[_r(f[k]) for k in folds] for f in L["heldout_folds"]]),
        "uq_2_lewis_interval.csv": _csv_text(["quantity", "value"], summary),
    }


# ── examples for `physmap uq` ────────────────────────────────────────────────

def naca_examples(N: dict) -> dict[str, str]:
    import numpy as np
    from physmap.uq.naca import uq_terms
    rng = np.random.default_rng(NACA_SAMPLE_SEED)
    rows = []
    for p in N["points"]:
        pid = f"Re{p['Re']:g}_xD{p['x_over_D']:g}"
        re = p["Re"] * (1.0 + NACA_RE_SPREAD * rng.standard_normal(NACA_SAMPLES_PER_POINT))
        rows += [[pid, round(float(r), 3), p["Pr"]] for r in re]
    samples = ("# illustrative aleatory input: Re with a 2 % relative standard deviation, "
               f"{NACA_SAMPLES_PER_POINT} samples per point, seed {NACA_SAMPLE_SEED}. NACA TN-1451 "
               "declares no input uncertainty; this spread illustrates the propagation and is "
               "not a source value.\n" + _csv_text(["point", "Re", "Pr"], rows))
    t = uq_terms(N)
    th = ["point", "Re", "Pr", "x_over_D", "emulation", "closure_status", "validation",
          "extrapolation_band", "materiality"]
    terms = ("# terms relative to the prediction. emulation 0: the emulator is gnielinski-1976 "
             "itself. validation: the Q1 split-conformal half-width at nominal 90 %, inside the "
             "closure's validated range (x/D >= 10). Entrance points are outside it with no "
             "declared extrapolation band: UNBOUNDED. materiality 0: no omitted mechanism is "
             "modelled for this case.\n" + _csv_text(th, [[r[k] for k in th] for r in t]))
    return {"naca_samples.csv": samples, "naca_terms.csv": terms}


def lewis_examples(L: dict) -> dict[str, str]:
    from physmap.stress_tests.lewis_reuse import load_banked
    from physmap.uq.lewis import uq_terms
    bank = load_banked()
    dep = bank["input_contract"]["deployment_inputs"]
    srows = [[f"xD{x:g}", dep["Re"], dep["Pr"], x] for x in dep["x_over_D"]]
    samples = ("# no aleatory input distribution is declared for Lewis Test 35A: one nominal "
               "sample per station, so the aleatory CDF is a step and the box is the epistemic "
               "interval.\n" + _csv_text(["point", "Re", "Pr", "x_over_D"], srows))
    prows = [[f"xD{s['x_over_D']:g}", s["surrogate_prediction"]]
             for s in bank["headline_design_M"]["stations"]]
    preds = ("# design M surrogate predictions at Lewis's 12 stations, from the banked record "
             "results/lewis35A_head_to_head/stress_test_lewis_reuse.json; identical with gravity "
             "off and on because the inputs are.\n" + _csv_text(["point", "prediction"], prows))
    t = uq_terms(L)
    th = ["point", "x_over_D", "comparable", "emulation", "closure_status", "validation",
          "extrapolation_band", "materiality"]
    terms = ("# terms relative to the prediction. emulation: the Q2 held-out-run half-width at "
             "nominal 90 %. closure_status inside with validation 0: the surrogate is a GP "
             "with no closure, and the gravity-off CFD control is the declared validation "
             "(within 0.06 %, inside the emulation term). materiality: W-SURR-06 from the "
             "matched ablation, gated by --theta 0.10, which is illustrative.\n"
             + _csv_text(th, [[r[k] for k in th] for r in t]))
    return {"lewis_samples.csv": samples, "lewis_predictions.csv": preds, "lewis_terms.csv": terms}


def run_examples(which: str) -> dict:
    """Run `physmap uq` on the committed example inputs; return the report and the acceptance."""
    from physmap.cli import main as cli_main
    ex = _ex_dir()
    out = ex / f"{which}_report.json"
    if which == "naca":
        argv = ["uq", "--samples", str(ex / "naca_samples.csv"),
                "--predict", "physmap.closures.formulas:gnielinski_nu", "--inputs", "Re,Pr",
                "--terms", str(ex / "naca_terms.csv"), "--out", str(out)]
    else:
        argv = ["uq", "--samples", str(ex / "lewis_samples.csv"),
                "--predictions", str(ex / "lewis_predictions.csv"),
                "--terms", str(ex / "lewis_terms.csv"), "--theta", "0.10", "--out", str(out)]
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli_main(argv)
    if rc != 0:
        raise RuntimeError(f"physmap uq failed on the {which} example:\n{buf.getvalue()}")
    # the captured table, without the "Wrote the report to <absolute path>" line
    text = "\n".join(ln for ln in buf.getvalue().splitlines() if not ln.startswith("Wrote the report"))
    (ex / f"{which}_stdout.txt").write_text(text + "\n")
    return json.loads(out.read_text())


def acceptance(which: str, report: dict, N: dict | None = None, L: dict | None = None) -> list[str]:
    """Q3's acceptance and the second kill criterion, as failures (empty = pass)."""
    fails = []
    pts = {p["point"]: p for p in report["points"]}
    if which == "naca":
        q = N["half_width"]
        for p in N["points"]:
            r = pts[f"Re{p['Re']:g}_xD{p['x_over_D']:g}"]
            t = {x["name"]: x for x in r["terms"]}
            if p["region"] == "fully_developed":
                want = t["emulation"]["width"] + t["model_form_validated"]["width"]
                if r["relative_box_width"] == "unbounded" or abs(r["relative_box_width"] - want) > 1e-12:
                    fails.append(f"{r['point']}: box width {r['relative_box_width']} != emulation + validation {want}")
                # kill criterion 2: the box must not exceed the measured error band (±q) by more
                # than the emulation term
                excess = r["relative_box_width"] / 2 - q
                if excess > t["emulation"]["width"] / 2 + 1e-12:
                    fails.append(f"{r['point']}: box half-width exceeds the measured band by {excess}")
            else:
                if r["total_epistemic"] != "unbounded" or t["model_form_unvalidated"]["status"] != "unbounded":
                    fails.append(f"{r['point']}: entrance point should be unbounded")
    else:
        q = L["emulation"]["half_width"]
        for s in L["stations"]:
            r = pts[f"xD{s['x_over_D']:g}"]
            t = {x["name"]: x for x in r["terms"]}
            m = s["materiality_term_at_theta"]
            want = 2 * q + 2 * m
            if r["relative_box_width"] == "unbounded" or abs(r["relative_box_width"] - want) > 1e-12:
                fails.append(f"{r['point']}: box width {r['relative_box_width']} != 2 emulation + 2 materiality {want}")
            widened = t["omitted_mechanism"]["status"] == "declared"
            if widened != s["flag_at_illustrative_theta"]:
                fails.append(f"{r['point']}: materiality applied={widened}, flag={s['flag_at_illustrative_theta']}")
    return fails


# ── figures ──────────────────────────────────────────────────────────────────

def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 10, "axes.titlesize": 10.5, "axes.labelsize": 9.5,
        "axes.edgecolor": INK["axis"], "axes.linewidth": 0.8, "axes.facecolor": INK["surface"],
        "figure.facecolor": INK["surface"], "savefig.facecolor": INK["surface"],
        "axes.labelcolor": INK["secondary"], "xtick.color": INK["secondary"],
        "ytick.color": INK["secondary"], "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "text.color": INK["primary"], "axes.titlecolor": INK["primary"],
        "axes.grid": True, "grid.color": INK["grid"], "grid.linewidth": 0.6,
        "grid.linestyle": "-", "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "legend.fontsize": 8.5, "svg.fonttype": "none",
        "svg.hashsalt": "physmap-uq", "lines.linewidth": 2.0, "lines.markersize": 7,
        "axes.axisbelow": True,
    })
    return plt


def _save(fig, name: str, source: str):
    fig.text(0.012, 0.012, f"Source: {source}", fontsize=7, color=INK["muted"], ha="left",
             va="bottom")
    _fig_dir().mkdir(parents=True, exist_ok=True)
    fig.savefig(_fig_dir() / f"{name}.svg", metadata={"Date": None})
    fig.savefig(_fig_dir() / f"{name}.png", dpi=192)
    import matplotlib.pyplot as plt
    plt.close(fig)


def fig_naca(N: dict):
    plt = _mpl()
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    q = 100 * N["half_width"]
    curves = [c for c in N["counts"] if c["Re"] is not None]
    total = N["counts"][-1]
    fired = max(N["flags"]["novelty_density"], N["flags"]["gp_variance"])
    fig, axes = plt.subplots(2, 3, figsize=(W, H), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.065, right=0.985, top=0.775, bottom=0.11, wspace=0.12, hspace=0.3)
    fig.text(0.012, 0.975, "A 90 % interval that cannot see x/D: coverage at home and in the "
             "entrance region", fontsize=13, weight="bold", va="top")
    fig.text(0.012, 0.91, f"Emulator: Gnielinski, (Re, Pr) only, nothing fitted. Split-conformal "
             f"interval ±{q:.1f} % at nominal 90 %, calibrated on {N['n_calibration']} synthetic\n"
             f"replicates of the fully developed reads (x/D ≥ {N['fully_developed_from']:g}): each "
             "curve's 8 home reads are one value, and 5 units cannot calibrate a 90 % interval "
             "(it needs 9).\nx/D is not an emulator input, so every entrance point is "
             f"in-distribution. W-SURR-05 flags {N['flags']['closure_validity']} of "
             f"{N['flags']['of']} entrance points; the input-based detectors fire on {fired}.",
             fontsize=9, color=INK["secondary"], va="top", linespacing=1.45)
    for ax, c in zip(axes.flat, curves):
        Re = c["Re"]
        pts = [p for p in N["points"] if p["Re"] == Re]
        fd = [p for p in pts if p["region"] == "fully_developed"]
        en = [p for p in pts if p["region"] == "entrance"]
        ax.axvspan(0.5, N["fully_developed_from"], color=INK["panel"], lw=0, zorder=0)
        ax.axhspan(-q, q, color=INK["band"], lw=0, zorder=1, alpha=0.9)
        ax.axhline(0, color=INK["axis"], lw=0.8, zorder=2)
        ax.plot([p["x_over_D"] for p in fd], [p["test_replicate_error_pct"] for p in fd], "o",
                ms=4, mfc=INK["surface"], mec=INK["muted"], mew=1.0, zorder=3)
        ax.plot([p["x_over_D"] for p in en], [p["error_pct"] for p in en], "o", ms=9,
                mfc="none", mec=INK["on"], mew=1.6, zorder=4)
        ax.plot([p["x_over_D"] for p in pts], [p["error_pct"] for p in pts], "o", ms=4.5,
                color=INK["primary"], zorder=5)
        ax.set_title(f"Re {Re:g}", fontsize=9.5, loc="left")
        ax.text(0.98, 0.04, f"home {c['fully_developed_test_replicates_covered']} of "
                f"{c['fully_developed_points']} covered\nentrance {c['entrance_covered']} of "
                f"{c['entrance_points']} covered, {c['entrance_flagged_W_SURR_05']} of "
                f"{c['entrance_points']} flagged", transform=ax.transAxes, ha="right", va="bottom",
                fontsize=7.6, color=INK["secondary"], linespacing=1.3, zorder=6)
        ax.set_xlim(0.5, 17.5)
        ax.set_xticks([1, 5, 10, 15])
        ax.set_ylim(-45, 45)
        ax.set_yticks([-40, -20, 0, 20, 40])
    for ax in axes[1]:
        ax.set_xlabel("x/D")
    for ax in axes[:, 0]:
        ax.set_ylabel("emulator − read, % of read")
    ax = axes[1, 2]
    ax.axis("off")
    rows = [
        ("All five curves", None),
        ("home test replicates covered", f"{total['fully_developed_test_replicates_covered']} of "
                                         f"{total['fully_developed_points']}"),
        ("binomial band at 90 %, n = 40", f"{total['fully_developed_band_low']}–"
                                           f"{total['fully_developed_band_high']}"),
        ("entrance reads covered", f"{total['entrance_covered']} of {total['entrance_points']}"),
        ("binomial band at 90 %, n = 45", f"{total['entrance_band_low']}–{total['entrance_band_high']}"),
        ("W-SURR-05 flagged", f"{total['entrance_flagged_W_SURR_05']} of {total['entrance_points']}"),
        ("input-based detectors fired", f"{fired} of {total['entrance_points']}"),
        ("Noise model: 3 % paper, 5 % digitisation,", ""),
        ("in quadrature; seeds 1 (calibration), 2 (test)", ""),
    ]
    y = 1.0
    for label, value in rows:
        if value is None:
            y -= 0.02
            ax.text(0.0, y, label, transform=ax.transAxes, fontsize=9.2, weight="bold", va="top")
            y -= 0.1
            continue
        ax.text(0.0, y, label, transform=ax.transAxes, fontsize=8, color=INK["secondary"], va="top")
        if value:
            ax.text(1.0, y, value, transform=ax.transAxes, fontsize=8.6, weight="bold",
                    ha="right", va="top")
        y -= 0.085
    handles = [Line2D([], [], marker="o", ls="", color=INK["primary"], ms=4.5, label="read"),
               Line2D([], [], marker="o", ls="", mfc=INK["surface"], mec=INK["muted"], ms=4,
                      label="test replicate"),
               Line2D([], [], marker="o", ls="", mfc="none", mec=INK["on"], mew=1.6, ms=9,
                      label="W-SURR-05 flagged"),
               Patch(color=INK["band"], label=f"interval ±{q:.1f} %"),
               Patch(color=INK["panel"], label="entrance region")]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(-0.02, -0.1), ncol=2,
              fontsize=7.8, handletextpad=0.5, columnspacing=1.0)
    _save(fig, "uq_1_naca_coverage",
          "python -m physmap.uq.figures build on data/naca/cross_validated_fig10.csv; "
          "plotted values: docs/uq/figures/data/uq_1_naca_coverage.csv, counts: uq_1_naca_counts.csv")


def fig_lewis(L: dict):
    plt = _mpl()
    q = 100 * L["emulation"]["half_width"]
    st = L["stations"]
    fig, ax = plt.subplots(figsize=(W, H))
    fig.subplots_adjust(left=0.075, right=0.655, top=0.80, bottom=0.12)
    fig.text(0.012, 0.975, "The interval that does not move, and the term that opens: Lewis 35A",
             fontsize=13, weight="bold", va="top")
    fig.text(0.012, 0.905, f"The emulation interval (±{q:.2f} %, split conformal at nominal 90 % "
             f"over {L['emulation']['n_units']} held-out gravity-off runs) depends on Re, Pr and "
             "x/D only.\nThose are identical with gravity off and on, so the interval is identical. "
             "W-SURR-06's materiality is what widens, where the mechanism is material.",
             fontsize=9.5, color=INK["secondary"], va="top", linespacing=1.4)
    ax.axhspan(-q, q, color=INK["muted"], lw=0, zorder=1, alpha=0.9)
    ax.axhline(0, color=INK["axis"], lw=0.8, zorder=2)
    for s in st:
        if s["flag_at_illustrative_theta"]:
            m = 100 * s["materiality_term_at_theta"]
            ax.plot([s["x_over_D"], s["x_over_D"]], [-m, m], color=INK["on"], lw=9, alpha=0.3,
                    solid_capstyle="butt", zorder=2)
    for s in st:
        fc_off = INK["off"] if s["comparable"] else INK["surface"]
        fc_on = INK["on"] if s["comparable"] else INK["surface"]
        ax.plot(s["x_over_D"], s["control_relative_to_prediction_pct"], "o", ms=7, mec=INK["off"],
                mfc=fc_off, mew=1.6, zorder=4)
        ax.plot(s["x_over_D"], s["measurement_relative_to_prediction_pct"], "o", ms=7, mec=INK["on"],
                mfc=fc_on, mew=1.6, zorder=5)
    ax.set_xscale("log")
    ax.set_xlim(0.2, 250)
    ax.set_xticks([0.3, 1, 3, 10, 30, 100])
    ax.set_xticklabels(["0.3", "1", "3", "10", "30", "100"])
    ax.minorticks_off()
    ax.set_ylim(-45, 50)
    ax.set_xlabel("x/D")
    ax.set_ylabel("truth − surrogate prediction, % of prediction")
    ax.plot([], [], "o", mec=INK["off"], mfc=INK["off"], label="gravity-off CFD control")
    ax.plot([], [], "o", mec=INK["on"], mfc=INK["on"], label="Lewis's measurement (gravity on)")
    ax.plot([], [], "s", mec=INK["muted"], mfc=INK["muted"], label=f"emulation interval ±{q:.2f} %")
    ax.plot([], [], "s", mec=INK["on"], mfc=INK["on"], alpha=0.3,
            label=f"materiality interval, θ = {L['theta_illustrative']:.2f} illustrative")
    ax.plot([], [], "o", mec=INK["secondary"], mfc=INK["surface"], label="hollow: station Lewis disowns")
    ax.legend(loc="upper right", fontsize=8)
    x0 = 0.685
    fig.text(x0, 0.78, "Same inputs, same interval", fontsize=10.5, weight="bold", va="top")
    fig.text(x0, 0.73, f"inputs identical between gravity states: "
             f"{'yes' if L['inputs_identical_between_gravity_states'] else 'no'}\n"
             f"interval identical between gravity states: "
             f"{'yes' if L['interval_identical_between_gravity_states'] else 'no'}\n"
             f"control inside the interval at every station: "
             f"{'yes' if all(s['control_within_statistical'] for s in st) else 'no'}",
             fontsize=8.8, color=INK["secondary"], va="top", linespacing=1.5)
    fig.text(x0, 0.56, f"Materiality at θ = {L['theta_illustrative']:.2f}, illustrative",
             fontsize=10, weight="bold", va="top")
    rows = [s for s in st if s["flag_at_illustrative_theta"]]
    y = 0.51
    fig.text(x0, y, "x/D", fontsize=8.5, color=INK["secondary"])
    fig.text(x0 + 0.08, y, "materiality", fontsize=8.5, color=INK["secondary"])
    fig.text(x0 + 0.17, y, "measured − prediction", fontsize=8.5, color=INK["secondary"])
    for s in rows:
        y -= 0.045
        tag = "" if s["comparable"] else "  (disowned)"
        fig.text(x0, y, f"{s['x_over_D']:g}", fontsize=9)
        fig.text(x0 + 0.08, y, f"±{s['materiality_term_at_theta']:.3f}", fontsize=9)
        fig.text(x0 + 0.17, y, f"{s['measurement_relative_to_prediction_pct']:+.1f} %{tag}", fontsize=9)
    y -= 0.07
    fig.text(x0, y, "The rest of the gap is the base model's: the\ngravity-on CFD against the "
             "measurement (facts\nsheet §6). θ is not locked; no flag here is a\nverdict. "
             "Materiality is from the matched CFD\npair, not from the measurement.",
             fontsize=8.3, color=INK["secondary"], va="top", linespacing=1.4)
    _save(fig, "uq_2_lewis_materiality",
          "python -m physmap.uq.figures build on the Lewis bank and docs/uq/data/"
          "uq_2_lewis_emulation_heldout.json; plotted values: docs/uq/figures/data/uq_2_lewis_stations.csv")


# ── captions ─────────────────────────────────────────────────────────────────

def _para(text: str) -> str:
    import textwrap
    return textwrap.fill(" ".join(text.split()), width=96)


def captions(N: dict, L: dict) -> str:
    tn = N["counts"][-1]
    q1 = 100 * N["half_width"]
    q2 = 100 * L["emulation"]["half_width"]
    three = L["materiality_at_three_downstream"]
    mstr = ", ".join(f"{m:.3f} at x/D {x:g}" for x, m in three.items())
    text = f"""# UQ figures — generated, do not edit

Built by `python -m physmap.uq.figures build` from committed records only. Each figure ships
as an editable vector SVG and a 1920-pixel PNG, with a table twin in `data/` holding every
plotted value. Blue is gravity off and orange is gravity on; the only dashed line would be an
illustrative threshold. Light theme only.

## A 90 % interval that cannot see x/D (NACA TN-1451)

![A 90 % interval that cannot see x/D](uq_1_naca_coverage.png)

@@P@@The emulator is the Gnielinski correlation, which takes Re and Pr only; nothing was fitted. Its
split-conformal interval, nominal 90 %, has half-width {q1:.1f} % and was calibrated on
{N['n_calibration']} synthetic replicates of the {N['n_calibration']} fully developed reads
(x/D ≥ {N['fully_developed_from']:g}) under the digitisation's declared noise model
({N['noise_model']['paper_pct']:g} % paper reproducibility, {N['noise_model']['digitisation_pct']:g} %
digitisation floor, in quadrature). Synthetic replicates because the 40 reads are 5 values, one
per Reynolds curve, and 5 exchangeable units cannot calibrate a 90 % interval (it needs 9) — the
first kill criterion fired and this is its named fallback. On fresh test replicates of the fully
developed reads the interval covers {tn['fully_developed_test_replicates_covered']} of
{tn['fully_developed_points']} (binomial band {tn['fully_developed_band_low']}–{tn['fully_developed_band_high']}
at 90 %); on the {tn['entrance_points']} entrance reads, {tn['entrance_covered']} of {tn['entrance_points']}
(band {tn['entrance_band_low']}–{tn['entrance_band_high']}), per curve in each panel and in
`data/uq_1_naca_counts.csv`. x/D is not an emulator input, so every entrance point is in-distribution
to the interval and to the input-based detectors, which fire on 0; PhysMAP's W-SURR-05 flags
{tn['entrance_flagged_W_SURR_05']} of {tn['entrance_points']} (orange rings). The points the
interval covers in the entrance region are numerically close, but not supported by validation
evidence for this region.@@/P@@

- Files: [`uq_1_naca_coverage.svg`](uq_1_naca_coverage.svg) · [`uq_1_naca_coverage.png`](uq_1_naca_coverage.png)
- Plotted values: [`data/uq_1_naca_coverage.csv`](data/uq_1_naca_coverage.csv); counts: [`data/uq_1_naca_counts.csv`](data/uq_1_naca_counts.csv); the interval: [`data/uq_1_naca_interval.csv`](data/uq_1_naca_interval.csv); the data-trained attempts: [`data/uq_1_naca_calibration_attempts.csv`](data/uq_1_naca_calibration_attempts.csv)
- Source data: [`data/naca/cross_validated_fig10.csv`](../../../data/naca/cross_validated_fig10.csv)

## The interval that does not move, and the term that opens (Lewis 35A)

![The interval that does not move, and the term that opens](uq_2_lewis_materiality.png)

@@P@@Design M's surrogate, a Gaussian process on gravity-off CFD, carries an emulation interval of
±{q2:.2f} %: split conformal at nominal 90 % with one unit per held-out run, over the
{L['emulation']['n_units']} DOE runs each refitted without (`data/uq_2_lewis_heldout_runs.csv`).
The interval depends on Re, Pr and x/D only; those are identical with gravity off and on, so the
interval is identical, and the gravity-off control sits inside it at every station. What opens
with gravity on is W-SURR-06's materiality from the matched ablation, shown at the illustrative
θ = {L['theta_illustrative']:.2f}: {mstr}, the bank's values. θ is not locked; no flag here is a
verdict. Hollow markers are the three stations Lewis disowns. Materiality comes from the matched
CFD pair, not from the measurement; the remaining gap to the measurement is the base model's.@@/P@@

- Files: [`uq_2_lewis_materiality.svg`](uq_2_lewis_materiality.svg) · [`uq_2_lewis_materiality.png`](uq_2_lewis_materiality.png)
- Plotted values: [`data/uq_2_lewis_stations.csv`](data/uq_2_lewis_stations.csv); the interval: [`data/uq_2_lewis_interval.csv`](data/uq_2_lewis_interval.csv); held-out runs: [`data/uq_2_lewis_heldout_runs.csv`](data/uq_2_lewis_heldout_runs.csv)
- Source data: [`results/lewis35A_head_to_head/stress_test_lewis_reuse.json`](../../../results/lewis35A_head_to_head/stress_test_lewis_reuse.json), [`docs/uq/data/uq_2_lewis_emulation_heldout.json`](../data/uq_2_lewis_emulation_heldout.json)
"""
    import re
    return re.sub(r"@@P@@(.*?)@@/P@@", lambda m: _para(m.group(1)), text, flags=re.S)


# ── build and check ──────────────────────────────────────────────────────────

def _compute(parts):
    N = L = None
    if "naca" in parts:
        import warnings
        from physmap.uq import naca
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", module="sklearn")   # as the stress test does
            N = naca.compute()
    if "lewis" in parts:
        from physmap.uq import lewis
        L = lewis.compute()
    return N, L


def build(parts=("naca", "lewis")) -> int:
    N, L = _compute(parts)
    _data_dir().mkdir(parents=True, exist_ok=True)
    _ex_dir().mkdir(parents=True, exist_ok=True)
    fails = []
    if N:
        for name, text in {**naca_tables(N)}.items():
            (_data_dir() / name).write_text(text)
        for name, text in naca_examples(N).items():
            (_ex_dir() / name).write_text(text)
        fails += acceptance("naca", run_examples("naca"), N=N)
        fig_naca(N)
    if L:
        for name, text in lewis_tables(L).items():
            (_data_dir() / name).write_text(text)
        for name, text in lewis_examples(L).items():
            (_ex_dir() / name).write_text(text)
        fails += acceptance("lewis", run_examples("lewis"), L=L)
        fig_lewis(L)
    if N and L:
        (_fig_dir() / "README.md").write_text(captions(N, L))
    for f in fails:
        print(f"ACCEPTANCE FAILED: {f}")
    print(f"built {', '.join(parts)} under {_uq()}")
    return 1 if fails else 0


def check(parts=("naca", "lewis")) -> int:
    """Recompute the tables and examples and compare with what is committed. No matplotlib."""
    N, L = _compute(parts)
    fails = []
    want = {}
    if N:
        want.update({_data_dir() / k: v for k, v in naca_tables(N).items()})
        want.update({_ex_dir() / k: v for k, v in naca_examples(N).items()})
    if L:
        want.update({_data_dir() / k: v for k, v in lewis_tables(L).items()})
        want.update({_ex_dir() / k: v for k, v in lewis_examples(L).items()})
    if N and L:
        want[_fig_dir() / "README.md"] = captions(N, L)
    for path, text in want.items():
        if not path.exists():
            fails.append(f"{path.name} is missing -- run build")
        elif path.read_text() != text:
            fails.append(f"{path.name} is stale -- run build")
    for name in (["uq_1_naca_coverage"] if N else []) + (["uq_2_lewis_materiality"] if L else []):
        for ext in ("svg", "png"):
            if not (_fig_dir() / f"{name}.{ext}").exists():
                fails.append(f"{name}.{ext} is missing -- run build")
    if N:
        fails += acceptance("naca", json.loads((_ex_dir() / "naca_report.json").read_text()), N=N)
    if L:
        fails += acceptance("lewis", json.loads((_ex_dir() / "lewis_report.json").read_text()), L=L)
    for f in fails:
        print(f"FAIL: {f}")
    print("uq package: " + ("stale" if fails else "every table, example and report is what the code gives"))
    return 1 if fails else 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in ("build", "check"):
        print("usage: python -m physmap.uq.figures build|check [naca] [lewis]", file=sys.stderr)
        return 2
    parts = tuple(a for a in argv[1:] if a in ("naca", "lewis")) or ("naca", "lewis")
    return build(parts) if argv[0] == "build" else check(parts)


if __name__ == "__main__":
    raise SystemExit(main())
