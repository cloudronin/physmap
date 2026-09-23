#!/usr/bin/env python3
"""Compare the VARIABLE-PROPERTY Lewis 35A case against Lewis's measurement AND his own
laminar prediction curve.

Two references, and they answer different questions:
  measurement  -- what the experiment recorded, reduced by Lewis's own rule
  prediction   -- Lewis's steady laminar code, traced from Figure 7.4

Against the MEASUREMENT a gap could be transition or a model defect. Against HIS PREDICTION
it can only be a model defect, because both are steady laminar solutions of the same case.
That is the diagnostic signal this script exists to produce.

Test 35A is a BURNED development run. Agreement here is a debugging signal. It is not a
result and no metric may be computed from it.

Wall temperature is READ from the patch, which externalWallHeatFluxTemperature writes out.
The constant-property script had to reconstruct it as T_cell + (q/k)(dr/2), a first-order
estimate; that error is gone here.
"""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import foamread

D_TUBE, L_TUBE, Q_W = 0.0119, 1.900, 12749.6
K_REDUCTION = 0.5922                  # Lewis reduces every run on inlet-bulk k
T_IN, T_IN_C, TBE_C = 286.21, 13.06, 30.00   # calculated exit bulk, not the measured 29.32

LEWIS_MEASURED = [(0.31, 33.72), (0.85, 32.69), (2.45, 22.15), (5.65, 19.07), (9.92, 14.92),
                  (16.32, 13.95), (33.39, 10.76), (50.47, 9.38), (67.55, 9.37),
                  (101.69, 8.41), (135.84, 7.99), (159.33, 8.82)]


def _prediction(path: pathlib.Path | None):
    if path is None or not path.exists():
        return None
    curves = json.loads(path.read_text())["curves"]
    xs = [p[0] for p in curves["35A"]]
    ys = [p[1] for p in curves["35A"]]
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    return [xs[i] for i in order], [ys[i] for i in order]


def compare(case: pathlib.Path, time: str, nr: int, ny: int,
            pred_path: pathlib.Path | None = None) -> dict:
    meta = json.loads((case / "case.json").read_text())
    ny_entry = int(meta.get("ny_entry", 0))
    T = foamread.read_internal(case / time / "T")
    U = foamread.read_internal(case / time / "U")
    Tw_all = foamread.read_patch(case / time / "T", "wall")
    if len(Tw_all) != ny_entry + ny:
        raise SystemExit(f"wall patch has {len(Tw_all)} faces, expected {ny_entry + ny}")
    Tw = Tw_all[ny_entry:]                      # drop the unheated entry
    T = T[ny_entry * nr:]
    U = U[ny_entry * nr:]

    aw = foamread.radial_weights(nr, D_TUBE / 2)
    dy = L_TUBE / ny
    pred = _prediction(pred_path)
    RePr = 9672.0                                # Lewis's printed Re*Pr for 35A

    rows = []
    for k in range(ny):
        sl = slice(k * nr, (k + 1) * nr)
        Tk, uy = T[sl], [u[1] for u in U[sl]]
        y = (k + 0.5) * dy
        xd = y / D_TUBE
        Tb_lin = T_IN + (TBE_C - T_IN_C) * (y / L_TUBE)
        num = sum(a * u * t for a, u, t in zip(aw, uy, Tk))
        den = sum(a * u for a, u in zip(aw, uy))
        Tb_mix = num / den if abs(den) > 1e-30 else float("nan")
        dT = Tw[k] - Tb_lin
        rows.append({"x_over_d": xd, "T_wall": Tw[k], "Tb_linear": Tb_lin,
                     "Tb_mixing_cup": Tb_mix,
                     "Nu": Q_W * D_TUBE / (K_REDUCTION * dT) if dT > 1e-9 else float("nan"),
                     "min_axial_velocity": min(uy),
                     "n_cells_reversed": sum(1 for v in uy if v < 0)})

    def at(target):
        return min(rows, key=lambda r: abs(r["x_over_d"] - target))

    out = []
    for xd, nu_exp in LEWIS_MEASURED:
        r = at(xd)
        nu = r["Nu"]
        rec = {"x_over_d": xd, "Nu_experiment": nu_exp, "Nu_cfd": round(nu, 4),
               "cfd_vs_experiment_pct": round(100 * (nu / nu_exp - 1), 2)}
        if pred:
            xs = xd / RePr
            if pred[0][0] <= xs <= pred[0][-1]:
                import bisect
                i = bisect.bisect_left(pred[0], xs)
                i = max(1, min(i, len(pred[0]) - 1))
                x0, x1 = pred[0][i - 1], pred[0][i]
                y0, y1 = pred[1][i - 1], pred[1][i]
                p = y0 + (y1 - y0) * (xs - x0) / (x1 - x0) if x1 != x0 else y0
                rec["Nu_lewis_prediction"] = round(p, 3)
                rec["cfd_vs_prediction_pct"] = round(100 * (nu / p - 1), 2)
        out.append(rec)

    rev = [r for r in rows if r["n_cells_reversed"] > 0]
    worst = min(rows, key=lambda r: r["min_axial_velocity"])
    return {"points": out, "n_stations": ny,
            "property_model": meta.get("property_model"),
            "reduction_k_W_mK": K_REDUCTION,
            "wall_T_source": "read from the patch, not reconstructed",
            "unheated_entry_cells_dropped": ny_entry,
            "reversal_stations": len(rev),
            "first_reversal_x_over_d": min((r["x_over_d"] for r in rev), default=None),
            "min_axial_velocity_m_s": round(worst["min_axial_velocity"], 6),
            "reversal_confined_to_outlet_row": bool(rev) and all(
                r["x_over_d"] >= rows[-1]["x_over_d"] - 1e-9 for r in rev)}


if __name__ == "__main__":
    case = pathlib.Path(sys.argv[1]); time = sys.argv[2]
    nr, ny = int(sys.argv[3]), int(sys.argv[4])
    pred = pathlib.Path(sys.argv[5]) if len(sys.argv) > 5 else None
    res = compare(case, time, nr, ny, pred)
    has_pred = any("Nu_lewis_prediction" in p for p in res["points"])
    hdr = f"{'x/d':>8} {'measured':>9} {'CFD':>8} {'vs meas':>9}"
    if has_pred:
        hdr += f"   {'Lewis pred':>10} {'vs pred':>9}"
    print(hdr)
    for p in res["points"]:
        line = (f"{p['x_over_d']:>8.2f} {p['Nu_experiment']:>9.2f} {p['Nu_cfd']:>8.3f} "
                f"{p['cfd_vs_experiment_pct']:>8.1f}%")
        if "Nu_lewis_prediction" in p:
            line += f"   {p['Nu_lewis_prediction']:>10.2f} {p['cfd_vs_prediction_pct']:>8.1f}%"
        print(line)
    d = [abs(p["cfd_vs_experiment_pct"]) for p in res["points"]]
    print(f"\n  vs measurement: mean |diff| {sum(d)/len(d):.1f}%   max {max(d):.1f}%")
    dp = [abs(p["cfd_vs_prediction_pct"]) for p in res["points"] if "cfd_vs_prediction_pct" in p]
    if dp:
        print(f"  vs Lewis's own laminar prediction: mean |diff| {sum(dp)/len(dp):.1f}%   "
              f"max {max(dp):.1f}%   ({len(dp)} stations in the traced range)")
    print(f"  reversed stations: {res['reversal_stations']} of {res['n_stations']}"
          f"   min axial velocity {res['min_axial_velocity_m_s']:+.5f} m/s")
    if res["reversal_confined_to_outlet_row"]:
        print("  NOTE: confined to the final row -> outlet BC artifact, not buoyancy reversal.")
    (case / "lewis_comparison_vp.json").write_text(json.dumps(res, indent=2) + "\n")
