"""Draw the hand-review sample of differing lines (seeded) and print it compactly."""
import json, random, sys
from common import OUT
ED, spec = sys.argv[1], sys.argv[2]   # spec: play:n,play:n
d = json.loads((OUT / f"{ED}-align.json").read_text(encoding="utf-8"))
rnd = random.Random(20260929)
out = []
for part in spec.split(","):
    play, n = part.split(":")
    rows = [r for r in d["rows"] if r["play"] == play and r["diffs"]]
    out += sorted(rnd.sample(rows, min(int(n), len(rows))), key=lambda r: r["src"])
(OUT / f"{ED}-sample.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
for k, r in enumerate(out, 1):
    ds = "; ".join(f"{x['o']}>{x['c']}" + ("" if x["cls"] == "EDIT" else f"[{x['cls'][0]}]") for x in r["diffs"])
    print(f"{k}|{r['play'][:4]} {r['src']} {r['pn']}|{r['ocr']}||{r['cmp']}||{ds}")
