#!/usr/bin/env python3
"""Lewis (1992) Test 35A with VARIABLE water properties -- the model of record.

WHY THIS REPLACES THE BOUSSINESQ CASE. Tracing Lewis's own Figure 7.4 prediction curves
showed our constant-property case sitting 19-29% below HIS steady laminar prediction at
stations where his prediction matches his measurement to within 8%. A property-basis sweep
then moved Nu by 12-27% on its own -- the same size and sign as the gap. The gap was the
frozen-property assumption, not transition.

The fix is not a better constant. Picking the basis that agrees best would tune the model to
the measurement it is about to be tested against. The fix is to remove the choice.

PROPERTIES ARE LEWIS'S OWN. Appendix B equations B.2 (viscosity), B.4 (conductivity),
B.5 (specific heat) and B.6 (density) -- the polynomials his NUMERICAL code used, not the
ESDU forms his spreadsheet used. Verified against his tabulated property table at all four
of his bases: k, cp and rho agree to within 0.04%, mu to within 0.42%, which is the
difference he himself documents between B.1 and B.2 ("less than 0.8%"). Expansion
coefficient is not an input here at all: buoyancy enters through rho(T)*g directly, so the
beta choice that was the single largest lever in the Boussinesq case simply disappears.

OpenFOAM polynomials are in KELVIN; Lewis's are in CELSIUS. The coefficients below are the
exact binomial shift, round-trip accurate to 1e-11 over 5-80 degC.

RETAINED UNCHANGED from the constant-property case, per the protocol:
  - the 2.5-diameter unheated starting length before x = 0
  - geometry d = 0.0119 m, heated length 1.900 m, L/d = 159.66
  - uniform wall heat flux over the heated length, adiabatic over the entry
  - Nu reduced on Lewis's linear energy-balance bulk and inlet-bulk k = 0.5922

13A, 16A and 35A are BURNED development runs. They diagnose this implementation. No metric
may be computed from them.
"""
from __future__ import annotations
import argparse, json, math, pathlib, shutil
import gencase
from gencase import blockmesh, w

D_TUBE, L_TUBE = 0.0119, 1.900
Q_W = 12749.6                      # W/m2, from the corrected energy input
T_IN_C, T_IN = 13.06, 286.21
V_DOT = 0.7679 / 60000.0           # m3/s
K_REDUCTION = 0.5922               # inlet-bulk k -- Lewis reduces EVERY run on this

# Lewis Appendix B, shifted to Kelvin. Padded to 8 for OpenFOAM's <8> coefficient lists.
COEFFS_K = {
 "mu":    [1.893037002, -0.02777543226, 1.634914135e-4, -4.820134115e-7, 7.112643535e-10,
           -4.200253e-13, 0.0, 0.0],
 "kappa": [-0.4929251144, 5.918453387e-3, -7.434436e-6, 0.0, 0.0, 0.0, 0.0, 0.0],
 "Cp":    [253366.415, -3743.596413, 22.47767125, -0.06741382257, 1.009647131e-4,
           -6.038683e-8, 0.0, 0.0],
 "rho":   [-6728.681145, 112.1662054, -0.6544616402, 1.924924029e-3, -2.855835157e-6,
           1.702156e-9, 0.0, 0.0],
}
MOL_WEIGHT = 18.015


def _poly(name: str) -> str:
    return "(" + " ".join(f"{v:.10g}" for v in COEFFS_K[name]) + ")"


def inlet_properties() -> dict:
    """Evaluate the polynomials at the inlet bulk, for the reported dimensionless groups."""
    def ev(n, T=T_IN):
        return sum(a * T ** i for i, a in enumerate(COEFFS_K[n]))
    mu, k, cp, rho = ev("mu"), ev("kappa"), ev("Cp"), ev("rho")
    A = math.pi * (D_TUBE / 2) ** 2
    U = V_DOT / A
    # beta is NOT a model input; it is reported only so the case can be compared with the
    # Boussinesq runs and with Lewis's tabulation.
    drho = sum(i * a * T_IN ** (i - 1) for i, a in enumerate(COEFFS_K["rho"]) if i)
    beta = -drho / rho
    return {"U_inlet": U, "mu": mu, "k": k, "cp": cp, "rho": rho, "beta_reported": beta,
            "Re": rho * U * D_TUBE / mu, "Pr": mu * cp / k,
            "Gr_q": 9.81 * beta * Q_W * D_TUBE ** 4 / (k * (mu / rho) ** 2)}


def build(out: pathlib.Path, nr: int, ny: int, iters: int, entry_d: float = 2.5) -> dict:
    if out.exists():
        shutil.rmtree(out)
    d = inlet_properties()
    U = d["U_inlet"]
    entry_len = entry_d * D_TUBE
    ny_entry = int(round(ny * entry_len / L_TUBE)) if entry_len > 0 else 0
    ny_tot = ny + ny_entry

    gencase.RAD, gencase.L = D_TUBE / 2, L_TUBE + entry_len
    w(out / "system/blockMeshDict", "dictionary", "blockMeshDict", blockmesh(nr, ny_tot), "system")

    w(out / "system/controlDict", "dictionary", "controlDict", f"""application     buoyantSimpleFoam;
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
        type solverInfo; libs (utilityFunctionObjects); fields (U h p_rgh);
        writeResidualFields false; writeControl timeStep; writeInterval 1;
    }}
}}""")

    w(out / "system/fvSchemes", "dictionary", "fvSchemes", """ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,h)      bounded Gauss limitedLinear 1;
    div(phi,e)      bounded Gauss limitedLinear 1;
    div(phi,K)      bounded Gauss limitedLinear 1;
    div(phi,Ekp)    bounded Gauss limitedLinear 1;
    div(phi,k)      bounded Gauss limitedLinear 1;
    div(phi,epsilon) bounded Gauss limitedLinear 1;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }""")

    w(out / "system/fvSolution", "dictionary", "fvSolution", """solvers
{
    p_rgh { solver GAMG; tolerance 1e-9; relTol 0.01; smoother GaussSeidel; }
    "(U|h|e|k|epsilon)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-10; relTol 0.1; }
}
SIMPLE
{
    nNonOrthogonalCorrectors 0;
    pRefCell 0; pRefValue 101325;
    residualControl { p_rgh 1e-5; U 1e-5; h 1e-5; }
}
relaxationFactors { fields { rho 1.0; p_rgh 0.7; } equations { U 0.3; h 0.3; } }""")

    w(out / "constant/g", "uniformDimensionedVectorField", "g",
      "dimensions [0 1 -2 0 0 0 0];\nvalue (0 -9.81 0);", "constant")
    w(out / "constant/momentumTransport", "dictionary", "momentumTransport",
      "simulationType laminar;", "constant")
    # buoyantSimpleFoam still reads the legacy name; both must be present and agree.
    w(out / "constant/turbulenceProperties", "dictionary", "turbulenceProperties",
      "simulationType laminar;", "constant")

    # Variable-property water. Buoyancy comes from rho(T)*g -- there is no beta input.
    w(out / "constant/thermophysicalProperties", "dictionary", "thermophysicalProperties",
      f"""thermoType
{{
    type            heRhoThermo;
    mixture         pureMixture;
    transport       polynomial;
    thermo          hPolynomial;
    equationOfState icoPolynomial;
    specie          specie;
    energy          sensibleEnthalpy;
}}

mixture
{{
    specie          {{ molWeight {MOL_WEIGHT}; }}
    equationOfState {{ rhoCoeffs<8> {_poly('rho')}; }}
    thermodynamics  {{ CpCoeffs<8> {_poly('Cp')}; Hf 0; Sf 0; }}
    transport       {{ muCoeffs<8> {_poly('mu')}; kappaCoeffs<8> {_poly('kappa')}; }}
}}""", "constant")

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

    # Uniform heat flux where heated, adiabatic over the entry. externalWallHeatFluxTemperature
    # imposes q using the LOCAL conductivity, which a fixedGradient cannot do once k varies
    # with temperature -- and it writes the wall temperature out, so the comparison reads it
    # instead of reconstructing it from the adjacent cell.
    qvals = " ".join(("0" if k < ny_entry else f"{Q_W:.4f}") for k in range(ny_tot))
    w(out / "0/T", "volScalarField", "T", f"""dimensions [0 0 0 1 0 0 0];
internalField uniform {T_IN:.4f};
boundaryField
{{
    inlet  {{ type fixedValue; value uniform {T_IN:.4f}; }}
    outlet {{ type zeroGradient; }}
    wall
    {{
        type            externalWallHeatFluxTemperature;
        mode            flux;
        q               nonuniform List<scalar> {ny_tot}({qvals});
        kappaMethod     fluidThermo;
        value           uniform {T_IN:.4f};
    }}
{wedge}
}}""", "0")

    w(out / "0/p_rgh", "volScalarField", "p_rgh", f"""dimensions [1 -1 -2 0 0 0 0];
internalField uniform 101325;
boundaryField
{{
    inlet  {{ type fixedFluxPressure; value uniform 101325; }}
    outlet {{ type fixedValue; value uniform 101325; }}
    wall   {{ type fixedFluxPressure; value uniform 101325; }}
{wedge}
}}""", "0")
    w(out / "0/p", "volScalarField", "p", f"""dimensions [1 -1 -2 0 0 0 0];
internalField uniform 101325;
boundaryField
{{
    inlet  {{ type calculated; value uniform 101325; }}
    outlet {{ type calculated; value uniform 101325; }}
    wall   {{ type calculated; value uniform 101325; }}
{wedge}
}}""", "0")

    meta = {"case": "Lewis (1992) Test 35A, VARIABLE properties",
            "solver": "buoyantSimpleFoam", "properties": "Lewis Appendix B, B.2/B.4/B.5/B.6",
            "property_model": "icoPolynomial + polynomial transport + hPolynomial",
            "beta_is_an_input": False,
            "buoyancy": "rho(T)*g -- no Boussinesq approximation, no beta choice",
            "geometry": {"d_m": D_TUBE, "L_heated_m": L_TUBE, "L_over_D": L_TUBE / D_TUBE},
            "unheated_entry_diameters": entry_d, "ny_entry": ny_entry, "ny_heated": ny,
            "q_w_W_m2": Q_W, "T_inlet_C": T_IN_C, "V_dot_L_min": 0.7679,
            "solver_k_W_mK": None, "reduction_k_W_mK": K_REDUCTION,
            "wall_T_is_written_by_the_BC": True,
            "inlet_bulk_values": {k: d[k] for k in ("mu", "k", "cp", "rho", "beta_reported",
                                                    "Re", "Pr", "Gr_q", "U_inlet")},
            "mesh": {"nr": nr, "ny_total": ny_tot}, "iterations": iters}
    (out / "case.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--nr", type=int, default=30)
    ap.add_argument("--ny", type=int, default=400)
    ap.add_argument("--iters", type=int, default=25000)
    ap.add_argument("--entry-diameters", type=float, default=2.5, dest="entry_d")
    a = ap.parse_args()
    m = build(a.out, a.nr, a.ny, a.iters, entry_d=a.entry_d)
    v = m["inlet_bulk_values"]
    print(f"  wrote {a.out}")
    print(f"  properties  VARIABLE (Lewis Appendix B); beta is not an input")
    print(f"  at inlet bulk: mu {v['mu']:.6e}  k {v['k']:.4f}  cp {v['cp']:.1f}  rho {v['rho']:.2f}")
    print(f"  Re  CFD {v['Re']:8.1f}   Lewis   1143.4   diff {100*(v['Re']/1143.4-1):+.3f}%")
    print(f"  Pr  CFD {v['Pr']:8.3f}   Lewis     8.46   diff {100*(v['Pr']/8.46-1):+.3f}%")
    print(f"  Gr_q CFD {v['Gr_q']:.4e}  Lewis 3.7466e+05  diff {100*(v['Gr_q']/3.7466e5-1):+.2f}%")
    print(f"  (beta implied by rho(T): {v['beta_reported']:.3e}; Lewis inlet-bulk 1.27e-04)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
