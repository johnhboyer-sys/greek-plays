"""Token-align OCR verse to the Perseus Greek (primary comparator) and check
residual differences against the TLG text of the same line (secondary).

usage: align.py paley|jebb
Writes build/sweeps/genie-ocr/<ed>-diffs.tsv and <ed>-align.json.
"""
from __future__ import annotations

import collections
import difflib
import json
import sys
import unicodedata

from common import (OUT, PERSEUS, compare_form, corpus_vocab, key_form, levenshtein,
                    morpheus_valid, perseus_lines, tlg_lines, tokens)

ED = sys.argv[1]
if ED == "paley":
    from paley import PLAYS
    AUTHOR = "tlg0006"
    PLAYLIST = [(slug, pno) for slug, _v, _f, _l, pno in PLAYS]
else:
    AUTHOR = "tlg0011"
    PLAYLIST = [("oedipus-tyrannus", "004"), ("oedipus-coloneus", "007")]

VOCAB = corpus_vocab()
_valid_cache: dict[str, bool] = {}


def valid(tok: str) -> bool:
    cf = compare_form(tok)
    if cf in _valid_cache:
        return _valid_cache[cf]
    ok = cf in VOCAB or morpheus_valid(tok)
    _valid_cache[cf] = ok
    return ok


def sub2ad(form: str) -> str:
    s = unicodedata.normalize("NFD", form).replace("ͅ", "ι")
    return unicodedata.normalize("NFC", s)


def strip_diacritics_except(form: str, keep: set) -> str:
    return unicodedata.normalize("NFC", "".join(
        c for c in unicodedata.normalize("NFD", form) if c.isalpha() or c in keep or c == "’"))


def diff_kind(o: str, c: str) -> str:
    """Describe what differs between two compare forms."""
    if key_form(o) == key_form(c):
        no = unicodedata.normalize("NFD", o)
        nc = unicodedata.normalize("NFD", c)
        so = collections.Counter(ch for ch in no if not ch.isalpha())
        sc = collections.Counter(ch for ch in nc if not ch.isalpha())
        kinds = set()
        for ch in set(so) | set(sc):
            if so[ch] != sc[ch]:
                kinds.add({"̓": "breathing", "̔": "breathing", "́": "accent",
                           "͂": "accent", "ͅ": "iota-sub", "̈": "diaeresis",
                           "’": "apostrophe"}.get(ch, "mark"))
        if not kinds:
            kinds.add("mark-position")
        return "diacritic:" + "+".join(sorted(kinds))
    return "letters"


def classify(o_tok: str, c_tok: str, tlg_forms: set) -> tuple[str, str]:
    o, c = compare_form(o_tok), compare_form(c_tok)
    kind = diff_kind(o, c)
    if o in tlg_forms or sub2ad(o) in tlg_forms:
        return "EDIT", kind + "|=TLG"
    v = valid(o_tok)
    if kind.startswith("diacritic"):
        if kind == "diacritic:apostrophe":
            return "EDIT", kind
        return ("AMB" if v else "OCR"), kind
    lev = levenshtein(key_form(o), key_form(c))
    if v:
        return "EDIT", kind + f"|lev{lev}"
    if lev <= 2:
        return "OCR", kind + f"|lev{lev}"
    return "AMB", kind + f"|lev{lev}"


def load_ocr(ed: str) -> dict:
    return json.loads((OUT / f"{ed}-lines.json").read_text(encoding="utf-8"))


def main():
    ocr = load_ocr(ED)
    rows = []
    summary = []
    for slug, pno in PLAYLIST:
        recs = [r for r in ocr[slug] if r["kind"] == "verse"]
        plines = perseus_lines(PERSEUS / f"{AUTHOR}.tlg{pno}.perseus-grc2.xml")
        try:
            tl = tlg_lines(slug)
        except FileNotFoundError:
            tl = []
        tlg_by_ref = collections.defaultdict(set)
        for ln in tl:
            base = "".join(ch for ch in ln["n"] if ch.isdigit())
            for t in tokens(ln["text"]):
                tlg_by_ref[base].add(compare_form(t))
        # token streams
        otoks, oline = [], []
        for li, r in enumerate(recs):
            for t in tokens(r["text"]):
                otoks.append(t)
                oline.append(li)
        ptoks, pline = [], []
        for li, ln in enumerate(plines):
            for t in tokens(ln["text"]):
                ptoks.append(t)
                pline.append(li)
        ok = [key_form(t) for t in otoks]
        pk = [key_form(t) for t in ptoks]
        sm = difflib.SequenceMatcher(None, ok, pk, autojunk=False)
        line_diffs = collections.defaultdict(list)  # ocr line idx -> list
        line_pmap = collections.defaultdict(collections.Counter)
        ins_del = collections.Counter()

        def tlg_forms_for(pi: int) -> set:
            n = plines[pline[pi]]["n"]
            base = "".join(ch for ch in n if ch.isdigit())
            if not base:
                return set()
            b = int(base)
            s = set()
            for k in (b - 1, b, b + 1):
                s |= tlg_by_ref.get(str(k), set())
            return s

        def record(oi, pi, cls, kind):
            line_diffs[oline[oi]].append({"o": otoks[oi], "c": ptoks[pi] if pi is not None else "",
                                          "cls": cls, "kind": kind})

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            for a, b in zip(range(i1, i2), range(j1, j2)):
                line_pmap[oline[a]][pline[b]] += 1
            if tag == "equal":
                for a, b in zip(range(i1, i2), range(j1, j2)):
                    o, c = compare_form(otoks[a]), compare_form(ptoks[b])
                    if o != c:
                        cls, kind = classify(otoks[a], ptoks[b], tlg_forms_for(b))
                        record(a, b, cls, kind)
            elif tag == "replace":
                la, lb = i2 - i1, j2 - j1
                joined_o = "".join(ok[i1:i2])
                joined_p = "".join(pk[j1:j2])
                if joined_o == joined_p and la != lb:
                    # word division differs
                    ovalid = all(valid(otoks[a]) for a in range(i1, i2))
                    cls = "EDIT" if ovalid else "OCR"
                    line_diffs[oline[i1]].append({
                        "o": " ".join(otoks[i1:i2]), "c": " ".join(ptoks[j1:j2]),
                        "cls": cls, "kind": "division"})
                elif la == lb:
                    for a, b in zip(range(i1, i2), range(j1, j2)):
                        if compare_form(otoks[a]) == compare_form(ptoks[b]):
                            continue
                        cls, kind = classify(otoks[a], ptoks[b], tlg_forms_for(b))
                        record(a, b, cls, kind)
                else:
                    tf = set()
                    for b in range(j1, j2):
                        tf |= tlg_forms_for(b)
                    for a in range(i1, i2):
                        o = compare_form(otoks[a])
                        if o in tf or sub2ad(o) in tf:
                            cls, kind = "EDIT", "block|=TLG"
                        elif valid(otoks[a]):
                            cls, kind = "EDIT", "block"
                        else:
                            cls, kind = "AMB", "block-invalid"
                        line_diffs[oline[a]].append({"o": otoks[a], "c": " ".join(ptoks[j1:j2])[:60],
                                                     "cls": cls, "kind": kind})
            elif tag == "delete":
                ins_del["ocr_extra"] += i2 - i1
                for a in range(i1, i2):
                    o = compare_form(otoks[a])
                    cls = "EDIT" if valid(otoks[a]) else "AMB"
                    line_diffs[oline[a]].append({"o": otoks[a], "c": "", "cls": cls, "kind": "extra"})
            elif tag == "insert":
                ins_del["ocr_missing"] += j2 - j1
                # attach to the nearest OCR line
                a = min(i1, len(oline) - 1)
                line_diffs[oline[a]].append({"o": "", "c": " ".join(ptoks[j1:j2])[:80],
                                             "cls": "MISSING", "kind": f"missing{j2-j1}"})
        # per-line output
        nchars = 0
        for li, r in enumerate(recs):
            chars = sum(1 for ch in unicodedata.normalize("NFC", r["text"]) if ch.isalpha())
            nchars += chars
            pm = line_pmap.get(li)
            pn = plines[pm.most_common(1)[0][0]]["n"] if pm else ""
            ptxt = plines[pm.most_common(1)[0][0]]["text"] if pm else ""
            ds = line_diffs.get(li, [])
            rows.append({"play": slug, "src": r["src"], "page": r.get("page"), "pn": pn,
                         "ocr": r["text"], "cmp": ptxt, "diffs": ds, "chars": chars})
        summary.append({"play": slug, "ocr_lines": len(recs), "cmp_lines": len(plines),
                        "ocr_tokens": len(otoks), "cmp_tokens": len(ptoks),
                        "matched_tokens": sum(bl.size for bl in sm.get_matching_blocks()),
                        "ocr_chars": nchars, **ins_del})
        print(slug, summary[-1], flush=True)
    (OUT / f"{ED}-align.json").write_text(json.dumps({"rows": rows, "summary": summary},
                                                     ensure_ascii=False), encoding="utf-8")
    with (OUT / f"{ED}-diffs.tsv").open("w", encoding="utf-8") as fh:
        fh.write("play\tsrc\tpage\tcmp_n\tocr_line\tcmp_line\tdiffs\n")
        for r in rows:
            if r["diffs"]:
                d = " ; ".join(f"{x['o']}→{x['c']} [{x['cls']} {x['kind']}]" for x in r["diffs"])
                fh.write(f"{r['play']}\t{r['src']}\t{r['page']}\t{r['pn']}\t{r['ocr']}\t{r['cmp']}\t{d}\n")


if __name__ == "__main__":
    main()
