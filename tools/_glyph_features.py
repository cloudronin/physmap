import numpy as np
from scipy import ndimage

def features(mask):
    """Shape descriptors that separate the five Lewis marker glyphs."""
    m = mask.astype(bool)
    h, w = m.shape
    area = m.sum()
    fill = area / (h * w)
    ys, xs = np.nonzero(m)
    cy = (ys.mean() - (h - 1) / 2) / h          # + = mass sits low in the box
    cx = (xs.mean() - (w - 1) / 2) / w
    # holes: label the background inside the bbox; interior components = holes
    inv = ~m
    lab, n = ndimage.label(inv)
    border = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    holes = sum(1 for k in range(1, n + 1) if k not in border and (lab == k).sum() > 4)
    # ink on the central cross vs the two diagonals -- separates + from x
    r = max(2, min(h, w) // 8)
    mid_r = m[max(0,h//2-r):h//2+r+1, :].sum()
    mid_c = m[:, max(0,w//2-r):w//2+r+1].sum()
    cross = (mid_r + mid_c) / max(area, 1)
    dg = 0
    for i in range(h):
        j = int(round(i * (w - 1) / max(h - 1, 1)))
        for dj in range(-r, r + 1):
            if 0 <= j + dj < w and m[i, j + dj]: dg += 1
        j2 = w - 1 - j
        for dj in range(-r, r + 1):
            if 0 <= j2 + dj < w and m[i, j2 + dj]: dg += 1
    diag = dg / max(area, 1)
    # corner occupancy -- separates the square from the circle
    q = max(2, min(h, w) // 4)
    corners = (m[:q, :q].sum() + m[:q, -q:].sum() + m[-q:, :q].sum() + m[-q:, -q:].sum()) / max(area, 1)
    return dict(h=h, w=w, area=int(area), fill=round(fill,3), aspect=round(w/h,3),
                cy=round(cy,3), cx=round(cx,3), holes=holes,
                cross=round(cross,3), diag=round(diag,3), corners=round(corners,3))
