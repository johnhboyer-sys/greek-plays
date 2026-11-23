"""Extract Jebb's Greek verse from pages shared with apparatus, commentary and
his English (Q5). Two rules:

Rule A (page head): a page (between '---' lines) whose running head names
  ΣΟΦΟΚΛΕΟΥΣ is a Greek-text page. Its verse block runs from after the head
  to the first apparatus/commentary line (starts '**<digit>' or '<digit> ',
  or is longer than 90 characters). Inside the block keep lines whose
  letters are >= 80% Greek; '###' headings and all-caps names are speakers.
Rule B (no head): anywhere in the play, a line is verse when, after its
  trailing number is removed, it is <= 75 characters, >= 90% Greek letters,
  does not start with '**' or a digit, and a neighbouring line also passes.

Writes jebb-lines.json (rule A) and jebb-lines-B.json.
"""
from __future__ import annotations

import json
import re

from common import ED, OUT, LAT2GRK, greek_share
from paley import clean_markup, SPAN_NUM, TRAIL_NUM, BRACK_NUM, STROPHE, LEAD_SPK, MID_SPK, ALLCAPS

PLAYS = [("oedipus-tyrannus", "Jebb Sophocles 01 Oedipus Tyrannus.txt", 2405, 8415),
         ("oedipus-coloneus", "Jebb Sophocles 02 Oedipus Coloneus.txt", 2000, 10055)]

APP = re.compile(r"^\s*(\*\*\s*\d|\d{1,4}\s*(f\.|ff\.)?\s+[A-Za-z(\[])")
COLON = re.compile(r"^\s*(\d{1,2})\s+(?=[^\sA-Za-z0-9])")
LEADSTR = re.compile(r"^\s*\*?((?:στρ|ἀντ|ἐπῳδ|ἐπωδ|μεσῳδ)\.?(?:\s*[α-ω][΄'ʹ’`]?\.?)?)\*?\s+")


def verse_rec(i, page, s, raw):
    s = re.sub(r"\$\s*(\d{1,4})\s*\$", r" \1", s)
    colon = None
    m = COLON.match(s)
    if m:
        colon = int(m.group(1)); s = s[m.end():]
    lead = None
    m = LEADSTR.match(s)
    if m:
        lead = m.group(1); s = s[m.end():]
    txt, indent = clean_markup(s)
    txt = re.sub(r"<[^>]+>", " ", txt).rstrip()
    printed = None
    mode = None
    strophe = None
    for _ in range(2):
        m = STROPHE.search(txt)
        if m and len(txt) > len(m.group(0)) + 2:
            strophe = m.group(1)
            txt = txt[:m.start()].rstrip()
        m = BRACK_NUM.search(txt) or TRAIL_NUM.search(txt)
        if m and printed is None:
            printed = int(m.group(1))
            mode = "trailing"
            txt = txt[:m.start()].rstrip()
    speakers = []
    m = LEAD_SPK.match(txt)
    if m:
        speakers.append(m.group(1))
        txt = txt[m.end():]
        m2 = re.match(r"\s*(\d{1,2})\s+", txt)
        if m2:
            colon = int(m2.group(1)); txt = txt[m2.end():]
    for m in MID_SPK.finditer(txt):
        speakers.append(m.group(1))
    verse = MID_SPK.sub(" | ", txt).strip()
    return {"kind": "verse", "src": i, "page": page, "text": verse, "printed": printed,
            "num_mode": mode, "speakers": speakers, "indent": indent, "strophe": strophe,
            "raw": raw, "colon": colon, "lead_strophe": lead}


def pages_of(fname, first, last):
    lines = (ED / fname).read_text(encoding="utf-8").split("\n")[first - 1:last]
    pages = [[]]
    for i, s in enumerate(lines, start=first):
        if s.strip() in ("---", "***"):
            pages.append([])
        else:
            pages[-1].append((i, s))
    return pages


def head_of(nonempty):
    """(is_greek_page, printed page, lines used)."""
    used, page, greek = 0, None, False
    for _, s in nonempty[:3]:
        c = s.strip().strip("#").strip()
        if not re.search(r"SOPHO", c):
            c = c.translate(LAT2GRK)
        c = re.sub(r"\*+", "", c).strip()
        if re.fullmatch(r"\d{1,4}", c):
            page = int(c); used += 1; continue
        m = re.fullmatch(r"(\d{1,4}|[Il]{1,3})?\s*(ΣΟΦΟΚΛΕΟΥΣ|SOPHOKLES|SOPHOCLEOUS|SOPHOCLES|ΟΙΔΙΠΟΥΣ[\sΑ-Ω]*?)\s*(\d{1,4}|[Il]{1,3})?", c)
        if m:
            greek = greek or not m.group(2).startswith("ΟΙΔΙΠΟΥΣ")
            for g in (m.group(1), m.group(3)):
                if g and g.isdigit():
                    page = int(g)
            used += 1
            continue
        break
    return greek, page, used


FALLBACK = []


def rule_a(fname, first, last):
    out = []
    for pg in pages_of(fname, first, last):
        ne = [(i, s) for i, s in pg if s.strip()]
        if not ne:
            continue
        greek, page, used = head_of(ne)
        if not greek:
            body = [clean_markup(s)[0].strip() for _, s in ne[used:used + 2]]
            def vl(c):
                c = re.sub(r"\s\d{1,4}\s*$", "", COLON.sub("", c))
                return 0 < len(c) <= 75 and greek_share(c) >= 0.9 and not APP.match(c)
            if len(body) == 2 and all(vl(c) for c in body):
                greek = True
                FALLBACK.append((fname, ne[0][0], ne[0][1][:40]))
            else:
                continue
        for i, s in ne[used:]:
            c = s.strip()
            plain = clean_markup(c)[0].strip()
            if APP.match(c) or len(plain) > 90:
                break
            if c.startswith("#"):
                name = c.strip("# ").strip().strip("*")
                out.append({"kind": "speaker", "src": i, "page": page, "text": name})
                continue
            core = clean_markup(c)[0].strip()
            if ALLCAPS.match(core.translate(LAT2GRK)) and len(core) < 40:
                out.append({"kind": "speaker", "src": i, "page": page, "text": core})
                continue
            if re.fullmatch(r"\d{1,4}", core):
                out.append({"kind": "num", "src": i, "page": page, "text": core, "n": int(core)})
                continue
            if greek_share(core) < 0.8:
                out.append({"kind": "other", "src": i, "page": page, "text": core})
                continue
            out.append(verse_rec(i, page, s, s))
    return out


def rule_b(fname, first, last):
    lines = (ED / fname).read_text(encoding="utf-8").split("\n")
    cand = {}
    for i in range(first, last + 1):
        s = lines[i - 1]
        c = s.strip()
        if not c or c.startswith("**") or c[:1].isdigit() or c.startswith(("#", "|", "---")):
            continue
        core = re.sub(r"\s\d{1,4}\s*$", "", clean_markup(c)[0]).strip()
        if len(core) <= 75 and greek_share(core) >= 0.9 and not (ALLCAPS.match(core) and len(core) < 40):
            cand[i] = s
    out = []
    for i, s in cand.items():
        if (i - 1) in cand or (i + 1) in cand:
            out.append(verse_rec(i, None, s, s))
    return out


def main():
    a, b = {}, {}
    for slug, fname, first, last in PLAYS:
        a[slug] = rule_a(fname, first, last)
        b[slug] = rule_b(fname, first, last)
        print(slug, "A verse", sum(r["kind"] == "verse" for r in a[slug]),
              "other", sum(r["kind"] == "other" for r in a[slug]),
              "| B verse", len(b[slug]))
    print("pages taken by the body test (head not read):", len(FALLBACK))
    for f in FALLBACK[:40]:
        print("   ", f)
    (OUT / "jebb-lines.json").write_text(json.dumps(a, ensure_ascii=False), encoding="utf-8")
    (OUT / "jebbB-lines.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
