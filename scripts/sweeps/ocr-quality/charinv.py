"""Character inventory of the Genie OCR files: non-Greek, non-ASCII characters."""
import collections
import sys
from pathlib import Path

ED = Path("/Users/johnboyer/Developer/greek-plays/build/genie/editions")
for f in sorted(ED.glob("*.txt")):
    t = f.read_text(encoding="utf-8")
    c = collections.Counter(
        ch for ch in t
        if not ("Ͱ" <= ch <= "Ͽ" or "ἀ" <= ch <= "῿" or ch.isascii())
    )
    print(f.name)
    print("  ", [(k, f"U+{ord(k):04X}", v) for k, v in c.most_common(45)])
