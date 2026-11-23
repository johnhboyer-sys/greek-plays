"""Summaries of <ed>-align.json: class counts per play, missing stretches, top patterns."""
import collections
import json
import sys

from common import OUT

ED = sys.argv[1]
d = json.loads((OUT / f"{ED}-align.json").read_text(encoding="utf-8"))
rows = d["rows"]
by = collections.defaultdict(collections.Counter)
kinds = collections.Counter()
for r in rows:
    for x in r["diffs"]:
        by[r["play"]][x["cls"]] += 1
        kinds[(x["cls"], x["kind"].split("|")[0])] += 1
for p, c in by.items():
    n = sum(1 for r in rows if r["play"] == p)
    nd = sum(1 for r in rows if r["play"] == p and r["diffs"])
    print(f"{p:22s} lines={n:5d} difflines={nd:5d} {dict(c)}")
print()
for k, v in kinds.most_common(40):
    print(v, k)
if len(sys.argv) > 2:
    cls = sys.argv[2]
    lim = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    play = sys.argv[4] if len(sys.argv) > 4 else None
    k = 0
    for r in rows:
        if play and r["play"] != play:
            continue
        for x in r["diffs"]:
            if x["cls"] == cls:
                print(r["play"], r["src"], r["pn"], "|", x["o"], "→", x["c"], "|", x["kind"], "|", r["ocr"][:70])
                k += 1
                break
        if k >= lim:
            break
