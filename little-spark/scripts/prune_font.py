"""Copy only the LXGW WenKai subset chunks needed for the text in index.html.

Usage: python3 scripts/prune_font.py <path-to-lxgw-wenkai-webfont-package>
"""
import re
import shutil
import sys
from pathlib import Path

pkg = Path(sys.argv[1])
root = Path(__file__).resolve().parent.parent
out_dir = root / "assets" / "fonts"
html = (root / "index.html").read_text(encoding="utf-8")
chars = {ord(c) for c in re.sub(r"<[^>]+>", "", html) if ord(c) > 32}

css = (pkg / "lxgwwenkai-regular.css").read_text(encoding="utf-8")
blocks = re.findall(r"@font-face\s*{[^}]*}", css)


def covers(block):
    rng = re.search(r"unicode-range:\s*([^;}]+)", block).group(1)
    for part in rng.split(","):
        part = part.strip().lower().removeprefix("u+")
        lo, _, hi = part.partition("-")
        lo, hi = int(lo, 16), int(hi or lo, 16)
        if any(lo <= c <= hi for c in chars):
            return True
    return False


for old in out_dir.glob("*.woff2"):
    old.unlink()
kept = [b for b in blocks if covers(b)]
for b in kept:
    fname = re.search(r"url\('\./files/([^']+)'\)", b).group(1)
    shutil.copy(pkg / "files" / fname, out_dir / fname)
(out_dir / "lxgwwenkai-regular.css").write_text(
    "/* LXGW WenKai (SIL OFL 1.1) — pruned to the glyphs used in this video */\n"
    + "\n".join(b.replace("./files/", "./") for b in kept),
    encoding="utf-8",
)
shutil.copy(pkg / "OFL.txt", out_dir / "OFL.txt")
print(f"kept {len(kept)}/{len(blocks)} font chunks")
