#!/usr/bin/env python3
"""Lewis 35A head-to-head: the SHIPPED input-based OOD detector against PhysMAP's causal path.

DEVELOPMENT DEMONSTRATION. 35A is a spent run: every station of it has been inspected against
agreement. Stations along one tube are measurements of ONE operating condition, not independent
cases. No precision, recall or F1 is computed here, and none may be computed from this output.

WHAT IS COMPARED, AND WHY IT IS A FAIR FIGHT

The input-based OOD detector is the one the seven-vehicle benchmark ships -- the SAME tuple
object, imported from physmap.benchmarks.benchmark_v0_4, not rebuilt: Mahalanobis k=3
distance-to-training, and a Matern-5/2 GP whose signal is posterior std / |mean|. Each fires
when its score exceeds the given percentile of the TRAINING rows' own scores (GP floored at
0.05), swept over the benchmark's operating percentiles with 99 as reference.

Both detectors judge the SAME surrogate, and the OOD detector receives EVERY input the surrogate
receives -- including position. That input contract is recorded in the output, not implied.

The surrogate is the NAFEMS original's own recipe: a forced-convection model fitted to
GRAVITY-OFF CFD. It mirrors the benchmark's buoyancy vehicle (Jin): a surrogate that omits the
buoyancy mechanism, detectors fitted on benign rows that span the same inputs as the deploy
rows, and a physics difference that is not an input. Its training set brackets 35A's inputs
WITHOUT containing them, so 35A is interpolated, not memorised.

PhysMAP's output is the CAUSAL path -- the applicability screen, the matched-ablation
materiality, and the flag rule -- because the guardrail's closure-validity layer has no laminar
vertical-tube closure in the shipped corpus (every pipe regime maps to a turbulent closure with
Re >= 3000). Run under a turbulent pipe regime it would fire on Re alone at every station, for a
reason unrelated to buoyancy. That is reported as a side check, not used as PhysMAP's answer.
"""
from __future__ import annotations
import csv, json, math, pathlib, sys, tempfile

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import foamread

from physmap.benchmarks.benchmark_v0_4 import _DETECTORS, OPERATING_PERCENTILES, REFERENCE_PCT
from physmap.guardrail.guardrail import CredibilityGuardrail
from physmap.guardrail.configs import ColumnMap
from physmap.guardrail.enums import DetectorKind, Regime
from physmap.applicability.screen import screen_case
from physmap.core.mechanism import CalibrationWindow, Mechanism
from physmap.materiality.estimator import (
    AblationInputs, AblationProvenance, estimate_materiality, materiality_signal)
from physmap.release import EvidenceState

D, L = 0.0119, 1.900
NR, NY = 30, 400

# Lewis Appendix B polynomials (Kelvin form), for each training run's OWN inlet-bulk values.
_K  = [-0.4929251144, 5.918453387e-3, -7.434436e-6]
_CP = [253366.415, -3743.596413, 22.47767125, -0.06741382257, 1.009647131e-4, -6.038683e-8]
_RH = [-6728.681145, 112.1662054, -0.6544616402, 1.924924029e-3, -2.855835157e-6, 1.702156e-9]
def _ev(c, T): return sum(a * T ** i for i, a in enumerate(c))

# Lewis Test 35A, Appendix D-2 -- the experimental truth, and the reported deploy inputs.
LEWIS_35A = [(0.31, 33.72), (0.85, 32.69), (2.45, 22.15), (5.65, 19.07), (9.92, 14.92),
             (16.32, 13.95), (33.39, 10.76), (50.47, 9.38), (67.55, 9.37), (101.69, 8.41),
             (135.84, 7.99), (159.33, 8.82)]
RE_35A, PR_35A, GRQ_35A = 1143.4, 8.46, 3.7466e5
RI_35A = GRQ_35A / RE_35A ** 2
# Lewis disowns three stations on his own authority, for reasons unrelated to buoyancy.
DISOWNED = {0.31: "axial wall conduction (Lewis Sec 7.1.1)",
            0.85: "axial wall conduction (Lewis Sec 7.1.1)",
            159.33: "'suspect' -- flange heat loss (Lewis Sec 7.1.1)"}
# The bulk-temperature error expressed as a Nu uncertainty grows linearly along the tube;
# 35A: 1.2 % at mid-tube and 3.6 % at the exit (data/lewis1992/closing_checks.json).
def bulk_unc_pct(xd): return 3.6 * (xd / 159.66)


def lewis_nu(case: pathlib.Path, time: str, xds) -> list[float]:
    """Local Nu by LEWIS'S definition, using the case's own operating point: linear bulk from
    the inlet to the CALCULATED exit, reduced on the case's own inlet-bulk k. Wall temperature
    is read from the patch. Linear interpolation between cell centres."""
    m = json.loads((case / "case.json").read_text())
    # Cases generated before the operating-point overrides existed record the same three
    # values under their original names. Read those -- never assume 35A's defaults.
    op = m.get("operating_point") or {"T_in_C": m["T_inlet_C"],
                                      "V_dot_L_min": m["V_dot_L_min"],
                                      "q_w_W_m2": m["q_w_W_m2"]}
    T_in = op["T_in_C"] + 273.15
    vdot = op["V_dot_L_min"] / 60000.0
    q = op["q_w_W_m2"]
    rho, cp, k = _ev(_RH, T_in), _ev(_CP, T_in), _ev(_K, T_in)
    dT_cal = q * math.pi * D * L / (rho * vdot * cp)
    ne, nx = m["ny_entry"], m.get("ny_exit", 0)
    Tw = foamread.read_patch(case / time / "T", "wall")[ne:ne + NY]
    dy = L / NY
    xs = [((j + 0.5) * dy) / D for j in range(NY)]
    nu = [q * D / (k * (Tw[j] - (T_in + dT_cal * ((j + 0.5) * dy) / L))) for j in range(NY)]
    return [float(np.interp(x, xs, nu)) for x in xds]


def latest_time(case: pathlib.Path) -> str:
    """The last written time directory. Training runs are carried to convergence rather than
    to a fixed count, so the low-Re runs finish later than the high-Re ones."""
    return str(max(int(p.name) for p in case.iterdir() if p.name.isdigit() and p.name != "0"))


def training_table(doe_dirs) -> list[dict]:
    """Forty log-spaced stations per gravity-off run -- a practitioner's sampling, not keyed to
    Lewis's thermocouple positions."""
    xds = list(np.geomspace(0.3, 159.5, 40))
    rows = []
    for d in doe_dirs:
        m = json.loads((d / "case.json").read_text())
        v = m["inlet_bulk_values"]
        for xd, nu in zip(xds, lewis_nu(d, latest_time(d), xds)):
            rows.append({"run": d.name, "Re": v["Re"], "Pr": v["Pr"], "x_over_D": xd,
                         "Nu": nu, "q_w": m["operating_point"]["q_w_W_m2"],
                         "gravity_on": m["gravity_on"]})
    return rows


def _X(rows):
    return np.array([[math.log10(r["Re"]), r["Pr"], math.log10(r["x_over_D"])] for r in rows])


def fit_surrogate(rows):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    X, y = _X(rows), np.log([r["Nu"] for r in rows])
    mu, sd = X.mean(0), X.std(0)
    kern = ConstantKernel(1.0) * Matern(length_scale=[1.0, 1.0, 1.0], nu=2.5) + WhiteKernel(1e-6)
    gp = GaussianProcessRegressor(kernel=kern, normalize_y=True, n_restarts_optimizer=3,
                                  random_state=0).fit((X - mu) / sd, y)
    def predict(rs):
        return np.exp(gp.predict((_X(rs) - mu) / sd))
    predict.kernel = str(gp.kernel_)
    return predict


def _write(rows, path, pred):
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Re", "Pr", "x_over_D", "truth", "prediction"])
        for r, p in zip(rows, pred):
            w.writerow([r["Re"], r["Pr"], r["x_over_D"], r["Nu"], float(p)])


def run_detectors(train, train_pred, test, test_pred, regime: Regime) -> dict:
    """The benchmark's own detector tuple, fitted and assessed through the public API exactly as
    run_cell does it, over the benchmark's own operating percentiles."""
    colmap = ColumnMap(inputs=["Re", "Pr", "x_over_D"], truth="truth", prediction="prediction")
    out = {}
    with tempfile.TemporaryDirectory() as td:
        tr, te = pathlib.Path(td) / "train.csv", pathlib.Path(td) / "test.csv"
        _write(train, tr, train_pred)
        _write(test, te, test_pred)
        for pct in OPERATING_PERCENTILES:
            g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr", "x_over_D"], regime=regime,
                                     detectors=_DETECTORS, operating_pct=float(pct))
            g.fit(tr, columns=colmap)
            res = []
            for a in g.assess(te, columns=colmap):
                s = {}
                for kind, key in ((DetectorKind.DISTANCE_TO_TRAINING, "distance"),
                                  (DetectorKind.GP_VARIANCE, "gp_variance"),
                                  (DetectorKind.CLOSURE_VALIDITY, "closure_validity")):
                    sig = a.signals.get(kind)
                    s[key] = None if sig is None else {
                        "fired": bool(sig.fired), "score": _f(sig.score),
                        "threshold": _f(sig.threshold),
                        "rationale": sig.rationale}
                res.append(s)
            out[str(pct)] = res
    return out


def _f(v):
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    runs = pathlib.Path(sys.argv[1])            # directory holding doe_* and pair_g{ON,OFF}
    out_json = pathlib.Path(sys.argv[2])
    # Which training design. A = the pre-committed 8 runs; A3 = A plus the pre-committed
    # third inlet level (13.25 degC). Nothing else may be selected here.
    design = sys.argv[3] if len(sys.argv) > 3 else "A"
    if design == "M":
        return main_matched(runs, out_json)
    levels = {"A": ("T12p0", "T14p5"), "A3": ("T12p0", "T13p25", "T14p5")}[design]
    doe = sorted(p for p in runs.glob("doe_*")
                 if p.name.split("_")[-1] in levels and latest_time(p) in ("2000", "4000"))
    expected = 4 * len(levels)
    assert len(doe) == expected, f"design {design}: expected {expected} runs, found {len(doe)}"

    train = training_table(doe)
    assert not any(r["gravity_on"] for r in train), "a training run had gravity ON"
    surrogate = fit_surrogate(train)

    # leave-one-run-out: how good is the surrogate in its OWN (forced-convection) regime?
    loro = {}
    for d in doe:
        tr = [r for r in train if r["run"] != d.name]
        te = [r for r in train if r["run"] == d.name]
        p = fit_surrogate(tr)(te)
        e = [100 * (pi / r["Nu"] - 1) for pi, r in zip(p, te)]
        loro[d.name] = {"max_abs_pct": round(max(abs(x) for x in e), 2),
                        "mean_abs_pct": round(sum(abs(x) for x in e) / len(e), 2)}

    xds = [x for x, _ in LEWIS_35A]
    test = [{"Re": RE_35A, "Pr": PR_35A, "x_over_D": x, "Nu": nu} for x, nu in LEWIS_35A]
    pred = surrogate(test)

    # does the surrogate reproduce gravity-off CFD at 35A? (interpolation fidelity)
    nu_off = lewis_nu(runs / "pair_gOFF", "3000", xds)
    nu_on = lewis_nu(runs / "pair_gON", "3000", xds)
    interp = [round(100 * (p / o - 1), 2) for p, o in zip(pred, nu_off)]

    det = run_detectors(train, surrogate(train), test, pred, Regime.UNLISTED)
    det_side = run_detectors(train, surrogate(train), test, pred, Regime.ENTRANCE_REGION_PIPE)

    # PhysMAP causal path
    screen = screen_case("lewis-35A", "local_Nusselt_number", qoi_decomposes=True,
                         mechanisms_separable=True, has_calibration_window=True,
                         ablation_available=True, evidence_state=EvidenceState.MEASURED)
    # The surrogate's calibration window for buoyancy is its training data's: every training
    # run had g = 0, so the window is Ri = 0 exactly. Derived from the surrogate, not chosen.
    mech = Mechanism("buoyancy-vertical-pipe-aiding", "buoyancy (Richardson number)",
                     CalibrationWindow("richardson_number", 0.0, 0.0), RI_35A)

    stations = []
    for i, (xd, nu_exp) in enumerate(LEWIS_35A):
        r = estimate_materiality(mech, "local_Nusselt_number",
                                 AblationInputs(nu_on[i], nu_off[i],
                                                AblationProvenance.MATCHED_ABLATION),
                                 evidence_state=EvidenceState.MEASURED)
        ref = det[str(int(REFERENCE_PCT))][i]
        stations.append({
            "x_over_D": xd,
            "comparable": xd not in DISOWNED,
            "why_not_comparable": DISOWNED.get(xd),
            "surrogate_prediction": round(float(pred[i]), 3),
            "experimental_Nu": nu_exp,
            "prediction_error_pct": round(100 * (float(pred[i]) / nu_exp - 1), 2),
            "experimental_bulk_error_unc_pct": round(bulk_unc_pct(xd), 2),
            "ood_at_ref_pct": {"distance": ref["distance"], "gp_variance": ref["gp_variance"],
                               "either_fired": bool(ref["distance"]["fired"]
                                                    or ref["gp_variance"]["fired"])},
            "ood_fired_at_any_pct": any(det[p][i]["distance"]["fired"]
                                        or det[p][i]["gp_variance"]["fired"] for p in det),
            "ood_fired_by_pct": {p: bool(det[p][i]["distance"]["fired"]
                                         or det[p][i]["gp_variance"]["fired"]) for p in det},
            "physmap": {
                "applicability": screen.applicability.value,
                "mechanism_outside_calibration": mech.outside_calibration(),
                "materiality": None if r.value is None else round(r.value, 4),
                "materiality_status": r.status.value,
                "flag_theta_0p10": materiality_signal(mech, r, theta=0.10).fired,
                "flag_theta_0p20": materiality_signal(mech, r, theta=0.20).fired},
            "nu_gravity_on_cfd": round(nu_on[i], 3), "nu_gravity_off_cfd": round(nu_off[i], 3),
            "surrogate_vs_gravity_off_cfd_pct": interp[i],
        })

    out = {
        "status": "DEVELOPMENT DEMONSTRATION. 35A is spent. Stations are not cases. No "
                  "precision, recall or F1.",
        "input_contract": {
            "surrogate_inputs": ["Re", "Pr", "x_over_D"],
            "ood_detector_features": ["log10_Re", "Pr", "x_over_D"],
            "mapping": "the guardrail's own input_to_feature: Re -> log10_Re; Pr and x_over_D "
                       "pass through. Identical to the surrogate's inputs; position included.",
            "NOT_an_input_to_either": ["Gr_q", "Ri", "wall heat flux", "gravity",
                                       "flow direction"],
            "deploy_inputs_35A": {"Re": RE_35A, "Pr": PR_35A,
                                  "source": "Lewis Appendix D-2, inlet-bulk basis"},
        },
        "ood_detector": {
            "object": "physmap.benchmarks.benchmark_v0_4._DETECTORS, imported unchanged",
            "baselines": "distance_to_training (Mahalanobis, k=3) OR gp_variance (Matern-5/2, "
                         "posterior std / |mean|, threshold floored at 0.05)",
            "threshold": "percentile of the training rows' own scores",
            "operating_percentiles": list(OPERATING_PERCENTILES),
            "reference_pct": REFERENCE_PCT,
            "regime_for_the_run": "UNLISTED -- statistical layer only; see side check",
        },
        "surrogate": {
            "recipe": "GP on (log10 Re, Pr, log10 x/D) -> log Nu, fitted to GRAVITY-OFF "
                      "variable-property CFD (Lewis Appendix B properties), Nu reduced by "
                      "Lewis's own definition with each run's own inlet-bulk k",
            "kernel_fitted": surrogate.kernel,
            "training_runs": [d.name for d in doe],
            "training_rows": len(train),
            "design": design,
            "doe": ("Re {750, 950, 1350, 1550} x inlet " +
                    ("{12.0, 14.5}" if design == "A" else "{12.0, 13.25, 14.5}") +
                    " degC, q_w fixed at 35A's 12749.6 W/m2; 35A (Re 1143, 13.06 degC) is "
                    "interior, not a node"),
            "leave_one_run_out": loro,
            "fidelity_at_35A": "surrogate versus gravity-off CFD at 35A's exact conditions, "
                               "per station, in stations[].surrogate_vs_gravity_off_cfd_pct",
        },
        "physmap": {
            "applicability": {"verdict": screen.applicability.value,
                              "reason_code": screen.reason_code.value,
                              "rationale": screen.rationale},
            "mechanism_window": mech.window.describe(),
            "why_that_window": "every training run had g = 0; the surrogate has never seen "
                               "buoyancy, so its calibrated range for Ri is exactly zero",
            "operating_Ri": round(RI_35A, 4),
            "theta_note": "theta is DECISION_REQUIRED in the protocol. Flags are shown at 0.10 "
                          "(the NAFEMS abstract's value) and 0.20 as illustrations only.",
        },
        "side_check_closure_validity_under_turbulent_regime": {
            "regime": "ENTRANCE_REGION_PIPE (gnielinski-1976, turbulent)",
            "fired_per_station_at_ref": [det_side[str(int(REFERENCE_PCT))][i]["closure_validity"]["fired"]
                                         if det_side[str(int(REFERENCE_PCT))][i]["closure_validity"] else None
                                         for i in range(len(xds))],
            "input_detectors_identical_to_UNLISTED_run": all(
                det_side[p][i]["distance"]["fired"] == det[p][i]["distance"]["fired"]
                and det_side[p][i]["gp_variance"]["fired"] == det[p][i]["gp_variance"]["fired"]
                for p in det for i in range(len(xds))),
        },
        "stations": stations,
    }
    out_json.write_text(json.dumps(out, indent=2) + "\n")
    return 0


def matched_rows(case: pathlib.Path) -> list[dict]:
    """The one change in design M: a gravity-off run AT 35A's operating point, sampled at the
    same 40 stations as every other run PLUS Lewis's 12, and labelled with the EVALUATED inputs
    (Re 1143.4, Pr 8.46) so every evaluated (Re, Pr, x/D) is an exact training input. Its
    polynomial-evaluated inlet values differ by -0.062 % and +0.141 % (pre-declared)."""
    m = json.loads((case / "case.json").read_text())
    assert m["gravity_on"] is False, "the matched training run must be gravity-off"
    xds = sorted(set(float(x) for x in np.geomspace(0.3, 159.5, 40)) | {x for x, _ in LEWIS_35A})
    return [{"run": case.name, "Re": RE_35A, "Pr": PR_35A, "x_over_D": xd, "Nu": nu,
             "q_w": m.get("q_w_W_m2"), "gravity_on": False}
            for xd, nu in zip(xds, lewis_nu(case, latest_time(case), xds))]


def _in_sample_alarm_rate(train, train_pred) -> dict:
    """Fraction of TRAINING rows that fire at each percentile -- the detector's built-in alarm
    rate, since each training point is its own nearest neighbour. Context, not a criterion."""
    colmap = ColumnMap(inputs=["Re", "Pr", "x_over_D"], truth="truth", prediction="prediction")
    out = {}
    with tempfile.TemporaryDirectory() as td:
        tr = pathlib.Path(td) / "train.csv"
        _write(train, tr, train_pred)
        for pct in OPERATING_PERCENTILES:
            g = CredibilityGuardrail(surrogate_inputs=["Re", "Pr", "x_over_D"],
                                     regime=Regime.UNLISTED, detectors=_DETECTORS,
                                     operating_pct=float(pct))
            g.fit(tr, columns=colmap)
            a = g.assess(tr, columns=colmap)
            n = sum(1 for x in a if x.signals[DetectorKind.DISTANCE_TO_TRAINING].fired
                    or x.signals[DetectorKind.GP_VARIANCE].fired)
            out[str(pct)] = round(n / len(a), 4)
    return out


def main_matched(runs: pathlib.Path, out_json: pathlib.Path) -> int:
    base = sorted(p for p in runs.glob("doe_*")
                  if p.name.split("_")[-1] in ("T12p0", "T13p25", "T14p5")
                  and latest_time(p) in ("2000", "4000"))
    assert len(base) == 12, f"design M builds on A3's 12 runs; found {len(base)}"
    train = training_table(base) + matched_rows(runs / "pair_gOFF")
    assert not any(r["gravity_on"] for r in train), "a training row had gravity ON"
    surrogate = fit_surrogate(train)
    train_pred = surrogate(train)

    loro = {}
    for name in sorted({r["run"] for r in train}):
        tr = [r for r in train if r["run"] != name]
        te = [r for r in train if r["run"] == name]
        pr = fit_surrogate(tr)(te)
        e = [100 * (a / r["Nu"] - 1) for a, r in zip(pr, te)]
        loro[name] = {"max_abs_pct": round(max(abs(x) for x in e), 3),
                      "mean_abs_pct": round(sum(abs(x) for x in e) / len(e), 3)}

    xds = [x for x, _ in LEWIS_35A]
    nu_off = lewis_nu(runs / "pair_gOFF", "3000", xds)
    nu_on = lewis_nu(runs / "pair_gON", "3000", xds)
    tests = {
        "gravity_on_experiment": [{"Re": RE_35A, "Pr": PR_35A, "x_over_D": x, "Nu": n}
                                  for x, n in LEWIS_35A],
        "gravity_off_control": [{"Re": RE_35A, "Pr": PR_35A, "x_over_D": x, "Nu": n}
                                for x, n in zip(xds, nu_off)],
    }
    exact = all(any(r["Re"] == t["Re"] and r["Pr"] == t["Pr"] and r["x_over_D"] == t["x_over_D"]
                    for r in train) for t in tests["gravity_on_experiment"])

    screen = screen_case("lewis-35A", "local_Nusselt_number", qoi_decomposes=True,
                         mechanisms_separable=True, has_calibration_window=True,
                         ablation_available=True, evidence_state=EvidenceState.MEASURED)
    window = CalibrationWindow("richardson_number", 0.0, 0.0)
    mechs = {"gravity_on_experiment": Mechanism("buoyancy-vertical-pipe-aiding",
                                                "buoyancy (Richardson number)", window, RI_35A),
             "gravity_off_control": Mechanism("buoyancy-vertical-pipe-aiding",
                                              "buoyancy (Richardson number)", window, 0.0)}
    ref = str(int(REFERENCE_PCT))
    states = {}
    for state, test in tests.items():
        pred = surrogate(test)
        det = run_detectors(train, train_pred, test, pred, Regime.UNLISTED)
        rows = []
        for i, (xd, t) in enumerate(zip(xds, test)):
            q_full, q_abl = (nu_on[i], nu_off[i]) if state == "gravity_on_experiment" \
                else (nu_off[i], nu_off[i])
            r = estimate_materiality(mechs[state], "local_Nusselt_number",
                                     AblationInputs(q_full, q_abl,
                                                    AblationProvenance.MATCHED_ABLATION),
                                     evidence_state=EvidenceState.MEASURED)
            d99 = det[ref][i]
            rows.append({
                "x_over_D": xd, "comparable": xd not in DISOWNED,
                "surrogate_prediction": round(float(pred[i]), 4), "truth": round(t["Nu"], 4),
                "prediction_error_pct": round(100 * (float(pred[i]) / t["Nu"] - 1), 3),
                "ood_ref": {"distance": d99["distance"], "gp_variance": d99["gp_variance"],
                            "either_fired": bool(d99["distance"]["fired"]
                                                 or d99["gp_variance"]["fired"])},
                "ood_fired_by_pct": {p: bool(det[p][i]["distance"]["fired"]
                                             or det[p][i]["gp_variance"]["fired"]) for p in det},
                "physmap": {"applicability": screen.applicability.value,
                            "mechanism_outside_calibration":
                                mechs[state].outside_calibration(),
                            "materiality": None if r.value is None else round(r.value, 4),
                            "flag_theta_0p10": materiality_signal(mechs[state], r,
                                                                  theta=0.10).fired,
                            "flag_theta_0p20": materiality_signal(mechs[state], r,
                                                                  theta=0.20).fired}})
        states[state] = {"stations": rows, "detectors_raw": det}

    on, off = states["gravity_on_experiment"]["stations"], states["gravity_off_control"]["stations"]
    identical = all(states["gravity_on_experiment"]["detectors_raw"][p][i]
                    == states["gravity_off_control"]["detectors_raw"][p][i]
                    for p in states["gravity_on_experiment"]["detectors_raw"]
                    for i in range(len(xds)))
    comp = lambda rows: [r for r in rows if r["comparable"]]
    c1 = not any(r["ood_ref"]["either_fired"] for r in comp(on) + comp(off))
    c2 = any(r["physmap"]["flag_theta_0p10"] for r in comp(on))
    c3 = not any(r["physmap"]["flag_theta_0p10"] for r in off)
    fired_at_ref = sorted({r["x_over_D"] for r in comp(on) + comp(off)
                           if r["ood_ref"]["either_fired"]})

    out = {
        "design": "M -- operating-point-matched, pre-declared in PREDECLARE_design_M_matched.md",
        "status": "DEVELOPMENT DEMONSTRATION. 35A is spent; stations are not cases; no "
                  "precision, recall or F1.",
        "input_contract": {"surrogate_inputs": ["Re", "Pr", "x_over_D"],
                           "ood_detector_features": ["log10_Re", "Pr", "x_over_D"],
                           "withheld_from_both": ["gravity", "Ri", "Gr_q", "wall heat flux",
                                                  "flow direction"],
                           "every_evaluated_input_is_an_exact_training_input": exact},
        "training": {"runs": sorted({r["run"] for r in train}), "rows": len(train),
                     "matched_run": "pair_gOFF, labelled Re 1143.4 Pr 8.46 (pre-declared)",
                     "leave_one_run_out": loro, "kernel_fitted": surrogate.kernel},
        "in_sample_alarm_rate_by_pct": _in_sample_alarm_rate(train, train_pred),
        "ood_output_identical_between_gravity_states": identical,
        "predeclared_criteria": {
            "1_ood_quiet_at_every_comparable_station_both_states_at_99": c1,
            "2_physmap_flags_a_comparable_station_with_gravity_on": c2,
            "3_physmap_flags_nothing_with_gravity_off": c3,
            "stronger_claim_supported": bool(c1 and c2 and c3),
            "comparable_stations_where_ood_fired_at_99": fired_at_ref},
        "states": {k: {"stations": v["stations"]} for k, v in states.items()},
    }
    out_json.write_text(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
