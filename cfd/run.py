#!/usr/bin/env python3
"""Generate, solve and post-process one case. Records everything needed to reproduce it.

Numerical acceptance is judged on the CFD's own checks -- residuals, continuity, energy
balance, grid convergence, Nusselt-extraction sensitivity. The Eq 13 comparison is
computed and reported SEPARATELY and is never an acceptance gate.
"""
from __future__ import annotations
import argparse, json, pathlib, re, shutil, subprocess, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import foamread
from gencase import build, K_TH, CP, D, L

IMAGE = "opencfd/openfoam-default:2312"


def docker(workdir: pathlib.Path, case: str, cmd: str) -> tuple[int, str]:
    p = subprocess.run(
        ["docker", "run", "--rm", "--platform", "linux/arm64",
         "-v", f"{workdir}:/work", IMAGE, "bash", "-c", f"cd /work/{case} && {cmd}"],
        capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def last_residuals(log: str) -> dict:
    out = {}
    for fld, pat in (("Ux", r"Solving for Ux, Initial residual = ({n})"),
                     ("Uy", r"Solving for Uy, Initial residual = ({n})"),
                     ("h",  r"Solving for h, Initial residual = ({n})"),
                     ("p_rgh", r"Solving for p_rgh, Initial residual = ({n})")):
        m = re.findall(pat.replace("{n}", r"[-+0-9.eE]+"), log)
        if m:
            out[fld] = float(re.findall(r"[-+0-9.eE]+", m[-1])[-1])
    m = re.findall(r"cumulative = ([-+0-9.eE]+)", log)
    if m:
        out["continuity_cumulative"] = float(m[-1])
    return out


def outlet_bulk_T(case: pathlib.Path) -> float | None:
    """Flux-weighted outlet temperature from the solver's OWN patch integral.

    Not the last cell centre. Using the last cell instead cost a systematic 3.7% in the
    energy balance -- the half-cell offset plus the difference between a cell-centre
    reconstruction and a face integral. Measured, not argued: at q_w = 50 the closure
    moves from 3.70% to 0.07% when read from the patch.
    """
    f = case / "postProcessing/inletOutletBalance/0/surfaceFieldValue.dat"
    if not f.exists():
        return None
    last = [ln for ln in f.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
    return float(last[-1].split()[-1]) if last else None


def energy_balance(case: pathlib.Path, nu: dict, q_w: float, mdot: float) -> dict:
    """Wall heat in versus enthalpy rise out. A closure check, not a tuning knob."""
    area = 3.141592653589793 * D * L
    Q_wall = q_w * area
    Tb_patch = outlet_bulk_T(case)
    Tb = Tb_patch if Tb_patch is not None else nu["Tb_flux_outlet"]
    dT = Tb - 300.0
    Q_fluid = mdot * CP * dT
    return {"Q_wall_W": Q_wall, "Q_fluid_W": Q_fluid, "mdot_kg_s": mdot,
            "T_outlet_bulk_K": Tb, "from_patch_integral": Tb_patch is not None,
            "dT_bulk_K": dT,
            "closure_rel_error": abs(Q_wall - Q_fluid) / Q_wall if Q_wall else None}


def run(out: pathlib.Path, workdir: pathlib.Path, Re: float, q_w: float, gravity: bool,
        nr: int, ny: int, iters: int) -> dict:
    name = out.name
    meta = build(out, Re, q_w, gravity, nr, ny, iters, write_interval=iters)
    t0 = time.time()
    rc, log_bm = docker(workdir, name, "blockMesh")
    if rc: raise RuntimeError(f"blockMesh failed:\n{log_bm[-2000:]}")
    rc, log_cm = docker(workdir, name, "checkMesh")
    rc, log = docker(workdir, name, "buoyantSimpleFoam")
    wall = time.time() - t0
    (out / "log.solver").write_text(log)
    (out / "log.checkMesh").write_text(log_cm)
    if rc: raise RuntimeError(f"solver failed:\n{log[-2000:]}")

    times = sorted((p.name for p in out.iterdir()
                    if re.fullmatch(r"\d+", p.name) and p.name != "0"), key=int)
    if not times: raise RuntimeError("no time directory written")
    tlast = times[-1]

    nu = foamread.nusselt(out, tlast, nr, ny, D / 2, K_TH, q_w)
    mflux = re.findall(r"sum\(outlet\)\s+of\s+phi\s+=\s+([-+0-9.eE]+)", log)
    mdot = abs(float(mflux[-1])) if mflux else meta["derived"]["rho"] * \
        meta["derived"]["U_inlet"] * 3.141592653589793 * (D / 2) ** 2
    res = last_residuals(log)
    eb = energy_balance(out, nu, q_w, mdot)
    converged = re.search(r"SIMPLE solution converged", log) is not None

    rec = {
        **meta,
        "numerics": {
            "final_time": int(tlast),
            "converged_by_residual_control": converged,
            "final_residuals": res,
            "energy_balance": eb,
            "profile_shape_diagnostic_rel": nu["profile_shape_diagnostic_rel"],
            "stations_with_non_positive_net_flux": nu["stations_with_non_positive_net_flux"],
            "checkMesh_failed_checks": len(re.findall(r"\*\*\*", log_cm)),
            "wall_clock_s": round(wall, 1),
        },
        "result": {k: v for k, v in nu.items() if k != "local"},
    }
    (out / "result.json").write_text(json.dumps(rec, indent=2) + "\n")
    (out / "local_nu.json").write_text(json.dumps(nu["local"], indent=1) + "\n")
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", type=pathlib.Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--Re", type=float, required=True)
    ap.add_argument("--qw", type=float, default=200.0)
    ap.add_argument("--gravity", choices=("on", "off"), required=True)
    ap.add_argument("--nr", type=int, default=30)
    ap.add_argument("--ny", type=int, default=300)
    ap.add_argument("--iters", type=int, default=3000)
    a = ap.parse_args()
    r = run(a.workdir / a.name, a.workdir, a.Re, a.qw, a.gravity == "on", a.nr, a.ny, a.iters)
    n, res = r["numerics"], r["result"]
    print(f"{a.name}: Nu={res['Nu_avg_flux_weighted']:.4f}  "
          f"converged={n['converged_by_residual_control']}  "
          f"energy closure={n['energy_balance']['closure_rel_error']:.3%}  "
          f"profile diag={n['profile_shape_diagnostic_rel']:.3%}  "
          f"{n['wall_clock_s']}s")
