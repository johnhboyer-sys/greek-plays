"""Extract Paley's verse lines, per play, from the Genie .txt files.

Each line record: play, vol, src (1-based line in the .txt), page (printed page
number from the running head, if read), text (verse only), printed (margin
number or None), speakers (abbreviations found on the line), indent (the
line was indented with &nbsp; / em spaces), strophe (margin strophe mark).
"""
from __future__ import annotations

import json
import re

from common import ED, OUT, LAT2GRK, greek_share

PLAYS = [
    # slug, vol, first line (title heading), last line, perseus no.
    ("rhesus", 1, 190, 1411, "019"),
    ("medea", 1, 1454, 3112, "003"),
    ("hippolytus", 1, 3145, 4859, "005"),
    ("alcestis", 1, 4885, 6292, "002"),
    ("heraclidae", 1, 6313, 7580, "004"),
    ("suppliants-eur", 1, 7604, 9092, "008"),
    ("trojan-women", 1, 9113, 10690, "011"),
    ("ion", 2, 295, 2248, "010"),
    ("helen", 2, 2272, 4327, "014"),
    ("andromache", 2, 4328, 5837, "006"),
    ("electra-eur", 2, 5860, 7446, "012"),
    ("bacchae", 2, 7479, 9133, "017"),
    ("hecuba", 2, 9134, 10630, "007"),
    ("heracles", 3, 256, 1939, "009"),
    ("phoenician-women", 3, 1993, 4116, "015"),
    ("orestes", 3, 4149, 6192, "016"),
    ("iphigenia-in-tauris", 3, 6217, 7989, "013"),
    ("iphigenia-at-aulis", 3, 7990, 10000, "018"),
    ("cyclops", 3, 10024, 10880, "001"),
]

SPACE_ENT = re.compile(r"(&nbsp;|&emsp;|&ensp;| | | )+")
SPAN_NUM = re.compile(r"<span[^>]*>\s*(\d{1,4})\s*</span>")
BRACK_NUM = re.compile(r"\[(\d{1,4})\]\s*$")
TRAIL_NUM = re.compile(r"\s(\d{1,4})\s*$")
STROPHE = re.compile(
    r"(?:^|\s)\[?\s*((?:στρ|ἀντ|ἀντιστρ|ἐπῳδ|ἐπωδ|μεσῳδ|ἐφύμν)(?:οφή|ιστροφή|ός)?\.?(?:\s*[α-ω][΄'ʹ’`]?\.?)?)\s*\]?\s*$")
SPK = r"(?:[ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩABEZHIKMNOPTYX]{1,5}\.?\s?[αβγ΄']?\.)"
LEAD_SPK = re.compile(r"^\s*(" + SPK + r")\s*")
MID_SPK = re.compile(r"(?<=[\s·;,.’᾽])(" + SPK + r")\s")
ALLCAPS = re.compile(r"^[ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩΆΈΉΊΌΎΏ\s.,ʹ΄']+$")
HEAD = re.compile(
    r"^(?:#+\s*)?(?:(\d{1,4}|[Il]{1,3}\d*)\s+)?(ΕΥΡΙΠΙΔΟΥ|[ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ][ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ\s]*\.?)?\s*(\d{1,4}|[Il]{1,3}\d*)?$")


def clean_markup(s: str) -> tuple[str, bool]:
    indent = bool(re.match(r"^\s*(&nbsp;|&emsp;| | )", s)) or s.startswith("    ")
    s = SPACE_ENT.sub(" ", s)
    s = s.replace("**", "").replace("__", "")
    s = re.sub(r"^\s*>\s?", "", s)
    s = re.sub(r"(?<!\w)_(?=\S)|(?<=\S)_(?!\w)", "", s)
    s = re.sub(r"(?<![\w*])\*(?=\S)|(?<=\S)\*(?![\w*])", "", s)
    return s.rstrip(), indent


def parse_head(lines: list[str]) -> tuple[int | None, int]:
    """Return (printed page, number of head lines consumed)."""
    page = None
    used = 0
    for s in lines[:2]:
        c = SPACE_ENT.sub(" ", s).strip().strip("#").strip().translate(LAT2GRK)
        c = re.sub(r"\$\s*(\d+)\s*\$", r"\1", c)
        if not c:
            used += 1
            continue
        m = HEAD.match(c)
        if m and (m.group(1) or m.group(2) or m.group(3)) and len(c) < 60:
            for g in (m.group(1), m.group(3)):
                if g and g.isdigit():
                    page = int(g)
            used += 1
            if m.group(2) and (m.group(1) or m.group(3)):
                break
        else:
            break
    return page, used


def extract(vol: int, first: int, last: int, slug: str) -> list[dict]:
    path = ED / f"Paley Euripides Text 0{vol}.txt"
    all_lines = path.read_text(encoding="utf-8").split("\n")
    block = all_lines[first - 1:last]
    # split into pages on '---'
    pages: list[list[tuple[int, str]]] = [[]]
    for i, s in enumerate(block, start=first):
        if s.strip() in ("---", "***", "* * *"):
            pages.append([])
        else:
            pages[-1].append((i, s))
    out = []
    stopped = False
    seen_verse = False
    for pg in pages:
        nonempty = [(i, s) for i, s in pg if s.strip()]
        if not nonempty:
            continue
        page, used = parse_head([s for _, s in nonempty])
        for i, s in nonempty[used:]:
            raw = s
            latex = "$\\" in s or bool(re.search(r"\$[^$]*\\[a-z]", s))
            s = re.sub(r"\$\s*(\d{1,4})\s*\$", r" \1", s)
            s = re.sub(r"\$~+\$", " ", s)
            s = re.sub(r"\$\\([a-z]+)\^?\{?\\?(prime)?\}?\$\.", r"\1.", s)
            table = False
            if s.strip().startswith("|"):
                cells = [c.strip() for c in s.strip().strip("|").split("|")]
                if all(re.fullmatch(r":?-*:?", c) for c in cells):
                    continue
                if not any(cells):
                    continue
                table = True
                num = [c for c in cells if re.fullmatch(r"\d{1,4}", c)]
                rest = [c for c in cells if c and not re.fullmatch(r"\d{1,4}", c)]
                s = " ".join(rest) + (" " + num[0] if num else "")
            txt, indent = clean_markup(s)
            core = txt.strip()
            if re.fullmatch(r"(\\\s*)+", core) or re.fullmatch(r"[IVX]+\.?\s*—?\s*\d*", core) or re.fullmatch(r"[.\s]+", core):
                out.append({"kind": "junk", "src": i, "page": page, "text": core})
                continue
            if re.fullmatch(r"\d{1,4}", core):
                n = int(core)
                prev = next((r for r in reversed(out) if r["kind"] in ("verse", "num")), None)
                if prev and prev["kind"] == "verse" and prev.get("printed") is None and prev["src"] >= i - 2:
                    prev["printed"] = n
                    prev["num_mode"] = "own-line-after"
                else:
                    out.append({"kind": "num", "src": i, "page": page, "text": core, "n": n})
                continue
            if re.search(r"ΥΠΟΘΕΣΙΣ|ΠΡΟΣΩΠΑ", core) and seen_verse:
                stopped = True
                break
            if core.startswith("#"):
                name = core.strip("# ").strip()
                if ALLCAPS.match(name) and "ΕΥΡΙΠΙΔΟΥ" not in name:
                    out.append({"kind": "speaker", "src": i, "page": page, "text": name})
                continue
            if ALLCAPS.match(core.translate(LAT2GRK)) and len(core) < 40:
                out.append({"kind": "speaker", "src": i, "page": page, "text": core})
                continue
            printed = None
            num_mode = None
            m = SPAN_NUM.search(txt)
            if m:
                printed = int(m.group(1))
                num_mode = "span"
                txt = SPAN_NUM.sub(" ", txt).rstrip()
            txt = re.sub(r"<[^>]+>", " ", txt).rstrip()
            strophe = None
            for _ in range(2):
                m = STROPHE.search(txt)
                if m and len(txt) > len(m.group(0)) + 2:
                    strophe = m.group(1)
                    txt = txt[:m.start()].rstrip()
                m = BRACK_NUM.search(txt) or TRAIL_NUM.search(txt)
                if m and printed is None:
                    printed = int(m.group(1))
                    num_mode = "table" if table else ("bracket" if m.re is BRACK_NUM else "trailing")
                    txt = txt[:m.start()].rstrip()
            if not txt.strip():
                continue
            if latex:
                txt = re.sub(r"\$[^$]*\$", " ", txt)
            if greek_share(txt) < 0.6 and not latex:
                out.append({"kind": "other", "src": i, "page": page, "text": txt.strip()})
                continue
            if len(txt) > 160:
                out.append({"kind": "prose", "src": i, "page": page, "text": txt.strip()})
                continue
            speakers = []
            m = LEAD_SPK.match(txt)
            if m:
                speakers.append(m.group(1))
                txt = txt[m.end():]
            for m in MID_SPK.finditer(txt):
                speakers.append(m.group(1))
            verse = MID_SPK.sub(" | ", txt).strip()
            seen_verse = True
            out.append({"kind": "verse", "src": i, "page": page, "text": verse.strip(),
                        "printed": printed, "speakers": speakers, "indent": indent,
                        "strophe": strophe, "raw": raw, "latex": latex, "table": table,
                        "num_mode": num_mode})
        if stopped:
            break
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for slug, vol, first, last, pno in PLAYS:
        recs = extract(vol, first, last, slug)
        res[slug] = recs
        v = [r for r in recs if r["kind"] == "verse"]
        print(f"{slug:22s} vol{vol} verse={len(v):5d} printed={sum(1 for r in v if r['printed']):4d} "
              f"other={sum(1 for r in recs if r['kind']=='other'):3d} prose={sum(1 for r in recs if r['kind']=='prose'):3d}")
    (OUT / "paley-lines.json").write_text(json.dumps(res, ensure_ascii=False, indent=0), encoding="utf-8")


if __name__ == "__main__":
    main()
