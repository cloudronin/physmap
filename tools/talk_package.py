#!/usr/bin/env python3
"""Build and check the NAFEMS Multiphysics 2026 talk package from COMMITTED records only.

    python tools/talk_package.py build   # figures (SVG + 1920-px PNG; needs matplotlib, which
                                         # the [experiment] extra installs), figure data CSVs,
                                         # captions, the facts sheet and the numbers registry
    python tools/talk_package.py check   # needs no matplotlib; exit 0 only if everything agrees

Every number the package displays goes through `_Reg.num`, which records the displayed
string, the raw value and the committed file it came from. `check` recomputes all of it from
the committed files and fails if:

  - any registered number, figure-data CSV, caption or the facts sheet has drifted from them;
  - a figure's SVG no longer shows every number it is registered as showing;
  - a Lewis number differs from what `physmap stress-test lewis-reuse` printed in the clean
    clone, a benchmark cell differs from what `physmap benchmark report` printed, or the NACA
    counts differ from what `examples/naca_entrance_region.py` printed;
  - the clean clone's record drifts from the committed bank, or its exit status was not 0;
  - a hand-written talk document contains a decimal number, or a whole-number percentage, that
    is neither a registered display value nor a historical value quoted in
    `protocols/known-results-declaration.md`.

Nothing here reruns OpenFOAM or runs a new experiment. The only computation beyond reading
records is the NACA entrance-region example, re-executed exactly as the example runs it, on
its committed fixture, because its per-point detector outputs are not banked.
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import re
import runpy
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

TALK = REPO / "docs" / "talk"
FIG = TALK / "figures"
FIGDATA = FIG / "data"
REPRO = TALK / "reproduction"
README = REPO / "README.md"

SRC = {
    "bank": "results/lewis35A_head_to_head/stress_test_lewis_reuse.json",
    "manifest": "data/stress_tests/lewis_reuse/manifest.json",
    "profiles": "data/stress_tests/lewis_reuse/cfd_profiles.json",
    "reduction": "data/lewis1992/test_35A_reduction.json",
    "grid": "results/lewis35A_vp/grid_pair.json",
    "predeclared": "results/lewis35A_head_to_head/design_M_matched.json",
    "predeclaration": "results/lewis35A_head_to_head/PREDECLARE_design_M_matched.md",
    "lowpct": "results/lewis35A_head_to_head/design_M_low_pct_mechanism.json",
    "matrix": "data/benchmarks/v0_4/matrix_full_seven.json",
    "home": "data/benchmarks/v0_4/home_baseline.json",
    "axis": "data/benchmarks/v0_4/architecture_axis.json",
    "naca": "data/naca/cross_validated_fig10.csv",
    "naca_example": "examples/naca_entrance_region.py",
    "known": "protocols/known-results-declaration.md",
}
REF_PCT = "99"                 # the benchmark's shipped reference operating percentile
DOWNSTREAM_FROM = 60.0         # "downstream": the comparable stations beyond x/D 60
THETAS_SHOWN = (0.05, 0.10, 0.20)


def _load(key):
    return json.loads((REPO / SRC[key]).read_text())


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO))
    except ValueError:                 # a copy outside the checkout, as the tests use
        return str(p)


# ── the numbers registry ──────────────────────────────────────────────────────

class _Reg:
    def __init__(self):
        self.items: dict[str, dict] = {}
        self.fig: str | None = None
        self.used: dict[str, list[str]] = {}

    def num(self, key: str, value, fmt: str, source: str) -> str:
        disp = value if isinstance(value, str) else fmt.format(value)
        prev = self.items.get(key)
        if prev and prev["display"] != disp:
            raise ValueError(f"{key} registered twice: {prev['display']} / {disp}")
        self.items[key] = {"display": disp, "value": value, "source": source}
        return disp

    def d(self, key: str) -> str:
        """The display string for `key`; inside a figure, records that the figure shows it."""
        if self.fig is not None:
            u = self.used.setdefault(self.fig, [])
            if key not in u:
                u.append(key)
        return self.items[key]["display"]


# ── Lewis: everything displayed, from committed files ────────────────────────

def compute_lewis(reg: _Reg) -> dict:
    from physmap.stress_tests.lewis_reuse import ILLUSTRATIVE_THETA
    bank, man, prof = _load("bank"), _load("manifest"), _load("profiles")
    red, grid, pre, low = _load("reduction"), _load("grid"), _load("predeclared"), _load("lowpct")
    B, P = SRC["bank"], SRC["profiles"]
    M = bank["headline_design_M"]
    S = M["stations"]
    comp = [s for s in S if s["comparable"]]
    n = len(comp)
    on_cfd = dict(zip(prof["ablation_full"]["x_over_D"], prof["ablation_full"]["Nu"]))
    off_cfd = dict(zip(prof["ablation_removed"]["x_over_D"], prof["ablation_removed"]["Nu"]))
    L = {"stations": []}

    # per station -- the CLI's own formats, so the two can be compared as printed
    for s in S:
        x = s["x_over_D"]
        k = f"lewis.x{x:g}"
        on, off = s["ood_gravity_on"][REF_PCT], s["ood_gravity_off"][REF_PCT]
        m = s["materiality_gravity_on"]
        g = on_cfd[x] / s["experiment_Nu"] - 1           # the base model's own gap
        fit = s["surrogate_prediction"] / off_cfd[x] - 1  # surrogate vs gravity-off CFD
        reg.num(f"{k}.x_over_D", x, "{:g}", B)
        reg.num(f"{k}.control_error_pct", s["control_error_pct"], "{:+.2f}", B)
        reg.num(f"{k}.experimental_error_pct", s["experimental_error_pct"], "{:+.1f}", B)
        reg.num(f"{k}.ood_distance", on["distance"]["score"], "{:.3f}", B)
        reg.num(f"{k}.ood_gp", on["gp_variance"]["score"], "{:.4f}", B)
        reg.num(f"{k}.ood_p99", "fires" if on["fired"] else "quiet", "{}", B)
        reg.num(f"{k}.materiality_off", s["materiality_gravity_off"], "{:.3f}", B)
        reg.num(f"{k}.materiality_on", m, "{:.3f}", B)
        reg.num(f"{k}.Nu_experiment", s["experiment_Nu"], "{:.2f}", B)
        reg.num(f"{k}.Nu_surrogate", s["surrogate_prediction"], "{:.2f}", B)
        reg.num(f"{k}.Nu_control", s["control_gravity_off_truth"], "{:.2f}", B)
        reg.num(f"{k}.split_missing_buoyancy_pct", -100 * m, "{:+.1f}", B)
        reg.num(f"{k}.split_base_model_gap_pct", 100 * g, "{:+.1f}", f"{P} (ablation_full) + {B}")
        reg.num(f"{k}.split_fit_pct", 100 * fit, "{:+.2f}", f"{P} (ablation_removed) + {B}")
        L["stations"].append({
            "k": k, "x": x, "comparable": s["comparable"], "why_not": s["why_not"],
            "pred": s["surrogate_prediction"], "Nu_exp": s["experiment_Nu"],
            "Nu_ctl": s["control_gravity_off_truth"], "ctl": s["control_error_pct"],
            "exp": s["experimental_error_pct"], "dist_on": on["distance"]["score"],
            "dist_off": off["distance"]["score"], "gp_on": on["gp_variance"]["score"],
            "gp_off": off["gp_variance"]["score"], "fired_on": on["fired"],
            "fired_off": off["fired"], "m_on": m, "m_off": s["materiality_gravity_off"],
            "flag_on_illustrative": s["physmap_flag_gravity_on_at_illustrative_theta"],
            "flag_off_illustrative": s["physmap_flag_gravity_off_at_illustrative_theta"]})

    thr = S[0]["ood_gravity_on"][REF_PCT]
    reg.num("lewis.ood.threshold_distance", thr["distance"]["threshold"], "{:.3f}", B)
    reg.num("lewis.ood.threshold_gp", thr["gp_variance"]["threshold"], "{:.3f}", B)
    L["thr_distance"] = thr["distance"]["threshold"]
    L["thr_gp"] = thr["gp_variance"]["threshold"]
    L["ood_identical"] = M["ood"]["identical_between_gravity_states"]
    diffs = [abs(s["ood_gravity_on"][p][d]["score"] - s["ood_gravity_off"][p][d]["score"])
             for s in S for p in s["ood_gravity_on"] for d in ("distance", "gp_variance")]
    reg.num("lewis.ood.max_abs_difference_on_vs_off", max(diffs), "{:g}", B)
    reg.num("lewis.ood.max_distance_comparable",
            max(s["ood_gravity_on"][REF_PCT]["distance"]["score"] for s in comp), "{:.3f}", B)
    reg.num("lewis.ood.min_distance_comparable",
            min(s["ood_gravity_on"][REF_PCT]["distance"]["score"] for s in comp), "{:.3f}", B)
    reg.num("lewis.ood.max_gp_all", max(s["ood_gravity_on"][REF_PCT]["gp_variance"]["score"]
                                        for s in S), "{:.4f}", B)
    L["sweep"] = M["ood"]["comparable_stations_fired_by_pct"]
    for p, v in L["sweep"].items():
        if v["gravity_on"] != v["gravity_off"]:
            raise ValueError("the sweep differs between gravity states -- the bank is not what "
                             "this package describes")
        reg.num(f"lewis.ood.sweep_p{p}", f"{v['gravity_on']}/{n}", "{}", B)
    reg.num("lewis.ood.fired_p99_comparable", L["sweep"][REF_PCT]["gravity_on"], "{}", B)
    reg.num("lewis.n_stations", len(S), "{}", B)
    reg.num("lewis.n_comparable", n, "{}", B)
    reg.num("lewis.control_error_max_abs_pct", max(abs(s["control_error_pct"]) for s in comp),
            "{:.2f}", B)
    dn = [s for s in comp if s["x_over_D"] > DOWNSTREAM_FROM]
    L["downstream"] = [s["x_over_D"] for s in dn]
    reg.num("lewis.downstream_stations", ", ".join(f"{s['x_over_D']:g}" for s in dn), "{}", B)
    errs = sorted(abs(s["experimental_error_pct"]) for s in dn)
    reg.num("lewis.downstream_error_range_pct", f"{round(errs[0])}–{round(errs[-1])}", "{}", B)
    gaps = sorted(abs(100 * (on_cfd[s["x_over_D"]] / s["experiment_Nu"] - 1)) for s in dn)
    reg.num("lewis.downstream_base_gap_range_pct", f"{gaps[0]:.1f}–{gaps[-1]:.1f}", "{}",
            f"{P} + {B}")
    mats = [s["materiality_gravity_on"] for s in comp]
    reg.num("lewis.materiality_on_max", max(mats), "{:.3f}", B)
    reg.num("lewis.materiality_on_min", min(mats), "{:.3f}", B)
    L["mat_max_x"] = max(comp, key=lambda s: s["materiality_gravity_on"])["x_over_D"]
    td = {t["result"]: t for t in bank["threshold_dependence"]}
    reg.num("lewis.theta_any_flag_up_to",
            td["PhysMAP flags at least one comparable station with gravity on"]
            ["holds_for_theta_up_to"], "{:.3f}", B)
    reg.num("lewis.theta_illustrative", ILLUSTRATIVE_THETA, "{:.2f}",
            "src/physmap/stress_tests/lewis_reuse.py (ILLUSTRATIVE_THETA); protocols/protocol.json")
    L["theta"] = ILLUSTRATIVE_THETA
    for th in THETAS_SHOWN:
        reg.num(f"lewis.flags_on_at_theta_{th:.2f}", sum(1 for m in mats if m >= th), "{}", B)
        reg.num(f"lewis.theta_{th:.2f}", th, "{:.2f}", "shown for illustration; theta is unlocked")
    flagged = [s["x_over_D"] for s in comp if s["physmap_flag_gravity_on_at_illustrative_theta"]]
    reg.num("lewis.flagged_at_illustrative", ", ".join(f"{x:g}" for x in flagged), "{}", B)
    L["flags_off_any"] = any(s["physmap_flag_gravity_off_at_illustrative_theta"] for s in S)
    reg.num("lewis.Ri_gravity_on", bank["physmap"]["Ri_gravity_on"], "{:.2f}", B)
    L["window"] = bank["physmap"]["calibration_window"]

    ic = bank["input_contract"]
    L["contract"] = ic
    reg.num("lewis.deploy_Re", ic["deployment_inputs"]["Re"], "{:.1f}", B)
    reg.num("lewis.deploy_Pr", ic["deployment_inputs"]["Pr"], "{:.2f}", B)
    L["exact_overlap"] = ic["design_M_every_visible_input_exactly_in_training"]
    reg.num("lewis.M.training_runs", M["training_runs"], "{}", B)
    reg.num("lewis.M.training_rows", M["training_rows"], "{}", B)
    A3 = bank["secondary_design_A3"]
    a3c = [s for s in A3["stations"] if s["comparable"]]
    reg.num("lewis.A3.training_runs", A3["training_runs"], "{}", B)
    reg.num("lewis.A3.training_rows", A3["training_rows"], "{}", B)
    reg.num("lewis.A3.fired_p99_off", A3["ood"]["comparable_stations_fired_by_pct"][REF_PCT]
            ["gravity_off"], "{}", B)
    reg.num("lewis.A3.fired_p99_on", A3["ood"]["comparable_stations_fired_by_pct"][REF_PCT]
            ["gravity_on"], "{}", B)
    L["A3_identical"] = A3["ood"]["identical_between_gravity_states"]
    reg.num("lewis.A3.control_error_max_abs_pct", max(abs(s["control_error_pct"]) for s in a3c),
            "{:.2f}", B)
    dists = [s["ood_gravity_on"][REF_PCT]["distance"]["score"] for s in a3c]
    reg.num("lewis.A3.distance_range", f"{min(dists):.2f}–{max(dists):.2f}", "{}", B)
    reg.num("lewis.A3.threshold_distance",
            A3["stations"][0]["ood_gravity_on"][REF_PCT]["distance"]["threshold"], "{:.3f}", B)

    # the training runs, as banked
    runs = prof["training_runs"] + [prof["matched_training_run"]]
    L["runs"] = [{"case": r["case"], "Re": r["inlet_bulk"]["Re"], "Pr": r["inlet_bulk"]["Pr"],
                  "T_in": r["operating_point"]["T_in_C"], "it": r["iterations"],
                  "energy": r["energy_closure_pct"], "h": r["final_initial_residuals"]["h_initial"],
                  "rev": r["reversed_cells_in_heated_section"], "n": len(r["x_over_D"])}
                 for r in runs]
    doe = prof["training_runs"]
    reg.num("lewis.train.Re_min", min(r["inlet_bulk"]["Re"] for r in doe), "{:.0f}", P)
    reg.num("lewis.train.Re_max", max(r["inlet_bulk"]["Re"] for r in doe), "{:.0f}", P)
    reg.num("lewis.train.Re_levels", ", ".join(
        f"{v:.0f}" for v in sorted({round(r["inlet_bulk"]["Re"]) for r in doe})), "{}", P)
    reg.num("lewis.train.T_in_levels", ", ".join(
        f"{v:g}" for v in sorted({r["operating_point"]["T_in_C"] for r in doe})), "{}", P)
    reg.num("lewis.train.stations_per_run", len(doe[0]["x_over_D"]), "{}", P)
    reg.num("lewis.train.matched_run_stations", len(prof["matched_training_run"]["x_over_D"]),
            "{}", P)
    reg.num("lewis.train.energy_max_abs_pct", max(abs(r["energy_closure_pct"]) for r in runs),
            "{:.2f}", P)
    reg.num("lewis.train.reversed_cells_total", sum(r["reversed_cells_in_heated_section"]
                                                    for r in runs), "{}", P)
    reg.num("lewis.train.iterations", " or ".join(
        str(v) for v in sorted({r["iterations"] for r in doe})), "{}", P)
    mr = prof["matched_training_run"]["inlet_bulk"]
    reg.num("lewis.train.matched_label_offset_Re_pct",
            100 * (mr["Re"] / ic["deployment_inputs"]["Re"] - 1), "{:+.3f}", f"{P} + {B}")
    reg.num("lewis.train.matched_label_offset_Pr_pct",
            100 * (mr["Pr"] / ic["deployment_inputs"]["Pr"] - 1), "{:+.3f}", f"{P} + {B}")
    loo = pre["training"]["leave_one_run_out"]
    reg.num("lewis.surrogate.loo_worst_pct", max(v["max_abs_pct"] for v in loo.values()),
            "{:.2f}", SRC["predeclared"])

    ma = bank["matched_ablation"]
    L["only_difference"] = ma["only_difference"]
    reg.num("lewis.ablation.energy_full_inlet_ref", ma["full"]["energy_closure_pct"], "{:+.2f}", B)
    reg.num("lewis.ablation.energy_removed_inlet_ref", ma["removed"]["energy_closure_pct"],
            "{:+.2f}", B)
    reg.num("lewis.ablation.iterations", ma["iterations"], "{}", B)
    L["energy_definition"] = man["energy_closure_definition"]
    m1 = re.search(r"against Lewis's own calculated rise of ([\d.]+) K the same fields read "
                   r"([−+-]?\d+\.\d+) % and ([−+-]?\d+\.\d+) %", man["energy_closure_definition"])
    reg.num("lewis.ablation.energy_full_lewis_ref", float(m1.group(2)), "{:+.2f}",
            SRC["manifest"] + " (energy_closure_definition)")
    reg.num("lewis.ablation.energy_removed_lewis_ref", float(m1.group(3)), "{:+.2f}",
            SRC["manifest"] + " (energy_closure_definition)")
    it = re.search(r"within ([\d.]+) %", ma["iteration_check"])
    reg.num("lewis.ablation.iteration_check_pct", float(it.group(1)), "{:.3f}",
            SRC["manifest"] + " (matched_ablation.iteration_check)")
    L["iteration_check"] = ma["iteration_check"]
    it25 = re.search(r"reproduces a (\d+)-iteration", ma["iteration_check"])
    reg.num("lewis.grid.iterations", int(it25.group(1)), "{}",
            SRC["manifest"] + " (matched_ablation.iteration_check)")

    # the physical case -- Lewis's own reduction sheet
    R = SRC["reduction"]
    geo, raw, der = red["geometry"], red["raw_inputs"], red["derived"]
    ib = red["dimensionless_by_basis"]["inlet_bulk"]
    reg.num("lewis.case.d_m", geo["d_m"], "{:.4f}", R)
    reg.num("lewis.case.L_m", geo["L_heated_m"], "{:.3f}", R)
    reg.num("lewis.case.L_over_d", geo["L_over_d"], "{:.2f}", R)
    reg.num("lewis.case.entry_d", geo["adiabatic_starting_length_diameters"], "{:g}", R)
    reg.num("lewis.case.q_w", der["wall_heat_flux_W_m2"], "{:.1f}", R)
    reg.num("lewis.case.T_in", raw["inlet_bulk_T_C"], "{:.2f}", R)
    reg.num("lewis.case.Vdot", raw["volume_flowrate_L_min"], "{:.4f}", R)
    reg.num("lewis.case.T_exit_calc", der["exit_bulk_T_calculated_C"], "{:.2f}", R)
    reg.num("lewis.case.T_exit_meas", raw["exit_bulk_T_measured_C"], "{:.2f}", R)
    reg.num("lewis.case.rise_calc", der["exit_bulk_T_calculated_C"] - raw["inlet_bulk_T_C"],
            "{:.2f}", R)
    reg.num("lewis.case.energy_balance_pct", der["energy_balance_error_pct"], "{:+.2f}", R)
    reg.num("lewis.case.Gr_q", ib["Gr_q_heat_flux_based"], "{:d}", R)
    reg.num("lewis.case.k_inlet", red["property_bases"]["inlet_bulk"]["k"], "{:.4f}", R)

    # mesh: the gravity-on grid pair, committed
    G = SRC["grid"]
    gst = grid["stations"]
    meshes = sorted({k[3:] for k in gst[0] if re.fullmatch(r"Nu_\d+x\d+", k)},
                    key=lambda m: int(m.split("x")[0]))
    L["grid"] = [{"x": g["x_over_d"], "coarse": g[f"Nu_{meshes[0]}"], "fine": g[f"Nu_{meshes[1]}"],
                  "change": g["grid_change_pct"], "ok": g["grid_converged_1pct"]} for g in gst]
    L["grid_meshes"] = [m.replace("x", "×") for m in meshes]
    conv = [g for g in gst if g["grid_converged_1pct"]]
    reg.num("lewis.grid.meshes", " and ".join(L["grid_meshes"]), "{}", G)
    reg.num("lewis.grid.criterion_pct", grid["grid_convergence_criterion_pct"], "{:g}", G)
    reg.num("lewis.grid.n_converged", len(conv), "{}", G)
    reg.num("lewis.grid.n_stations", len(gst), "{}", G)
    reg.num("lewis.grid.band_from", min(g["x_over_d"] for g in conv), "{:.2f}", G)
    reg.num("lewis.grid.band_to", max(g["x_over_d"] for g in conv), "{:.2f}", G)
    reg.num("lewis.grid.max_change_in_band_pct", max(abs(g["grid_change_pct"]) for g in conv),
            "{:.2f}", G)
    ent = [g for g in gst if not g["grid_converged_1pct"]]
    reg.num("lewis.grid.entrance_stations", ", ".join(f"{g['x_over_d']:g}" for g in ent), "{}", G)
    reg.num("lewis.grid.energy_pct", grid["energy_closure_pct"], "{:+.2f}", G)
    reg.num("lewis.grid.cfd_vs_measurement_max_in_band_pct",
            max(abs(g["cfd_vs_experiment_pct"]) for g in conv), "{:.1f}", G)
    vp = [abs(g["cfd_vs_prediction_pct"]) for g in gst if "cfd_vs_prediction_pct" in g]
    reg.num("lewis.grid.cfd_vs_lewis_prediction_range_pct", f"{min(vp):.1f}–{max(vp):.1f}", "{}",
            G)
    # two extraction paths: the grid pair reads the nearest cell centre
    # (cfd/compare_lewis_vp.py); the stress test interpolates between cell centres
    # (cfd/lewis_head_to_head.py:lewis_nu). Committed gravity-on profiles, compared:
    xd = {g["x_over_d"]: 100 * abs(on_cfd[g["x_over_d"]] / g[f"Nu_{meshes[1]}"] - 1) for g in gst}
    reg.num("lewis.extraction.max_diff_grid_band_pct",
            max(xd[g["x_over_d"]] for g in conv), "{:.2f}", f"{G} + {P}")
    reg.num("lewis.extraction.max_diff_downstream_pct",
            max(xd[x] for x in L["downstream"]), "{:.2f}", f"{G} + {P}")
    reg.num("lewis.extraction.diff_entrance", "; ".join(
        f"x/D {g['x_over_d']:g}: {xd[g['x_over_d']]:.1f} %" for g in ent), "{}", f"{G} + {P}")

    # the lower operating percentiles
    for p, v in pre["in_sample_alarm_rate_by_pct"].items():
        reg.num(f"lewis.M.in_sample_alarm_p{p}_pct", 100 * v, "{:.1f}", SRC["predeclared"])
    L["alarm_pcts"] = list(pre["in_sample_alarm_rate_by_pct"])
    reg.num("lewis.lowpct.p75_rows_firing_xd50_100_pct",
            100 * low["pct_75"]["by_x_over_D"]["50-100"], "{:.0f}", SRC["lowpct"])
    reg.num("lewis.lowpct.p75_rows_firing_xd0_10_pct",
            100 * low["pct_75"]["by_x_over_D"]["0-10"], "{:.0f}", SRC["lowpct"])
    L["criteria"] = pre["predeclared_criteria"]
    return L


# ── the seven-vehicle benchmark, as banked ───────────────────────────────────

BENCH_ORDER = ["naca_tn1451", "casper_hypersonic_transition", "jin_sco2_buoyancy",
               "velazquez_sco2", "dirker_water", "marineau_hypersonic_transition", "forrest"]


def compute_benchmark(reg: _Reg) -> dict:
    from physmap.benchmarks import registry as R
    m = _load("matrix")
    rows = {}
    for c in m["cells"]:
        v = R.get(c["vehicle_id"])
        vid = c["vehicle_id"]
        rows[vid] = {"vehicle": vid, "domain": c["domain"], "failure_var": c["failure_var"],
                     "observability": c["failure_observability"],
                     "outcome": c["empirical_outcome"], "n_train": c["n_train"],
                     "n_test": c["n_test"], "redistribution": v.redistribution.value,
                     "quality": v.quality.value}
        for f in ("observability", "outcome"):
            reg.num(f"bench.{vid}.{f}", rows[vid][f], "{}", SRC["matrix"])
        reg.num(f"bench.{vid}.n_train", c["n_train"], "{}", SRC["matrix"])
        reg.num(f"bench.{vid}.n_test", c["n_test"], "{}", SRC["matrix"])
        # what the closure check adds, at the shipped reference percentile -- per vehicle,
        # as counts of rows; never pooled
        ref = (c.get("per_pct") or {}).get(str(int(c.get("ref_pct") or 0)))
        rows[vid]["ref"] = ref
        src = f"{SRC['matrix']} (per_pct at the reference percentile)"
        if ref:
            reg.num(f"bench.{vid}.ref_caught_only", ref["clean_lift"], "{}", src)
            reg.num(f"bench.{vid}.ref_wrong", ref["n_wrong"], "{}", src)
            reg.num(f"bench.{vid}.ref_caught_of_wrong",
                    f"{ref['clean_lift']} of {ref['n_wrong']}", "{}", src)
            reg.num(f"bench.{vid}.ref_flagged_right", ref["misaligned"], "{}", src)
    reg.num("bench.ref_pct", int(next(c["ref_pct"] for c in m["cells"] if c.get("ref_pct"))),
            "{}", SRC["matrix"])
    naca = next(c for c in m["cells"] if c["vehicle_id"] == "naca_tn1451")
    for f in ("ref_n_baseline_fired", "ref_n_distance_fired", "ref_n_gp_var_fired",
              "ref_n_corpus_fired"):
        reg.num(f"bench.naca_tn1451.{f}", naca[f], "{}", SRC["matrix"])
    reg.num("bench.n_vehicles", len(rows), "{}", SRC["matrix"])
    for oc in ("PHYSMAP_WINS", "PARTIAL", "BASELINE_VISIBLE", "DO_NO_HARM"):
        reg.num(f"bench.count_{oc}", sum(1 for r in rows.values() if r["outcome"] == oc), "{}",
                SRC["matrix"])
    # the home baseline beside each count: derived, never in place of the bank
    hsrc = SRC["home"]
    home = _load("home")
    for c in home["cells"]:
        vid = c["vehicle_id"]
        rows[vid]["home"] = c
        h, dp = c["home_held_out"], c["deployment"]
        reg.num(f"bench.{vid}.home_kind", "in-sample fit error, with a held-out refit"
                if c["home_in_sample"] else "held-out home error", "{}", hsrc)
        reg.num(f"bench.{vid}.home_heldout", f"{h['n_wrong']} of {h['n']}", "{}", hsrc)
        reg.num(f"bench.{vid}.home_heldout_pct", round(100 * h["n_wrong"] / h["n"]), "{}", hsrc)
        if c["home_in_sample"]:
            s = c["home_in_sample"]
            reg.num(f"bench.{vid}.home_insample", f"{s['n_wrong']} of {s['n']}", "{}", hsrc)
            reg.num(f"bench.{vid}.home_insample_pct", round(100 * s["n_wrong"] / s["n"]), "{}",
                    hsrc)
        elif c["home_inside_validated_range"] is not None:
            reg.num(f"bench.{vid}.home_inside_range",
                    f"{c['home_inside_validated_range']} of {h['n']}", "{}", hsrc)
        reg.num(f"bench.{vid}.deploy_wrong", f"{dp['n_wrong']} of {dp['n']}", "{}", hsrc)
        reg.num(f"bench.{vid}.deploy_pct", round(100 * dp["n_wrong"] / dp["n"]), "{}", hsrc)
        reg.num(f"bench.{vid}.blind_spot", "yes" if c["supports_blind_spot"] else "no", "{}", hsrc)
        reg.num(f"bench.{vid}.fisher_p", _p(c["fisher_p"]), "{}", hsrc)
    reg.num("bench.home_alpha", 0.05, "{:g}", hsrc)
    reg.num("bench.home_supported", sum(c["supports_blind_spot"] for c in home["cells"]), "{}",
            hsrc)
    # the architecture axis: three model types per flagged vehicle, each gated first
    asrc = SRC["axis"]
    axis = _load("axis")
    ref = str(axis["reference_pct"])
    for c in axis["cells"]:
        key = f"arch.{c['vehicle_id']}.{c['architecture']}"
        reg.num(key, f"{c['clean_lift_by_pct'][ref]} of {c['gate2_n_wrong_in_deploy']}"
                if c["outcome"] == "TRAINABLE" else "fails gate", "{}", asrc)
    reg.num("arch.n_vehicles", len(axis["vehicles"]), "{}", asrc)
    reg.num("arch.n_testable", sum(len(a["trainable_architectures"]) >= 2
                                   for a in axis["agreement"].values()), "{}", asrc)
    reg.num("arch.casper_n_pass",
            len(axis["agreement"]["casper_hypersonic_transition"]["trainable_architectures"]),
            "{}", asrc)
    return {"rows": [rows[v] for v in BENCH_ORDER if v in rows],
            "all_guards_passed": m["all_guards_passed"], "axis": axis}


def _p(p: float) -> str:
    """A p-value as the home-baseline report prints it."""
    return f"{p:.1g}" if p < 0.01 else f"{p:.2g}"


# ── NACA: the example's own computation, on its committed fixture ────────────

def compute_naca(reg: _Reg) -> dict:
    import numpy as np
    from physmap import ColumnMap, CredibilityGuardrail, DetectorKind, Regime
    import warnings
    ex = runpy.run_path(str(REPO / SRC["naca_example"]), run_name="talk_package")
    rows = ex["load"]()
    coords, cut = ex["COORDS"], ex["FULLY_DEVELOPED"]
    train = [r for r in rows if r["x_over_D"] >= cut]
    test = [r for r in rows if r["x_over_D"] < cut]
    g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr"], regime=Regime.ENTRANCE_REGION_PIPE)
    with warnings.catch_warnings():   # sklearn's GP convergence chatter, as in the example
        warnings.simplefilter("ignore")
        g.fit(np.array([[r[c] for c in coords] for r in train]),
              train_y=np.array([r["Nu_meas"] for r in train]), columns=ColumnMap(inputs=coords))
        res = g.assess(np.array([[r[c] for c in coords] for r in test]),
                       columns=ColumnMap(inputs=coords))
    for r, a in zip(test, res):
        r["closure"] = bool(a.signals[DetectorKind.CLOSURE_VALIDITY].fired)
        r["novelty"] = bool(a.signals[DetectorKind.NOVELTY_DENSITY].fired)
        r["gp"] = bool(a.signals[DetectorKind.GP_VARIANCE].fired)
    src = f"{SRC['naca_example']} on {SRC['naca']}"
    reg.num("naca.n_entrance", len(test), "{}", src)
    reg.num("naca.n_training", len(train), "{}", src)
    reg.num("naca.closure_fired", sum(r["closure"] for r in test), "{}", src)
    reg.num("naca.novelty_fired", sum(r["novelty"] for r in test), "{}", src)
    reg.num("naca.gp_fired", sum(r["gp"] for r in test), "{}", src)
    reg.num("naca.either_input_based_fired", sum(r["novelty"] or r["gp"] for r in test), "{}",
            src)
    reg.num("naca.bound", cut, "{:g}", src)
    reg.num("naca.n_Re_curves", len({r["Re"] for r in rows}), "{}", SRC["naca"])
    reg.num("naca.entrance_positions_per_curve", len({r["x_over_D"] for r in test}), "{}",
            SRC["naca"])
    reg.num("naca.Pr", sorted({r["Pr"] for r in rows})[0], "{:.2f}", SRC["naca"])
    # where gnielinski-1976 actually fails, at the benchmark's own NACA threshold
    from scipy.stats import fisher_exact
    from physmap.benchmarks.benchmark_v0_4 import bench_spec_from_config
    from physmap.closures.registry import get_closure
    from physmap.substrate.vehicle_config import load_named_vehicle
    thr = bench_spec_from_config(load_named_vehicle("naca_tn1451")).calib.lift_threshold_pct
    gn = get_closure("gnielinski-1976")
    for r in rows:
        pred = float(gn.fn(Re=np.array([r["Re"]]), Pr=np.array([r["Pr"]]))[0])
        r["gn_err"] = abs(pred - r["Nu_meas"]) / r["Nu_meas"] * 100.0
    hw = sum(r["gn_err"] > thr for r in train)
    wrong = [r for r in test if r["gn_err"] > thr]
    worst = max(test, key=lambda r: r["gn_err"])
    _, pv = fisher_exact([[len(wrong), len(test) - len(wrong)], [hw, len(train) - hw]],
                         alternative="greater")
    reg.num("naca.threshold_pct", thr, "{:.1f}", "data/vehicles/naca_tn1451.yaml")
    reg.num("naca.gn_home_wrong", f"{hw} of {len(train)}", "{}", src)
    reg.num("naca.gn_entrance_wrong", f"{len(wrong)} of {len(test)}", "{}", src)
    reg.num("naca.gn_entrance_max_xd", max(r["x_over_D"] for r in wrong), "{:g}", src)
    reg.num("naca.gn_worst_pct", worst["gn_err"], "{:.0f}", src)
    reg.num("naca.gn_worst_xd", worst["x_over_D"], "{:g}", src)
    reg.num("naca.gn_fisher_p", pv, "{:.1g}", src)
    reg.num("naca.gn_flagged_right",
            sum(1 for r in test if r["closure"] and r["gn_err"] <= thr), "{}", src)
    return {"train": train, "test": test, "cut": cut}


# ── figure data (shared by build and check; no matplotlib) ───────────────────

def control_table(reg: _Reg, L: dict):
    d = reg.d
    header = ["", "surrogate error", "input-based OOD detector", "PhysMAP materiality",
              f"illustrative θ = {d('lewis.theta_illustrative')}"]
    rows = [
        ["gravity off — the control (CFD)",
         f"within {d('lewis.control_error_max_abs_pct')} % at every comparable station",
         f"distance {d('lewis.ood.min_distance_comparable')}–"
         f"{d('lewis.ood.max_distance_comparable')} against "
         f"{d('lewis.ood.threshold_distance')}: quiet at p{REF_PCT}",
         "0 at every station", "flags nothing"],
        ["gravity on — Lewis's measurement",
         f"{d('lewis.downstream_error_range_pct')} % at x/D {d('lewis.downstream_stations')}",
         "the same scores, at every station and every percentile",
         f"{d('lewis.materiality_on_min')} to {d('lewis.materiality_on_max')}, "
         "rising down the tube",
         f"would flag x/D {d('lewis.flagged_at_illustrative')}"],
    ]
    return header, rows


def table_rows(name: str, reg: _Reg, L: dict, Bn: dict, N: dict):
    d = lambda k: reg.items[k]["display"]  # noqa: E731
    st = L["stations"]
    if name == "lewis_1_input_contract":
        c = L["contract"]
        return ["item", "value"], [
            ["surrogate_inputs", "; ".join(c["surrogate_inputs"])],
            ["ood_detector_inputs", "; ".join(c["ood_detector_inputs"])],
            ["withheld_from_both", "; ".join(c["withheld_from_both"])],
            ["deployment_Re", d("lewis.deploy_Re")], ["deployment_Pr", d("lewis.deploy_Pr")],
            ["deployment_stations", d("lewis.n_stations")],
            ["every_visible_deployment_input_is_a_training_input", L["exact_overlap"]],
            ["training_runs", d("lewis.M.training_runs")],
            ["training_rows", d("lewis.M.training_rows")],
            ["training_Re_levels", d("lewis.train.Re_levels")],
            ["training_inlet_T_C_levels", d("lewis.train.T_in_levels")],
            ["physmap_calibration_window", L["window"]],
            ["Ri_gravity_on", d("lewis.Ri_gravity_on")]]
    if name == "lewis_2_control_vs_gravity_on":
        return (["x_over_D", "comparable", "Nu_surrogate", "Nu_control_gravity_off_CFD",
                 "Nu_measured_gravity_on", "surrogate_error_vs_control_pct",
                 "surrogate_error_vs_measurement_pct", "ood_distance_score",
                 "ood_gp_variance_score", f"ood_at_p{REF_PCT}", "materiality_gravity_off",
                 "materiality_gravity_on"],
                [[f"{s['x']:g}", s["comparable"], d(f"{s['k']}.Nu_surrogate"),
                  d(f"{s['k']}.Nu_control"), d(f"{s['k']}.Nu_experiment"),
                  d(f"{s['k']}.control_error_pct"), d(f"{s['k']}.experimental_error_pct"),
                  d(f"{s['k']}.ood_distance"), d(f"{s['k']}.ood_gp"), d(f"{s['k']}.ood_p99"),
                  d(f"{s['k']}.materiality_off"), d(f"{s['k']}.materiality_on")] for s in st])
    if name == "lewis_3_ood_identical":
        return (["x_over_D", "distance_gravity_off", "distance_gravity_on", "gp_gravity_off",
                 "gp_gravity_on", "identical"],
                [[f"{s['x']:g}", repr(s["dist_off"]), repr(s["dist_on"]), repr(s["gp_off"]),
                  repr(s["gp_on"]), s["dist_off"] == s["dist_on"] and s["gp_off"] == s["gp_on"]]
                 for s in st])
    if name == "lewis_4_materiality":
        rows = [[f"{s['x']:g}", s["comparable"], d(f"{s['k']}.materiality_off"),
                 d(f"{s['k']}.materiality_on")] for s in st]
        rows += [[f"stations flagged at theta={d('lewis.theta_%.2f' % th)} (illustrative)", "",
                  "0", d(f"lewis.flags_on_at_theta_{th:.2f}")] for th in THETAS_SHOWN]
        return ["x_over_D", "comparable", "materiality_gravity_off", "materiality_gravity_on"], rows
    if name == "lewis_5_control_table":
        header, rows = control_table(reg, L)
        return ["state"] + header[1:], rows
    if name == "bench_1_naca_entrance":
        return (["x_over_D", "Re", "Nu_measured", "role", "closure_validity_fired",
                 "novelty_density_fired", "gp_variance_fired"],
                [[r["x_over_D"], r["Re"], r["Nu_meas"], "training", "", "", ""]
                 for r in N["train"]] +
                [[r["x_over_D"], r["Re"], r["Nu_meas"], "entrance", r["closure"], r["novelty"],
                  r["gp"]] for r in N["test"]])
    if name == "bench_3_what_physmap_adds":
        byv = {r["vehicle"]: r for r in Bn["rows"]}
        out = []
        for group, vids in BENCH_GROUPS:
            for vid in vids:
                r = byv[vid]
                ref = r.get("ref")
                out.append([vid, group, r["observability"],
                            ref["n_wrong"] if ref else "", ref["clean_lift"] if ref else "",
                            ref["misaligned"] if ref else "",
                            "" if ref else "not tested: no detector fit"])
        return (["vehicle", "group", "failure_variable_observability",
                 f"wrong_predictions_p{d('bench.ref_pct')}",
                 f"caught_only_by_physmap_p{d('bench.ref_pct')}",
                 f"right_predictions_flagged_p{d('bench.ref_pct')}", "note"], out)
    if name == "bench_4_home_baseline":
        out = []
        for vid in HOME_ORDER:
            c = next(r for r in Bn["rows"] if r["vehicle"] == vid)["home"]
            h, dp, s = c["home_held_out"], c["deployment"], c["home_in_sample"]
            out.append([vid, c["home_evaluation_provenance"], h["n"], h["n_wrong"],
                        d(f"bench.{vid}.home_heldout_pct"),
                        "" if s is None else s["n_wrong"], dp["n"], dp["n_wrong"],
                        d(f"bench.{vid}.deploy_pct"), d(f"bench.{vid}.fisher_p"),
                        d(f"bench.{vid}.blind_spot"), c["reason"]])
        return (["vehicle", "home_evaluation_provenance", "home_points", "home_wrong_held_out",
                 "home_error_rate_pct", "home_wrong_in_sample", "deployment_points",
                 "deployment_wrong", "deployment_error_rate_pct", "fisher_p_one_sided",
                 "supports_deployment_induced_blind_spot", "reason"], out)
    if name == "bench_2_seven_vehicles":
        return (["vehicle", "domain", "failure_variable", "observability", "outcome",
                 "redistribution", "data_quality", "n_train_rows", "n_test_rows"],
                [[r["vehicle"], r["domain"], r["failure_var"], r["observability"], r["outcome"],
                  r["redistribution"], r["quality"], r["n_train"], r["n_test"]]
                 for r in Bn["rows"]])
    raise KeyError(name)


FIGURES = {
    "lewis_1_input_contract": "Input contract: what the surrogate and the OOD detector see",
    "lewis_2_control_vs_gravity_on":
        "Gravity-off control against gravity-on measurement, by position",
    "lewis_3_ood_identical": "The input-based OOD scores are identical in both gravity states",
    "lewis_4_materiality": "Continuous materiality by position, and what θ would change",
    "lewis_5_control_table": "The control table",
    "bench_1_naca_entrance":
        "The x/D entrance region: closure validity fires, both input-based detectors silent",
    "bench_2_seven_vehicles": "Seven-vehicle benchmark: closure validity and observability",
    "bench_3_what_physmap_adds": "What PhysMAP adds to input-based OOD detection",
    "bench_4_home_baseline": "The home baseline behind each count",
}

# Supported readings first, then the rest, each in benchmark order.
HOME_ORDER = ["casper_hypersonic_transition", "dirker_water", "naca_tn1451",
              "jin_sco2_buoyancy", "velazquez_sco2", "marineau_hypersonic_transition", "forrest"]

# The seven vehicles, grouped by whether the variable that breaks the surrogate is visible to
# the input-based detectors -- the axis the result turns on.
BENCH_GROUPS = (
    ("cause hidden from the inputs", ("naca_tn1451", "casper_hypersonic_transition",
                                      "jin_sco2_buoyancy")),
    ("cause partly visible", ("velazquez_sco2", "dirker_water")),
    ("cause visible to the inputs", ("marineau_hypersonic_transition", "forrest")),
)
BENCH_NAMES = {
    "naca_tn1451": "NACA TN-1451 · pipe entrance",
    "casper_hypersonic_transition": "Casper · hypersonic transition",
    "jin_sco2_buoyancy": "Jin · sCO2, vertical tube",
    "velazquez_sco2": "Velazquez · sCO2 property variation",
    "dirker_water": "Dirker · water, horizontal tube",
    "marineau_hypersonic_transition": "Marineau · hypersonic transition",
    "forrest": "Forrest · rectangular channel",
}


# ── figures ───────────────────────────────────────────────────────────────────
# Palette: the dataviz reference instance, validated with its script (slot 1 blue + slot 2
# orange: every check passes). Blue = gravity off, orange = gravity on, in EVERY Lewis figure.
# The surrogate is neutral ink. Gridlines are solid hairlines; the only dashed line anywhere is
# the illustrative threshold, because it is one. Light theme only: these are slide images.

INK = {"surface": "#fcfcfb", "primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781",
       "grid": "#e1e0d9", "axis": "#c3c2b7", "panel": "#f1f0ec", "off": "#2a78d6",
       "on": "#eb6834"}
W, H = 10.0, 5.625             # 16:9; PNG at 192 dpi = 1920 x 1080
THETA_DASH = (0, (5, 4))


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 10, "axes.titlesize": 10.5, "axes.labelsize": 9.5,
        "axes.edgecolor": INK["axis"], "axes.linewidth": 0.8, "axes.facecolor": INK["surface"],
        "figure.facecolor": INK["surface"], "savefig.facecolor": INK["surface"],
        "axes.labelcolor": INK["secondary"], "xtick.color": INK["secondary"],
        "ytick.color": INK["secondary"], "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "text.color": INK["primary"], "axes.titlecolor": INK["primary"],
        "axes.grid": True, "grid.color": INK["grid"], "grid.linewidth": 0.6,
        "grid.linestyle": "-", "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "legend.fontsize": 8.5, "svg.fonttype": "none",
        "svg.hashsalt": "physmap-talk", "lines.linewidth": 2.0, "lines.markersize": 7,
        "axes.axisbelow": True,
    })
    return plt


def _save(fig, name: str, source: str):
    fig.text(0.012, 0.012, f"Source: {source}", fontsize=7, color=INK["muted"], ha="left",
             va="bottom")
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.svg", metadata={"Date": None})
    fig.savefig(FIG / f"{name}.png", dpi=192)
    import matplotlib.pyplot as plt
    plt.close(fig)


def _csv_text(header: list, rows: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def _logx(ax):
    ax.set_xscale("log")
    ax.set_xlim(0.2, 250)
    ax.set_xticks([0.3, 1, 3, 10, 30, 100])
    ax.set_xticklabels(["0.3", "1", "3", "10", "30", "100"])
    ax.minorticks_off()


def _marks(ax, st, key, color, size=7, zorder=3):
    for s in st:
        ax.plot(s["x"], s[key], "o", ms=size, mec=color, mew=1.6, zorder=zorder,
                mfc=color if s["comparable"] else INK["surface"])


def fig_input_contract(reg: _Reg, L: dict):
    plt = _mpl()
    from matplotlib.patches import FancyBboxPatch
    d = reg.d
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56.25)
    ax.axis("off")

    def box(x, y, w, h, title, body, edge=INK["axis"], fill="#ffffff", lw=1.1):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.0",
                                    linewidth=lw, edgecolor=edge, facecolor=fill))
        ax.text(x + 1.6, y + h - 1.5, title, ha="left", va="top", fontsize=11, weight="bold")
        ax.text(x + 1.6, y + h - 5.4, body, ha="left", va="top", fontsize=9.3,
                color=INK["secondary"], linespacing=1.45)

    def arrow(p0, p1):
        ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(
            arrowstyle="-|>", color=INK["secondary"], lw=1.2, shrinkA=0, shrinkB=0))

    ax.text(2, 54, "Lewis 35A stress test — the input contract", fontsize=15, weight="bold",
            va="top")
    ax.text(2, 49.4, "The surrogate and the input-based OOD detector see the same three inputs. "
            "Gravity is not one of them.", fontsize=10.5, color=INK["secondary"], va="top")

    box(2, 24.5, 28, 20, "Training: forced convection",
        f"{d('lewis.M.training_runs')} gravity-off CFD runs, "
        f"{d('lewis.M.training_rows')} rows\n"
        f"Re {d('lewis.train.Re_levels')}\n"
        f"× inlet {d('lewis.train.T_in_levels')} °C\n"
        "+ one run at 35A's own operating point\n"
        "gravity never varied")
    box(2, 4.5, 28, 16.5, "Deployment: Lewis Test 35A",
        f"Re {d('lewis.deploy_Re')}, Pr {d('lewis.deploy_Pr')}\n"
        f"x/D at Lewis's {d('lewis.n_stations')} stations\n"
        "every visible input is a training input")
    ax.plot([4.3], [7.4], "o", ms=8, color=INK["off"])
    ax.text(5.7, 7.4, "gravity off (control)", fontsize=9, va="center", color=INK["secondary"])
    ax.plot([18.0], [7.4], "o", ms=8, color=INK["on"])
    ax.text(19.4, 7.4, "gravity on", fontsize=9, va="center", color=INK["secondary"])

    box(38, 24.5, 22, 20, "Visible inputs", "Re\nPr\nx_over_D", edge=INK["secondary"], lw=1.5)
    box(38, 4.5, 22, 16.5, "Not an input to either",
        "gravity\nRi (Richardson number)\nGr (Grashof number)\nwall heat flux",
        edge=INK["muted"], fill=INK["panel"])

    box(68, 35.5, 30, 10, "Surrogate", "Gaussian process, predicts local Nu")
    box(68, 22.5, 30, 10, "Input-based OOD detector",
        "the seven-vehicle benchmark's own:\ndistance + GP variance, unchanged")
    box(68, 4.5, 30, 15, "PhysMAP",
        f"reads the mechanism: Ri = {d('lewis.Ri_gravity_on')} with gravity\n"
        "on, outside the training's Ri = 0;\n"
        "materiality from a matched CFD pair,\ngravity on against gravity off")

    arrow((30.4, 36), (37.6, 36))
    arrow((30.4, 15.5), (37.6, 27.5))
    arrow((60.4, 38.5), (67.6, 40.5))
    arrow((60.4, 30.5), (67.6, 27.5))
    arrow((60.4, 12.75), (67.6, 12.75))
    _save(fig, "lewis_1_input_contract",
          f"{SRC['bank']} (input_contract, physmap); {SRC['profiles']}")


def fig_control_vs_gravity_on(reg: _Reg, L: dict):
    plt = _mpl()
    from matplotlib.lines import Line2D
    d = reg.d
    st = L["stations"]
    xs = [s["x"] for s in st]
    fig, axs = plt.subplots(2, 2, figsize=(W, H), sharex=True)
    fig.subplots_adjust(left=0.065, right=0.985, top=0.80, bottom=0.12, hspace=0.42, wspace=0.2)
    fig.text(0.012, 0.975, "Lewis 35A, design M — the same visible inputs, gravity off and on",
             fontsize=13, weight="bold", va="top")
    handles = [Line2D([], [], color=INK["primary"], lw=2, label="surrogate prediction"),
               Line2D([], [], marker="o", ls="", ms=7, color=INK["off"],
                      label="gravity off: CFD, the control"),
               Line2D([], [], marker="o", ls="", ms=7, color=INK["on"],
                      label="gravity on: Lewis's measurement (materiality: matched CFD pair)"),
               Line2D([], [], marker="o", ls="", ms=7, mfc=INK["surface"], mec=INK["muted"],
                      mew=1.6, label="station Lewis disowns")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.005, 0.915), ncol=4,
               fontsize=8.5, handletextpad=0.4, columnspacing=1.4)

    ax = axs[0, 0]
    ax.plot(xs, [s["pred"] for s in st], "-", color=INK["primary"], lw=1.8, zorder=2)
    _marks(ax, st, "Nu_ctl", INK["off"])
    _marks(ax, st, "Nu_exp", INK["on"])
    ax.set_yscale("log")
    ax.set_ylim(5, 80)
    ax.set_yticks([5, 10, 20, 40, 80])
    ax.set_yticklabels(["5", "10", "20", "40", "80"])
    ax.minorticks_off()
    ax.set_title("Local Nu", loc="left", weight="bold")

    ax = axs[0, 1]
    ax.axhline(0, color=INK["axis"], lw=0.9, zorder=1)
    _marks(ax, st, "ctl", INK["off"])
    top = 20
    for s in st:
        off_scale = s["exp"] > top
        ax.plot(s["x"], min(s["exp"], top), "^" if off_scale else "o", ms=7, mec=INK["on"],
                mew=1.6, mfc=INK["on"] if s["comparable"] else INK["surface"], zorder=3,
                clip_on=False)
        if off_scale:
            ax.annotate(f"{d(s['k'] + '.experimental_error_pct')} %, off scale",
                        (s["x"], top), xytext=(9, -2), textcoords="offset points", fontsize=7.5,
                        color=INK["secondary"], va="top")
    ax.text(0.02, 0.05, f"gravity on, x/D {d('lewis.downstream_stations')}: "
            f"{d('lewis.downstream_error_range_pct')} % off the measurement",
            transform=ax.transAxes, fontsize=7.8, color=INK["primary"], va="bottom")
    ax.set_ylim(-34, top)
    ax.set_ylabel("%")
    ax.set_title("Surrogate error", loc="left", weight="bold")
    ax.text(0.985, 0.95, f"against the control: within {d('lewis.control_error_max_abs_pct')} %",
            transform=ax.transAxes, ha="right", va="top", fontsize=7.8, color=INK["secondary"])

    ax = axs[1, 0]
    thr = L["thr_distance"]
    ax.axhline(thr, color=INK["secondary"], lw=1.0)
    ax.text(0.22, thr + 0.012, f"fires above {d('lewis.ood.threshold_distance')} "
            f"(benchmark reference percentile {REF_PCT})", fontsize=7.8,
            color=INK["secondary"], va="bottom")
    for s in st:
        ax.plot(s["x"], s["dist_off"], "o", ms=10, mfc=INK["surface"], mec=INK["off"], mew=1.8,
                zorder=3)
        ax.plot(s["x"], s["dist_on"], "o", ms=4.2, color=INK["on"], zorder=4)
    ax.set_ylim(0, 0.5)
    ax.set_title("Input-based OOD detector: distance score", loc="left", weight="bold")
    ax.text(0.22, 0.29, "gravity off (ring), gravity on (dot):\nthe same at every station",
            fontsize=7.8, color=INK["secondary"], va="center")
    ax.text(0.985, 0.62, f"GP variance: max {d('lewis.ood.max_gp_all')},\n"
            f"fires above {d('lewis.ood.threshold_gp')}", transform=ax.transAxes, ha="right",
            va="top", fontsize=7.8, color=INK["secondary"])

    ax = axs[1, 1]
    _marks(ax, st, "m_off", INK["off"])
    _marks(ax, st, "m_on", INK["on"])
    ax.set_ylim(-0.012, 0.25)
    ax.set_title("PhysMAP materiality", loc="left", weight="bold")
    mx = next(s for s in st if s["x"] == L["mat_max_x"])
    ax.annotate(d("lewis.materiality_on_max"), (mx["x"], mx["m_on"]), xytext=(-10, 3),
                textcoords="offset points", ha="right", fontsize=8)
    ax.text(0.22, 0.2, "gravity off: 0 everywhere —\nno buoyancy to remove",
            fontsize=7.8, color=INK["secondary"], va="center")
    for a in axs[1]:
        _logx(a)
        a.set_xlabel("x/D from the start of heating (log scale)")
    _save(fig, "lewis_2_control_vs_gravity_on",
          f"{SRC['bank']} (headline_design_M.stations); plotted values: "
          "docs/talk/figures/data/lewis_2_control_vs_gravity_on.csv")


def fig_ood_identical(reg: _Reg, L: dict):
    plt = _mpl()
    d = reg.d
    st = L["stations"]
    fig, axs = plt.subplots(1, 2, figsize=(W, H))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.79, bottom=0.12, wspace=0.28)
    fig.text(0.012, 0.975, "The input-based OOD scores do not change when gravity is switched on",
             fontsize=13, weight="bold", va="top")
    fig.text(0.012, 0.905, f"All {d('lewis.n_stations')} stations lie on the diagonal. Largest "
             f"difference between the two states, over every score and every operating "
             f"percentile: {d('lewis.ood.max_abs_difference_on_vs_off')}.",
             fontsize=9.5, color=INK["secondary"], va="top")
    for ax, k_on, k_off, thr, tk, name in (
            (axs[0], "dist_on", "dist_off", L["thr_distance"], "lewis.ood.threshold_distance",
             "distance-to-training score"),
            (axs[1], "gp_on", "gp_off", L["thr_gp"], "lewis.ood.threshold_gp",
             "GP-variance score")):
        hi = thr * 1.18
        ax.fill_between([thr, hi], 0, hi, color=INK["panel"], lw=0, zorder=0)
        ax.fill_between([0, thr], thr, hi, color=INK["panel"], lw=0, zorder=0)
        ax.plot([0, hi], [0, hi], "-", color=INK["axis"], lw=1.0, zorder=1)
        ax.axvline(thr, color=INK["secondary"], lw=0.9)
        ax.axhline(thr, color=INK["secondary"], lw=0.9)
        ax.text(thr * 0.03, thr * 1.03, f"fires above {d(tk)} (p{REF_PCT})", fontsize=7.8,
                color=INK["secondary"], va="bottom")
        ax.plot([s[k_off] for s in st], [s[k_on] for s in st], "o", ms=7, mfc=INK["surface"],
                mec=INK["primary"], mew=1.5, zorder=3)
        ax.set_xlim(0, hi)
        ax.set_ylim(0, hi)
        ax.set_aspect("equal")
        ax.set_xlabel(f"{name}, gravity OFF")
        ax.set_ylabel(f"{name}, gravity ON")
        ax.set_title(name, loc="left", weight="bold")
    _save(fig, "lewis_3_ood_identical",
          f"{SRC['bank']} (ood_gravity_on vs ood_gravity_off, every percentile); plotted values: "
          "docs/talk/figures/data/lewis_3_ood_identical.csv")


def fig_materiality(reg: _Reg, L: dict):
    plt = _mpl()
    from matplotlib.lines import Line2D
    d = reg.d
    st = L["stations"]
    comp = [s for s in st if s["comparable"]]
    fig, axs = plt.subplots(1, 2, figsize=(W, H), gridspec_kw={"width_ratios": [1.5, 1]})
    fig.subplots_adjust(left=0.07, right=0.975, top=0.77, bottom=0.12, wspace=0.26)
    fig.text(0.012, 0.975, "PhysMAP materiality is a continuous value — the headline needs no θ",
             fontsize=13, weight="bold", va="top")
    fig.text(0.012, 0.905, f"Gravity off: 0 at every station. Gravity on: "
             f"{d('lewis.materiality_on_min')} to {d('lewis.materiality_on_max')} at the "
             f"comparable stations, growing down the tube.\nθ is unlocked: "
             f"{d('lewis.theta_illustrative')} is drawn for illustration only.",
             fontsize=9.5, color=INK["secondary"], va="top", linespacing=1.4)
    ax = axs[0]
    ax.plot([s["x"] for s in st], [s["m_on"] for s in st], "-", color=INK["on"], lw=1.2,
            alpha=0.55, zorder=2)
    _marks(ax, st, "m_off", INK["off"])
    _marks(ax, st, "m_on", INK["on"])
    th = L["theta"]
    ax.axhline(th, color=INK["secondary"], lw=1.1, ls=THETA_DASH)
    ax.text(0.22, th + 0.005, f"illustrative θ = {d('lewis.theta_illustrative')} "
            "(unlocked — not a verdict)", fontsize=7.8, color=INK["secondary"], va="bottom")
    for s in comp:
        if s["x"] in L["downstream"]:
            ax.annotate(d(s["k"] + ".materiality_on"), (s["x"], s["m_on"]), xytext=(-9, 3),
                        textcoords="offset points", ha="right", fontsize=7.8)
    _logx(ax)
    ax.set_ylim(-0.012, 0.25)
    ax.set_xlabel("x/D from the start of heating (log scale)")
    ax.set_ylabel("materiality = 1 − Nu(gravity off) / Nu(gravity on)")
    ax.set_title("By position", loc="left", weight="bold")
    ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=7, color=INK["on"],
                              label="gravity on"),
                       Line2D([], [], marker="o", ls="", ms=7, color=INK["off"],
                              label="gravity off"),
                       Line2D([], [], marker="o", ls="", ms=7, mfc=INK["surface"],
                              mec=INK["muted"], mew=1.6, label="disowned by Lewis")],
              loc="upper left")
    ax = axs[1]
    thetas = [i / 1000 for i in range(1, 261)]
    ax.step(thetas, [sum(1 for s in comp if s["m_on"] >= t) for t in thetas], where="post",
            color=INK["on"], lw=2.0, label="gravity on")
    ax.step(thetas, [0] * len(thetas), where="post", color=INK["off"], lw=2.0,
            label="gravity off: 0 at every θ")
    ax.axvline(th, color=INK["secondary"], lw=1.1, ls=THETA_DASH)
    ax.text(th + 0.004, len(comp) * 0.5, "illustrative", rotation=90, fontsize=7.8,
            color=INK["secondary"], va="center")
    upto = float(d("lewis.theta_any_flag_up_to"))
    ax.annotate(f"at least one flag\nfor any θ ≤ {d('lewis.theta_any_flag_up_to')}", (upto, 1),
                xytext=(-8, 38), textcoords="offset points", ha="right", fontsize=7.8,
                color=INK["secondary"],
                arrowprops=dict(arrowstyle="-", color=INK["muted"], lw=0.8))
    ax.set_xlim(0, 0.26)
    ax.set_ylim(-0.4, len(comp) + 0.6)
    ax.set_yticks(range(0, len(comp) + 1, 3))
    ax.set_xlabel("θ")
    ax.set_ylabel(f"comparable stations that would flag (of {d('lewis.n_comparable')})")
    ax.set_title("What θ would change", loc="left", weight="bold")
    ax.legend(loc="upper right")
    _save(fig, "lewis_4_materiality",
          f"{SRC['bank']} (materiality_gravity_on/off, threshold_dependence); plotted values: "
          "docs/talk/figures/data/lewis_4_materiality.csv")


def fig_control_table(reg: _Reg, L: dict):
    plt = _mpl()
    header, rows = control_table(reg, L)
    fig = plt.figure(figsize=(W, 3.6))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.012, 0.95, "Lewis 35A, design M — every visible deployment input is a training "
            "input", fontsize=13, weight="bold", va="top")
    xs = [0.012, 0.215, 0.405, 0.605, 0.80]
    wrap = [20, 22, 23, 22, 22]
    for x, h in zip(xs, header):
        ax.text(x, 0.77, h, fontsize=9, weight="bold", color=INK["secondary"], va="top")
    ax.plot([0.012, 0.988], [0.695, 0.695], color=INK["axis"], lw=0.9)
    for i, (r, col) in enumerate(zip(rows, (INK["off"], INK["on"]))):
        y = 0.655 - i * 0.26
        ax.add_patch(plt.Rectangle((0.012, y - 0.2), 0.0045, 0.2, color=col, lw=0))
        for j, (x, cell) in enumerate(zip(xs, r)):
            ax.text(x + (0.012 if j == 0 else 0), y, textwrap.fill(cell, wrap[j]), fontsize=9.3,
                    va="top", linespacing=1.3, weight="bold" if j == 0 else "normal")
    ax.plot([0.012, 0.988], [0.125, 0.125], color=INK["grid"], lw=0.8)
    ax.text(0.012, 0.105, "One run: its stations are not independent cases. No precision, "
            "recall or F1. Only gravity differs between the rows, and gravity is not an input.",
            fontsize=8.3, color=INK["secondary"], va="top")
    _save(fig, "lewis_5_control_table", f"{SRC['bank']}; table: "
          "docs/talk/figures/data/lewis_5_control_table.csv")


def fig_naca(reg: _Reg, N: dict):
    plt = _mpl()
    d = reg.d
    tr, te, cut = N["train"], N["test"], N["cut"]
    fig, ax = plt.subplots(figsize=(W, H))
    fig.subplots_adjust(left=0.07, right=0.69, top=0.8, bottom=0.12)
    fig.text(0.012, 0.975, "The x/D entrance region: a variable the surrogate never had",
             fontsize=13, weight="bold", va="top")
    fig.text(0.012, 0.905, "The surrogate and both input-based detectors see Re and Pr only. "
             "Entrance points have ordinary Re and Pr; only x/D is new,\nand only the closure "
             "check reads it.", fontsize=9.5, color=INK["secondary"], va="top",
             linespacing=1.4)
    ax.axvspan(0.8, cut, color=INK["panel"], lw=0, zorder=0)
    ax.plot([r["x_over_D"] for r in tr], [r["Nu_meas"] for r in tr], "o", ms=6,
            mfc=INK["surface"], mec=INK["muted"], mew=1.4,
            label=f"training: x/D ≥ {d('naca.bound')}, {d('naca.n_training')} points")
    ax.plot([r["x_over_D"] for r in te], [r["Nu_meas"] for r in te], "o", ms=6.5,
            color=INK["primary"],
            label=f"deployment: x/D < {d('naca.bound')}, {d('naca.n_entrance')} points")
    ax.axvline(cut, color=INK["secondary"], lw=1.0)
    ax.text(cut * 1.03, 0.97, f"validated range of the\nclosure (gnielinski-1976)\n"
            f"starts at x/D = {d('naca.bound')}", transform=ax.get_xaxis_transform(),
            fontsize=8, color=INK["secondary"], va="top")
    ax.set_xscale("log")
    ax.set_xlim(0.8, 20)
    ax.set_xticks([1, 2, 5, 10, 20])
    ax.set_xticklabels(["1", "2", "5", "10", "20"])
    ax.minorticks_off()
    ax.set_xlabel("x/D")
    ax.set_ylabel("measured local Nu (NACA TN-1451, Fig 10)")
    fig.legend(*ax.get_legend_handles_labels(), loc="upper left",
               bbox_to_anchor=(0.715, 0.2), fontsize=8.5)
    n = d("naca.n_entrance")
    fig.text(0.72, 0.74, f"Fired, of the {n} entrance points", fontsize=10.5, weight="bold",
             va="top")
    for i, (lab, key) in enumerate((("closure validity (PhysMAP)", "naca.closure_fired"),
                                    ("novelty density (input-based)", "naca.novelty_fired"),
                                    ("GP variance (input-based)", "naca.gp_fired"))):
        y = 0.64 - i * 0.075
        fig.text(0.72, y, lab, fontsize=9.5, color=INK["secondary"], va="center")
        fig.text(0.975, y, d(key), fontsize=12, weight="bold", va="center", ha="right")
    fig.text(0.72, 0.43, "Novelty density and GP variance are the\nguardrail's default "
             "input-based detectors.\nThey see Re and Pr, which look ordinary.\nClosure "
             "validity reads x/D against the\nclosure's validated range.", fontsize=8.5,
             color=INK["secondary"], va="top", linespacing=1.45)
    _save(fig, "bench_1_naca_entrance",
          f"{SRC['naca_example']} on {SRC['naca']}; plotted values: "
          "docs/talk/figures/data/bench_1_naca_entrance.csv")


def fig_seven(reg: _Reg, Bn: dict):
    plt = _mpl()
    d = reg.d
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.012, 0.965, "Seven-vehicle benchmark — closure validity and observability",
            fontsize=13, weight="bold", va="top")
    ax.text(0.012, 0.9, "Is the variable that breaks each surrogate visible to an input-based "
            "detector? Not evidence for causal materiality.\nEach outcome is an observability "
            "class, not a performance rate.", fontsize=9.5, color=INK["secondary"], va="top",
            linespacing=1.4)
    cols = ["vehicle", "domain", "failure variable", "observability", "outcome", "source data"]
    xs = [0.012, 0.255, 0.375, 0.515, 0.635, 0.785]
    y0 = 0.755
    for x, c in zip(xs, cols):
        ax.text(x, y0, c, fontsize=9, weight="bold", color=INK["secondary"], va="top")
    ax.plot([0.012, 0.988], [y0 - 0.05, y0 - 0.05], color=INK["axis"], lw=0.9)
    basis = {"clear": "licensed", "no_licence_facts_basis": "no licence",
             "against_publisher_terms": "against terms"}
    y = y0 - 0.075
    for r in Bn["rows"]:
        vid = r["vehicle"]
        weak = r["quality"] == "triage_only"
        cells = [vid, r["domain"], r["failure_var"], d(f"bench.{vid}.observability"),
                 d(f"bench.{vid}.outcome"),
                 basis.get(r["redistribution"], r["redistribution"]) +
                 ("; TRIAGE ONLY" if weak else "")]
        for x, c in zip(xs, cells):
            ax.text(x, y, c, fontsize=9.3, va="top",
                    color=INK["secondary"] if weak else INK["primary"],
                    style="italic" if weak else "normal")
        y -= 0.056
    ax.plot([0.012, 0.988], [y + 0.022, y + 0.022], color=INK["grid"], lw=0.8)
    ax.text(0.012, y - 0.004,
            "forrest: its own data file calls its values visual estimates for triage only, and "
            f"its cell is degenerate ({d('bench.forrest.n_train')} training row, no detector "
            "fit), so DO_NO_HARM is short-circuited, not earned.\nmarineau: the negative "
            "control, where the input-based baseline already sees the failure variable.   "
            "Counts are data rows, not independent cases.",
            fontsize=8.2, color=INK["secondary"], va="top", linespacing=1.45)
    defs = [("PHYSMAP_WINS", "the failure variable is invisible to the input-based baseline, "
                             "and the closure check caught wrong rows the baseline missed"),
            ("PARTIAL", "the same, with the failure variable partly visible"),
            ("BASELINE_VISIBLE", "the input-based baseline already sees the failure variable"),
            ("DO_NO_HARM", "the failure variable is a surrogate input: the baseline suffices")]
    yy = y - 0.095
    for k, v in defs:
        ax.text(0.012, yy, k, fontsize=8.2, weight="bold", color=INK["secondary"], va="top")
        ax.text(0.15, yy, v, fontsize=8.2, color=INK["secondary"], va="top")
        yy -= 0.033
    _save(fig, "bench_2_seven_vehicles", f"{SRC['matrix']}; physmap.benchmarks.registry; "
          "table: docs/talk/figures/data/bench_2_seven_vehicles.csv")


def fig_what_physmap_adds(reg: _Reg, Bn: dict):
    """Two panels, one measure each, rows grouped by whether the cause is visible to the
    inputs. Aqua marks what PhysMAP catches that the input-based detectors missed; neutral
    ink marks the cost. Counts are printed on every bar: aqua is low-contrast on the surface
    (validator WARN, 2.74:1), and a number beside each mark is the required relief."""
    plt = _mpl()
    d = reg.d
    AQUA = "#1baf7a"
    byv = {r["vehicle"]: r for r in Bn["rows"]}
    ys, labels, heads, y = {}, {}, [], 0.0
    for group, vids in BENCH_GROUPS:
        heads.append((group, y))
        y += 1.0
        for vid in vids:
            ys[vid] = y
            labels[vid] = BENCH_NAMES[vid]
            y += 1.0
        y += 0.35
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, H), sharey=True,
                                 gridspec_kw={"width_ratios": [1.55, 1]})
    fig.subplots_adjust(left=0.265, right=0.975, top=0.74, bottom=0.1, wspace=0.08)
    fig.text(0.012, 0.975, "What PhysMAP adds to input-based OOD detection",
             fontsize=13, weight="bold", va="top")
    fig.text(0.012, 0.905,
             f"Seven published datasets, at the default setting (percentile "
             f"{d('bench.ref_pct')}). Counts are rows of each dataset: rows are not independent "
             "cases,\nand the datasets are not pooled. Whether a count shows a blind spot that "
             "deployment created depends on the home baseline.",
             fontsize=9.5, color=INK["secondary"], va="top", linespacing=1.4)
    h = 0.56
    wmax = max((r["ref"]["n_wrong"] for r in Bn["rows"] if r.get("ref")), default=1)
    fmax = max((r["ref"]["misaligned"] for r in Bn["rows"] if r.get("ref")), default=1)
    for vid, yy in ys.items():
        ref = byv[vid].get("ref")
        if not ref:
            for ax in (a1, a2):
                ax.text(0.5 if ax is a2 else 1.0, yy, "not tested: one training row, no "
                        "detector fit" if ax is a1 else "—", va="center", fontsize=8.5,
                        color=INK["muted"], style="italic")
            continue
        a1.barh(yy, ref["n_wrong"], height=h, color=INK["grid"], lw=0, zorder=1)
        a1.barh(yy, ref["clean_lift"], height=h, color=AQUA, lw=0, zorder=2)
        a1.text(ref["n_wrong"] + wmax * 0.015, yy,
                d(f"bench.{vid}.ref_caught_of_wrong"), va="center", fontsize=9.5)
        a2.barh(yy, ref["misaligned"], height=h, color=INK["secondary"], lw=0, zorder=2)
        a2.text(ref["misaligned"] + fmax * 0.03, yy, d(f"bench.{vid}.ref_flagged_right"),
                va="center", fontsize=9.5)
    a1.set_yticks(list(ys.values()))
    a1.set_yticklabels([labels[v] for v in ys], fontsize=9)
    a1.tick_params(axis="y", length=0)
    a2.tick_params(axis="y", length=0)
    for group, yy in heads:
        a1.text(-0.012, yy, group, transform=a1.get_yaxis_transform(), ha="right",
                va="center", fontsize=9, weight="bold", color=INK["secondary"])
    a1.set_ylim(y - 0.2, -0.8)
    a1.set_xlim(0, wmax * 1.22)
    a2.set_xlim(0, fmax * 1.3)
    a1.set_title("Wrong predictions the OOD detectors missed,\ncaught by PhysMAP",
                 loc="left", fontsize=10, weight="bold")
    a2.set_title("Right predictions PhysMAP\nflagged anyway (false alarms)", loc="left",
                 fontsize=10, weight="bold")
    for ax in (a1, a2):
        ax.grid(axis="y", visible=False)
        ax.set_xlabel("rows")
    from matplotlib.patches import Patch
    a1.legend(handles=[Patch(color=INK["grid"], label="all wrong predictions"),
                       Patch(color=AQUA, label="caught only by PhysMAP")],
              loc="upper right", fontsize=8.5)
    _save(fig, "bench_3_what_physmap_adds",
          f"{SRC['matrix']} (per vehicle, at the reference percentile); the same counts print "
          "in `physmap benchmark report`; data: docs/talk/figures/data/"
          "bench_3_what_physmap_adds.csv")


def fig_home_baseline(reg: _Reg, Bn: dict):
    """One row per vehicle: the share of predictions off by more than the benchmark's own
    threshold at home (held out; hollow) and when deployed (filled), joined by a line.
    Neutral ink only -- identity is carried by the marker's fill and by the legend, never
    by colour -- and every count is printed beside its row, in a panel sharing the rows."""
    plt = _mpl()
    from matplotlib.lines import Line2D
    from matplotlib.transforms import blended_transform_factory
    d = reg.d
    byv = {r["vehicle"]: r for r in Bn["rows"]}
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0.25, 0.12, 0.33, 0.6])
    tab = fig.add_axes([0.6, 0.12, 0.39, 0.6], sharey=ax)
    tab.set_axis_off()
    fig.text(0.012, 0.975, "Is the surrogate right at home? The baseline behind each count",
             fontsize=13, weight="bold", va="top")
    fig.text(0.012, 0.905,
             "Share of predictions off by more than the benchmark's own threshold: at home, held "
             "out, and when deployed. A count shows a\nblind spot that deployment created only "
             "where deployment is distinguishably worse (one-sided Fisher exact p < "
             f"{d('bench.home_alpha')}). No row is removed.",
             fontsize=9.5, color=INK["secondary"], va="top", linespacing=1.4)
    ys = {vid: i for i, vid in enumerate(HOME_ORDER)}
    ax.set_ylim(len(ys) - 0.4, -0.9)
    ax.set_xlim(-4, 104)
    cols = blended_transform_factory(tab.transAxes, tab.transData)
    for x, label in ((0.0, "home wrong,\nheld out"), (0.27, "deployed\nwrong"),
                     (0.52, "deployment-induced\nblind spot?")):
        tab.text(x, -0.75, label, transform=cols, va="bottom", fontsize=8.5,
                 color=INK["secondary"], weight="bold")
    for vid, y in ys.items():
        c = byv[vid]["home"]
        h, dp = c["home_held_out"], c["deployment"]
        hx, dx = 100 * h["n_wrong"] / h["n"], 100 * dp["n_wrong"] / dp["n"]
        ax.plot([hx, dx], [y, y], color=INK["axis"], lw=1.6, zorder=1)
        ax.plot(dx, y, "o", ms=8, mfc=INK["primary"], mec=INK["primary"], mew=1.8, zorder=2)
        ax.plot(hx, y, "o", ms=8, mfc=INK["surface"], mec=INK["primary"], mew=1.8, zorder=3)
        tab.text(0.0, y, d(f"bench.{vid}.home_heldout"), transform=cols, va="center", fontsize=9)
        tab.text(0.27, y, d(f"bench.{vid}.deploy_wrong"), transform=cols, va="center",
                 fontsize=9)
        reading = (f"yes, p = {d(f'bench.{vid}.fisher_p')}" if c["supports_blind_spot"] else
                   "no: one home row" if h["n"] < 2 else
                   f"no, p = {d(f'bench.{vid}.fisher_p')}")
        tab.text(0.52, y, reading, transform=cols, va="center", fontsize=9,
                 weight="bold" if c["supports_blind_spot"] else "normal")
    ax.set_yticks(list(ys.values()))
    ax.set_yticklabels([BENCH_NAMES[v] for v in ys], fontsize=9)
    ax.tick_params(axis="y", length=0)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("predictions off by more than the threshold")
    ax.legend(handles=[
        Line2D([], [], ls="", marker="o", ms=8, mfc=INK["surface"], mec=INK["primary"], mew=1.8,
               label="at home, held out"),
        Line2D([], [], ls="", marker="o", ms=8, mfc=INK["primary"], mec=INK["primary"],
               label="deployed")], loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2,
        fontsize=8.5, handletextpad=0.3, columnspacing=1.2, borderaxespad=0.3)
    _save(fig, "bench_4_home_baseline",
          f"{SRC['home']}, beside the unchanged banked matrix; plotted values: "
          "docs/talk/figures/data/bench_4_home_baseline.csv")


# ── captions (generated, so their numbers cannot drift) ──────────────────────

def captions(reg: _Reg, L: dict, Bn: dict, N: dict) -> str:
    d = lambda k: reg.items[k]["display"]  # noqa: E731
    o = ["# Figures — generated, do not edit",
         "",
         "Built by `python tools/talk_package.py build` from committed records only. Each figure "
         "ships as an editable vector SVG (text kept as text) and a 1920-pixel PNG for slides, "
         "and has a table twin in `data/` holding the plotted values. Blue is gravity off and "
         "orange is gravity on in every Lewis figure; the only dashed line is the illustrative "
         "θ. Light theme only: these are slide images, not interactive charts.",
         ""]
    cap = {
        "lewis_1_input_contract":
            f"The input contract. The surrogate and the input-based OOD detector both receive "
            f"Re, Pr and x_over_D, and nothing else. Neither receives gravity, Ri, Gr or wall "
            f"heat flux. Training: {d('lewis.M.training_runs')} gravity-off CFD runs, "
            f"{d('lewis.M.training_rows')} rows, one run at 35A's own operating point. "
            f"Deployment: Re {d('lewis.deploy_Re')}, Pr {d('lewis.deploy_Pr')}, at Lewis's "
            f"{d('lewis.n_stations')} stations; every visible deployment input is a training "
            f"input. PhysMAP reads Ri = {d('lewis.Ri_gravity_on')} with gravity on, outside the "
            f"surrogate's calibrated window ({L['window']}).",
        "lewis_2_control_vs_gravity_on":
            f"Four views of the same {d('lewis.n_stations')} stations of one run. Top left: the "
            f"surrogate's prediction, the gravity-off CFD control and Lewis's measurement. Top "
            f"right: the surrogate is within {d('lewis.control_error_max_abs_pct')} % of the "
            f"control and {d('lewis.downstream_error_range_pct')} % off the measurement at x/D "
            f"{d('lewis.downstream_stations')}. Bottom left: the OOD distance score, identical "
            f"in both states and under its threshold {d('lewis.ood.threshold_distance')} "
            f"everywhere; GP variance is quiet too (max {d('lewis.ood.max_gp_all')} against "
            f"{d('lewis.ood.threshold_gp')}). Bottom right: materiality, 0 with gravity off, up "
            f"to {d('lewis.materiality_on_max')} with gravity on. Materiality comes from the "
            f"matched CFD pair, not from the measurement. Hollow markers: the three stations "
            f"Lewis disowns — the first two for axial wall conduction, the last as suspect.",
        "lewis_3_ood_identical":
            f"Each input-based OOD score with gravity off, against the same score with gravity "
            f"on, for all {d('lewis.n_stations')} stations. Every point is on the diagonal; the "
            f"largest difference, over every station, both scores and every operating "
            f"percentile, is {d('lewis.ood.max_abs_difference_on_vs_off')}. Shaded: where the "
            f"detector would fire at the reference percentile {REF_PCT}.",
        "lewis_4_materiality":
            f"Left: materiality by position, as continuous values. Right: how many of the "
            f"{d('lewis.n_comparable')} comparable stations would flag at each θ — at least one "
            f"for any θ ≤ {d('lewis.theta_any_flag_up_to')}, and none with gravity off at any "
            f"θ. The dashed line is the illustrative θ = {d('lewis.theta_illustrative')}, the "
            f"original study's value. θ is unlocked, so no flag here is a verdict. At θ = "
            f"{d('lewis.theta_0.05')}: {d('lewis.flags_on_at_theta_0.05')} stations; at "
            f"{d('lewis.theta_0.10')}: {d('lewis.flags_on_at_theta_0.10')}; at "
            f"{d('lewis.theta_0.20')}: {d('lewis.flags_on_at_theta_0.20')}.",
        "lewis_5_control_table":
            "The control table, for a slide. Two rows, one difference: gravity, which is not an "
            "input to the surrogate or to the OOD detector.",
        "bench_1_naca_entrance":
            f"NACA TN-1451, Fig 10, two-reader digitisation. The detectors are fitted on the "
            f"fully developed region (x/D ≥ {d('naca.bound')}, {d('naca.n_training')} points) "
            f"using Re and Pr, and assess the entrance region ({d('naca.n_entrance')} points: "
            f"{d('naca.entrance_positions_per_curve')} positions on each of "
            f"{d('naca.n_Re_curves')} Reynolds-number curves). Closure validity fires on "
            f"{d('naca.closure_fired')} of {d('naca.n_entrance')}; novelty density on "
            f"{d('naca.novelty_fired')}; GP variance on {d('naca.gp_fired')}. The benchmark's "
            f"own NACA cell uses its own split ({d('bench.naca_tn1451.n_train')} training rows, "
            f"{d('bench.naca_tn1451.n_test')} test rows) and shows the same pattern: baseline "
            f"{d('bench.naca_tn1451.ref_n_baseline_fired')}, distance "
            f"{d('bench.naca_tn1451.ref_n_distance_fired')}, GP variance "
            f"{d('bench.naca_tn1451.ref_n_gp_var_fired')}, closure "
            f"{d('bench.naca_tn1451.ref_n_corpus_fired')}. Scored against the measurement at "
            f"the benchmark's NACA threshold ({d('naca.threshold_pct')} %), the Gnielinski "
            f"correlation is wrong on {d('naca.gn_home_wrong')} fully developed points and "
            f"{d('naca.gn_entrance_wrong')} entrance points, all at x/D ≤ "
            f"{d('naca.gn_entrance_max_xd')} (one-sided Fisher exact p = "
            f"{d('naca.gn_fisher_p')}); the closure check flags every entrance point, "
            f"{d('naca.gn_flagged_right')} of them where the correlation is right. This is "
            f"observability, not causal materiality.",
        "bench_3_what_physmap_adds":
            f"For each of the seven datasets, at the default setting (percentile "
            f"{d('bench.ref_pct')}): left, the surrogate's wrong predictions that the input-based "
            f"OOD detectors missed and PhysMAP's closure check caught; right, the right predictions "
            f"the closure check flagged anyway. Where the cause of failure is hidden from the "
            f"inputs, PhysMAP flags wrong predictions the OOD detectors miss — "
            f"{d('bench.naca_tn1451.ref_caught_of_wrong')} for NACA. Whether a count shows a "
            f"blind spot that deployment created depends on the home baseline in the next "
            f"figure: it holds for Casper and Dirker, not for NACA, Jin or Velazquez, whose "
            f"surrogates are wrong about as often at home. Where the cause is visible "
            f"(Marineau), it adds nothing: {d('bench.marineau_hypersonic_transition.ref_caught_of_wrong')}. "
            f"The cost is false alarms: {d('bench.naca_tn1451.ref_flagged_right')} for NACA and "
            f"{d('bench.dirker_water.ref_flagged_right')} for Dirker. Counts are rows of each "
            f"dataset, not independent cases, and are never pooled into a rate across datasets. "
            f"Forrest has one training row, so nothing was tested.",
        "bench_4_home_baseline":
            f"For each dataset: the share of the surrogate's predictions off by more than the "
            f"benchmark's own threshold, at home (held out) and when deployed. Home error is "
            f"labelled by how it was obtained: where the surrogate was fitted to the home rows "
            f"(Casper, Dirker, Marineau) it is refitted without each row in turn; where it is a "
            f"published correlation (NACA, Jin, Velazquez, Forrest) the rows were never fitted. "
            f"Deployment is distinguishably worse — one-sided Fisher exact p < "
            f"{d('bench.home_alpha')}, a rule fixed after these counts were first seen — for "
            f"Casper ({d('bench.casper_hypersonic_transition.home_heldout')} at home, "
            f"{d('bench.casper_hypersonic_transition.deploy_wrong')} deployed) and Dirker "
            f"({d('bench.dirker_water.home_heldout')}, {d('bench.dirker_water.deploy_wrong')}). "
            f"It is not for NACA ({d('bench.naca_tn1451.home_heldout')} at home, "
            f"{d('bench.naca_tn1451.deploy_wrong')} deployed), Jin, Velazquez or Marineau; "
            f"Forrest has one home row. Their detector counts stand, but cannot show that "
            f"deployment created the failure. No row is removed.",
        "bench_2_seven_vehicles":
            "The seven vehicles as `physmap benchmark report` prints them, with each dataset's "
            "redistribution basis and data quality. An outcome is an observability class. "
            "Forrest is shown but is not evidence: triage-only values and a degenerate cell. No "
            "rate is computed across vehicles.",
    }
    srcs = {
        "lewis_1_input_contract": [SRC["bank"], SRC["profiles"]],
        "lewis_2_control_vs_gravity_on": [SRC["bank"]],
        "lewis_3_ood_identical": [SRC["bank"]],
        "lewis_4_materiality": [SRC["bank"]],
        "lewis_5_control_table": [SRC["bank"]],
        "bench_1_naca_entrance": [SRC["naca_example"], SRC["naca"], SRC["matrix"]],
        "bench_2_seven_vehicles": [SRC["matrix"], "src/physmap/benchmarks/registry.py"],
        "bench_3_what_physmap_adds": [SRC["matrix"]],
        "bench_4_home_baseline": [SRC["home"], SRC["matrix"]],
    }
    for name, title in FIGURES.items():
        o += [f"## {title}", "",
              f"![{title}]({name}.png)", "",
              cap[name], "",
              f"- Files: [`{name}.svg`]({name}.svg) (vector, editable) · "
              f"[`{name}.png`]({name}.png) (1920 px)",
              f"- Plotted values: [`data/{name}.csv`](data/{name}.csv)",
              "- Source data: " + ", ".join(f"[`{s}`](../../../{s})" for s in srcs[name]), ""]
    return "\n".join(o)


# ── facts sheet ──────────────────────────────────────────────────────────────

def facts_sheet(reg: _Reg, L: dict, Bn: dict, N: dict) -> str:
    d = lambda k: reg.items[k]["display"]  # noqa: E731
    st = L["stations"]
    c = L["contract"]
    o = ["# Facts sheet — generated, do not edit", "",
         "Built by `python tools/talk_package.py build` from committed records. "
         "`python tools/talk_package.py check` fails if anything here drifts from those records "
         "or from the clean-clone CLI output. Every section names its source.", ""]

    o += ["## 1. What is being counted", "",
          f"- **One experimental run.** Lewis (1992) Test 35A. Its {d('lewis.n_stations')} "
          f"thermocouple stations are **positions within that one run, not independent "
          f"cases**. {d('lewis.n_comparable')} are comparable; Lewis disowns x/D 0.31 and 0.85 "
          f"(axial wall conduction) and 159.33 (suspect).",
          f"- **Training data are CFD runs, not experiments.** Design M: "
          f"{d('lewis.M.training_runs')} gravity-off runs, {d('lewis.M.training_rows')} rows — "
          f"{d('lewis.train.stations_per_run')} positions in each of twelve runs, "
          f"{d('lewis.train.matched_run_stations')} in the matched run. The rows are positions "
          f"within runs.",
          "- **The matched ablation is two CFD cases**, gravity on and gravity off. No "
          "measurement enters materiality.",
          f"- **NACA:** the {d('naca.n_entrance')} entrance points are "
          f"{d('naca.entrance_positions_per_curve')} positions on each of "
          f"{d('naca.n_Re_curves')} curves of one figure.",
          "- **Benchmark:** n_train and n_test are data rows, not independent cases.",
          "- **No precision, recall or F1** is computed anywhere in this package.", "",
          f"Sources: `{SRC['bank']}`, `{SRC['profiles']}`, `{SRC['naca']}`.", ""]

    o += ["## 2. The physical case — Lewis Test 35A", "",
          "| quantity | value |", "|---|---|",
          f"| tube diameter | {d('lewis.case.d_m')} m |",
          f"| heated length | {d('lewis.case.L_m')} m (L/d {d('lewis.case.L_over_d')}) |",
          f"| unheated entry before heating | {d('lewis.case.entry_d')} d |",
          f"| wall heat flux | {d('lewis.case.q_w')} W/m² |",
          f"| inlet bulk temperature | {d('lewis.case.T_in')} °C |",
          f"| flow rate | {d('lewis.case.Vdot')} L/min |",
          f"| Re, Pr (inlet-bulk basis) | {d('lewis.deploy_Re')}, {d('lewis.deploy_Pr')} |",
          f"| Gr_q (heat-flux based) | {d('lewis.case.Gr_q')} |",
          f"| Ri = Gr_q / Re², gravity on | {d('lewis.Ri_gravity_on')} |",
          f"| exit bulk: calculated / measured | {d('lewis.case.T_exit_calc')} / "
          f"{d('lewis.case.T_exit_meas')} °C |",
          f"| Lewis's own energy-balance error | {d('lewis.case.energy_balance_pct')} % |",
          f"| Nu reduction | linear bulk to the calculated exit; k at inlet bulk, "
          f"{d('lewis.case.k_inlet')} W/m·K |", "",
          f"Source: `{SRC['reduction']}`; Ri from `{SRC['bank']}`.", ""]

    o += ["## 3. Input contract", "",
          "| | |", "|---|---|",
          f"| surrogate receives | {', '.join(c['surrogate_inputs'])} |",
          f"| input-based OOD detector receives | {', '.join(c['ood_detector_inputs'])} |",
          f"| neither receives | {', '.join(c['withheld_from_both'])} |",
          f"| training | {d('lewis.M.training_runs')} gravity-off CFD runs: Re "
          f"{d('lewis.train.Re_levels')} × inlet {d('lewis.train.T_in_levels')} °C, plus the "
          f"gravity-off half of the matched pair at 35A's operating point |",
          f"| deployment | Re {d('lewis.deploy_Re')}, Pr {d('lewis.deploy_Pr')}, x/D at "
          f"{d('lewis.n_stations')} stations |",
          f"| every visible deployment input exactly matches a training input | "
          f"{'yes' if L['exact_overlap'] else 'NO'} |",
          f"| how the matched run is labelled | with the deployment values Re "
          f"{d('lewis.deploy_Re')}, Pr {d('lewis.deploy_Pr')}; its own inlet values differ by "
          f"{d('lewis.train.matched_label_offset_Re_pct')} % and "
          f"{d('lewis.train.matched_label_offset_Pr_pct')} %. Pre-declared in "
          f"`{SRC['predeclaration']}` |",
          f"| PhysMAP's calibration window | {L['window']} — the training never saw buoyancy |",
          "", f"Source: `{SRC['bank']}` (input_contract), `{SRC['profiles']}`.", ""]

    o += [f"## 4. Per station — design M, reference percentile {REF_PCT}", "",
          "| x/D | comparable | control error (gravity off) | error vs measurement (gravity on) "
          "| Nu measured | Nu surrogate | OOD distance | OOD GP | OOD | materiality off | "
          "materiality on |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in st:
        k = s["k"]
        o.append(f"| {s['x']:g} | {'yes' if s['comparable'] else 'no'} | "
                 f"{d(k + '.control_error_pct')} % | {d(k + '.experimental_error_pct')} % | "
                 f"{d(k + '.Nu_experiment')} | {d(k + '.Nu_surrogate')} | "
                 f"{d(k + '.ood_distance')} | {d(k + '.ood_gp')} | {d(k + '.ood_p99')} | "
                 f"{d(k + '.materiality_off')} | {d(k + '.materiality_on')} |")
    o += ["", f"Source: `{SRC['bank']}` (headline_design_M.stations). Same formats as the "
          "command's own table; `check` compares them line by line.", ""]

    o += ["## 5. Summary values", "",
          f"- **Control accuracy:** within {d('lewis.control_error_max_abs_pct')} % of the "
          f"gravity-off CFD at every comparable station. Leave-one-run-out, worst station of "
          f"any run: {d('lewis.surrogate.loo_worst_pct')} % (`{SRC['predeclared']}`).",
          f"- **Error against the measurement, downstream** (x/D "
          f"{d('lewis.downstream_stations')}): {d('lewis.downstream_error_range_pct')} %.",
          f"- **OOD thresholds at p{REF_PCT}:** distance {d('lewis.ood.threshold_distance')}, GP "
          f"variance {d('lewis.ood.threshold_gp')}. Fired at p{REF_PCT}: "
          f"{d('lewis.ood.fired_p99_comparable')} of {d('lewis.n_comparable')} comparable "
          f"stations, in both states.",
          f"- **OOD scores identical between the two gravity states:** "
          f"{'yes' if L['ood_identical'] else 'NO'}. Largest difference over every station, "
          f"score and percentile: {d('lewis.ood.max_abs_difference_on_vs_off')}.",
          "- **Comparable stations where it fires, by operating percentile** (identical in both "
          "states): " + ", ".join(f"p{p} {d('lewis.ood.sweep_p' + p)}" for p in L["sweep"]) + ".",
          "- **In-sample alarm rate** — the share of its own training rows that fire: " +
          ", ".join(f"p{p} {d('lewis.M.in_sample_alarm_p' + p + '_pct')} %"
                    for p in L["alarm_pcts"]) +
          f". At p75, {d('lewis.lowpct.p75_rows_firing_xd50_100_pct')} % of training rows at "
          f"x/D 50–100 fire, and {d('lewis.lowpct.p75_rows_firing_xd0_10_pct')} % at x/D 0–10 "
          f"(`{SRC['predeclared']}`, `{SRC['lowpct']}`).",
          f"- **Materiality, gravity on:** {d('lewis.materiality_on_min')} to "
          f"{d('lewis.materiality_on_max')} at the comparable stations. **Gravity off:** 0 at "
          f"every station, by construction — the gravity-off state has no buoyancy to remove.",
          f"- **θ is unlocked.** Illustrative value {d('lewis.theta_illustrative')}, the original "
          f"study's. Comparable stations that would flag with gravity on: "
          + "; ".join(f"θ = {d('lewis.theta_%.2f' % t)} → {d('lewis.flags_on_at_theta_%.2f' % t)}"
                      for t in THETAS_SHOWN)
          + f". At least one for any θ ≤ {d('lewis.theta_any_flag_up_to')}. With gravity off, "
          f"none at any θ. At the illustrative value: x/D {d('lewis.flagged_at_illustrative')}.",
          f"- **Design A3 (secondary):** the operating point between training runs. OOD fires at "
          f"{d('lewis.A3.fired_p99_off')} of {d('lewis.n_comparable')} comparable stations with "
          f"gravity off and {d('lewis.A3.fired_p99_on')} with gravity on; scores identical: "
          f"{'yes' if L['A3_identical'] else 'NO'}; distance {d('lewis.A3.distance_range')} "
          f"against {d('lewis.A3.threshold_distance')}; control within "
          f"{d('lewis.A3.control_error_max_abs_pct')} %.",
          f"- **Pre-declared criteria** (`{SRC['predeclaration']}`): " + "; ".join(
              f"{k.split('_', 1)[1].replace('_', ' ')}: {'met' if v else 'NOT met'}"
              + (f" (at the illustrative θ = {d('lewis.theta_illustrative')}; it holds for any "
                 f"θ ≤ {d('lewis.theta_any_flag_up_to')})" if k.startswith("2_") else "")
              for k, v in L["criteria"].items() if k[0].isdigit()) + ".",
          "", f"Source: `{SRC['bank']}` unless named.", ""]

    o += ["## 6. How the surrogate's error splits", "",
          "(1 + error) = (1 − materiality) × (1 + base-model gap) × (1 + fit error). The "
          "base-model gap is the gravity-on CFD against the measurement; the fit error is the "
          "surrogate against the gravity-off CFD. The identity is exact, not fitted.", "",
          "| x/D | error vs measurement | missing buoyancy (−materiality) | base-model gap | "
          "fit error |", "|---|---|---|---|---|"]
    for s in st:
        if s["comparable"]:
            k = s["k"]
            o.append(f"| {s['x']:g} | {d(k + '.experimental_error_pct')} % | "
                     f"{d(k + '.split_missing_buoyancy_pct')} % | "
                     f"{d(k + '.split_base_model_gap_pct')} % | {d(k + '.split_fit_pct')} % |")
    o += ["", f"Downstream, the base-model gap is {d('lewis.downstream_base_gap_range_pct')} % in "
          "size: there the measurement sides with the gravity-on CFD. The link between "
          "materiality and this error is partly built in — the surrogate and the materiality "
          "both rest on the gravity-off CFD — which is one reason no detection rate is computed "
          "from it.", "",
          f"Sources: `{SRC['profiles']}` (ablation_full, ablation_removed), `{SRC['bank']}`.", ""]

    o += ["## 7. Energy closure — two definitions, one flow field", "",
          f"> {L['energy_definition']}", "",
          f"- Matched pair against the inlet-property balance: "
          f"{d('lewis.ablation.energy_full_inlet_ref')} % (gravity on), "
          f"{d('lewis.ablation.energy_removed_inlet_ref')} % (gravity off).",
          f"- The same fields against Lewis's calculated rise of {d('lewis.case.rise_calc')} K: "
          f"{d('lewis.ablation.energy_full_lewis_ref')} % and "
          f"{d('lewis.ablation.energy_removed_lewis_ref')} %.",
          f"- Every training run: |closure| ≤ {d('lewis.train.energy_max_abs_pct')} % on the "
          f"inlet-property balance. Reversed cells in the heated section, all runs together: "
          f"{d('lewis.train.reversed_cells_total')}.",
          f"- Lewis's own measured exit temperature differs from his calculated one by "
          f"{d('lewis.case.energy_balance_pct')} %. That is a property of the experiment, not of "
          "the CFD.",
          "", f"Sources: `{SRC['manifest']}`, `{SRC['profiles']}`, `{SRC['reduction']}`.", ""]

    o += ["## 8. Mesh and convergence", "",
          f"- **Grid pair** (gravity on, {d('lewis.grid.meshes')} cells, "
          f"{d('lewis.grid.iterations')} iterations): {d('lewis.grid.n_converged')} of "
          f"{d('lewis.grid.n_stations')} stations change by less than "
          f"{d('lewis.grid.criterion_pct')} % — x/D {d('lewis.grid.band_from')} to "
          f"{d('lewis.grid.band_to')}, largest change there "
          f"{d('lewis.grid.max_change_in_band_pct')} %. The entrance stations x/D "
          f"{d('lewis.grid.entrance_stations')} are grid-sensitive. Energy closure recorded with "
          f"that pair: {d('lewis.grid.energy_pct')} % (the record does not name its reference; "
          f"it equals the gravity-on figure against Lewis's rise).",
          "- **No separate grid study** was run for gravity off or for the training runs. They "
          "use the finer mesh of the pair.",
          f"- **Iterations:** the matched pair ran {d('lewis.ablation.iterations')} each. The "
          f"manifest records: \"{L['iteration_check']}\". That comparison was made when the "
          "inputs were banked, and the profile it used is not in the committed data, so this "
          "one figure is a recorded statement, not recomputable here.",
          "- **Two extraction paths.** The grid pair reads Nu at the nearest cell centre "
          "(`cfd/compare_lewis_vp.py`); the stress test interpolates linearly between cell "
          "centres (`cfd/lewis_head_to_head.py`, `lewis_nu`). The two committed gravity-on "
          "profiles — the grid pair's fine mesh and the matched pair — differ by at most "
          f"{d('lewis.extraction.max_diff_grid_band_pct')} % in the grid-converged band and "
          f"{d('lewis.extraction.max_diff_downstream_pct')} % at the downstream stations, but "
          f"at the entrance by {d('lewis.extraction.diff_entrance')}. Near the start of heating "
          "Nu changes fast along the tube, so where you read it matters. The entrance stations "
          "are sensitive to both mesh and extraction; downstream, each effect stays under 1 %.",
          f"- **Training runs:** {d('lewis.train.iterations')} iterations; the low-Re runs were "
          "continued because their enthalpy residual was still falling, decided before any "
          "head-to-head output existed.",
          "- **Grid convergence is numerical stability, not validation.** Whether a steady "
          "laminar model represents the experiment is a separate question. On the grid pair's "
          f"fine mesh, in the grid-converged band, the gravity-on CFD differs from Lewis's "
          f"measurement by at most {d('lewis.grid.cfd_vs_measurement_max_in_band_pct')} %, and "
          f"from Lewis's own steady laminar prediction by "
          f"{d('lewis.grid.cfd_vs_lewis_prediction_range_pct')} % where that prediction was "
          "traced. That is development evidence: 35A was inspected while the model was built.",
          "",
          "| run | Re | Pr | inlet °C | iterations | energy closure | h residual | reversed cells |",
          "|---|---|---|---|---|---|---|---|"]
    for r in L["runs"]:
        o.append(f"| {r['case']} | {r['Re']:.1f} | {r['Pr']:.3f} | {r['T_in']:g} | {r['it']} | "
                 f"{r['energy']:+.2f} % | {r['h']:.1e} | {r['rev']} |")
    o += ["", "| x/D | Nu " + " | Nu ".join(L["grid_meshes"]) + " | change | under 1 %? |",
          "|---|---|---|---|---|"]
    for g in L["grid"]:
        o.append(f"| {g['x']:g} | {g['coarse']:.2f} | {g['fine']:.2f} | {g['change']:+.2f} % | "
                 f"{'yes' if g['ok'] else 'no'} |")
    o += ["", f"Sources: `{SRC['grid']}`, `{SRC['profiles']}`, `{SRC['manifest']}`.", ""]

    o += ["## 9. Seven-vehicle benchmark — closure validity and observability", "",
          "Not evidence for causal materiality. Outcomes are observability classes, not rates.",
          "", "| vehicle | domain | failure variable | observability | outcome | redistribution | "
          "data quality | train rows | test rows |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in Bn["rows"]:
        o.append(f"| {r['vehicle']} | {r['domain']} | {r['failure_var']} | {r['observability']} "
                 f"| {r['outcome']} | {r['redistribution']} | {r['quality']} | {r['n_train']} | "
                 f"{r['n_test']} |")
    o += ["", f"**What the closure check adds, at percentile {d('bench.ref_pct')}** — per "
          "vehicle, counts of rows, never pooled:", "",
          "| vehicle | failure variable | wrong predictions caught only by PhysMAP | right "
          "predictions flagged anyway |", "|---|---|---|---|"]
    for group, vids in BENCH_GROUPS:
        for vid in vids:
            r = next(x for x in Bn["rows"] if x["vehicle"] == vid)
            if r.get("ref"):
                o.append(f"| {vid} | {r['observability']} | "
                         f"{d(f'bench.{vid}.ref_caught_of_wrong')} | "
                         f"{d(f'bench.{vid}.ref_flagged_right')} |")
            else:
                o.append(f"| {vid} | {r['observability']} | not tested: no detector fit | — |")
    o += ["", "**The home baseline behind each count** — derived beside the bank, which is "
          "unchanged. A count shows a blind spot that deployment created only where deployment "
          "is distinguishably worse than home (one-sided Fisher exact p < "
          f"{d('bench.home_alpha')}; rule fixed after these counts were first seen). No row is "
          "removed.", "",
          "| vehicle | home error: how obtained | home wrong (held out) | in-sample | "
          "deployed wrong | deployment-induced blind spot |", "|---|---|---|---|---|---|"]
    for vid in HOME_ORDER:
        c = next(x for x in Bn["rows"] if x["vehicle"] == vid)["home"]
        ins = (f"{d(f'bench.{vid}.home_insample')} ({d(f'bench.{vid}.home_insample_pct')}%)"
               if c["home_in_sample"] else "—")
        o.append(f"| {vid} | {d(f'bench.{vid}.home_kind')} | "
                 f"{d(f'bench.{vid}.home_heldout')} ({d(f'bench.{vid}.home_heldout_pct')}%) | "
                 f"{ins} | {d(f'bench.{vid}.deploy_wrong')} ({d(f'bench.{vid}.deploy_pct')}%) | "
                 f"{d(f'bench.{vid}.blind_spot')}, p = {d(f'bench.{vid}.fisher_p')} |")
    ax_ = Bn["axis"]
    o += ["", "**Architecture axis** — three model types per flagged vehicle, each trained on "
          "the surrogate inputs and first gated on its held-out error; at percentile "
          f"{d('bench.ref_pct')}, the wrong predictions only PhysMAP flags. Testable on "
          f"{d('arch.n_testable')} of {d('arch.n_vehicles')} vehicles.", "",
          "| vehicle | gp | deeponet | gbt |", "|---|---|---|---|"]
    for vid in ax_["vehicles"]:
        o.append(f"| {vid} | " + " | ".join(d(f"arch.{vid}.{a}") for a in ("gp", "deeponet", "gbt"))
                 + " |")
    o += ["", f"Observability guards all passed: {'yes' if Bn['all_guards_passed'] else 'NO'}. "
          "Forrest: triage-only values; one training row, no detector fit; DO_NO_HARM "
          "short-circuited, not earned.", "",
          f"Sources: `{SRC['matrix']}`, `{SRC['home']}`, `{SRC['axis']}`, "
          "`src/physmap/benchmarks/registry.py`.", ""]

    o += ["## 10. NACA x/D entrance-region example", "",
          f"- Training: {d('naca.n_training')} fully developed points (x/D ≥ {d('naca.bound')}). "
          f"Deployment: {d('naca.n_entrance')} entrance points. Pr {d('naca.Pr')} (air).",
          f"- Closure validity fired on {d('naca.closure_fired')} of {d('naca.n_entrance')}; "
          f"novelty density on {d('naca.novelty_fired')}; GP variance on {d('naca.gp_fired')}.",
          f"- Gnielinski against the measurement, at the benchmark's NACA threshold "
          f"({d('naca.threshold_pct')} %): wrong on {d('naca.gn_home_wrong')} fully developed "
          f"points and {d('naca.gn_entrance_wrong')} entrance points, all at x/D ≤ "
          f"{d('naca.gn_entrance_max_xd')}; worst {d('naca.gn_worst_pct')} % at x/D "
          f"{d('naca.gn_worst_xd')}; one-sided Fisher exact p = {d('naca.gn_fisher_p')}. The "
          f"closure check flags all {d('naca.n_entrance')}; the correlation is right on "
          f"{d('naca.gn_flagged_right')} of them.",
          f"- The benchmark's NACA cell uses its own split — {d('bench.naca_tn1451.n_train')} "
          f"training rows, {d('bench.naca_tn1451.n_test')} test rows — with the same pattern.",
          "", f"Source: `{SRC['naca_example']}` on `{SRC['naca']}`.", ""]
    return "\n".join(o)


# ── build ────────────────────────────────────────────────────────────────────

def _compute_all():
    reg = _Reg()
    L = compute_lewis(reg)
    Bn = compute_benchmark(reg)
    N = compute_naca(reg)
    return reg, L, Bn, N


def _capture(fn) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return buf.getvalue()


def build() -> int:
    reg, L, Bn, N = _compute_all()
    figs = {
        "lewis_1_input_contract": lambda: fig_input_contract(reg, L),
        "lewis_2_control_vs_gravity_on": lambda: fig_control_vs_gravity_on(reg, L),
        "lewis_3_ood_identical": lambda: fig_ood_identical(reg, L),
        "lewis_4_materiality": lambda: fig_materiality(reg, L),
        "lewis_5_control_table": lambda: fig_control_table(reg, L),
        "bench_1_naca_entrance": lambda: fig_naca(reg, N),
        "bench_2_seven_vehicles": lambda: fig_seven(reg, Bn),
        "bench_3_what_physmap_adds": lambda: fig_what_physmap_adds(reg, Bn),
        "bench_4_home_baseline": lambda: fig_home_baseline(reg, Bn),
    }
    FIGDATA.mkdir(parents=True, exist_ok=True)
    for name, draw in figs.items():
        reg.fig = name
        draw()
        reg.fig = None
        (FIGDATA / f"{name}.csv").write_text(_csv_text(*table_rows(name, reg, L, Bn, N)))
    (FIG / "README.md").write_text(captions(reg, L, Bn, N) + "\n")
    (TALK / "facts-sheet.md").write_text(facts_sheet(reg, L, Bn, N) + "\n")
    (TALK / "numbers.json").write_text(json.dumps({
        "generated_by": "python tools/talk_package.py build",
        "numbers": {k: {"display": v["display"], "source": v["source"]}
                    for k, v in sorted(reg.items.items())},
        "figures": reg.used}, indent=1, ensure_ascii=False) + "\n")
    # the CLI outputs the benchmark and NACA figures are checked against, from this checkout
    from physmap import cli
    REPRO.mkdir(parents=True, exist_ok=True)
    (REPRO / "benchmark_report.txt").write_text(
        _capture(lambda: cli.main(["benchmark", "report"])))
    (REPRO / "naca_example.txt").write_text(_capture(
        lambda: runpy.run_path(str(REPO / SRC["naca_example"]), run_name="__main__")))
    print(f"built {len(figs)} figures (SVG + PNG), their data, captions, the facts sheet and "
          f"{len(reg.items)} registered numbers")
    return 0


# ── check ────────────────────────────────────────────────────────────────────

_CLI_ROW = re.compile(
    r"^\s+(?P<x>\d+\.\d+)\s+\*?\s*\|\s+(?P<ctl>[+-]\d+\.\d+)%\s+(?P<exp>[+-]\d+\.\d+)%\s+\|"
    r"\s+(?P<dist>\d+\.\d+)\s+(?P<gp>\d+\.\d+)\s+(?P<ood>fires|quiet)\s+\|"
    r"\s+(?P<moff>-?\d+\.\d+)\s+(?P<mon>-?\d+\.\d+)\s*$")
# a decimal number, or a whole number directly followed by a percent sign
_NUM = re.compile(r"(?<![\w.])[−+-]?\d+(?:\.\d+)+(?!\w)|(?<![\w.])[−+-]?\d+(?=\s?%)")


def _cli_expectations(reg: _Reg, L: dict) -> list[tuple[str, str]]:
    """(text the CLI must print, what it proves) -- built from registered displays."""
    d = lambda k: reg.items[k]["display"]  # noqa: E731
    sweep = ", ".join(f"{p}: {d('lewis.ood.sweep_p' + p)}" for p in L["sweep"])
    return [
        (f"deployment Re {d('lewis.deploy_Re')}, Pr {d('lewis.deploy_Pr')}, x/D at Lewis's "
         f"{d('lewis.n_stations')} stations", "deployment inputs"),
        ("every visible deployment input exactly matches a training input (design M): YES",
         "exact overlap"),
        (f"energy closure {d('lewis.ablation.energy_full_inlet_ref')} % (full), "
         f"{d('lewis.ablation.energy_removed_inlet_ref')} % (removed)", "matched-pair energy"),
        (f"{d('lewis.ablation.iterations')} iterations each", "matched-pair iterations"),
        (f"distance {d('lewis.ood.threshold_distance')}, GP variance "
         f"{d('lewis.ood.threshold_gp')}", "OOD thresholds"),
        ("every score, every percentile: YES", "OOD identical"),
        (f"(both states): {sweep}", "percentile sweep"),
        (f"OOD fires at {d('lewis.A3.fired_p99_off')} of {d('lewis.n_comparable')} comparable "
         f"stations with gravity off (surrogate accurate) and {d('lewis.A3.fired_p99_on')} of "
         f"{d('lewis.n_comparable')} with gravity on; scores identical between them: YES",
         "design A3"),
        (f"holds for theta <= {d('lewis.theta_any_flag_up_to')}", "theta range"),
        (f"ILLUSTRATIVE theta = {d('lewis.theta_illustrative')}", "illustrative theta"),
        (f"would flag x/D {d('lewis.flagged_at_illustrative')} with gravity on, and nothing with "
         "gravity off", "illustrative flags"),
        ("Assertions hold", "assertions"),
        ("The record matches the banked record exactly.", "bank comparison"),
    ]


def check() -> int:
    fails: list[str] = []
    reg, L, Bn, N = _compute_all()

    # 1. registry, figure data, captions and facts sheet are what the committed records give
    saved = json.loads((TALK / "numbers.json").read_text())
    for k, v in reg.items.items():
        s = saved["numbers"].get(k)
        if s is None:
            fails.append(f"numbers.json lacks {k}")
        elif s["display"] != v["display"]:
            fails.append(f"{k}: numbers.json shows {s['display']}, the records give {v['display']}")
    for k in set(saved["numbers"]) - set(reg.items):
        fails.append(f"numbers.json has {k}, which the records no longer produce")
    if (TALK / "facts-sheet.md").read_text() != facts_sheet(reg, L, Bn, N) + "\n":
        fails.append("facts-sheet.md is stale -- run build")
    if (FIG / "README.md").read_text() != captions(reg, L, Bn, N) + "\n":
        fails.append("figures/README.md (the captions) is stale -- run build")
    for name in FIGURES:
        want = _csv_text(*table_rows(name, reg, L, Bn, N))
        path = FIGDATA / f"{name}.csv"
        if not path.exists() or path.read_text() != want:
            fails.append(f"figures/data/{name}.csv is stale -- run build")
        # 2. every number the figure is registered as showing is in its SVG's text
        svg, png = FIG / f"{name}.svg", FIG / f"{name}.png"
        if not svg.exists() or not png.exists():
            fails.append(f"{name}: SVG or PNG missing")
            continue
        text = " ".join(re.findall(r">([^<>]+)<", svg.read_text()))
        text = text.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
        text = " ".join(text.replace("&#39;", "'").replace("&quot;", '"').split())
        for key in saved["figures"].get(name, []):
            disp = " ".join(reg.items[key]["display"].split())
            if disp not in text:
                fails.append(f"{name}.svg does not show {key} = {disp}")

    # 3. the Lewis numbers against the clean clone's CLI output, line by line
    stdout = (REPRO / "stdout.txt").read_text()
    rows = {float(m["x"]): m for m in map(_CLI_ROW.match, stdout.splitlines()) if m}
    if len(rows) != len(L["stations"]):
        fails.append(f"parsed {len(rows)} station rows from the CLI output, expected "
                     f"{len(L['stations'])}")
    pairs = (("control_error_pct", "ctl"), ("experimental_error_pct", "exp"),
             ("ood_distance", "dist"), ("ood_gp", "gp"), ("ood_p99", "ood"),
             ("materiality_off", "moff"), ("materiality_on", "mon"))
    for s in L["stations"]:
        m = rows.get(s["x"])
        for ours, theirs in (pairs if m else ()):
            mine = reg.items[f"{s['k']}.{ours}"]["display"]
            if mine != m[theirs]:
                fails.append(f"x/D {s['x']:g} {ours}: package shows {mine}, CLI printed "
                             f"{m[theirs]}")
    flat = " ".join(stdout.split())
    for want, what in _cli_expectations(reg, L):
        if " ".join(want.split()) not in flat:
            fails.append(f"the CLI output does not contain the {what}: {want!r}")

    # 4. the clean clone itself
    log = (REPRO / "log.txt").read_text()
    if "exit status: 0" not in log:
        fails.append("the clean-clone run did not exit 0")
    commit = re.search(r"commit: ([0-9a-f]{40})", log)
    readme = (REPRO / "README.md").read_text() if (REPRO / "README.md").exists() else ""
    if not commit or commit.group(1) not in readme:
        fails.append("reproduction/README.md does not name the commit the clean clone ran")
    from physmap.stress_tests.lewis_reuse import compare_with_bank
    cmp = compare_with_bank(json.loads((REPRO / "fresh_record.json").read_text()))
    if not cmp.matches:
        fails.append(f"the clean-clone record drifts from the bank: {cmp.drift[:3]}")

    # 5. the benchmark and NACA figures against their own CLI outputs
    rep = (REPRO / "benchmark_report.txt").read_text()
    for r in Bn["rows"]:
        line = next((ln for ln in rep.splitlines() if ln.startswith(r["vehicle"] + " ")), "")
        if line.split()[:5] != [r["vehicle"], r["domain"], r["failure_var"],
                                r["observability"], r["outcome"]]:
            fails.append(f"benchmark report row for {r['vehicle']} differs: {line!r}")
    adds = {}
    for ln in rep.splitlines():
        m = re.match(r"^\s+(\S+)\s+(unobservable|partial|observable)\s+(\d+ of \d+)\s+(\d+)\s*$", ln)
        if m:
            adds[m.group(1)] = (m.group(3), m.group(4))
    readme = README.read_text().splitlines()
    for r in Bn["rows"]:
        vid = r["vehicle"]
        if not r.get("ref"):
            continue
        want = (reg.items[f"bench.{vid}.ref_caught_of_wrong"]["display"],
                reg.items[f"bench.{vid}.ref_flagged_right"]["display"])
        if adds.get(vid) != want:
            fails.append(f"benchmark report prints {adds.get(vid)} for {vid}; the matrix gives {want}")
        line = next((ln for ln in readme if ln.startswith("|") and f"`{vid}`" in ln), None)
        if line is None or f"| {want[0]} | {want[1]} |" not in line:
            fails.append(f"README table row for {vid} does not show {want[0]} and {want[1]}")
    for r in Bn["rows"]:
        vid = r["vehicle"]
        lines = [ln for ln in readme if ln.startswith("|") and f"`{vid}`" in ln]
        want = (reg.items[f"bench.{vid}.home_heldout"]["display"],
                reg.items[f"bench.{vid}.deploy_wrong"]["display"])
        if len(lines) < 2 or not all(w in lines[1] for w in want):
            fails.append(f"README home-baseline row for {vid} does not show {want[0]} at home "
                         f"and {want[1]} deployed")
        if f"deployment: {want[1]} wrong" not in rep:
            fails.append(f"benchmark report lacks the home-baseline line for {vid}")
    ex = (REPRO / "naca_example.txt").read_text()
    for want in (f"fully developed (home): {reg.items['naca.gn_home_wrong']['display']} wrong",
                 f"entrance:               {reg.items['naca.gn_entrance_wrong']['display']} wrong",
                 f"one-sided Fisher exact p = {reg.items['naca.gn_fisher_p']['display']}",
                 f"within the threshold on {reg.items['naca.gn_flagged_right']['display']} of them"):
        if want not in ex:
            fails.append(f"the NACA example output lacks {want!r}")
    for want in (f"input-based OOD detectors fired on "
                 f"{reg.items['naca.either_input_based_fired']['display']} of "
                 f"{reg.items['naca.n_entrance']['display']} entrance points",
                 f"test: {reg.items['naca.n_entrance']['display']} entrance points",
                 f"train: {reg.items['naca.n_training']['display']} fully-developed points"):
        if want not in ex:
            fails.append(f"the NACA example output lacks {want!r}")

    # 6. every decimal (and whole-number percentage) in the hand-written prose is sourced
    tokens = re.compile(r"\d+(?:\.\d+)*")
    displays = {t for v in reg.items.values() for t in tokens.findall(str(v["display"]))}
    historical = set(tokens.findall((REPO / SRC["known"]).read_text()))
    docs = [p for p in sorted(TALK.glob("*.md")) if p.name != "facts-sheet.md"]
    docs.append(REPRO / "README.md")
    for doc in docs:
        if not doc.exists():
            continue
        fence = False
        for ln, line in enumerate(doc.read_text().splitlines(), 1):
            if line.strip().startswith("```"):
                fence = not fence
                continue
            if fence:
                continue
            body = re.sub(r"`[^`]*`", "", line)             # code spans: paths, commands
            body = re.sub(r"\]\([^)]*\)", "]", body)        # link targets
            for tok in _NUM.findall(body):
                t = tok.lstrip("+-−")
                if t.count(".") > 1 or t in displays or t in historical:
                    continue
                fails.append(f"{_rel(doc)}:{ln}: '{tok}' is neither a registered number nor a "
                             f"historical value in {SRC['known']}")

    if fails:
        print("TALK PACKAGE CHECK FAILED")
        for f in fails:
            print("  " + f)
        return 1
    print(f"Talk package check passed. {len(reg.items)} registered numbers, the figure data, the "
          f"captions and the facts sheet match the committed records. Every figure shows the "
          f"numbers it is registered for. Every Lewis number matches the clean-clone CLI output "
          f"({len(rows)} station rows, {len(_cli_expectations(reg, L))} summary lines). The "
          f"clean-clone record is {cmp.summary()} against the bank. The benchmark and NACA "
          f"figures match their CLI outputs. Every number in the talk prose is sourced.")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd not in ("build", "check"):
        raise SystemExit("usage: python tools/talk_package.py build|check")
    raise SystemExit(build() if cmd == "build" else check())
