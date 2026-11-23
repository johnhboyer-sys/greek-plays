"""Q6: what the .docx carries beyond the .txt: run formatting counts, paragraph
alignment/indent, font sizes, tabs, page breaks; and a font-size profile of
Jebb verse vs apparatus vs commentary paragraphs."""
import collections, re, sys, zipfile
import xml.etree.ElementTree as ET
from common import ED
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
for f in sorted(ED.glob("*.docx")):
    z = zipfile.ZipFile(f)
    doc = ET.fromstring(z.read("word/document.xml"))
    c = collections.Counter(); sizes = collections.Counter(); jc = collections.Counter()
    prof = collections.defaultdict(collections.Counter)
    for p in doc.iter(W + "p"):
        c["paragraphs"] += 1
        ppr = p.find(W + "pPr")
        if ppr is not None:
            j = ppr.find(W + "jc")
            if j is not None: jc[j.get(W + "val")] += 1
            if ppr.find(W + "ind") is not None: c["para indent"] += 1
            st = ppr.find(W + "pStyle")
            if st is not None: c["style:" + st.get(W + "val")] += 1
        text = "".join(t.text or "" for t in p.iter(W + "t"))
        kind = ("apparatus" if re.match(r"^\d{1,4}\s", text) and len(text) > 60 else
                "long" if len(text) > 100 else "short-greek" if re.search(r"[ἀ-῿Ͱ-Ͽ]", text) and len(text) < 80 else "other")
        for r in p.iter(W + "r"):
            rpr = r.find(W + "rPr")
            if rpr is None: continue
            for tag in ("i", "b", "smallCaps", "vertAlign", "sz", "rFonts", "u", "caps"):
                el = rpr.find(W + tag)
                if el is not None:
                    c["run:" + tag] += 1
                    if tag == "sz":
                        sizes[el.get(W + "val")] += 1
                        prof[kind][el.get(W + "val")] += 1
        for br in p.iter(W + "br"):
            if br.get(W + "type") == "page": c["page breaks"] += 1
        c["tabs"] += sum(1 for _ in p.iter(W + "tab"))
    c["tables"] = sum(1 for _ in doc.iter(W + "tbl"))
    print("==", f.name)
    print("  ", dict(c.most_common(25)))
    print("   align:", dict(jc), " sizes:", dict(sizes.most_common(6)))
    if prof: print("   size by para kind:", {k: dict(v.most_common(3)) for k, v in prof.items()})
