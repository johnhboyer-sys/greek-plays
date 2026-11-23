"""For every comparator stretch the aligner could not find in the OCR verse
(>= MIN tokens), look for it in the raw OCR file: present (extraction miss),
or absent (lost from the OCR, or an editorial omission)."""
import json
import sys

from common import ED as EDDIR, OUT, key_form, tokens

ED = sys.argv[1]
MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 3
d = json.loads((OUT / f"{ED}-align.json").read_text(encoding="utf-8"))
files = {"paley": [EDDIR / f"Paley Euripides Text 0{v}.txt" for v in (1, 2, 3)],
         "jebb": [EDDIR / "Jebb Sophocles 01 Oedipus Tyrannus.txt",
                  EDDIR / "Jebb Sophocles 02 Oedipus Coloneus.txt"]}[ED]
raw_lines = []
for f in files:
    for i, s in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
        raw_lines.append((f.name[:24], i, s, " ".join(key_form(t) for t in tokens(s))))
for r in d["rows"]:
    for x in r["diffs"]:
        if x["cls"] == "MISSING" and int(x["kind"][7:]) >= MIN:
            ks = [key_form(t) for t in tokens(x["c"])]
            # try 3-word windows
            hits = set()
            for k in range(0, max(1, len(ks) - 2)):
                w = " ".join(ks[k:k + 3])
                if len(w) < 8:
                    continue
                for fn, i, s, kk in raw_lines:
                    if w in kk:
                        hits.add((fn, i))
            print(f"{r['play']:20s} near src {r['src']} cmp {r['pn']:6s} {x['kind']:10s} "
                  f"{'FOUND ' + str(sorted(hits)[:4]) if hits else 'ABSENT'} | {x['c'][:60]}")
