"""Split numbering disagreements into dialogue-looking spans (all lines 34-62
chars: trimeters) and the rest (lyric / anapaests / tetrameters)."""
import collections, json, sys
from common import OUT
ED = sys.argv[1]
d = json.loads((OUT / f"{ED}-lines.json").read_text(encoding="utf-8"))
res = collections.Counter(); ex = []
for play, recs in d.items():
    verse = [r for r in recs if r["kind"] == "verse"]
    pn = pi = None
    for i, r in enumerate(verse):
        p = r.get("printed")
        if not p: continue
        if pn is not None and 0 < p - pn <= 20:
            span = verse[pi + 1:i + 1]
            dia = all(34 <= len(x["text"]) <= 62 for x in span) and all(34 <= len(x["text"]) <= 62 for x in verse[max(0,pi-2):pi+1])
            ok = (i - pi) == (p - pn)
            res[(dia, ok)] += 1
            if dia and not ok:
                ex.append((play, r["src"], pn, p, i - pi, r.get("num_mode"), r["text"][:40]))
        pn, pi = p, i
for k in sorted(res): print(("dialogue" if k[0] else "other   "), ("agree" if k[1] else "DISAGREE"), res[k])
for e in ex[: int(sys.argv[2]) if len(sys.argv) > 2 else 20]: print(e)
