"""Contact sheet of every extracted sprite of a page, rendered on a mid-tone
background so paint, ink and transparency are all visible.

Usage: python3 scripts/sheet.py 1 out.png
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
page, out = sys.argv[1], sys.argv[2]
man = json.loads((ROOT / f"assets/art/p{page}/manifest.json").read_text())
tiles = []
with tempfile.TemporaryDirectory() as td:
    for eid, e in man.items():
        items = [(eid, e["src"])] + [(f"{eid}:{k}", p["src"]) for k, p in e["parts"].items()]
        for name, src in items:
            png = Path(td) / "t.png"
            subprocess.run(["rsvg-convert", "-z", "1.5", "-o", str(png), str(ROOT / src)], check=True)
            im = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
            a = im[:, :, 3:4].astype(np.float32) / 255
            bg = np.full(im.shape[:2] + (3,), (205, 190, 170), np.float32)
            comp = (im[:, :, :3] * a + bg * (1 - a)).astype(np.uint8)
            h, w = comp.shape[:2]
            tile = np.full((h + 24, max(w, 140), 3), 255, np.uint8)
            tile[24:, :w] = comp
            cv2.putText(tile, name, (2, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 0, 0), 1)
            tiles.append(tile)
W = 1600
rows, row, rw = [], [], 0
for t in tiles:
    if rw + t.shape[1] + 12 > W and row:
        rows.append(row)
        row, rw = [], 0
    row.append(t)
    rw += t.shape[1] + 12
rows.append(row)
lines = []
for r in rows:
    H = max(t.shape[0] for t in r)
    line = np.full((H + 12, W, 3), 255, np.uint8)
    x = 0
    for t in r:
        line[: t.shape[0], x: x + t.shape[1]] = t
        x += t.shape[1] + 12
    lines.append(line)
cv2.imwrite(out, np.vstack(lines))
