"""Q1: per play line counts, token recall vs Perseus, duplicated lines, running-head
leaks, LaTeX-damaged lines, last printed number."""
import collections, json, re, sys
from common import OUT, key_form, tokens
for ed in ("paley", "jebb"):
    lines = json.loads((OUT / f"{ed}-lines.json").read_text(encoding="utf-8"))
    al = json.loads((OUT / f"{ed}-align.json").read_text(encoding="utf-8"))
    summ = {s["play"]: s for s in al["summary"]}
    print(f"== {ed}\n| play | OCR verse lines | Perseus lines | last printed no. | Perseus tokens found | OCR tokens not in Perseus | dup lines | head leaks | LaTeX lines |")
    print("|---|---|---|---|---|---|---|---|---|")
    for play, recs in lines.items():
        v = [r for r in recs if r["kind"] == "verse"]
        keys = [" ".join(key_form(t) for t in tokens(r["text"])) for r in v]
        dup = 0
        for i, k in enumerate(keys):
            if len(k) > 12 and k in keys[max(0, i - 6):i]:
                dup += 1; print("   DUP", play, v[i]["src"], v[i]["text"][:50], file=sys.stderr)
        leaks = sum(1 for r in v if re.search(r"ΕΥΡΙΠΙΔΟΥ|ΣΟΦΟΚΛΕΟΥΣ|^\.?[ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ]{4,}\.?\s*\d*$", r["text"]))
        latex = sum(1 for r in v if r.get("latex"))
        pr = [r["printed"] for r in v if r.get("printed")]
        s = summ[play]
        print(f"| {play} | {len(v)} | {s['cmp_lines']} | {max(pr) if pr else ''} | {s['matched_tokens']/s['cmp_tokens']:.1%} | {s['ocr_tokens']-s['matched_tokens']} | {dup} | {leaks} | {latex} |")
