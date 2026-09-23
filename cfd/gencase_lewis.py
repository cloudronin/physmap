#!/usr/bin/env python3
"""Generate the Lewis (1992) Test 35A case. Water, Boussinesq, uniform wall flux.

Geometry and conditions are transcribed from the thesis, Appendix D specimen calculation:
d = 11.9 mm bore, heated length 1.9 m (L/D = 159.7), water upward, q_w from the CORRECTED
energy input (electrical power less the empirical heat loss), inlet bulk 13.06 degC.

DOCUMENTED CHOICES, because the comparison is meaningless without them
---------------------------------------------------------------------
**Property basis: INLET BULK (13.06 degC).** Lewis reports every group on three bases --
inlet bulk, mean bulk, mean film -- and they differ materially: Re is 1143.4 on the inlet
basis and 1417.1 on the mean-bulk basis, a 24% spread. The inlet basis is chosen because
it is fixed by a boundary condition rather than by the solution, so the case can be built
without circularity. Constant properties at that temperature reproduce Lewis's stated
Re = 1143.4 and Pr = 8.46 to four figures.

**Thermal expansion: beta at the MEAN bulk (2.23e-4).** Water's beta runs 1.27e-4 at the
inlet to 4.46e-4 at the mean wall -- a factor of 3.5 -- so no single value is right. The
mean-bulk value is a compromise and it is a real limitation of a Boussinesq treatment
here, stated rather than hidden. Density itself varies only 1.1% across the case, which is
what makes Boussinesq admissible at all.

**QoI: Lewis's definition, not the CFD's natural one.** Lewis states it plainly -- "the
local bulk temperature is assumed to vary linearly along the tube" -- so his Nu(x) uses an
energy-balance bulk temperature, not a mixing-cup integral. To compare with him the CFD
must use the same definition. The mixing-cup value is also computed, and their difference
is reported: it is a definitional difference, not an uncertainty in either.
"""
from __future__ import annotations
import argparse, json, math, pathlib, shutil, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gencase import w, blockmesh
import gencase

# Lewis Appendix D, Test 35A
D_TUBE, L_TUBE = 0.0119, 1.900
Q_W = 12749.6                 # W/m2, from the CORRECTED energy input
T_IN_C, T_IN = 13.06, 286.21  # degC, K
V_DOT = 0.7679 / 60000.0      # m3/s
MU, K_TH, CP, RHO = 0.001197, 0.5922, 4187.8, 999.37   # at inlet bulk 13.06 degC

# Lewis's spreadsheet tabulates water properties on four bases. His NUMERICAL code does not
# use any of them -- it carries polynomial property variation with temperature, "the option
# to include ... the effect of fluid property variation with temperature was chosen for all
# properties" (Sec 7.1). A constant-property Boussinesq case cannot reproduce that, so these
# bases exist to BOUND the error it introduces, not to pick a winner. Viscosity falls by a
# factor of 2.1 from inlet bulk to mean wall, which is a first-order effect on the near-wall
# layer, not a refinement.
PROPERTY_BASES = {
    "inlet_bulk": dict(T_C=13.06, mu=0.001197, k=0.5922, cp=4187.8, rho=999.37, beta=1.27e-4),
    "mean_bulk":  dict(T_C=21.53, mu=0.000966, k=0.6058, cp=4180.7, rho=997.88, beta=2.23e-4),
    "exit_bulk":  dict(T_C=30.00, mu=0.000798, k=0.6183, cp=4178.4, rho=995.65, beta=3.04e-4),
    "mean_wall":  dict(T_C=48.36, mu=0.000563, k=0.6414, cp=4180.5, rho=988.77, beta=4.46e-4),
}
def film_basis():
    """Mean film = midway between mean bulk and mean wall. Lewis does not tabulate it, so it
    is linearly interpolated between the two he does, and labelled as interpolated."""
    a, b = PROPERTY_BASES["mean_bulk"], PROPERTY_BASES["mean_wall"]
    f = 0.5
    return {k: a[k] + f * (b[k] - a[k]) for k in a}
BETA = 2.23e-4                # at mean bulk 21.53 degC -- see the docstring
NU = MU / RHO
PR = MU * CP / K_TH


def derived() -> dict:
    A = math.pi * (D_TUBE / 2) ** 2
    U = V_DOT / A
    Re = U * D_TUBE / NU
    Gr_q = 9.81 * BETA * Q_W * D_TUBE ** 4 / (K_TH * NU ** 2)
    Tbe = T_IN_C + Q_W * math.pi * D_TUBE * L_TUBE / (RHO * V_DOT * CP)
    return {"U_inlet": U, "Re": Re, "Pr": PR, "Gr_q": Gr_q, "Ri": Gr_q / Re ** 2,
            "T_exit_bulk_C_energy_balance": Tbe, "L_over_D": L_TUBE / D_TUBE,
            "nu": NU, "rho": RHO, "k": K_TH, "Cp": CP, "beta": BETA}


def build(out: pathlib.Path, nr: int, ny: int, iters: int, beta: float = BETA,
          entry_d: float = 0.0, basis: str = "inlet_bulk") -> dict:
    """entry_d: unheated starting length in tube diameters, upstream of x = 0.

    Lewis ran a 2.5-diameter adiabatic section before the heated tube, "for partial
    development of the initially uniform entrance flow", and his own code models it. With
    entry_d = 0 the heated section begins on a plug profile, which is NOT his geometry. The
    hydrodynamic entry length here is ~0.05*Re*d = 57 diameters, so 2.5 d develops the
    profile only slightly -- but "slightly" is a claim to measure, not to assume.
    """
    if out.exists():
        shutil.rmtree(out)
    global BETA, MU, K_TH, CP, RHO, NU, PR
    BETA = beta
    props = film_basis() if basis == "mean_film" else PROPERTY_BASES[basis]
    MU, K_TH, CP, RHO = props["mu"], props["k"], props["cp"], props["rho"]
    NU, PR = MU / RHO, MU * CP / K_TH
    d = derived()
    U, grad = d["U_inlet"], Q_W / K_TH

    entry_len = entry_d * D_TUBE
    ny_entry = int(round(ny * entry_len / L_TUBE)) if entry_len > 0 else 0
    ny_tot = ny + ny_entry
    gencase.RAD, gencase.L = D_TUBE / 2, L_TUBE + entry_len
    w(out / "system/blockMeshDict", "dictionary", "blockMeshDict",
      blockmesh(nr, ny_tot), "system")

    w(out / "system/controlDict", "dictionary", "controlDict", f"""application     buoyantBoussinesqSimpleFoam;
startFrom       startTime;   startTime 0;   stopAt endTime;   endTime {iters};
deltaT          1;  writeControl timeStep;  writeInterval {iters};  purgeWrite 2;
writeFormat     ascii;  writePrecision 8;  writeCompression off;
timeFormat      general; timePrecision 6; runTimeModifiable false;

functions
{{
    outletBulk
    {{
        type surfaceFieldValue; libs (fieldFunctionObjects); regionType patch;
        name outlet; operation weightedAverage; weightField phi; fields (T);
        writeFields false; writeControl timeStep; writeInterval {iters}; log false;
    }}
    residuals
    {{
        type solverInfo; libs (utilityFunctionObjects); fields (U T p_rgh);
        writeResidualFields false; writeControl timeStep; writeInterval 1;
    }}
}}""")

    w(out / "system/fvSchemes", "dictionary", "fvSchemes", """ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default none;
    div(phi,U)  bounded Gauss linearUpwind grad(U);
    div(phi,T)  bounded Gauss limitedLinear 1;
    div(phi,k)  bounded Gauss limitedLinear 1;
    div(phi,epsilon) bounded Gauss limitedLinear 1;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }""")

    w(out / "system/fvSolution", "dictionary", "fvSolution", """solvers
{
    p_rgh { solver GAMG; tolerance 1e-9; relTol 0.01; smoother GaussSeidel; }
    "(U|T)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-10; relTol 0.1; }
}
SIMPLE
{
    nNonOrthogonalCorrectors 0;
    pRefCell 0; pRefValue 0;
    residualControl { p_rgh 1e-5; U 1e-5; T 1e-5; }
}
relaxationFactors { fields { p_rgh 0.7; } equations { U 0.7; T 0.7; } }""")

    w(out / "constant/g", "uniformDimensionedVectorField", "g",
      "dimensions [0 1 -2 0 0 0 0];\nvalue (0 -9.81 0);", "constant")
    w(out / "constant/transportProperties", "dictionary", "transportProperties", f"""transportModel  Newtonian;
nu              {NU:.8e};
beta            {BETA:.6e};
TRef            {T_IN:.4f};
Pr              {PR:.6f};
Prt             0.85;""", "constant")
    w(out / "constant/momentumTransport", "dictionary", "momentumTransport",
      "simulationType laminar;", "constant")
    w(out / "constant/turbulenceProperties", "dictionary", "turbulenceProperties",
      "simulationType laminar;", "constant")

    # The wall carries zero flux over the unheated entry and q/k over the heated length.
    # fixedGradient takes a per-face List<scalar>; wall faces run in the axial direction.
    if ny_entry:
        vals = " ".join(("0" if k < ny_entry else f"{grad:.6f}") for k in range(ny_tot))
        wall_grad = f"nonuniform List<scalar> {ny_tot}({vals})"
    else:
        wall_grad = f"uniform {grad:.6f}"

    wedge = "    front { type wedge; }\n    back  { type wedge; }\n    axis  { type empty; }"
    w(out / "0/U", "volVectorField", "U", f"""dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 {U:.8f} 0);
boundaryField
{{
    inlet  {{ type fixedValue; value uniform (0 {U:.8f} 0); }}
    outlet {{ type zeroGradient; }}
    wall   {{ type noSlip; }}
{wedge}
}}""", "0")
    w(out / "0/T", "volScalarField", "T", f"""dimensions [0 0 0 1 0 0 0];
internalField uniform {T_IN:.4f};
boundaryField
{{
    inlet  {{ type fixedValue; value uniform {T_IN:.4f}; }}
    outlet {{ type zeroGradient; }}
    // uniform wall heat flux: dT/dn = q_w / k
    wall   {{ type fixedGradient; gradient {wall_grad}; }}
{wedge}
}}""", "0")
    for fld in ("p_rgh", "p"):
        w(out / f"0/{fld}", "volScalarField", fld, f"""dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{{
    inlet  {{ type fixedFluxPressure; value uniform 0; }}
    outlet {{ type {'fixedValue' if fld=='p_rgh' else 'calculated'}; value uniform 0; }}
    wall   {{ type fixedFluxPressure; value uniform 0; }}
{wedge}
}}""", "0")
    w(out / "0/alphat", "volScalarField", "alphat", f"""dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{{
    inlet  {{ type calculated; value uniform 0; }}
    outlet {{ type calculated; value uniform 0; }}
    wall   {{ type fixedValue; value uniform 0; }}
{wedge}
}}""", "0")

    meta = {"source": "Lewis (1992) Test 35A", "geometry": {"d_m": D_TUBE, "L_m": L_TUBE,
            "L_over_D": L_TUBE / D_TUBE}, "q_w_W_m2": Q_W, "T_inlet_C": T_IN_C,
            "unheated_entry_diameters": entry_d, "ny_entry": ny_entry, "ny_heated": ny,
            "property_basis_used": basis, "solver_k_W_mK": K_TH, "solver_mu": MU,
            "solver_rho": RHO, "solver_cp": CP, "solver_beta": BETA,
            "V_dot_L_min": 0.7679, "property_basis": "inlet bulk 13.06 degC",
            "beta_basis": "mean bulk 21.53 degC", "solver": "buoyantBoussinesqSimpleFoam",
            "mesh": {"nr": nr, "ny": ny, "cells": nr * ny}, "iterations": iters,
            "derived": d,
            "lewis_reported": {"Re": 1143.4, "Pr": 8.46, "Gr_q": 374663, "Nu_mean": 9.55,
                               "T_exit_bulk_calc_C": 30.00, "energy_bal_error_pct": -3.96}}
    (out / "case.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--nr", type=int, default=20); ap.add_argument("--ny", type=int, default=300)
    ap.add_argument("--iters", type=int, default=4000)
    ap.add_argument("--beta", type=float, default=BETA)
    ap.add_argument("--basis", default="inlet_bulk",
                    choices=["inlet_bulk","mean_bulk","mean_film","exit_bulk","mean_wall"],
                    help="constant-property basis for the solver. Nu is ALWAYS reduced on "
                         "inlet-bulk k, matching Lewis, whatever the solver used.")
    ap.add_argument("--entry-diameters", type=float, default=0.0, dest="entry_d",
                    help="unheated starting length upstream of x=0, in tube diameters "
                         "(Lewis used 2.5; default 0 reproduces the earlier runs)")
    a = ap.parse_args()
    m = build(a.out, a.nr, a.ny, a.iters, a.beta, entry_d=a.entry_d, basis=a.basis)
    d = m["derived"]; lr = m["lewis_reported"]
    print(f"  U_inlet      {d['U_inlet']:.6f} m/s")
    print(f"  Re  CFD {d['Re']:8.1f}   Lewis {lr['Re']:8.1f}   diff {100*(d['Re']-lr['Re'])/lr['Re']:+.3f}%")
    print(f"  Pr  CFD {d['Pr']:8.3f}   Lewis {lr['Pr']:8.2f}   diff {100*(d['Pr']-lr['Pr'])/lr['Pr']:+.3f}%")
    print(f"  Gr_q CFD {d['Gr_q']:.4e}  Lewis {lr['Gr_q']:.4e}  diff {100*(d['Gr_q']-lr['Gr_q'])/lr['Gr_q']:+.2f}%")
    print(f"  T_exit (energy balance) CFD {d['T_exit_bulk_C_energy_balance']:.2f} C   Lewis {lr['T_exit_bulk_calc_C']:.2f} C")
    print(f"  L/D {d['L_over_D']:.1f}")
