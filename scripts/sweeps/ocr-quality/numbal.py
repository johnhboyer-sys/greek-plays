"""Of the numbering disagreements, which cancel out at the next printed number
(a number set one line off), and which leave a lasting offset (a line lost,
split, merged, or a colometry difference)?"""
import collections, json, sys
from common import OUT
ED = sys.argv[1]
d = json.loads((OUT / f"{ED}-lines.json").read_text(encoding="utf-8"))
res = collections.Counter(); lasting = []
for play, recs in d.items():
    v = [r for r in recs if r["kind"] == "verse"]
    nums = [(i, r["printed"]) for i, r in enumerate(v) if r.get("printed")]
    for k in range(1, len(nums) - 1):
        (i0, p0), (i1, p1), (i2, p2) = nums[k - 1], nums[k], nums[k + 1]
        if not (0 < p1 - p0 <= 20 and 0 < p2 - p1 <= 20):
            continue
        if i1 - i0 == p1 - p0:
            continue
        dia = all(34 <= len(x["text"]) <= 62 for x in v[i0:i2 + 1])
        if (i2 - i0) == (p2 - p0):
            res[("dialogue" if dia else "other", "cancels (number set 1 line off)")] += 1
        else:
            res[("dialogue" if dia else "other", "lasting")] += 1
            if dia: lasting.append((play, v[i1]["src"], p0, p1, i1 - i0, v[i1]["text"][:45]))
for k, n in sorted(res.items()): print(k, n)
for x in lasting: print("  ", x)
