"""Full-page art for the bookends: the whole page's ink as one SVG plus each
panel's interior outline (for color washes under the ink).

Usage: python3 scripts/page_art.py source/page1.json
Needs in the page spec: "page_clip" (polygon keeping the sheet, dropping the
photo's desk/shadow), optional "border_lines" to restore panel edges lost in
that shadow, and "panels" (each panel's corner polygon, copied to panels.json).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_art as ea  # noqa: E402

U = ea.U


def main():
    spec = json.loads(Path(sys.argv[1]).read_text())
    page = spec["page"]
    mask = ea.page_ink(ea.ROOT / spec["image"], ea.ROOT / ".cache").copy()
    keep = np.zeros_like(mask)
    cv2.fillPoly(keep, [np.array([[x * U, y * U] for x, y in spec["page_clip"]], np.int32)], 1)
    mask &= keep
    for x0, y0, x1, y1, t in spec.get("border_lines", []):  # borders lost in the photo's edge shadow
        cv2.line(mask, (x0 * U, y0 * U), (x1 * U, y1 * U), 1, t * U)
    # drop isolated specks (paper grain) but keep the comic's own snow dots
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    small = np.zeros(n, bool)
    small[1:] = stats[1:, cv2.CC_STAT_AREA] < 6 * U * U
    mask[small[lab]] = 0

    out_dir = ea.ROOT / "assets" / "art" / f"p{page}"
    out_dir.mkdir(parents=True, exist_ok=True)
    h, w = mask.shape
    tf, d = ea.potrace_paths(mask, turd=6)
    (out_dir / "page-ink.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w // U}" height="{h // U}">'
        f'<g transform="{tf}" fill="{ea.INK}"><path d="{d}"/></g></svg>'
    )

    panels = spec["panels"]
    (out_dir / "panels.json").write_text(json.dumps(panels))


if __name__ == "__main__":
    main()
