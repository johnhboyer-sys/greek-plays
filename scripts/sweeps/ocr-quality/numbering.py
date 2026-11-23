"""Q3: do the printed margin numbers agree with counting OCR verse lines?

For each printed number P on a verse line, count verse lines since the
previous printed number Q: agreement when count == P - Q. Reports per play:
numbers attached (and how), agreements, disagreements (with the delta),
and numbers the parser could not attach to a verse line (own-line runs).
usage: numbering.py paley|jebb [play-to-list]
"""
import collections
import json
import sys

from common import OUT

ED = sys.argv[1]
SHOW = sys.argv[2] if len(sys.argv) > 2 else None
d = json.loads((OUT / f"{ED}-lines.json").read_text(encoding="utf-8"))
tot = collections.Counter()
rows = []
print(f"{'play':22s} {'nums':>5s} {'agree':>5s} {'disag':>5s} {'unatt':>5s}  modes; deltas")
for play, recs in d.items():
    verse = [r for r in recs if r["kind"] == "verse"]
    unatt = sum(1 for r in recs if r["kind"] == "num")
    modes = collections.Counter(r.get("num_mode") for r in verse if r.get("printed"))
    prev_n, prev_i = None, None
    agree = disag = 0
    deltas = collections.Counter()
    for i, r in enumerate(verse):
        p = r.get("printed")
        if not p:
            continue
        if prev_n is not None and 0 < p - prev_n <= 20:
            cnt = i - prev_i
            if cnt == p - prev_n:
                agree += 1
            else:
                disag += 1
                deltas[cnt - (p - prev_n)] += 1
                rows.append((play, r["src"], prev_n, p, cnt, r["text"][:50]))
        elif prev_n is not None:
            disag += 1
            deltas["jump"] += 1
            rows.append((play, r["src"], prev_n, p, i - prev_i, "JUMP " + r["text"][:44]))
        prev_n, prev_i = p, i
    tot.update({"nums": agree + disag + 1, "agree": agree, "disag": disag, "unatt": unatt})
    print(f"{play:22s} {agree+disag+1:5d} {agree:5d} {disag:5d} {unatt:5d}  {dict(modes)}; "
          f"{dict(sorted(deltas.items(), key=lambda kv: str(kv[0])))}")
print("TOTAL", dict(tot))
with (OUT / f"{ED}-numbering.tsv").open("w", encoding="utf-8") as fh:
    fh.write("play\tsrc\tprev_printed\tprinted\tcounted_lines\tline\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
if SHOW:
    for r in rows:
        if r[0] == SHOW:
            print(r)
