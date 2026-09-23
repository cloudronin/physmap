#!/usr/bin/env python3
"""Compare the CFD against Lewis (1992) Test 35A, on HIS definition of Nusselt number.

Lewis states it explicitly: "the local bulk temperature is assumed to vary linearly along
the tube". So his Nu(x) uses an ENERGY-BALANCE bulk temperature, not a mixing-cup
integral. Comparing a mixing-cup CFD Nu against it would be comparing different
quantities, so the linear definition is used for the comparison and the mixing-cup value
is reported alongside as a definitional difference.

This is a NUMERICAL RECONSTRUCTION CHECK. No label, flag or performance metric is computed.
"""
from __future__ import annotations
import json, math, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import foamread

# Lewis Appendix D, Test 35A, inlet-bulk property basis
LEWIS = [(0.31,33.72),(0.85,32.69),(2.45,22.15),(5.65,19.07),(9.92,14.92),(16.32,13.95),
         (33.39,10.76),(50.47,9.38),(67.55,9.37),(101.69,8.41),(135.84,7.99),(159.33,8.82)]
D_TUBE, L_TUBE, Q_W, K_TH = 0.0119, 1.900, 12749.6, 0.5922
T_IN, TBE_C = 286.21, 30.00          # K, and Lewis's calculated exit bulk in degC
T_IN_C = 13.06


def compare(case: pathlib.Path, time: str, nr: int, ny: int) -> dict:
    T = foamread.read_internal(case / time / "T")
    U = foamread.read_internal(case / time / "U")
    # Two conductivities are in play and confusing them silently corrupts every Nu.
    #   solver k  -- what the case actually ran with; sets the imposed wall gradient q/k,
    #                so the wall-temperature reconstruction must use it.
    #   Lewis's k -- inlet bulk, 0.5922; his reduction uses it for EVERY run regardless of
    #                the property basis, so Nu must be formed with it to compare like for like.
    meta = json.loads((case / "case.json").read_text()) if (case / "case.json").exists() else {}
    k_solver = float(meta.get("solver_k_W_mK", K_TH))
    ny_entry = int(meta.get("ny_entry", 0))
    if ny_entry:
        # Cells upstream of x = 0 are the unheated starting length; drop them and let the
        # axial coordinate start at the beginning of heating, which is what x/d means.
        nr_ = nr
        T = T[ny_entry * nr_:]
        U = U[ny_entry * nr_:]
    # The wall carries a fixedGradient BC, so no `value` is written. Reconstruct the
    # wall temperature from the adjacent cell and the imposed gradient over the
    # half-cell distance: T_wall = T_cell + (q/k) * (dr/2). First order, and the
    # error it carries shrinks with radial refinement -- which is why the radial
    # count is part of the grid study, not just the axial one.
    dr_half = (D_TUBE / 2) / nr / 2.0
    grad = Q_W / k_solver          # the gradient the solver actually imposed
    Tw = [T[(k + 1) * nr - 1] + grad * dr_half for k in range(ny)]
    aw = foamread.radial_weights(nr, D_TUBE / 2)
    dy = L_TUBE / ny
    rows = []
    for k in range(ny):
        sl = slice(k * nr, (k + 1) * nr)
        Tk, uy = T[sl], [u[1] for u in U[sl]]
        y = (k + 0.5) * dy
        xd = y / D_TUBE
        # Lewis: linear energy-balance bulk temperature
        Tb_lin = T_IN + (TBE_C - T_IN_C) * (y / L_TUBE)
        # the CFD's own natural definition, for contrast
        num = sum(a * u * t for a, u, t in zip(aw, uy, Tk))
        den = sum(a * u for a, u in zip(aw, uy))
        Tb_mix = num / den if abs(den) > 1e-30 else float("nan")
        rows.append({"x_over_d": xd, "T_wall": Tw[k], "Tb_linear": Tb_lin,
                     "Tb_mixing_cup": Tb_mix,
                     "Nu_lewis_definition": Q_W * D_TUBE / (K_TH * (Tw[k] - Tb_lin))
                         if Tw[k] - Tb_lin > 1e-9 else float("nan"),
                     "Nu_mixing_cup": Q_W * D_TUBE / (K_TH * (Tw[k] - Tb_mix))
                         if Tw[k] - Tb_mix > 1e-9 else float("nan"),
                     "net_axial_flux": den,
                     # Lewis's own criterion (Sec 7.1.1): the axial position where
                     # "negative values of the axial velocity first appeared". That is a
                     # per-CELL test. Testing the NET flux instead is wrong -- mass
                     # conservation keeps it positive even with a recirculating wall layer.
                     "min_axial_velocity": min(uy),
                     "n_cells_reversed": sum(1 for v in uy if v < 0)})

    def at(xd_target):
        return min(rows, key=lambda r: abs(r["x_over_d"] - xd_target))

    out = []
    for xd, nu_exp in LEWIS:
        r = at(xd)
        nu_cfd = r["Nu_lewis_definition"]
        out.append({"x_over_d": xd, "Nu_experiment": nu_exp,
                    "Nu_cfd_lewis_definition": round(nu_cfd, 4),
                    "Nu_cfd_mixing_cup": round(r["Nu_mixing_cup"], 4),
                    "rel_diff_pct": round(100 * (nu_cfd - nu_exp) / nu_exp, 2),
                    "definition_gap_pct": round(
                        100 * (r["Nu_mixing_cup"] - nu_cfd) / nu_cfd, 2)})
    rev_rows = [r for r in rows if r["n_cells_reversed"] > 0]
    first = min((r["x_over_d"] for r in rev_rows), default=None)
    worst = min(rows, key=lambda r: r["min_axial_velocity"])
    # A reversal confined to the final axial row is an OUTLET BOUNDARY artifact, not the
    # developing buoyancy reversal Lewis predicts: a physical one grows over many rows
    # upstream. Reported separately so the two are never conflated.
    outlet_only = bool(rev_rows) and all(
        r["x_over_d"] >= rows[-1]["x_over_d"] - 1e-9 for r in rev_rows)
    return {"points": out, "n_stations": ny,
            "solver_k_W_mK": k_solver, "reduction_k_W_mK": K_TH,
            "property_basis_used": meta.get("property_basis_used", "inlet_bulk"),
            "unheated_entry_cells_dropped": ny_entry,
            "reversal_stations": len(rev_rows),
            "first_reversal_x_over_d": first,
            "min_axial_velocity_m_s": round(worst["min_axial_velocity"], 6),
            "min_axial_velocity_at_x_over_d": round(worst["x_over_d"], 2),
            "reversal_confined_to_outlet_row": outlet_only}


if __name__ == "__main__":
    case = pathlib.Path(sys.argv[1]); time = sys.argv[2]
    nr, ny = int(sys.argv[3]), int(sys.argv[4])
    res = compare(case, time, nr, ny)
    print(f"{'x/d':>8} {'Nu exp':>8} {'Nu CFD':>8} {'diff':>8}   {'mixing-cup':>10} {'defn gap':>9}")
    for p in res["points"]:
        print(f"{p['x_over_d']:>8.2f} {p['Nu_experiment']:>8.2f} "
              f"{p['Nu_cfd_lewis_definition']:>8.3f} {p['rel_diff_pct']:>7.1f}%   "
              f"{p['Nu_cfd_mixing_cup']:>10.3f} {p['definition_gap_pct']:>8.1f}%")
    d = [abs(p["rel_diff_pct"]) for p in res["points"]]
    print(f"\n  mean |diff| {sum(d)/len(d):.1f}%   max {max(d):.1f}%")
    print(f"  reversed stations (any cell u_y<0): {res['reversal_stations']} of {res['n_stations']}"
          f"   first at x/d {res['first_reversal_x_over_d']}")
    print(f"  min axial velocity {res['min_axial_velocity_m_s']:+.5f} m/s "
          f"at x/d {res['min_axial_velocity_at_x_over_d']}")
    if res["reversal_confined_to_outlet_row"]:
        print("  NOTE: reversal is confined to the final axial row -> outlet BC artifact,"
              "\n        not the developing buoyancy reversal Lewis's Table 7.1 predicts.")
    (case / "lewis_comparison.json").write_text(json.dumps(res, indent=2) + "\n")
