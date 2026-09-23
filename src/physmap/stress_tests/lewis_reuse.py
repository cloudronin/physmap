"""Controlled model-reuse stress test: Lewis (1992) Test 35A.

WHAT IT IS
The surrogate was trained for forced convection, where gravity did not vary and was not an
input. It was then reused in vertical heated flow, where buoyancy became material. A
mixed-convection surrogate designed for this regime should include Richardson number, Grashof
number, or equivalent physical information.

THE CLAIM
PhysMAP detects when model reuse activates a physically relevant mechanism outside the
surrogate's observable input space. An input-only OOD detector cannot identify a change absent
from its input contract.

WHAT IT IS NOT
Not a claim that OOD detectors fail in general -- the input-based OOD detector does exactly
its job here. Not a suggestion that gravity should be left out: a mixed-convection surrogate
built correctly exposes the relevant physics. Not a claim about NVIDIA PhysicsNeMo, whose
out-of-distribution check and physics checks are distinct and were not run.

HOW
Design M (headline): the surrogate is trained on thirteen gravity-off CFD runs, one of them at
35A's own operating point, so every visible deployment input is an exact training input.
Design A3 (secondary): the same without that run, so 35A falls between training runs.

Both are scored twice with IDENTICAL visible inputs: against gravity-off CFD at 35A -- the
accurate control -- and against Lewis's measurement, where buoyancy is active. The OOD
detector is the seven-vehicle benchmark's own, imported unchanged. PhysMAP's output is the
causal path: the applicability screen, matched-ablation materiality and the flag rule.

STATUS
Development demonstration. ONE run, already inspected during development; its stations are
not independent cases; no performance metric is computed or implied. theta is unlocked, so
materiality is reported as continuous values and theta = 0.10 appears only as an illustration.

Reproduces cfd/lewis_head_to_head.py's pre-declared design M to the bit from the CFD-derived
inputs banked in data/stress_tests/lewis_reuse/.
"""

from __future__ import annotations

import csv
import json
import math
import tempfile
from pathlib import Path

import numpy as np

from physmap._paths import checkout_path

STRESS_TEST_ID = "lewis-reuse"
BANKED_RECORD = ("results", "lewis35A_head_to_head", "stress_test_lewis_reuse.json")

FRAMING = (
    "The surrogate was trained for forced convection, where gravity did not vary and was not "
    "an input. It was then reused in vertical heated flow, where buoyancy became material. A "
    "mixed-convection surrogate designed for this regime should include Richardson number, "
    "Grashof number, or equivalent physical information."
)
CLAIM = (
    "PhysMAP detects when model reuse activates a physically relevant mechanism outside the "
    "surrogate's observable input space. An input-only OOD detector cannot identify a change "
    "absent from its input contract."
)
NOT_CLAIMED = (
    "OOD detectors do not fail in general; this one does exactly its job.",
    "Gravity should not be omitted: a mixed-convection surrogate built correctly exposes Ri, Gr "
    "or equivalent physical information.",
    "Nothing is claimed about NVIDIA PhysicsNeMo; its OOD and physics checks are distinct and "
    "were not run.",
)
STATUS = (
    "Development demonstration. One run (Lewis 35A), already inspected during development. "
    "Its stations are not independent cases. No performance metric is computed or implied."
)

SURROGATE_INPUTS = ("Re", "Pr", "x_over_D")
WITHHELD = ("gravity", "Ri", "Gr", "wall heat flux", "flow direction")
ILLUSTRATIVE_THETA = 0.10     # the original study's value, recorded before any Lewis work
# Lewis disowns three stations on his own authority, for reasons unrelated to buoyancy.
DISOWNED = {0.31: "axial wall conduction (Lewis Sec 7.1.1)",
            0.85: "axial wall conduction (Lewis Sec 7.1.1)",
            159.33: "'suspect' -- flange heat loss (Lewis Sec 7.1.1)"}


# ── inputs ───────────────────────────────────────────────────────────────────

def _load_inputs() -> dict:
    cfd = json.loads(checkout_path("data", "stress_tests", "lewis_reuse", "cfd_profiles.json",
                                   what="the Lewis stress test's banked CFD profiles").read_text())
    manifest = json.loads(checkout_path("data", "stress_tests", "lewis_reuse", "manifest.json",
                                        what="the Lewis stress test's manifest").read_text())
    lewis = json.loads(checkout_path("data", "lewis1992", "test_35A_reduction.json",
                                     what="Lewis Test 35A reduction").read_text())
    ib = lewis["dimensionless_by_basis"]["inlet_bulk"]
    return {"cfd": cfd, "manifest": manifest,
            "Re": ib["Re"], "Pr": ib["Pr"], "Gr_q": ib["Gr_q_heat_flux_based"],
            "measured": [(p["x_over_d"], p["Nu"]) for p in lewis["local_nu_inlet_bulk_basis"]]}


def _training_rows(inp: dict, design: str) -> list[dict]:
    rows = []
    for run in inp["cfd"]["training_runs"]:
        for x, nu in zip(run["x_over_D"], run["Nu"]):
            rows.append({"run": run["case"], "Re": run["inlet_bulk"]["Re"],
                         "Pr": run["inlet_bulk"]["Pr"], "x_over_D": x, "Nu": nu})
    if design == "M":
        m = inp["cfd"]["matched_training_run"]
        # Labelled with the EVALUATED inputs, as pre-declared: its polynomial-evaluated inlet
        # values differ by -0.062 % (Re) and +0.141 % (Pr), inside Lewis's own property spread.
        for x, nu in zip(m["x_over_D"], m["Nu"]):
            rows.append({"run": m["case"], "Re": inp["Re"], "Pr": inp["Pr"], "x_over_D": x,
                         "Nu": nu})
    return rows


# ── the surrogate: a forced-convection GP on gravity-off CFD ─────────────────

def _X(rows):
    return np.array([[math.log10(r["Re"]), r["Pr"], math.log10(r["x_over_D"])] for r in rows])


def _fit_surrogate(rows):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    X, y = _X(rows), np.log([r["Nu"] for r in rows])
    mu, sd = X.mean(0), X.std(0)
    kern = ConstantKernel(1.0) * Matern(length_scale=[1.0, 1.0, 1.0], nu=2.5) + WhiteKernel(1e-6)
    gp = GaussianProcessRegressor(kernel=kern, normalize_y=True, n_restarts_optimizer=3,
                                  random_state=0).fit((X - mu) / sd, y)
    return lambda rs: np.exp(gp.predict((_X(rs) - mu) / sd))


# ── the input-based OOD detector: the benchmark's own, unchanged ─────────────

def _write_csv(rows, path: Path, pred) -> None:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Re", "Pr", "x_over_D", "truth", "prediction"])
        for r, p in zip(rows, pred):
            w.writerow([r["Re"], r["Pr"], r["x_over_D"], r["Nu"], float(p)])


def _ood(train, train_pred, tests: dict) -> dict:
    """Fit the benchmark's detector tuple once per operating percentile, exactly as run_cell
    does, and assess every test set with it. Each test set is written to its OWN file with its
    own truth column, so an unchanged score also shows that truth never reached the detector."""
    from physmap.benchmarks.benchmark_v0_4 import _DETECTORS, OPERATING_PERCENTILES
    from physmap.guardrail.configs import ColumnMap
    from physmap.guardrail.enums import DetectorKind, Regime
    from physmap.guardrail.guardrail import CredibilityGuardrail

    colmap = ColumnMap(inputs=list(SURROGATE_INPUTS), truth="truth", prediction="prediction")
    out = {name: {} for name in tests}
    with tempfile.TemporaryDirectory() as td:
        tr = Path(td) / "train.csv"
        _write_csv(train, tr, train_pred)
        files = {}
        for name, (rows, pred) in tests.items():
            files[name] = Path(td) / f"{name}.csv"
            _write_csv(rows, files[name], pred)
        for pct in OPERATING_PERCENTILES:
            # UNLISTED: the shipped corpus has no laminar vertical-tube closure, so the
            # guardrail's closure layer is left inactive rather than fired on Re < 3000 by a
            # turbulent closure for a reason unrelated to buoyancy.
            g = CredibilityGuardrail(surrogate_inputs=list(SURROGATE_INPUTS),
                                     regime=Regime.UNLISTED, detectors=_DETECTORS,
                                     operating_pct=float(pct))
            g.fit(tr, columns=colmap)
            for name, f in files.items():
                res = []
                for a in g.assess(f, columns=colmap):
                    d = a.signals[DetectorKind.DISTANCE_TO_TRAINING]
                    v = a.signals[DetectorKind.GP_VARIANCE]
                    res.append({
                        "distance": {"score": float(d.score), "threshold": float(d.threshold),
                                     "fired": bool(d.fired)},
                        "gp_variance": {"score": float(v.score), "threshold": float(v.threshold),
                                        "fired": bool(v.fired)},
                        "fired": bool(d.fired or v.fired)})
                out[name][str(pct)] = res
    return out


# ── PhysMAP: the causal path ─────────────────────────────────────────────────

def _physmap(inp: dict, n: int) -> dict:
    from physmap.applicability.screen import screen_case
    from physmap.core.mechanism import CalibrationWindow, Mechanism
    from physmap.materiality.estimator import (
        AblationInputs, AblationProvenance, estimate_materiality, materiality_signal)
    from physmap.release import EvidenceState

    screen = screen_case("lewis-35A", "local_Nusselt_number", qoi_decomposes=True,
                         mechanisms_separable=True, has_calibration_window=True,
                         ablation_available=True, evidence_state=EvidenceState.MEASURED)
    # The surrogate's training never saw gravity, so its calibrated window for buoyancy is
    # Ri = 0 exactly. Derived from the training data, not chosen.
    window = CalibrationWindow("richardson_number", 0.0, 0.0)
    ri_on = inp["Gr_q"] / inp["Re"] ** 2
    full = inp["cfd"]["ablation_full"]["Nu"]
    removed = inp["cfd"]["ablation_removed"]["Nu"]
    states = {}
    for state, ri, pairs in (("gravity_on", ri_on, list(zip(full, removed))),
                             ("gravity_off", 0.0, list(zip(removed, removed)))):
        mech = Mechanism("buoyancy-vertical-pipe-aiding", "buoyancy (Richardson number)",
                         window, ri)
        rows = []
        for q_full, q_abl in pairs[:n]:
            r = estimate_materiality(mech, "local_Nusselt_number",
                                     AblationInputs(q_full, q_abl,
                                                    AblationProvenance.MATCHED_ABLATION),
                                     evidence_state=EvidenceState.MEASURED)
            rows.append({"materiality": r.value, "status": r.status.value,
                         "flag_at_illustrative_theta": materiality_signal(
                             mech, r, theta=ILLUSTRATIVE_THETA).fired})
        states[state] = {"Ri": ri, "outside_calibration": mech.outside_calibration(),
                         "stations": rows}
    return {"applicability": screen.applicability.value, "reason_code": screen.reason_code.value,
            "window": window.describe(), "states": states}


# ── one design, both gravity states ──────────────────────────────────────────

def _design(inp: dict, design: str) -> dict:
    train = _training_rows(inp, design)
    surrogate = _fit_surrogate(train)
    xds = [x for x, _ in inp["measured"]]
    deploy = [{"Re": inp["Re"], "Pr": inp["Pr"], "x_over_D": x} for x in xds]
    truth = {"gravity_on": [nu for _, nu in inp["measured"]],
             "gravity_off": inp["cfd"]["ablation_removed"]["Nu"]}
    tests = {s: ([dict(d, Nu=t) for d, t in zip(deploy, truth[s])], None) for s in truth}
    pred = surrogate(tests["gravity_on"][0])
    tests = {s: (rows, pred) for s, (rows, _) in tests.items()}
    ood = _ood(train, surrogate(train), tests)

    seen = {(r["Re"], r["Pr"], r["x_over_D"]) for r in train}
    overlap = [(d["Re"], d["Pr"], d["x_over_D"]) in seen for d in deploy]
    return {"design": design, "training_runs": len({r["run"] for r in train}),
            "training_rows": len(train),
            "visible_inputs_exactly_in_training": overlap,
            "surrogate_prediction": [float(p) for p in pred],
            "truth": truth, "ood": ood}


# ── the record ───────────────────────────────────────────────────────────────

def run() -> dict:
    """Run the stress test and return its full record. Asserts nothing; `check` does."""
    import warnings
    from physmap.benchmarks.benchmark_v0_4 import OPERATING_PERCENTILES, REFERENCE_PCT
    inp = _load_inputs()
    xds = [x for x, _ in inp["measured"]]
    comparable = [x not in DISOWNED for x in xds]
    # scikit-learn's L-BFGS hyperparameter search warns when it stops at an iteration cap.
    # The warning is silenced here and ONLY here, and the fit is not taken on trust for it:
    # the control accuracy this record carries measures the surrogate against gravity-off
    # CFD at every deployment station, and `check` fails the run if that ever degrades.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", module="sklearn")
        M, A3 = _design(inp, "M"), _design(inp, "A3")
    pm = _physmap(inp, len(xds))
    ref = str(int(REFERENCE_PCT))
    on_mat = [s["materiality"] for s in pm["states"]["gravity_on"]["stations"]]
    comp_mat = [m for m, c in zip(on_mat, comparable) if c]

    def stations(d: dict) -> list[dict]:
        out = []
        for i, x in enumerate(xds):
            p = d["surrogate_prediction"][i]
            out.append({
                "x_over_D": x, "comparable": comparable[i], "why_not": DISOWNED.get(x),
                "surrogate_prediction": p,
                "control_gravity_off_truth": d["truth"]["gravity_off"][i],
                "control_error_pct": 100.0 * (p / d["truth"]["gravity_off"][i] - 1.0),
                "experiment_Nu": d["truth"]["gravity_on"][i],
                "experimental_error_pct": 100.0 * (p / d["truth"]["gravity_on"][i] - 1.0),
                "ood_gravity_off": {pc: d["ood"]["gravity_off"][pc][i] for pc in d["ood"]["gravity_off"]},
                "ood_gravity_on": {pc: d["ood"]["gravity_on"][pc][i] for pc in d["ood"]["gravity_on"]},
                "materiality_gravity_off": pm["states"]["gravity_off"]["stations"][i]["materiality"],
                "materiality_gravity_on": on_mat[i],
                "physmap_flag_gravity_off_at_illustrative_theta":
                    pm["states"]["gravity_off"]["stations"][i]["flag_at_illustrative_theta"],
                "physmap_flag_gravity_on_at_illustrative_theta":
                    pm["states"]["gravity_on"]["stations"][i]["flag_at_illustrative_theta"],
            })
        return out

    def ood_summary(d: dict) -> dict:
        per_pct = {}
        for pc in d["ood"]["gravity_on"]:
            per_pct[pc] = {s: sum(1 for i, c in enumerate(comparable)
                                  if c and d["ood"][s][pc][i]["fired"])
                           for s in ("gravity_off", "gravity_on")}
        return {"comparable_stations_fired_by_pct": per_pct,
                "identical_between_gravity_states": d["ood"]["gravity_off"] == d["ood"]["gravity_on"]}

    headline, secondary = stations(M), stations(A3)
    return {
        "stress_test": STRESS_TEST_ID,
        "kind": "controlled model-reuse stress test",
        "framing": FRAMING, "claim": CLAIM, "not_claimed": list(NOT_CLAIMED), "status": STATUS,
        "input_contract": {
            "surrogate_inputs": list(SURROGATE_INPUTS),
            "ood_detector_inputs": list(SURROGATE_INPUTS),
            "ood_detector_features": ["log10_Re", "Pr", "x_over_D"],
            "withheld_from_both": list(WITHHELD),
            "deployment_inputs": {"Re": inp["Re"], "Pr": inp["Pr"], "x_over_D": xds},
            "design_M_every_visible_input_exactly_in_training":
                all(M["visible_inputs_exactly_in_training"]),
            "design_A3_visible_inputs_in_training": sum(A3["visible_inputs_exactly_in_training"]),
        },
        "matched_ablation": {**inp["manifest"]["matched_ablation"],
                             "full": {k: inp["cfd"]["ablation_full"][k] for k in
                                      ("case", "gravity_on", "iterations", "energy_closure_pct",
                                       "final_initial_residuals",
                                       "reversed_cells_in_heated_section")},
                             "removed": {k: inp["cfd"]["ablation_removed"][k] for k in
                                         ("case", "gravity_on", "iterations", "energy_closure_pct",
                                          "final_initial_residuals",
                                          "reversed_cells_in_heated_section")}},
        "inputs_sha256": inp["manifest"]["cfd_profiles_sha256"],
        "ood_detector": {"object": "physmap.benchmarks.benchmark_v0_4._DETECTORS, unchanged",
                         "operating_percentiles": list(OPERATING_PERCENTILES),
                         "reference_pct": REFERENCE_PCT},
        "physmap": {"applicability": pm["applicability"], "reason_code": pm["reason_code"],
                    "calibration_window": pm["window"],
                    "Ri_gravity_on": pm["states"]["gravity_on"]["Ri"],
                    "outside_calibration": {s: pm["states"][s]["outside_calibration"]
                                            for s in pm["states"]}},
        "headline_design_M": {"training_runs": M["training_runs"],
                              "training_rows": M["training_rows"],
                              "ood": ood_summary(M), "stations": headline},
        "secondary_design_A3": {"training_runs": A3["training_runs"],
                                "training_rows": A3["training_rows"],
                                "ood": ood_summary(A3), "stations": secondary},
        "threshold_dependence": [
            {"result": "OOD scores identical between gravity off and gravity on",
             "threshold": "none", "depends_on_unlocked_threshold": False,
             "note": "exact equality of every score"},
            {"result": "every visible deployment input is a training input (design M)",
             "threshold": "none", "depends_on_unlocked_threshold": False,
             "note": "exact set membership"},
            {"result": "materiality: 0 with gravity off, continuous values with gravity on",
             "threshold": "none", "depends_on_unlocked_threshold": False,
             "note": "reported as values"},
            {"result": "control and experimental errors",
             "threshold": "none", "depends_on_unlocked_threshold": False,
             "note": "reported as values; no right/wrong label, the tolerance being unlocked"},
            {"result": "OOD fired or quiet at a station",
             "threshold": f"operating percentile -- shipped reference {REFERENCE_PCT:g}, fixed "
                          f"in code before this work",
             "depends_on_unlocked_threshold": False,
             "note": "the full sweep is reported; the fired/quiet pattern is identical between "
                     "gravity states at every percentile"},
            {"result": "PhysMAP flags nothing with gravity off",
             "threshold": "none", "depends_on_unlocked_threshold": False,
             "note": "holds for every theta: materiality is 0 and Ri = 0 is inside the window"},
            {"result": "PhysMAP flags at least one comparable station with gravity on",
             "threshold": "theta -- UNLOCKED", "depends_on_unlocked_threshold": True,
             "holds_for_theta_up_to": max(comp_mat)},
            {"result": "which stations PhysMAP flags",
             "threshold": "theta -- UNLOCKED", "depends_on_unlocked_threshold": True,
             "note": f"a station flags for theta up to its own materiality; shown at "
                     f"theta = {ILLUSTRATIVE_THETA:.2f}, illustrative only"},
        ],
    }


def check(record: dict) -> list[str]:
    """The stress test's own assertions. Returns the failures; empty means all hold."""
    fails = []
    ic = record["input_contract"]
    worst = max(abs(s["control_error_pct"]) for s in record["headline_design_M"]["stations"])
    if worst > 0.5:
        fails.append(f"design M: the surrogate misses the accurate gravity-off control by "
                     f"{worst:.2f} %, so it is no longer a trustworthy forced-convection model")
    if not ic["design_M_every_visible_input_exactly_in_training"]:
        fails.append("design M: a visible deployment input is not an exact training input")
    if ic["surrogate_inputs"] != ic["ood_detector_inputs"]:
        fails.append("the OOD detector does not receive exactly the surrogate's inputs")
    for key in ("headline_design_M", "secondary_design_A3"):
        if not record[key]["ood"]["identical_between_gravity_states"]:
            fails.append(f"{key}: OOD scores changed between gravity off and gravity on")
    for s in record["headline_design_M"]["stations"]:
        if s["materiality_gravity_off"] != 0.0:
            fails.append(f"x/D {s['x_over_D']}: materiality with gravity off is not zero")
    return fails


def load_banked() -> dict:
    return json.loads(checkout_path(*BANKED_RECORD,
                                    what="the banked Lewis stress-test record").read_text())


def render(record: dict) -> str:
    """Deterministic report. Continuous values first; the illustrative threshold last."""
    from physmap.benchmarks.benchmark_v0_4 import REFERENCE_PCT
    ref = str(int(REFERENCE_PCT))
    L = []
    L.append("CONTROLLED MODEL-REUSE STRESS TEST -- Lewis (1992) Test 35A")
    L.append("")
    L.append(_wrap(record["framing"]))
    L.append("")
    L.append("Claim: " + _wrap(record["claim"], indent=7).lstrip())
    L.append("")
    L.append(_wrap(record["status"]))
    L.append("")
    ic = record["input_contract"]
    L.append("INPUT CONTRACT")
    L.append(f"  surrogate receives     {', '.join(ic['surrogate_inputs'])}")
    L.append(f"  OOD detector receives  {', '.join(ic['ood_detector_inputs'])}")
    L.append(f"  neither receives       {', '.join(ic['withheld_from_both'])}")
    L.append(f"  deployment             Re {ic['deployment_inputs']['Re']}, "
             f"Pr {ic['deployment_inputs']['Pr']}, x/D at Lewis's 12 stations")
    L.append("  every visible deployment input exactly matches a training input (design M): "
             + ("YES" if ic["design_M_every_visible_input_exactly_in_training"] else "NO"))
    L.append("")
    ma = record["matched_ablation"]
    L.append("MATCHED ABLATION")
    L.append(f"  provenance {ma['provenance']}; {ma['cases'][0]} vs {ma['cases'][1]}")
    L.append(f"  only difference: {ma['only_difference'].split(';')[0]}")
    L.append(f"  energy closure {ma['full']['energy_closure_pct']:+.2f} % (full), "
             f"{ma['removed']['energy_closure_pct']:+.2f} % (removed), against the inlet-property "
             f"energy balance; {ma['iterations']} iterations each")
    L.append("")
    L.append("HEADLINE -- design M: every visible deployment input is a training input")
    L.append(f"  {'x/D':>7}   | {'surrogate error':^21} | {'input-based OOD detector':^27} | "
             f"{'PhysMAP materiality':^19}")
    L.append(f"  {'':>7}   | {'control':>9} {'experiment':>11} | {'distance':>9} {'GP var':>8} "
             f"{'@' + ref:>8} | {'grav off':>8} {'grav on':>9}")
    for s in record["headline_design_M"]["stations"]:
        on = s["ood_gravity_on"][ref]
        mark = " " if s["comparable"] else "*"
        L.append(f"  {s['x_over_D']:>7.2f} {mark} | {s['control_error_pct']:>+8.2f}% "
                 f"{s['experimental_error_pct']:>+10.1f}% | {on['distance']['score']:>9.3f} "
                 f"{on['gp_variance']['score']:>8.4f} {('fires' if on['fired'] else 'quiet'):>8} | "
                 f"{s['materiality_gravity_off']:>8.3f} {s['materiality_gravity_on']:>9.3f}")
    thr = record["headline_design_M"]["stations"][0]["ood_gravity_on"][ref]
    L.append(f"  * disowned by Lewis. OOD thresholds at the reference percentile {ref}: "
             f"distance {thr['distance']['threshold']:.3f}, GP variance "
             f"{thr['gp_variance']['threshold']:.3f}.")
    ident = record["headline_design_M"]["ood"]["identical_between_gravity_states"]
    L.append("  The OOD columns are the SAME with gravity off and on -- every score, every "
             "percentile: " + ("YES" if ident else "NO"))
    sweep = record["headline_design_M"]["ood"]["comparable_stations_fired_by_pct"]
    n_comp = sum(1 for s in record["headline_design_M"]["stations"] if s["comparable"])
    L.append("  Comparable stations where it fires, by operating percentile (both states): "
             + ", ".join(f"{pc}: {v['gravity_on']}/{n_comp}" for pc, v in sweep.items()))
    L.append("  (At low percentiles it fires on its own training data too -- see "
             "design_M_low_pct_mechanism.json.)")
    L.append("")
    L.append("SECONDARY -- design A3, the visible operating point falls BETWEEN training runs")
    sec = record["secondary_design_A3"]["ood"]
    n_comp = sum(1 for s in record["secondary_design_A3"]["stations"] if s["comparable"])
    L.append(f"  OOD fires at {sec['comparable_stations_fired_by_pct'][ref]['gravity_off']} of "
             f"{n_comp} comparable stations with gravity off (surrogate accurate) and "
             f"{sec['comparable_stations_fired_by_pct'][ref]['gravity_on']} of {n_comp} with "
             f"gravity on; scores identical between them: "
             + ("YES" if sec["identical_between_gravity_states"] else "NO"))
    L.append("  PhysMAP's materiality is the same as in the headline: it follows the physics, "
             "not the training design.")
    L.append("")
    L.append("THRESHOLDS -- which results depend on one")
    for t in record["threshold_dependence"]:
        extra = (f"holds for theta <= {t['holds_for_theta_up_to']:.3f}"
                 if "holds_for_theta_up_to" in t else t.get("note", ""))
        L.append(f"  {t['result']}")
        L.append(f"      threshold: {t['threshold']}. {extra}")
    flagged = [s["x_over_D"] for s in record["headline_design_M"]["stations"]
               if s["comparable"] and s["physmap_flag_gravity_on_at_illustrative_theta"]]
    L.append(f"  At the ILLUSTRATIVE theta = {ILLUSTRATIVE_THETA:.2f} (not a verdict; theta is "
             f"unlocked) PhysMAP would flag x/D {', '.join(f'{x:g}' for x in flagged)} with "
             f"gravity on, and nothing with gravity off.")
    L.append("")
    L.append("NOT CLAIMED")
    for n in record["not_claimed"]:
        L.append("  - " + _wrap(n, indent=4).lstrip())
    return "\n".join(L)


def _wrap(text: str, width: int = 92, indent: int = 0) -> str:
    import textwrap
    return textwrap.fill(text, width=width, initial_indent=" " * indent,
                         subsequent_indent=" " * indent)
