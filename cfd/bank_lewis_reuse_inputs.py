#!/usr/bin/env python3
"""Bank the CFD-derived inputs of the Lewis model-reuse stress test into the checkout.

The stress test's one-command path (`physmap stress-test lewis-reuse`) must run from a clone,
without Docker or OpenFOAM -- the same way `physmap benchmark run` runs from its committed
substrate data. This script is the bridge: it reads the solved OpenFOAM cases, extracts local
Nu by Lewis's own definition, and writes every number the stress test needs, at full float
precision, with the provenance of each case beside it.

Regenerating the CASES is documented in the manifest and needs Docker; regenerating THIS FILE
from existing cases needs only Python. Nothing downstream of it needs either.
"""
from __future__ import annotations
import hashlib, json, math, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import foamread
import lewis_head_to_head as H

_RH = [-6728.681145, 112.1662054, -0.6544616402, 1.924924029e-3, -2.855835157e-6, 1.702156e-9]
_CP = [253366.415, -3743.596413, 22.47767125, -0.06741382257, 1.009647131e-4, -6.038683e-8]
_ev = lambda c, T: sum(a * T ** i for i, a in enumerate(c))


def _residuals(case: pathlib.Path) -> dict:
    last = None
    for sub in sorted((case / "postProcessing/residuals").iterdir(), key=lambda p: float(p.name)):
        f = sub / "solverInfo.dat"
        hdr = [l for l in open(f) if l.startswith("#") and "Time" in l][0].lstrip("#").split()
        rows = [l.split() for l in open(f) if not l.startswith("#")]
        if rows:
            last = {k: float(rows[-1][hdr.index(k)])
                    for k in ("Ux_initial", "Uy_initial", "h_initial", "p_rgh_initial")}
    return last


def _energy_and_reversal(case: pathlib.Path, t: str) -> tuple[float, int]:
    m = json.loads((case / "case.json").read_text())
    op = m.get("operating_point") or {"T_in_C": m["T_inlet_C"], "V_dot_L_min": m["V_dot_L_min"],
                                      "q_w_W_m2": m["q_w_W_m2"]}
    T = foamread.read_internal(case / t / "T"); U = foamread.read_internal(case / t / "U")
    ne, nr, ny = m["ny_entry"], H.NR, H.NY
    aw = foamread.radial_weights(nr, H.D / 2)
    def mix(k):
        Tk = T[k * nr:(k + 1) * nr]; uy = [u[1] for u in U[k * nr:(k + 1) * nr]]
        return sum(a * u * x for a, u, x in zip(aw, uy, Tk)) / sum(a * u for a, u in zip(aw, uy))
    Tin = op["T_in_C"] + 273.15; vd = op["V_dot_L_min"] / 60000
    ideal = op["q_w_W_m2"] * math.pi * H.D * H.L / (_ev(_RH, Tin) * vd * _ev(_CP, Tin))
    closure = 100 * ((mix(ne + ny - 1) - mix(ne)) / ideal - 1)
    reversed_cells = sum(1 for u in U[ne * nr:(ne + ny) * nr] if u[1] < 0)
    return closure, reversed_cells


def _case_record(case: pathlib.Path, xds: list[float]) -> dict:
    m = json.loads((case / "case.json").read_text())
    t = H.latest_time(case)
    closure, rev = _energy_and_reversal(case, t)
    op = m.get("operating_point") or {"T_in_C": m["T_inlet_C"], "V_dot_L_min": m["V_dot_L_min"],
                                      "q_w_W_m2": m["q_w_W_m2"]}
    return {
        "case": case.name,
        "gravity_on": m["gravity_on"],
        "operating_point": op,
        "inlet_bulk": {k: m["inlet_bulk_values"][k] for k in ("Re", "Pr", "mu", "k", "cp", "rho")},
        "mesh": {"nr": H.NR, "ny_heated": H.NY, "ny_entry": m["ny_entry"],
                 "ny_exit": m.get("ny_exit", 0)},
        "iterations": int(t),
        "gamg_max_iter": m.get("gamg_max_iter"),
        "final_initial_residuals": _residuals(case),
        "energy_closure_pct": round(closure, 4),
        "reversed_cells_in_heated_section": rev,
        "x_over_D": xds,
        "Nu": H.lewis_nu(case, t, xds),
    }


def main() -> int:
    runs = pathlib.Path(sys.argv[1])
    out_dir = pathlib.Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    grid40 = [float(x) for x in H.np.geomspace(0.3, 159.5, 40)]
    lewis12 = [x for x, _ in H.LEWIS_35A]
    doe = sorted(p for p in runs.glob("doe_*")
                 if p.name.split("_")[-1] in ("T12p0", "T13p25", "T14p5"))
    assert len(doe) == 12, len(doe)

    # The matched pair must differ ONLY in constant/g. Checked here, recorded in the manifest.
    diff = subprocess.run(["diff", "-rq", "--exclude=polyMesh", "--exclude=[0-9]*",
                           "--exclude=postProcessing", "--exclude=log.*",
                           str(runs / "pair_gON" / "constant"), str(runs / "pair_gOFF" / "constant")],
                          capture_output=True, text=True).stdout.strip().splitlines()
    sysdiff = subprocess.run(["diff", "-rq", str(runs / "pair_gON" / "system"),
                              str(runs / "pair_gOFF" / "system")],
                             capture_output=True, text=True).stdout.strip()
    zerodiff = subprocess.run(["diff", "-rq", str(runs / "pair_gON" / "0"),
                               str(runs / "pair_gOFF" / "0")],
                              capture_output=True, text=True).stdout.strip()
    assert [l for l in diff if "/g " not in l and not l.endswith("/g differ")] == [], diff
    assert sysdiff == "" and zerodiff == "", (sysdiff, zerodiff)

    profiles = {
        "training_runs": [_case_record(d, grid40) for d in doe],
        "matched_training_run": _case_record(runs / "pair_gOFF", sorted(set(grid40) | set(lewis12))),
        "ablation_full": _case_record(runs / "pair_gON", lewis12),
        "ablation_removed": _case_record(runs / "pair_gOFF", lewis12),
    }
    for r in profiles["training_runs"] + [profiles["matched_training_run"]]:
        assert r["gravity_on"] is False, r["case"]
        assert abs(r["energy_closure_pct"]) < 0.5 and r["reversed_cells_in_heated_section"] == 0, r["case"]
    blob = json.dumps(profiles, indent=1)
    (out_dir / "cfd_profiles.json").write_text(blob + "\n")
    sha = hashlib.sha256((blob + "\n").encode()).hexdigest()

    manifest = {
        "what": "CFD-derived inputs to the Lewis model-reuse stress test. Every number the "
                "one-command path needs, at full float precision.",
        "cfd_profiles_sha256": sha,
        "solver": "OpenFOAM v2312 (docker image opencfd/openfoam-default:2312), buoyantSimpleFoam",
        "case_generator": "cfd/gencase_lewis_vp.py -- variable water properties from Lewis "
                          "Appendix B, 2.5 d unheated entry, 15 d unheated exit, uniform wall flux",
        "nu_extraction": "cfd/lewis_head_to_head.py:lewis_nu -- Lewis's own definition: linear "
                         "bulk to the calculated exit, each run's own inlet-bulk k, wall "
                         "temperature read from the patch",
        "regenerate_this_file": "python cfd/bank_lewis_reuse_inputs.py <runs-dir> "
                                "data/stress_tests/lewis_reuse",
        "regenerate_the_cases": "for each case in cfd_profiles.json: python cfd/gencase_lewis_vp.py "
                                "--nr 30 --ny 400 --exit-diameters 15 plus that case's recorded "
                                "operating point, gravity, iterations and gamg_max_iter; then "
                                "blockMesh and buoyantSimpleFoam in the docker image above",
        "matched_ablation": {
            "provenance": "matched_ablation",
            "energy_closure_reference": "inlet-property energy balance; see energy_closure_definition",
            "cases": ["pair_gON", "pair_gOFF"],
            "only_difference": "constant/g -- (0 -9.81 0) versus (0 0 0); a recursive diff of "
                               "system/, 0/ and constant/ excluding the generated mesh is otherwise "
                               "empty, checked when this file was written",
            "iterations": 3000,
            "iteration_check": "the gravity-on half at 3000 reproduces a 25000-iteration run to "
                               "within 0.063 % at every station",
        },
        "training_acceptance": "every training run closes energy within 0.5 % with no reversed "
                               "cells; asserted when this file was written",
        "energy_closure_definition": "mixing-cup temperature rise across the heated section "
                                     "against Q / (m_dot * cp), with cp and rho at the run's "
                                     "INLET bulk temperature. cp falls as water heats, so a "
                                     "correctly converged case sits slightly POSITIVE on this "
                                     "measure. For the matched pair this reads +0.15 % and "
                                     "+0.30 %; against Lewis's own calculated rise of 16.94 K "
                                     "the same fields read -0.05 % and +0.11 %. Two references, "
                                     "one flow field.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {out_dir}/cfd_profiles.json (sha256 {sha[:16]}...) and manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
