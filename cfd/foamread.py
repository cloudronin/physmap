"""Minimal reader for OpenFOAM ASCII fields, plus Nusselt extraction for the wedge.

The mesh is a structured wedge of `nr` radial by `ny` axial cells, and blockMesh orders
cells with the radial index fastest. So cells `[k*nr : (k+1)*nr]` are the radial profile
at axial station `k`, which makes the cross-sectional integrals direct.

THE QoI IS ONE DEFINITION, NOT TWO
----------------------------------
The quantity of interest is the **flux-weighted (mixing-cup) Nusselt number**:

    Nu = q_w D / (k (T_wall - T_bulk)),   T_bulk = integral(rho u T dA) / integral(rho u dA)

That is what `h = q/(T_w - T_b)` means for internal flow, and it is the definition the
original study settled on ("a reversal-aware mixing-cup bulk temperature").

An earlier version of this module also computed an **area-weighted** bulk temperature and
reported the gap as a "Nusselt-extraction sensitivity". **That framing was wrong.** The
two are different physical quantities, not two readings of one; the velocity profile
weights the core more heavily than the wall region, so a 20-30% gap is expected and says
nothing about how well the QoI is determined. Presenting it as an ambiguity in the QoI
made a well-defined quantity look uncertain.

The area-weighted value is still computed, and still reported -- as a **profile-shape
diagnostic**, labelled as such. A genuine extraction sensitivity (cell-centre versus
face-interpolated wall temperature, radial integration weighting, near-axis treatment)
is a separate study and has not been done.
"""
from __future__ import annotations
import math, pathlib, re

NUM = r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?"


def _strip(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def read_internal(path: pathlib.Path) -> list[float] | list[tuple[float, float, float]]:
    t = _strip(path.read_text())
    m = re.search(r"internalField\s+nonuniform\s+List<(scalar|vector)>\s*\n?\s*(\d+)\s*\((.*?)\n\)\s*;",
                  t, flags=re.S)
    if m:
        kind, n, body = m.group(1), int(m.group(2)), m.group(3)
        if kind == "scalar":
            vals = [float(x) for x in re.findall(NUM, body)]
            assert len(vals) == n, f"{path.name}: expected {n} scalars, got {len(vals)}"
            return vals
        trip = re.findall(rf"\(\s*({NUM})\s+({NUM})\s+({NUM})\s*\)", body)
        assert len(trip) == n, f"{path.name}: expected {n} vectors, got {len(trip)}"
        return [(float(a), float(b), float(c)) for a, b, c in trip]
    m = re.search(rf"internalField\s+uniform\s+({NUM})\s*;", t)
    if m:
        return [float(m.group(1))]
    m = re.search(rf"internalField\s+uniform\s*\(\s*({NUM})\s+({NUM})\s+({NUM})\s*\)\s*;", t)
    if m:
        return [tuple(float(m.group(i)) for i in (1, 2, 3))]
    raise ValueError(f"{path}: no internalField found")


def read_patch(path: pathlib.Path, patch: str) -> list[float]:
    """The `value` entry on one patch, uniform or nonuniform."""
    t = _strip(path.read_text())
    i = t.find("boundaryField")
    blk = t[i:]
    j = re.search(rf"\b{re.escape(patch)}\b\s*\{{", blk)
    if not j:
        raise ValueError(f"{path}: patch {patch!r} not found")
    sub = blk[j.end():]
    depth, end = 1, 0
    for k, ch in enumerate(sub):
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0: end = k; break
    sub = sub[:end]
    m = re.search(rf"value\s+nonuniform\s+List<scalar>\s*\n?\s*(\d+)\s*\((.*?)\)\s*;", sub, flags=re.S)
    if m:
        return [float(x) for x in re.findall(NUM, m.group(2))]
    m = re.search(rf"value\s+uniform\s+({NUM})\s*;", sub)
    if m:
        return [float(m.group(1))]
    raise ValueError(f"{path}: no value on patch {patch!r}")


def radial_weights(nr: int, R: float) -> list[float]:
    """Annular area weight per radial cell; proportional within the wedge."""
    dr = R / nr
    return [((i + 1) * dr) ** 2 - (i * dr) ** 2 for i in range(nr)]


def nusselt(case: pathlib.Path, time: str, nr: int, ny: int, R: float, k_th: float,
            q_w: float) -> dict:
    T = read_internal(case / time / "T")
    U = read_internal(case / time / "U")
    rho = read_internal(case / time / "rho") if (case / time / "rho").exists() else None
    Tw = read_patch(case / time / "T", "wall")
    if len(Tw) == 1:
        Tw = Tw * ny
    assert len(T) == nr * ny, f"expected {nr*ny} cells, got {len(T)}"
    aw = radial_weights(nr, R)
    D = 2 * R

    local = []
    for kk in range(ny):
        sl = slice(kk * nr, (kk + 1) * nr)
        Tk, Uk = T[sl], U[sl]
        rk = rho[sl] if rho else [1.0] * nr
        uy = [u[1] for u in Uk]
        num_f = sum(a * r * u * t for a, r, u, t in zip(aw, rk, uy, Tk))
        den_f = sum(a * r * u for a, r, u in zip(aw, rk, uy))
        Tb_flux = num_f / den_f if abs(den_f) > 1e-30 else float("nan")
        Tb_area = sum(a * t for a, t in zip(aw, Tk)) / sum(aw)
        tw = Tw[kk]
        local.append({
            "k": kk,
            "y": (kk + 0.5) * (0.9 / ny),
            "T_wall": tw,
            "Tb_flux": Tb_flux,
            "Tb_area": Tb_area,
            "Nu_flux": q_w * D / (k_th * (tw - Tb_flux)) if tw - Tb_flux > 1e-9 else float("nan"),
            "Nu_area": q_w * D / (k_th * (tw - Tb_area)) if tw - Tb_area > 1e-9 else float("nan"),
            "net_axial_flux": den_f,
        })

    def avg(key):
        vals = [r[key] for r in local if not math.isnan(r[key])]
        return sum(vals) / len(vals) if vals else float("nan")

    reversal = sum(1 for r in local if r["net_axial_flux"] <= 0)
    nu_f, nu_a = avg("Nu_flux"), avg("Nu_area")
    return {
        # THE QoI. One definition.
        "Nu": nu_f,
        "Nu_avg_flux_weighted": nu_f,
        # A profile-shape diagnostic, NOT a competing definition of the QoI and NOT an
        # extraction sensitivity. See the module docstring.
        "Nu_area_weighted_diagnostic": nu_a,
        "profile_shape_diagnostic_rel": abs(nu_f - nu_a) / nu_f if nu_f == nu_f else None,
        "stations_with_non_positive_net_flux": reversal,
        "T_wall_outlet": local[-1]["T_wall"],
        "Tb_flux_outlet": local[-1]["Tb_flux"],
        "local": local,
    }
