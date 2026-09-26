"""Turn a photographed comic page into clean, colored SVG sprites.

Pipeline per page:
  1. flatten the photo's lighting (divide by a dilated/blurred paper estimate)
  2. upscale the ink map 4x and keep each stroke's half-of-local-max core
     (consistent line weight for both faint pencil-light faces and bold outlines)
  3. per element box: isolate the drawing (drop neighbours cut by the box edge,
     stray specks, snow dots), split off animated parts (e.g. the flame)
  4. color: every enclosed hole of the line art is a paint region; seeds in the
     page spec pick region colors, unseeded regions take the element's base paint
  5. vectorize ink + paint masks with potrace into one layered SVG per element

Usage: python3 scripts/extract_art.py source/page1.json [--debug DIR]
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
U = 4  # tracing resolution multiplier
INK = "#2b1d17"

# base paints per element kind; seeds in the page spec override per region
PAINT = {
    "egg": {"base": "egg"},
    "candle": {"base": "wax"},
    "bubble": {"base": "paper"},
    "caption": {"base": None},
}
SWATCH = {
    "egg": ("#fff8ea", "#efd09e"),  # radial: highlight -> shade
    "wax": ("#f0876d", "#d9644c"),
    "cap": ("#ffc9b4", "#f7a58d"),  # melted top of the candle
    "flame": ("#ffe27a", "#ffb53d"),
    "paper": ("#fffdf7", "#fffdf7"),
    "earmuff": ("#ff9fb3", "#ec7792"),
    "band": ("#f4a4b6", "#e98aa0"),
    "scarf": ("#4fa7a0", "#3a8a84"),
    "pack": ("#ffc857", "#eda93a"),
    "bag": ("#9a6b4f", "#7f5540"),
    "white": ("#ffffff", "#f4f1ea"),
    "none": None,
}


def ellipse(d):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))


def page_ink(img_path, cache_dir):
    """Binary 4x ink mask of the whole page (cached)."""
    cache = cache_dir / (Path(img_path).stem + f"_ink{U}x.npy")
    if cache.exists():
        return np.load(cache)
    gray = cv2.cvtColor(cv2.imread(str(img_path)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    paper = cv2.GaussianBlur(cv2.dilate(gray, ellipse(25)), (0, 0), 15)
    ink = 1 - np.clip(gray / np.maximum(paper, 1), 0, 1)
    ink = cv2.GaussianBlur(ink, (0, 0), 0.8)
    ink = cv2.resize(ink, None, fx=U, fy=U, interpolation=cv2.INTER_CUBIC)
    local_max = cv2.GaussianBlur(cv2.dilate(ink, ellipse(31)), (0, 0), 8)
    mask = ((ink > np.maximum(0.45 * local_max, 0.12)) & (local_max > 0.16)).astype(np.uint8)
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache, mask)
    return mask


def drop_long_lines(crop):
    """Remove panel borders: straight runs spanning most of the crop."""
    h, w = crop.shape
    hl = cv2.morphologyEx(crop, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (int(w * 0.8), 1)))
    vl = cv2.morphologyEx(crop, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(h * 0.8))))
    return crop & (1 - cv2.dilate(hl | vl, ellipse(2 * U + 1)))


def components(mask):
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    h, w = mask.shape
    sizes = ndi.sum(mask, lab, range(1, n + 1)) if n else np.array([])
    objs = ndi.find_objects(lab)
    touches = np.array([s[0].start == 0 or s[1].start == 0 or s[0].stop == h or s[1].stop == w for s in objs], bool)
    return lab, n, sizes, objs, touches


def isolate(crop, kind, main_seed=None):
    """Keep the element's own strokes inside its (padded) crop."""
    crop = drop_long_lines(crop)
    lab, n, sizes, objs, touches = components(crop)
    if n == 0:
        return crop
    h, w = crop.shape

    if kind == "caption":
        # drop the label's frame (its edges can be tilted/wavy), keep the lettering
        frame = np.zeros_like(crop)
        segs = cv2.HoughLinesP(crop * 255, 1, np.pi / 360, threshold=int(w * 0.25), minLineLength=int(min(w * 0.3, 60 * U)), maxLineGap=U)
        for x_a, y_a, x_b, y_b in (segs.reshape(-1, 4) if segs is not None else []):
            horizontal = abs(x_b - x_a) > abs(y_b - y_a)
            # frame edges hug the rim of the label; lettering sits in the middle band
            on_rim_h = max(y_a, y_b) < h * 0.3 or min(y_a, y_b) > h * 0.7
            on_rim_v = max(x_a, x_b) < w * 0.12 or min(x_a, x_b) > w * 0.88
            if (horizontal and on_rim_h and abs(x_b - x_a) > w * 0.3) or (not horizontal and on_rim_v and abs(y_b - y_a) > h * 0.55):
                cv2.line(frame, (int(x_a), int(y_a)), (int(x_b), int(y_b)), 1, int(3 * U))
        vseg = cv2.morphologyEx(crop, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(h * 0.6))))
        text = crop & (1 - cv2.dilate(frame | vseg, ellipse(U + 1)))
        lab, n, sizes, objs, touches = components(text)
        keep = np.zeros(n + 1, bool)
        rim = 3 * U
        for i, (sl, sz) in enumerate(zip(objs, sizes), 1):
            bh, bw = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            inside = sl[0].start > rim and sl[1].start > rim and sl[0].stop < h - rim and sl[1].stop < w - rim
            sliver = bh <= 3.5 * U and bw >= 7 * U  # leftover piece of a frame edge
            keep[i] = inside and sz > 6 * U * U and not sliver
        return keep[lab].astype(np.uint8)

    if main_seed is not None:
        mx, my = main_seed
        yy, xx = np.nonzero(lab)
        k = np.argmin((xx - mx) ** 2 + (yy - my) ** 2)
        main = int(lab[yy[k], xx[k]])
    else:
        order = np.argsort(-sizes)
        main = next((int(i) + 1 for i in order if not touches[i]), int(order[0]) + 1)
    body = (lab == main).astype(np.uint8)
    sil = ndi.binary_fill_holes(cv2.morphologyEx(body, cv2.MORPH_CLOSE, ellipse(9 * U)))
    near = cv2.dilate(sil.astype(np.uint8), ellipse(4 * U + 1)).astype(bool)
    reach = cv2.dilate(sil.astype(np.uint8), ellipse(34 * U + 1)).astype(bool)
    keep = np.zeros(n + 1, bool)
    keep[main] = True
    for i, (s, sz) in enumerate(zip(objs, sizes), 1):
        if i == main or touches[i - 1]:
            continue
        comp = lab[s] == i
        span = max(s[0].stop - s[0].start, s[1].stop - s[1].start)
        if (near[s] & comp).any():  # face features, blush marks, accessory details
            keep[i] = True
        elif kind != "bubble" and span >= 8 * U and (reach[s] & comp).any():  # limbs, speed lines, effect marks (not snow dots)
            keep[i] = True
    return keep[lab].astype(np.uint8)


def paint_regions(ink, seeds, base, origin):
    """Label enclosed holes of the line art and map them to swatch names."""
    closed = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, ellipse(3 * U))
    filled = ndi.binary_fill_holes(closed)
    interior = filled & ~closed.astype(bool)
    lab, n = ndi.label(interior)
    names = {i: base for i in range(1, n + 1)}
    bx, by = origin
    for sx, sy, name in seeds:
        px, py = int((sx - bx) * U), int((sy - by) * U)
        if not (0 <= py < lab.shape[0] and 0 <= px < lab.shape[1]):
            print(f"  ! seed {sx},{sy} outside box", file=sys.stderr)
            continue
        r = 0
        while lab[py, px] == 0 and r < 12 * U:  # seed landed on a line: search nearby
            r += 1
            win = lab[max(0, py - r): py + r + 1, max(0, px - r): px + r + 1]
            if win.any():
                vals, counts = np.unique(win[win > 0], return_counts=True)
                names[int(vals[np.argmax(counts)])] = name
                break
        else:
            if lab[py, px]:
                names[int(lab[py, px])] = name
    return lab, names


def potrace_paths(mask, turd):
    """Vectorize a 0/1 mask → (transform, path d) using potrace."""
    h, w = mask.shape
    with tempfile.TemporaryDirectory() as td:
        pbm, svg = Path(td) / "m.pbm", Path(td) / "m.svg"
        pbm.write_bytes(f"P4\n{w} {h}\n".encode() + np.packbits(mask.astype(np.uint8), axis=1).tobytes())
        subprocess.run(
            ["potrace", str(pbm), "-s", "-o", str(svg), "--flat", "-t", str(turd), "-a", "1.15", "-O", "0.4", "-u", "2"],
            check=True,
        )
        text = svg.read_text()
    transform = re.search(r'<g transform="([^"]+)"', text).group(1)
    ds = re.findall(r'<path d="([^"]+)"', text, re.S)
    return transform, " ".join(d.replace("\n", " ") for d in ds)


def gradient_defs(uid, name):
    hi, lo = SWATCH[name]
    return (
        f'<radialGradient id="{uid}" cx="0.38" cy="0.3" r="0.85">'
        f'<stop offset="0" stop-color="{hi}"/><stop offset="1" stop-color="{lo}"/></radialGradient>'
    )


def build_svg(ink, lab, names, shadow_names=()):
    h, w = ink.shape
    defs, layers = [], []
    groups = {}
    for i, name in names.items():
        if SWATCH.get(name) is None:
            continue
        groups.setdefault(name, []).append(i)
    order = sorted(groups, key=lambda nm: -sum((lab == i).sum() for i in groups[nm]))
    for k, name in enumerate(order):
        region = np.isin(lab, groups[name]).astype(np.uint8)
        region = cv2.dilate(region, ellipse(2 * U - 1))  # tuck paint under the ink
        if region.sum() < 20:
            continue
        tf, d = potrace_paths(region, turd=2)
        uid = f"g{k}"
        defs.append(gradient_defs(uid, name))
        layers.append(f'<g transform="{tf}" fill="url(#{uid})"><path d="{d}"/></g>')
    tf, d = potrace_paths(ink, turd=6)
    layers.append(f'<g transform="{tf}" fill="{INK}"><path d="{d}"/></g>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w // U}" height="{h // U}">'
        f'<defs>{"".join(defs)}</defs>{"".join(layers)}</svg>'
    )


def main():
    spec_path = Path(sys.argv[1])
    debug = Path(sys.argv[sys.argv.index("--debug") + 1]) if "--debug" in sys.argv else None
    spec = json.loads(spec_path.read_text())
    page = spec["page"]
    mask = page_ink(ROOT / spec["image"], ROOT / ".cache")
    out_dir = ROOT / "assets" / "art" / f"p{page}"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for el in spec["elements"]:
        eid, kind = el["id"], el["kind"]
        pad = el.get("pad", 6)
        x0, y0, x1, y1 = el["box"][0] - pad, el["box"][1] - pad, el["box"][2] + pad, el["box"][3] + pad
        crop = mask[y0 * U: y1 * U, x0 * U: x1 * U].copy()
        if "clip" in el:  # polygon (page coords) that bounds this element when neighbours touch it
            poly = np.array([[(px - x0) * U, (py - y0) * U] for px, py in el["clip"]], np.int32)
            keep = np.zeros_like(crop)
            cv2.fillPoly(keep, [poly], 1)
            crop &= keep
        for (ex0, ey0, ex1, ey1) in el.get("erase", []):
            crop[(ey0 - y0) * U: (ey1 - y0) * U, (ex0 - x0) * U: (ex1 - x0) * U] = 0
        main_seed = None
        if "main" in el:
            main_seed = ((el["main"][0] - x0) * U, (el["main"][1] - y0) * U)
        ink = isolate(crop, kind, main_seed)
        entry = {"box": [x0, y0, x1, y1], "src": f"assets/art/p{page}/{eid}.svg", "parts": {}}

        # paint regions come from the intact drawing, before parts are lifted off
        base = PAINT[kind]["base"]
        if base is None:
            lab, names = np.zeros_like(ink, dtype=np.int32), {}
        else:
            lab, names = paint_regions(ink, el.get("seeds", []), base, (x0, y0))

        for part, pspec in el.get("parts", {}).items():
            # a part is a rect [x0, y0, x1, y1] or {"poly": [[x, y], ...], "pivot": [x, y]} in page coords
            poly = pspec["poly"] if isinstance(pspec, dict) else [
                [pspec[0], pspec[1]], [pspec[2], pspec[1]], [pspec[2], pspec[3]], [pspec[0], pspec[3]]]
            xs, ys = [q[0] for q in poly], [q[1] for q in poly]
            px0, py0, px1, py1 = max(min(xs), x0), max(min(ys), y0), min(max(xs), x1), min(max(ys), y1)
            pmask = np.zeros_like(ink)
            cv2.fillPoly(pmask, [np.array([[(qx - x0) * U, (qy - y0) * U] for qx, qy in poly], np.int32)], 1)
            pink = ink & pmask
            ink &= 1 - pmask
            # regions enclosed by the part (e.g. the flame's inside) move with it
            for i in np.unique(lab[pmask > 0]):
                if i and (pmask[lab == i]).mean() > 0.5:
                    names[int(i)] = "none"
            sl = (slice((py0 - y0) * U, (py1 - y0) * U), slice((px0 - x0) * U, (px1 - x0) * U))
            pcrop = pink[sl]
            plab, pnames = paint_regions(pcrop, [], "flame" if part == "flame" else "none", (px0, py0))
            (out_dir / f"{eid}--{part}.svg").write_text(build_svg(pcrop, plab, pnames))
            entry["parts"][part] = {"box": [px0, py0, px1, py1], "src": f"assets/art/p{page}/{eid}--{part}.svg"}
            if isinstance(pspec, dict) and "pivot" in pspec:
                entry["parts"][part]["pivot"] = pspec["pivot"]

        (out_dir / f"{eid}.svg").write_text(build_svg(ink, lab, names))
        manifest[eid] = entry

        if debug:
            debug.mkdir(parents=True, exist_ok=True)
            vis = np.full((*ink.shape, 3), 255, np.uint8)
            rng = np.random.default_rng(3)
            for i in range(1, int(lab.max()) + 1):
                vis[lab == i] = rng.integers(90, 250, 3)
            vis[ink > 0] = (30, 30, 30)
            vis = cv2.resize(vis, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
            for i in range(1, int(lab.max()) + 1):
                reg = (lab == i).astype(np.uint8)
                if reg.sum() < 30 * U * U:
                    continue
                dist = cv2.distanceTransform(reg, cv2.DIST_L2, 5)
                py, px = np.unravel_index(np.argmax(dist), dist.shape)
                cv2.circle(vis, (int(px / 2), int(py / 2)), 3, (0, 0, 0), -1)
                cv2.putText(vis, f"{x0 + px // U},{y0 + py // U}", (int(px / 2) - 26, int(py / 2) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 0, 0), 1)
            cv2.imwrite(str(debug / f"{eid}.png"), vis)
        print(f"{eid}: regions={int(lab.max())} parts={list(entry['parts'])}")

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
