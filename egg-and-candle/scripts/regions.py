"""List an element's paint regions (page coords of each region's deepest
point, and area) to pick seeds for the page spec.

Usage: python3 scripts/regions.py source/page3.json egg-back [candle-play ...]
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_art as ea  # noqa: E402

U = ea.U
spec = json.loads(Path(sys.argv[1]).read_text())
mask = ea.page_ink(ea.ROOT / spec["image"], ea.ROOT / ".cache", spec.get("ink", "fwhm"))
for eid in sys.argv[2:]:
    el = next(e for e in spec["elements"] if e["id"] == eid)
    pad = el.get("pad", 6)
    x0, y0, x1, y1 = el["box"][0] - pad, el["box"][1] - pad, el["box"][2] + pad, el["box"][3] + pad
    crop = mask[y0 * U: y1 * U, x0 * U: x1 * U].copy()
    if "clip" in el:
        keep = np.zeros_like(crop)
        cv2.fillPoly(keep, [np.array([[(px - x0) * U, (py - y0) * U] for px, py in el["clip"]], np.int32)], 1)
        crop &= keep
    for (ex0, ey0, ex1, ey1) in el.get("erase", []):
        crop[max(0, (ey0 - y0) * U): max(0, (ey1 - y0) * U), max(0, (ex0 - x0) * U): max(0, (ex1 - x0) * U)] = 0
    for mx0, my0, mx1, my1, mt in el.get("mend", []):
        cv2.line(crop, (round((mx0 - x0) * U), round((my0 - y0) * U)), (round((mx1 - x0) * U), round((my1 - y0) * U)), 1, round(mt * U))
    main = ((el["main"][0] - x0) * U, (el["main"][1] - y0) * U) if "main" in el else None
    ink = ea.isolate(crop, el["kind"], main, el.get("keep") == "all", el.get("borders", "hv"))
    sealed = ink.copy()
    for sx0, sy0, sx1, sy1 in el.get("seal", []):
        cv2.line(sealed, ((sx0 - x0) * U, (sy0 - y0) * U), ((sx1 - x0) * U, (sy1 - y0) * U), 1, 2 * U)
    lab, names = ea.paint_regions(sealed, el.get("seeds", []), "egg", (x0, y0))
    print(eid)
    for i in range(1, int(lab.max()) + 1):
        reg = (lab == i).astype(np.uint8)
        area = reg.sum() / (U * U)
        if area < 8:
            continue
        dist = cv2.distanceTransform(reg, cv2.DIST_L2, 5)
        py, px = np.unravel_index(np.argmax(dist), dist.shape)
        ys, xs = np.nonzero(reg)
        print(f"  region {i:2d} at {x0 + px // U},{y0 + py // U}  area {area:7.0f}  x {x0 + xs.min() // U}-{x0 + xs.max() // U} y {y0 + ys.min() // U}-{y0 + ys.max() // U}  -> {names[i]}")
