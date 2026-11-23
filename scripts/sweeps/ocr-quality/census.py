"""Q4/Q6 census over the extracted verse: mixed-script words, Latin speaker
labels, stray marks, apostrophe variants, brackets, lacunae, antilabe."""
import collections, json, re, sys
from common import OUT
for ed in ("paley", "jebb"):
    d = json.loads((OUT / f"{ed}-lines.json").read_text(encoding="utf-8"))
    c = collections.Counter(); ex = collections.defaultdict(list)
    for play, recs in d.items():
        for r in recs:
            if r["kind"] != "verse":
                continue
            raw, t = r["raw"], r["text"]
            c["lines"] += 1
            for w in re.findall(r"\S+", t):
                if re.search(r"[Ͱ-Ͽἀ-῿]", w) and re.search(r"[A-Za-z]", w):
                    c["mixed-script word"] += 1; ex["mixed-script word"].append(w)
            for s in r.get("speakers", []):
                c["speaker labels"] += 1
                if re.search(r"[A-Za-z]", s):
                    c["speaker label with Latin letters"] += 1; ex["speaker label with Latin letters"].append(s)
            if len(r.get("speakers", [])) > 1 or " | " in t:
                c["line with mid-line speaker change (antilabe on one line)"] += 1
            if r.get("indent"):
                c["indented line (&nbsp;)"] += 1
            for ch, name in (("\\", "backslash"), ("˙", "U+02D9 dot for ano teleia"), ("$", "LaTeX $"),
                             ("†", "crux †"), ("[", "square bracket"), ("⟨", "angle bracket ⟨"), ("<", "ASCII <"),
                             ("*", "asterisk"), ("᾿", "psili U+1FBF as apostrophe"), ("᾽", "koronis U+1FBD as apostrophe"),
                             ("’", "U+2019 apostrophe"), ("'", "ASCII apostrophe"), (" ;", "space before ;"), ("|", "table pipe")):
                if ch in raw:
                    c[name] += 1
                    if len(ex[name]) < 3: ex[name].append(raw.strip()[:70])
            if r.get("strophe") or r.get("lead_strophe"):
                c["strophe mark"] += 1
            if r.get("latex"):
                c["LaTeX line"] += 1
    print("==", ed)
    for k, v in c.most_common():
        e = ex.get(k, [])
        print(f"  {v:6d}  {k}   {collections.Counter(e).most_common(6) if k.startswith(('mixed','speaker label')) else e[:2]}")
