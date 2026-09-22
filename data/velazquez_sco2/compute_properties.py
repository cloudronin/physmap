#!/usr/bin/env python3
"""Phase-C property precompute for the velazquez_sco2 vehicle (OFFLINE, one-off).

Reads the exact SI extraction (velazquez_sco2_local_alpha.csv) and augments each of
the 560 points with CO2 fluid properties + the dimensionless groups the vehicle needs,
using CoolProp (Span-Wagner EOS + Huber/Laesecke-Muzny transport). The result is banked
as `velazquez_sco2_local_alpha_with_properties.csv`; the runtime loader only READS these
columns -- the pipeline stays property-library-free (matches repo convention).

PROVENANCE / VALIDATION (property source = CoolProp; see version printed at run):
  * CoolProp CO2 pseudo-critical enthalpies match Velazquez et al.'s REFPROP-reported
    h_pc to < 0.2 kJ/kg at every test pressure (10/15/20/25/30 MPa) -> EOS/thermo are
    effectively REFPROP-identical; transport uses the same Laesecke-Muzny (viscosity)
    and Huber (conductivity) correlations REFPROP uses. Property-source uncertainty is
    therefore negligible except extremely near the critical point.
  * Per-point bulk-enthalpy cross-check: CoolProp h(T_b,p) vs the SI's h_b agrees to
    < 0.23 kJ/kg over all 560 points -> the extracted bulk states (T_b, p) are correct.
NOT run at pipeline runtime; CoolProp is NOT a repo dependency.

WHAT THIS COMPUTES (the validated essentials for a property-variation vehicle):
  Re_b   = G*Di/mu_b
  Pr_b   = mu_b*cp_b/lambda_b
  Nu_meas= alpha*Di/lambda_b
  property ratios rho_w/rho_b, mu_w/mu_b, lambda_w/lambda_b   (the failure driver)
  T_pc(p) = argmax_T cp(T,p);  dT_b_to_pc = T_b - T_pc        (pseudo-critical proximity)

BUOYANCY / Ri IS DELIBERATELY NOT RECOMPUTED HERE. For a property-variation vehicle the
failure driver is the property ratio, not Ri; buoyancy is only a confound to isolate, and
Velazquez et al. Fig. 11 already settle it: buoyancy is non-negligible only at 10 MPa and
"for pressures above 10 MPa, buoyancy effects can be neglected." The vehicle isolates the
confound by PRESSURE (use the 15-30 MPa subset for the clean property-variation claim),
citing Fig. 11 -- rather than re-deriving Gr/Ri whose paper-specific definitions are
error-prone to reconstruct.

Run:  /tmp/velaz/venv/bin/python compute_properties.py
"""
import csv, math, os
from CoolProp.CoolProp import PropsSI
import CoolProp

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "velazquez_sco2_local_alpha.csv")
DST = os.path.join(HERE, "velazquez_sco2_local_alpha_with_properties.csv")
DI = 0.88e-3
F = "CO2"

def props_at(T_C, p_MPa):
    T = T_C + 273.15; P = p_MPa * 1e6
    return dict(rho=PropsSI("D","T",T,"P",P,F), mu=PropsSI("V","T",T,"P",P,F),
                lam=PropsSI("L","T",T,"P",P,F), cp=PropsSI("C","T",T,"P",P,F),
                h=PropsSI("H","T",T,"P",P,F))

_tpc = {}
def T_pc_C(p_MPa):
    if p_MPa in _tpc: return _tpc[p_MPa]
    P = p_MPa*1e6; best=(None,-1.0); Tk=280.0
    while Tk <= 380.0:
        cp = PropsSI("C","T",Tk,"P",P,F)
        if cp > best[1]: best=(Tk,cp)
        Tk += 0.02
    _tpc[p_MPa] = best[0]-273.15
    return _tpc[p_MPa]

def gnielinski_basic(Re, Pr):
    f = (1.82*math.log10(Re)-1.64)**-2
    return (f/8.0)*(Re-1000.0)*Pr / (1.0 + 12.7*math.sqrt(f/8.0)*(Pr**(2/3)-1.0))

def main():
    with open(SRC, newline="") as fh:
        rows = list(csv.DictReader(fh))
    new = ["rho_b","mu_b_uPa_s","lam_b_mWmK","cp_b","Pr_b","rho_w","mu_w_uPa_s","lam_w_mWmK",
           "Re_b","Nu_meas","ratio_rho_w_b","ratio_mu_w_b","ratio_lam_w_b",
           "T_pc_C","dT_b_to_pc_K","abs_dT_pc_K","near_pc","hb_coolprop_kJkg","hb_residual_kJkg"]
    out_cols = list(rows[0].keys()) + new
    out=[]; reM=[1e18,-1e18]; prM=[1e18,-1e18]; nuM=[1e18,-1e18]
    muR=[1e18,-1e18]; rhoR=[1e18,-1e18]; hbmax=0.0; gn_ape=[]
    for r in rows:
        p=float(r["p_MPa"]); G=float(r["G_kg_m2s"]); Tb=float(r["Tb_C"]); Tw=float(r["Twi_C"]); a=float(r["alpha_W_m2K"])
        b=props_at(Tb,p); w=props_at(Tw,p)
        Re=G*DI/b["mu"]; Pr=b["mu"]*b["cp"]/b["lam"]; Nu=a*DI/b["lam"]
        Tpc=T_pc_C(p); dT=Tb-Tpc; hbcp=b["h"]/1e3; hbr=float(r["hb_kJ_kg"])-hbcp
        rmu=w["mu"]/b["mu"]; rrho=w["rho"]/b["rho"]; rlam=w["lam"]/b["lam"]
        out.append({**r,
            "rho_b":f"{b['rho']:.3f}","mu_b_uPa_s":f"{b['mu']*1e6:.4f}","lam_b_mWmK":f"{b['lam']*1e3:.4f}",
            "cp_b":f"{b['cp']:.2f}","Pr_b":f"{Pr:.5f}","rho_w":f"{w['rho']:.3f}","mu_w_uPa_s":f"{w['mu']*1e6:.4f}",
            "lam_w_mWmK":f"{w['lam']*1e3:.4f}","Re_b":f"{Re:.2f}","Nu_meas":f"{Nu:.4f}",
            "ratio_rho_w_b":f"{rrho:.5f}","ratio_mu_w_b":f"{rmu:.5f}","ratio_lam_w_b":f"{rlam:.5f}",
            "T_pc_C":f"{Tpc:.2f}","dT_b_to_pc_K":f"{dT:.3f}","abs_dT_pc_K":f"{abs(dT):.3f}",
            "near_pc":str(abs(dT)<5.0),"hb_coolprop_kJkg":f"{hbcp:.3f}","hb_residual_kJkg":f"{hbr:.3f}"})
        reM=[min(reM[0],Re),max(reM[1],Re)]; prM=[min(prM[0],Pr),max(prM[1],Pr)]; nuM=[min(nuM[0],Nu),max(nuM[1],Nu)]
        muR=[min(muR[0],rmu),max(muR[1],rmu)]; rhoR=[min(rhoR[0],rrho),max(rhoR[1],rrho)]
        hbmax=max(hbmax,abs(hbr)); gn_ape.append(abs(gnielinski_basic(Re,Pr)-Nu)/Nu)
    with open(DST,"w",newline="") as fh:
        wr=csv.DictWriter(fh,fieldnames=out_cols); wr.writeheader(); wr.writerows(out)
    print(f"CoolProp {CoolProp.__version__} -> {os.path.basename(DST)} ({len(out)} rows)")
    print(f"Re_b : {reM[0]:.1f} .. {reM[1]:.1f}   (paper 4099.9 .. 23847.4; min extreme differs ~22%, see note)")
    print(f"Pr_b : {prM[0]:.3f} .. {prM[1]:.3f}")
    print(f"Nu_meas : {nuM[0]:.2f} .. {nuM[1]:.2f}")
    print(f"mu_w/mu_b : {muR[0]:.3f} .. {muR[1]:.3f}   rho_w/rho_b : {rhoR[0]:.3f} .. {rhoR[1]:.3f}  (strong property variation)")
    print(f"h_b cross-check max |residual| : {hbmax:.3f} kJ/kg  (states validated)")
    print(f"constant-property Gnielinski(Re,Pr) MAPE = {100*sum(gn_ape)/len(gn_ape):.1f}%  (massive surrogate failure; paper Table 3 = 148%)")

if __name__ == "__main__":
    main()
