"""Print a compact JS table of sprite boxes/parts for a page, to paste into its
composition (boxes are padded page-pixel crops; parts carry pivots).

Usage: python3 scripts/art_table.py 1
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
page = sys.argv[1]
man = json.loads((ROOT / f"assets/art/p{page}/manifest.json").read_text())
rows = []
for eid, e in man.items():
    parts = {}
    for k, p in e["parts"].items():
        parts[k] = {"b": p["box"]} | ({"pv": p["pivot"]} if "pivot" in p else {})
    row = {"b": e["box"]} | ({"p": parts} if parts else {})
    rows.append(f'  "{eid}": {json.dumps(row, separators=(",", ":"))}')
print("const ART = {\n" + ",\n".join(rows) + "\n};")
