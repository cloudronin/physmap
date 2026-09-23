#!/usr/bin/env python3
"""Digitise Figure 6.13 of Lewis (1992): local Nu vs x*, five runs at Re 1098-1181.

WHY THIS FIGURE. Figure 7.4 covers three of the same runs but overlays the numerical
prediction curves, and those curves merge with the markers into one ink component. 6.13
carries markers only.

WHY IT CAN BE TRUSTED AT ALL. Test 35A appears in this figure AND has its twelve local Nu
values printed in Appendix D-2. It is a calibration standard inside the plot, so the
digitisation error is measured rather than assumed. The independent check is the Prandtl
number: correcting the x* bias and forming Re*Pr = (x/d)/x* returns 8.46, which is exactly
Lewis's printed value, and Pr entered neither the axis fit nor the glyph templates.

WHAT IT REFUSES TO DO. Multi-marker ink clusters are skipped, never split. A guessed
decomposition would put invented points into an evaluation set.

The source PDF is NOT redistributed. Point --pdf at your own copy from
https://openaccess.city.ac.uk/id/eprint/28530/
"""
from __future__ import annotations
import argparse, json, pathlib, sys
import numpy as np
from scipy import ndimage

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _glyph_features import features

PAGE = 195                      # 1-based PDF page holding Figure 6.13
X_TICKS = [(1097.0, -5), (1832.5, -4), (2566.5, -3), (3300.5, -2), (4035.0, -1)]
Y_TICKS = [(921.5, 20), (1463.0, 10), (1636.0, 8), (1860.5, 6), (2178.0, 4), (2729.5, 2)]
PLOT = dict(top=470, bottom=2660, left=1170, right=3975)
LEGEND = dict(top=1900, bottom=2660, left=1550, right=3700)
LEGEND_COL = (1660, 1790)       # x-range of the legend's own marker glyphs
# legend order, top to bottom -- read from the figure, not guessed
SERIES = ["16A", "20A", "35A", "9A", "13A"]
X_OVER_D = [0.31, 0.85, 2.45, 5.65, 9.92, 16.32, 33.39, 50.47, 67.55, 101.69, 135.84, 159.33]


def _fit(ticks):
    p = np.array([t[0] for t in ticks], float)
    v = np.log10(np.array([t[1] for t in ticks], float)) if ticks[0][1] > 0 \
        else np.array([t[1] for t in ticks], float)
    m, c = np.linalg.lstsq(np.vstack([p, np.ones_like(p)]).T, v, rcond=None)[0]
    return m, c, float(np.abs(v - (m * p + c)).max())


def classify(f: dict) -> str | None:
    """Five glyphs: square, circle-with-dot, triangle, plus, cross.

    Thresholds sit midway between the legend templates' own values, so a marker that is
    damaged or overlapping falls through to None rather than into the nearest class.
    """
    if f["holes"] == 0:
        if f["cross"] > f["diag"] * 1.5: return "9A"      # plus
        if f["diag"] > f["cross"] * 1.5: return "13A"     # cross
        return None
    if f["cy"] > 0.055: return "35A"                      # triangle sits low in its box
    if f["corners"] > 0.26: return "16A"                  # square fills its corners
    if f["corners"] < 0.22: return "20A"                  # circle does not
    return None


def digitise(png: pathlib.Path) -> dict:
    from PIL import Image
    b = np.array(Image.open(png).convert("L")) < 128
    mx, cx, rx = _fit(X_TICKS)
    my, cy, ry = _fit(Y_TICKS)

    data = np.zeros_like(b)
    data[PLOT["top"]:PLOT["bottom"], PLOT["left"]:PLOT["right"]] = \
        b[PLOT["top"]:PLOT["bottom"], PLOT["left"]:PLOT["right"]]
    data[LEGEND["top"]:LEGEND["bottom"], LEGEND["left"]:LEGEND["right"]] = False

    lab, n = ndimage.label(data, np.ones((3, 3), int))
    pts, skipped = [], 0
    for k, sl in enumerate(ndimage.find_objects(lab), start=1):
        sub = (lab[sl] == k)
        area = int(sub.sum())
        if area < 200:
            continue
        h, w = sub.shape
        if not (30 <= h <= 62 and 30 <= w <= 64 and 500 <= area <= 1900):
            skipped += 1                      # merged cluster: skipped, never split
            continue
        t = classify(features(sub))
        if t is None:
            skipped += 1
            continue
        pts.append({"test": t,
                    "x_star": float(10 ** (mx * ((sl[1].start + sl[1].stop) / 2) + cx)),
                    "Nu_raw": float(10 ** (my * ((sl[0].start + sl[0].stop) / 2) + cy))})
    return {"points": pts, "skipped_components": skipped,
            "x_fit_max_resid_dex": rx, "y_fit_max_resid_dex": ry}


def snap_to_grid(pts: list[dict]) -> tuple[float | None, list[dict]]:
    """Assign each point an x/d from Lewis's fixed thermocouple grid.

    The grid is the same twelve axial positions for every run; only Re*Pr differs. A run
    whose points cannot all be placed within 5% of a grid position is rejected outright --
    that is how the 20A misclassification is caught rather than reported.
    """
    # A single point can be snapped to ANY grid position, so the consistency test below is
    # vacuous below three points. 20A recovers exactly one marker and would otherwise be
    # reported with a Prandtl number of 0.15; require a real constraint instead.
    if len(pts) < 3:
        return None, []
    pts = sorted(pts, key=lambda p: p["x_star"])
    best = None
    for cand in X_OVER_D:
        rp = cand / pts[-1]["x_star"]
        errs = []
        for p in pts:
            xd = p["x_star"] * rp
            near = min(X_OVER_D, key=lambda v: abs(v / xd - 1))
            e = abs(near / xd - 1)
            if e > 0.05:
                errs = None
                break
            errs.append(e)
        if errs and (best is None or np.mean(errs) < best[1]):
            best = (rp, float(np.mean(errs)))
    if best is None:
        return None, []
    # Water over Lewis's temperature range gives Pr roughly 4-10, and this figure's runs sit
    # near Re 1100, so Re*Pr near 5e3-1.2e4. A fit far outside that is a misclassification.
    if not (3.0e3 <= best[0] <= 1.5e4):
        return None, []
    rp, _ = best
    return rp, [dict(p, x_over_d=min(X_OVER_D, key=lambda v: abs(v / (p["x_star"] * rp) - 1)))
                for p in pts]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, help="your own copy of the Lewis 1992 thesis")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out", default="-")
    a = ap.parse_args()
    import pymupdf
    doc = pymupdf.open(a.pdf)
    png = pathlib.Path("/tmp") / f"lewis_p{PAGE}_{a.dpi}.png"
    doc[PAGE - 1].get_pixmap(dpi=a.dpi).save(png)

    res = digitise(png)
    by = {}
    for t in SERIES:
        rp, snapped = snap_to_grid([p for p in res["points"] if p["test"] == t])
        by[t] = {"Re_times_Pr_implied": rp, "n": len(snapped), "points": snapped}
    out = {"figure": "6.13", "dpi": a.dpi, **{k: v for k, v in res.items() if k != "points"},
           "series": by}
    text = json.dumps(out, indent=2)
    if a.out == "-":
        print(text)
    else:
        pathlib.Path(a.out).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
