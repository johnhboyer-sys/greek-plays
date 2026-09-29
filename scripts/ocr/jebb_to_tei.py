#!/usr/bin/env python3
"""Jebb's Sophocles (Genie OCR .txt) -> drama TEI (edition-picker plan §3.1).

    pipeline/.venv/bin/python scripts/ocr/jebb_to_tei.py oedipus-tyrannus [--qa]
    pipeline/.venv/bin/python scripts/ocr/jebb_to_tei.py all --qa

Writes sources/ocr/jebb/<play>.xml, refreshes sources/ocr/jebb/SHA256SUMS,
and dumps its line records to build/sweeps/jebb-ocr/<play>-lines.json. Run
it with the pipeline's venv: it reads the TLG text through the pipeline.
Scan page numbers come from each archive.org item's page_numbers.json, kept
in build/sweeps/jebb-ocr/.

1. Separation (build/sweeps/genie-ocr-quality-2026-09-29.md §5, rule A).
   A page (between '---' or '***' lines) is a Greek-text page when its
   running head reads ΣΟΦΟΚΛΕΟΥΣ (or the OCR's Latin SOPHOKLES), or, with
   no head read, when four of its first six lines are short Greek verse.
   The verse block runs from after the head to the first apparatus line
   (**<digit>, **<Latin>, '<digit> <Latin word>', a Latin word, or a lemma
   bracket), a line longer than 90 characters once markup is removed, or a
   line of mostly Latin letters. One OCR slip can be such a row, so the scan
   goes on: a later row within reach of a reference line (Storr, TLG)
   resumes the block. The report lists every stop (page_rows).
2. Inside the block: '#' headings and all-caps names are speakers; a
   leading ΟΙ.-style abbreviation opens a speech, one inside a line an
   antilabe share; a leading strophe mark opens a strophe div; a leading
   small number is Jebb's colon number (rend="colon-N"); a trailing number
   is the printed margin number (rend="margin-N"), and numbers printed on
   rows of their own are checked against their page (rend="margin-apart-N").
   A turn-over (the end of a long line on a row of its own, '[βροτῶν')
   joins the neighbour whose text, with it at the end, lies within one
   reference line (rend="turn"). Markdown tables, LaTeX letters, elision
   marks and the OCR's dot above (for the ano teleia) are normalised; Jebb's
   asterisk, his <additions> and [deletions], cruces, and lacunae are kept.
3. Numbering (number_lines): each line takes the number of the reference
   line it starts with, from Storr's Perseus Greek or the TLG, or the number
   of a checkpoint on it: Jebb's printed margin numbers and his commentary
   notes ('**N lemma**'). The choice is the cheapest path over the lines;
   see number_lines. NUMBER_FIXES holds hand fixes, each with its reason.
   check_margins then reports every printed number the numbering does not
   meet.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
GENIE = ROOT / "build/genie/editions"
PERSEUS = ROOT / "sources/perseus"
OUT = ROOT / "sources/ocr/jebb"

# slug: (OCR file, TLG work, archive.org id, first and last .txt line of the
# play text, edition statement read from the OCR's title pages)
PLAYS = {
    "oedipus-tyrannus": ("Jebb Sophocles 01 Oedipus Tyrannus.txt", "004", "playsfragmentspa0000unse_i8p4", 2400, 8415),
    "oedipus-coloneus": ("Jebb Sophocles 02 Oedipus Coloneus.txt", "007", "sophoclesplaysfr0000unse_k8j6", 2002, 10055),
    "antigone": ("Jebb Sophocles 03 Antigone.txt", "002", "sophoclesplaysfr03soph", 1791, 7923),
    "philoctetes": ("Jebb Sophocles 04 Philoctetes.txt", "006", "sophoclesplaysfr04soph", 1623, 7953),
    "trachiniae": ("Jebb Sophocles 05 Trachiniae.txt", "001", "trachiniaeofsoph0000unse", 1516, 7232),
    "electra-soph": ("Jebb Sophocles 06 Electra.txt", "005", "sophoclesplaysfr06soph", 2273, 8891),
    "ajax": ("Jebb Sophocles 07 Ajax.txt", "003", "ajaxsoph00soph", 1797, 8094),
}

# Per-play numbering exceptions: {ocr .txt line: n}, each with its reason.
NUMBER_FIXES: dict[str, dict[int, tuple[str, str]]] = {
    "oedipus-tyrannus": {
        # Scan p. 174: colon 12 prints 1345 (it holds 1342 and the start of
        # 1345); colon 13 is then 1346, and the Chorus's two trimeters 1347
        # and 1348 (Jebb's note '1348 ἂν'; the TLG count agrees).
        7616: ("1346", "scan p. 174: the colon after printed 1345"),
        7617: ("1347", "scan p. 174; TLG 1347"),
        7618: ("1348", "Jebb's note '1348 ἂν'; TLG 1348"),
    },
}
# Printed margin numbers that disagree with the numbering for a stated
# reason: {ocr .txt line: reason}. Every other disagreement fails. (None
# needed for OT.)
MARGIN_NOTES: dict[str, dict[int, str]] = {}

GREEK_RE = re.compile(r"[Ͱ-Ͽἀ-῿]")
LAT2GRK = str.maketrans({"A": "Α", "B": "Β", "E": "Ε", "Z": "Ζ", "H": "Η", "I": "Ι",
                         "K": "Κ", "M": "Μ", "N": "Ν", "O": "Ο", "P": "Ρ", "T": "Τ",
                         "Y": "Υ", "X": "Χ"})
CAPS = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
SPACE_ENT = re.compile(r"(&nbsp;|&emsp;|&ensp;| | | | )+")
APP = re.compile(r"^\s*(\*\*\s*\d|\*\*\s*[A-Za-z]|\d{1,4}\s*(f\.|ff\.)?\s+[A-Za-z(\[])")
TRAIL_NUM = re.compile(r"\s+(?:\*\*)?\$?\[?\s*(\d{1,4})\s*\]?\$?(?:\*\*)?\s*$")
SPK_ABBR = r"[%s]{2,3}\." % CAPS
LEAD_SPK = re.compile(r"^(%s)\s+" % SPK_ABBR)
MID_SPK = re.compile(r"(?<=[\s])(%s)\s+(?=\S)" % SPK_ABBR)
STROPHE = re.compile(r"^\*?((στρ|ἀντ|ἐπῳδ|ἐπωδ|μεσῳδ)(?:οφή|ιστροφή|ός)?\.?)\s*(?:([α-θ])\s*[΄'ʹ’`´]?\s*\.?)?\*?(?:\s+|$)")
COLON = re.compile(r"^(\d{1,2})\s+(?=[^\s\d])")
NAME_LINE = re.compile(r"^[%s][%s\s]{2,}\.?$" % (CAPS, CAPS))
NUMERAL = {c: i for i, c in enumerate("αβγδεζηθ", 1)}
SUBTYPE = {"στρ": "strophe", "ἀντ": "antistrophe", "ἐπῳδ": "epode", "ἐπωδ": "epode", "μεσῳδ": "mesode"}
APOS = "'’᾽ʼ᾿`"
COMB = {"̀", "́", "͂", "̓", "̔", "ͅ", "̈", "̄", "̆"}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def greek_share(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    return sum(1 for c in letters if GREEK_RE.match(c)) / len(letters) if letters else 0.0


def key(s: str) -> str:
    """Letters only, no diacritics, lower case, one sigma: the alignment key."""
    d = unicodedata.normalize("NFD", s)
    return "".join(c.lower() for c in d if c.isalpha() and GREEK_RE.match(c)).replace("ς", "σ")


def plain(s: str) -> str:
    """The line with OCR markup removed (for length and share tests)."""
    s = SPACE_ENT.sub(" ", s)
    s = re.sub(r"</?[A-Za-z][^>]*>", "", s)
    return s.replace("**", "").replace("\\*", "*").strip()


# ------------------------------------------------------------------ pages
def pages_of(lines: list[str], first: int, last: int):
    page: list[tuple[int, str]] = []
    for i in range(first, last + 1):
        s = lines[i - 1]
        if s.strip() in ("---", "***"):
            if page:
                yield page
            page = []
        else:
            page.append((i, s))
    if page:
        yield page


PAGE_NO = r"[\dIlOΙΟ]{1,4}"


def _page_no(g: str) -> int:
    """A printed page number, with the OCR's I/l/O lookalikes read as digits."""
    return int(g.translate(str.maketrans("IlΙOΟ", "11100")))


def read_head(ne: list[tuple[int, str]]):
    """(is a Greek-text page, printed page number, head lines used)."""
    used, number, greek = 0, None, False
    for _, s in ne[:3]:
        c = SPACE_ENT.sub(" ", s).strip().strip("#").strip()
        c = re.sub(r"\$\s*(\d+)\s*\$", r"\1", c).replace("*", "").replace("\\", "").strip()
        if re.fullmatch(PAGE_NO, c) and re.search(r"\d", c):
            number, used = _page_no(c), used + 1
            continue
        m = re.fullmatch(r"(%s)?\s*(ΣΟΦΟΚΛΕΟΥΣ|ΣΟΦΟΚΛΕΟΥΣ\.|SOPH\w*|ΣOΦOKΛEOYΣ|\S*ΟΦΟΚΛ\S*)\s*(%s)?" % (PAGE_NO, PAGE_NO),
                         c.translate(LAT2GRK) if "SOPH" not in c else c)
        if m:
            greek = True
            for g in (m.group(1), m.group(3)):
                if g and re.search(r"\d|^[IlΙ]+$", g):
                    number = _page_no(g)
            used += 1
            continue
        break
    return greek, number, used


GREEK_TEX = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε",
             "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ",
             "nu": "ν", "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ", "varsigma": "ς", "tau": "τ",
             "upsilon": "υ", "phi": "φ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω"}


def latex_greek(s: str) -> str | None:
    """Unwrap the OCR's LaTeX: '$715$' is a number, '$\\gamma'$' plain Greek
    letters. A row whose LaTeX holds anything else (a metrical scheme,
    '$– \\dot > | \\smile ...$') returns None; an accented letter set as
    LaTeX is left for the checks to flag."""
    if "$" not in s:
        return s
    bad = False

    def repl(m):
        nonlocal bad
        body = m.group(1).strip()
        if re.fullmatch(r"\d{1,4}", body):
            return " " + body
        out = re.sub(r"\\([a-z]+)\s*", lambda t: GREEK_TEX.get(t.group(1), "\x00"), body)
        if "\x00" in out or "\\" in out or re.search(r"[A-Za-z|<>]", out):
            bad = True
        return out.replace(" ", "")
    def bad_span(body: str) -> bool:
        body = body.strip()
        if re.fullmatch(r"\d{1,4}", body):
            return False
        t = re.sub(r"\\([a-z]+)\s*", lambda x: GREEK_TEX.get(x.group(1), "\x00"), body)
        return "\x00" in t or "\\" in t or bool(re.search(r"[A-Za-z|<>]", t))

    out = re.sub(r"\$([^$]*)\$", repl, s)
    if bad:
        rest = re.sub(r"\$[^$]*\$", "", s)
        if re.search(r"[\u0370-\u03ff\u1f00-\u1fff]{3}", rest.translate(LAT2GRK).replace("ΟΙ.", "")) is None:
            # Only a metrical scheme: Jebb marks a lost verse this way (OC
            # 181ff.). Keep the row's speaker and colon number; the verse is
            # a lacuna.
            return rest.rstrip() + " ⁂LACUNA"
        # Greek with a metrical sign set in LaTeX inside it: the sign marks
        # lost syllables, so it becomes an ellipsis.
        return re.sub(r"\$([^$]*)\$", lambda m: repl(m) if not bad_span(m.group(1)) else " … ", s)
    return out


def is_apparatus(p: str) -> bool:
    """A row of the critical notes: a Latin word (not a speaker abbreviation
    in Latin lookalikes) or a lemma bracket with no opening bracket."""
    probe = re.sub(r"(?:^|(?<=\s))[A-Z]{2,3}\.(?=\s)", " ", table_text(p) or "")
    if re.search(r"[A-Za-z]{2,}", probe) or re.search(r"(?:^|\s)(L|r)\.?(?:\s|$)", probe):
        return True
    return probe.count("]") > probe.count("[")


def table_text(s: str) -> str:
    """A markdown table row -> its cells joined; separator/empty rows -> ''."""
    t = s.strip()
    if "|" not in t:
        return s
    cells = [c.strip() for c in t.strip("|").split("|")]
    cells = [c for c in cells if c and not re.fullmatch(r":?-{3,}:?", c)]
    return " ".join(cells)


def is_verse_like(s: str) -> bool:
    c = re.sub(r"\s\d{1,4}\s*$", "", COLON.sub("", plain(s)))
    return 0 < len(c) <= 75 and greek_share(c) >= 0.9 and not APP.match(s)


def stop_reason(s: str, p: str) -> str | None:
    """Why a row ends the verse block (None: it is verse). s is the row, p
    its plain text."""
    if APP.match(s):
        return "apparatus marker"
    if len(p) > 90:
        return "row over 90 characters"
    letters = [c for c in p if c.isalpha()]
    if len(letters) >= 10 and greek_share(p) < 0.5:
        return "mostly Latin letters"
    if is_apparatus(p):
        return "apparatus text"
    return None


def _grams(a: str) -> Counter:
    return Counter(a[k:k + 2] for k in range(len(a) - 1)) if len(a) > 1 else Counter([a])


def ref_index(ref_keys: list[str] | None) -> list[tuple[Counter, int]]:
    return [(g, sum(g.values())) for g in map(_grams, sorted({k for k in ref_keys or [] if k}))]


def ref_score(text: str, index: list[tuple[Counter, int]]) -> float:
    """The best Dice coefficient (letter bigrams) of the row against a
    reference line; 0.0 for a row too short to tell."""
    k = key(text)
    if len(k) < 12 or not index:
        return 0.0
    g = _grams(k)
    n = sum(g.values())
    best = 0.0
    for rg, rn in index:
        if 0.6 * n <= rn <= 1.7 * n:
            best = max(best, 2.0 * sum((g & rg).values()) / (n + rn))
    return best


RESUME_SCORE = 0.8    # a row this close to a reference line is verse
SUSPECT_SCORE = 0.6   # a dropped row this close is reported as verse-like


def page_rows(ne: list[tuple[int, str]], number: int | None, ref_keys: list[str] | None = None) -> tuple[list[dict], list[dict]]:
    """The verse rows of one Greek-text page (ne: its rows after the head)
    and every stop.

    The block ends at the first row that stop_reason names. One OCR slip (a
    verse word read in Latin letters) can be such a row, so with reference
    keys the scan goes on: the first later row that is verse by the tests
    and lies within RESUME_SCORE of a reference line resumes the block (with
    the speaker-name rows just before it). Every stop is reported: page,
    row, reason, the rows dropped (the stop row included), where the block
    resumed, and the dropped rows that look like verse (no reference: verse
    by shape; with one, within SUSPECT_SCORE of a reference line). A stop
    row stays dropped even where the block resumes after it (Ant. 920
    'κατασκαφάς·]', a verse with a stray bracket); a stop that resumed is
    always worth a look."""
    index = ref_index(ref_keys)
    rows: list[dict] = []
    stops: list[dict] = []
    stop = None
    pending: list[tuple[int, dict]] = []   # name and label rows seen while stopped

    def parsed(i: int, s: str):
        row = parse_row(s)
        if row is not None:
            row.update(src=i, page=number)
        return row

    for i, s in ne:
        s = latex_greek(s)
        p = plain(table_text(s)).replace("⁂LACUNA", "")
        reason = stop_reason(s, p)
        if stop is None:
            if reason is not None:
                stop = {"page": number, "src": i, "reason": reason, "text": p[:40], "dropped": [i],
                        "resumed_at": None, "suspect": []}
                stops.append(stop)
                pending = []
                continue
            row = parsed(i, s)
            if row is not None:
                rows.append(row)
            continue
        row = parsed(i, s) if reason is None else None
        if row is not None and row["kind"] in ("name", "label"):
            pending.append((i, row))
            stop["dropped"].append(i)
        elif row is not None and row["kind"] == "verse" and index and ref_score(row["text"], index) >= RESUME_SCORE:
            rows.extend(r for _, r in pending)
            rows.append(row)
            stop["resumed_at"] = i
            stop["dropped"] = [d for d in stop["dropped"] if d not in {k for k, _ in pending}]
            stop = None
            pending = []
        else:
            pending = []
            stop["dropped"].append(i)
            if row is not None and row["kind"] == "verse" and is_verse_like(s) and (not index or ref_score(row["text"], index) >= SUSPECT_SCORE):
                stop["suspect"].append((i, row["text"][:40]))
    return rows, stops


def extract(slug: str, ref_keys: list[str] | None = None) -> tuple[list[dict], list[str], list[dict]]:
    """Raw rows of the Greek text: {kind: verse|name|turn, src, page, ...},
    the page log, and every stop of a page's verse block (page_rows)."""
    fname, _, _, first, last = PLAYS[slug]
    lines = (GENIE / fname).read_text(encoding="utf-8").split("\n")
    rows: list[dict] = []
    log: list[str] = []
    stops: list[dict] = []
    last_page = None
    for pg in pages_of(lines, first, last or len(lines)):
        ne = [(i, s) for i, s in pg if s.strip()]
        if not ne:
            continue
        greek, number, used = read_head(ne)
        if not greek:
            # No head read: a page whose first six lines are mostly short
            # Greek verse is a text page all the same.
            if sum(1 for _, s in ne[used:used + 6] if is_verse_like(s)) >= 4:
                greek = True
                log.append(f"page at .txt {ne[0][0]} taken by the verse test (head {ne[0][1][:30]!r})")
        if not greek:
            continue
        if number is None:
            number = last_page + 2 if last_page else None
            log.append(f"page at .txt {ne[0][0]}: no page number read, inferred {number}")
        elif last_page and number != last_page + 2:
            log.append(f"page at .txt {ne[0][0]}: page {number} follows {last_page}")
        last_page = number
        page, page_stops = page_rows(ne[used:], number, ref_keys)
        rows.extend(page)
        stops.extend(page_stops)
    return rows, log, stops


HEADINGS = {"κομμός", "κομμὸς"}


def parse_row(s: str) -> dict | None:
    s = table_text(nfc(s))
    if not s.strip():
        return None
    s = s.replace("\\*", "⁑")  # Jebb's asterisk, kept through markup removal
    s = SPACE_ENT.sub(" ", s)
    s = re.sub(r"</?(small|sup|sub|span|i|b|em|strong)\b[^>]*>", "", s)
    s = re.sub(r"\$\s*(\d{1,4})\s*\$", r" \1", s)
    s = s.replace("**", "").replace("__", "")
    s = s.strip()
    head = s.lstrip("#").strip().replace("*", "")
    if head and NAME_LINE.fullmatch(head.translate(LAT2GRK)) and len(head) < 40:
        return {"kind": "name", "text": head.translate(LAT2GRK).rstrip(".").strip()}
    if re.fullmatch(r"\d{1,4}(\s+\d{1,4})*", head):
        return {"kind": "num", "numbers": [int(x) for x in head.split()]}
    if head.strip(" .") in HEADINGS:
        return None
    s = s.lstrip("#").strip()
    printed = None
    m = TRAIL_NUM.search(s)
    if m and GREEK_RE.search(s[:m.start()] or ""):
        printed, s = int(m.group(1)), s[:m.start()].rstrip()
    colon = strophe = None
    speaker = None
    for _ in range(4):
        s = s.lstrip()
        m = LEAD_SPK.match(s.translate(LAT2GRK)[:6] + s[6:]) if s[:1].isupper() else None
        if m and speaker is None:
            speaker = m.group(1).translate(LAT2GRK)
            s = s[m.end():]
            continue
        m = STROPHE.match(s)
        if m and strophe is None:
            strophe = (SUBTYPE[m.group(2)], NUMERAL.get(m.group(3) or "", None))
            s = s[m.end():]
            continue
        m = re.match(r"^\*?(?:κομμός|κομμὸς)\.?\*?(?:\s+|$)", s)
        if m:
            s = s[m.end():]
            continue
        m = COLON.match(s)
        if m and colon is None:
            colon = int(m.group(1))
            s = s[m.end():]
            continue
        break
    # Italic marks went with the strophe label; any '*' left, escaped or
    # not, is Jebb's asterisk before an emended word.
    s = s.replace("⁑", "*")
    s = s.replace("\u02d9", "\u00b7")  # OCR's dot above for the ano teleia
    # One elision mark: the OCR mixes psili (U+1FBF), koronis (U+1FBD), the
    # modifier apostrophe and the ASCII one; the tokenizer reads U+2019.
    s = re.sub("[\u1fbf\u1fbd\u02bc']", "\u2019", s)
    s = re.sub(r"\*\s+(?=\S)", "*", s)
    if s.strip() == "⁂LACUNA":
        s = "* * *"
    if re.fullmatch(r"[*\s]+", s):
        return {"kind": "verse", "text": "", "lacuna": s.strip(), "printed": printed, "colon": colon,
                "strophe": strophe, "speaker": speaker, "turn": False}
    turn = s.startswith("[") and not re.match(r"\[\d", s) and "]" not in s
    if turn:
        s = s[1:].strip()
    if not s and strophe and not speaker:
        return {"kind": "label", "strophe": strophe}
    return {"kind": "verse", "text": re.sub(r"\s+", " ", s).strip(), "printed": printed,
            "colon": colon, "strophe": strophe, "speaker": speaker, "turn": turn}


# ------------------------------------------------------------ reference
TEI_NS = "{http://www.tei-c.org/ns/1.0}"


def _tei_text(el) -> str:
    parts = []

    def walk(e):
        tag = e.tag.replace(TEI_NS, "")
        if tag in ("note", "bibl", "milestone"):
            parts.append(e.tail or "")
            return
        parts.append(e.text or "")
        for c in e:
            walk(c)
        if e is not el:
            parts.append(e.tail or "")
    walk(el)
    return " ".join("".join(parts).split())


def tlg_lines(slug: str) -> list[dict]:
    """The reference (TLG) text as the pipeline reads it: [{n, text, parts}]."""
    sys.path.insert(0, str(ROOT / "pipeline"))
    from drama_pipeline.config import Manifest
    from drama_pipeline import stage1_greek
    manifest = Manifest.load(ROOT / "manifests" / f"{slug}.yaml")
    spine = stage1_greek.parse_spine(stage1_greek.run_export(manifest), manifest)
    return [{"n": line["ref"].split("-")[0], "text": nfc(line["text"]), "parts": []}
            for seg in spine["segments"] for line in seg["lines"]]


def storr_lines(tlg_work: str) -> list[dict]:
    """Storr's Perseus lines, antilabe shares merged: [{n, text, parts:[n...]}]."""
    root = ET.parse(PERSEUS / f"tlg0011.tlg{tlg_work}.perseus-grc2.xml").getroot()
    out: list[dict] = []
    for el in root.find(f".//{TEI_NS}body").iter(f"{TEI_NS}l"):
        if el.get("style") == "hidden" or el.get("n") in (None, "0"):
            continue
        text = nfc(_tei_text(el))
        if el.get("part") in ("M", "F") and out:
            out[-1]["text"] += " " + text
            out[-1]["parts"].append(el.get("n"))
        else:
            out.append({"n": el.get("n"), "text": text, "parts": []})
    return out


# -------------------------------------------------------------- assembly
def split_shares(text: str, speaker: str | None) -> list[tuple[str | None, str]]:
    """A line with speaker abbreviations inside it -> [(speaker, share)]."""
    shares: list[tuple[str | None, str]] = []
    pos, cur = 0, speaker
    probe = text.translate(LAT2GRK)
    for m in MID_SPK.finditer(probe):
        shares.append((cur, text[pos:m.start()].strip()))
        cur, pos = m.group(1), m.end()
    shares.append((cur, text[pos:].strip()))
    return [(sp, t) for sp, t in shares if t or sp]


def join_turnovers(rows: list[dict], ref_keys: list[str]) -> list[dict]:
    """Attach turn-over rows to the line above or below.

    A turn-over is the end of a long line printed on a row of its own,
    above its line ('[βροτῶν', a turn-up) or below it (a turn-down). A
    candidate is a row marked '[', or a short row with no speaker, colon
    number, or strophe mark. It joins the neighbour whose text, with the
    fragment at its end, is found within one reference line; a candidate
    that neither neighbour takes stays a line of its own (Jebb's short
    extra-metrical lines, 'ἴθ᾽ ὦναξ,')."""
    out: list[dict] = []
    for i, r in enumerate(rows):
        if r["kind"] != "verse" or r.get("lacuna") is not None:
            out.append(r)
            continue
        prev = out[-1] if out and out[-1]["kind"] == "verse" and out[-1].get("lacuna") is None else None
        nxt = rows[i + 1] if i + 1 < len(rows) and rows[i + 1]["kind"] == "verse" and rows[i + 1].get("lacuna") is None else None
        cand = r["turn"] or (r["colon"] is None and r["strophe"] is None and r["speaker"] is None
                             and len(r["text"]) <= 20)
        target = None
        if cand:
            frag = key(r["text"])
            up = prev is not None and _in_ref(key(prev["text"]) + frag, ref_keys)
            down = nxt is not None and _in_ref(key(nxt["text"]) + frag, ref_keys)
            alone = _in_ref_whole(frag, ref_keys)
            if up and not down and not alone:
                target = prev
            elif down and not up and not alone:
                target = nxt
        if target is None:
            out.append(r)
            continue
        target.setdefault("turnovers", []).append({"text": r["text"], "src": r["src"], "printed": r["printed"]})
        target["text"] = (target["text"] + " " + r["text"]).strip()
        if r["printed"] is not None and target.get("printed") is None:
            # A number on the turn-over's own row marks the traditional line
            # that begins there: the joined line's, or (a turn-down that
            # starts the next traditional line, OT 1195 'βροτῶν') the next.
            target["printed"] = r["printed"]
            target["printed_from_turn"] = True
        elif r["printed"] is not None:
            # Both rows print a number: the line keeps both (TEI: one
            # margin-N token each), and check_margins checks both.
            target.setdefault("printed_more", []).append(r["printed"])
    return out


def _in_ref(k: str, ref_keys: list[str]) -> bool:
    """The joined key's last 16 letters (the fragment and the words before
    it) lie within one reference line."""
    tail = k[-16:]
    return any(tail in rk for rk in ref_keys)


def _in_ref_whole(frag: str, ref_keys: list[str]) -> bool:
    """The fragment is a reference line by itself."""
    return frag in ref_keys


def build_lines(rows: list[dict]) -> list[dict]:
    """Rows -> logical lines, with speakers, strophe labels, and detached
    margin numbers (a run of numbers printed apart from their lines)."""
    lines: list[dict] = []
    pending_name = None
    pending_strophe = None
    for r in rows:
        if r["kind"] == "name":
            pending_name = r["text"]
            continue
        if r["kind"] == "label":
            pending_strophe = r["strophe"]
            continue
        if r["kind"] == "num":
            if lines:
                lines[-1].setdefault("detached", []).extend(r["numbers"])
            continue
        if pending_strophe and not r["strophe"]:
            r["strophe"] = pending_strophe
        pending_strophe = None
        spk = r["speaker"] or pending_name
        pending_name = None
        shares = split_shares(r["text"], spk)
        lines.append({**r, "shares": shares or [(spk, "")]})
    return lines


# ------------------------------------------------------------- alignment
def align(jebb: list[dict], ref: list[dict]) -> list[list[int]]:
    """Map each Jebb line to the reference lines it covers (maybe none).

    Banded DP over lines: steps 1:1, 1:2 (one Jebb line = two reference
    lines), 2:1 (two Jebb lines = one reference line), and skips. Score is
    difflib's ratio on the letter keys."""
    jk = [key(x["text"]) or "∅" for x in jebb]
    rk = [key(x["text"]) or "∅" for x in ref]
    J, R = len(jk), len(rk)
    band = max(40, abs(J - R) + 25)
    NEG = -1e9
    SKIP = -0.45
    best = {}
    back = {}

    cache: dict[str, Counter] = {}

    def grams(a: str) -> Counter:
        g = cache.get(a)
        if g is None:
            g = cache[a] = Counter(a[k:k + 2] for k in range(len(a) - 1)) if len(a) > 1 else Counter([a])
        return g

    def sim(a: str, b: str) -> float:
        """Dice coefficient on letter bigrams."""
        if not a or not b:
            return 0.0
        ga, gb = grams(a), grams(b)
        total = sum(ga.values()) + sum(gb.values())
        return 2.0 * sum((ga & gb).values()) / total if total else 0.0

    best[(0, 0)] = 0.0
    for i in range(J + 1):
        centre = i * R / max(J, 1)
        lo, hi = max(0, int(centre - band)), min(R, int(centre + band))
        for j in range(lo, hi + 1):
            if (i, j) == (0, 0):
                continue
            cands = []
            if i >= 1 and j >= 1 and (i - 1, j - 1) in best:
                cands.append((best[(i - 1, j - 1)] + sim(jk[i - 1], rk[j - 1]) * 1.0 - 0.3, (i - 1, j - 1, "11")))
            if i >= 1 and j >= 2 and (i - 1, j - 2) in best:
                cands.append((best[(i - 1, j - 2)] + sim(jk[i - 1], rk[j - 2] + rk[j - 1]) * 2.0 - 0.8, (i - 1, j - 2, "12")))
            if i >= 2 and j >= 1 and (i - 2, j - 1) in best:
                cands.append((best[(i - 2, j - 1)] + sim(jk[i - 2] + jk[i - 1], rk[j - 1]) * 2.0 - 0.8, (i - 2, j - 1, "21")))
            if i >= 1 and (i - 1, j) in best:
                cands.append((best[(i - 1, j)] + SKIP, (i - 1, j, "j")))
            if j >= 1 and (i, j - 1) in best:
                cands.append((best[(i, j - 1)] + SKIP, (i, j - 1, "r")))
            if cands:
                v, b = max(cands)
                best[(i, j)] = v
                back[(i, j)] = b
    cover: list[list[int]] = [[] for _ in range(J)]
    i, j = J, R
    while (i, j) != (0, 0):
        pi, pj, kind = back[(i, j)]
        if kind == "11":
            cover[pi] = [pj]
        elif kind == "12":
            cover[pi] = [pj, pj + 1]
        elif kind == "21":
            cover[pi] = [pj]
        i, j = pi, pj
    return cover


def _num(ref: str) -> tuple[int, str]:
    m = re.match(r"(\d+)([a-z]*)$", ref)
    return (int(m.group(1)), m.group(2)) if m else (0, ref)


PRINTED_WEIGHT = 50.0   # a printed margin number left unmet
LEMMA_WEIGHT = 5.0      # a commentary lemma's number left unmet


def lemma_checkpoints(slug: str, jebb: list[dict]) -> dict[int, list[int]]:
    """{line index: [N, ...]} from Jebb's commentary notes ('**N lemma**').

    A note checks the line that holds its lemma's first words, when exactly
    one line within six numbers of N (by either reference) holds them."""
    fname, _, _, first, last = PLAYS[slug]
    text = (GENIE / fname).read_text(encoding="utf-8").split("\n")[first - 1:last]
    keyed = []
    for i, x in enumerate(jebb):
        nums = [_num(v)[0] for v in x["cand"].values() if v]
        keyed.append((i, nums, key(x["text"])))
    out: dict[int, list[int]] = {}
    seen = set()
    for row in text:
        for m in LEMMA.finditer(nfc(row)):
            n, lemma = int(m.group(1)), re.split(r"\.\.\.|…|—|:|,|\(|\]", m.group(2))[0]
            k = key(lemma)
            if greek_share(lemma) < 0.9 or len(k) < 5 or (n, k) in seen:
                continue
            seen.add((n, k))
            hits = [i for i, nums, lk in keyed if k in lk and any(abs(v - n) <= 6 for v in nums)]
            if len(hits) == 1:
                out.setdefault(hits[0], []).append(n)
    return out


def number_lines(slug: str, jebb: list[dict], refs: dict[str, list[dict]], covers: dict[str, list[list[int]]]) -> None:
    """Give every Jebb line its n.

    Two references: 'S' (Storr's Perseus Greek, whose numbers the Perseus
    English of Jebb uses) and 'T' (the TLG text, the traditional count). A
    line may take the number of the reference line it starts with, from
    either reference, or the number of a checkpoint on it. Checkpoints are
    Jebb's own numbers: the printed margin numbers, and the numbers of his
    commentary notes whose lemma the line holds. A line numbered n meets a
    checkpoint N when n = N, or n < N < the next line's number (the line
    holds several numbers of the traditional count, as Jebb's long lyric
    lines do); a lemma on a continuation line (no number of its own) meets
    N when the line before is N.

    The numbering is the cheapest path over the lines: an unmet printed
    number costs 50, an unmet lemma 5, taking a printed number 0.5 and a
    lemma's 1, a switch between references 1, a TLG number 0.01 (Storr's
    hold wherever Jebb's numbers allow, so the Perseus English anchors land),
    an unnumbered line 3; numbers must rise."""
    fixes = NUMBER_FIXES.get(slug, {})

    def cand(x: str, i: int):
        cov = covers[x][i]
        return refs[x][cov[0]]["n"] if cov else None

    for i, line in enumerate(jebb):
        line["cand"] = {x: cand(x, i) for x in ("S", "T")}
    lemmas = lemma_checkpoints(slug, jebb)
    options: list[dict[str, tuple[str, float]]] = []   # state -> (n, cost)
    checks: list[list[tuple[int, float, str]]] = []
    for i, line in enumerate(jebb):
        cks = []
        if line.get("printed") is not None:
            cks.append((line["printed"], PRINTED_WEIGHT, "turn" if line.get("printed_from_turn") else "printed"))
        for n in line.get("printed_more") or []:
            cks.append((n, PRINTED_WEIGHT, "turn"))
        for n in lemmas.get(i, []):
            cks.append((n, LEMMA_WEIGHT, "lemma"))
        line["lemmas"] = lemmas.get(i, [])
        if line["src"] in fixes:
            # A hand fix keeps its checkpoints: an unmet one costs, and is
            # reported below (fix_conflicts).
            options.append({"F": (fixes[line["src"]][0], 0.0)})
            checks.append(cks)
            continue
        opts: dict[str, tuple[str, float]] = {}
        for x in ("S", "T"):
            if line["cand"][x] is not None:
                opts[x] = (line["cand"][x], 0.01 if x == "T" else 0.0)
        for n, _, kind in cks:
            opts.setdefault(f"C{n}", (str(n), 1.0 if kind == "lemma" else 0.5))
        opts["X"] = ("", 3.0)
        options.append(opts)
        checks.append(cks)

    # Only a lyric line (a colon number or strophe mark) or a line with a
    # turn-over can hold several numbers of the traditional count.
    multi = [x.get("colon") is not None or x.get("strophe") is not None or bool(x.get("turnovers")) for x in jebb]

    def unmet(i: int, st: str, before: tuple[int, str], nxt: tuple[int, str] | None) -> list[tuple[int, float, str]]:
        """Line i's unmet checkpoints, given its state, the number before
        it, and the next line's number."""
        out = []
        for n, w, kind in checks[i]:
            if st == "X":
                met = kind == "lemma" and before[0] == n
            else:
                v, suffix = _num(options[i][st][0])
                upper = nxt[0] if nxt is not None else 10 ** 6
                inside = multi[i] and v < n < upper
                met = (v == n and not suffix) or inside or (kind == "turn" and nxt == (n, ""))
            if not met:
                out.append((n, w, kind))
        return out

    def check_cost(i: int, st: str, before: tuple[int, str], nxt: tuple[int, str] | None) -> float:
        return sum(w for _, w, _ in unmet(i, st, before, nxt))

    INF = float("inf")
    # best[i][state] = (cost, previous state, last real number, number before line i)
    best: list[dict[str, tuple[float, str | None, tuple[int, str], tuple[int, str]]]] = []
    for i, opts in enumerate(options):
        row = {}
        for st, (n, cost) in opts.items():
            here = _num(n) if st != "X" else None
            if i == 0:
                row[st] = (cost, None, here or (0, ""), (0, ""))
                continue
            choice = (INF, None, (0, ""), (0, ""))
            for pst, (pc, _, plast, pbefore) in best[i - 1].items():
                c = pc + cost + (1.0 if st[0] != pst[0] and st[0] in "ST" and pst[0] in "ST" else 0.0)
                if here is not None and not (here > plast):
                    c += 100.0  # numbers must rise
                c += check_cost(i - 1, pst, pbefore, here)
                last = here if here is not None else plast
                if c < choice[0]:
                    choice = (c, pst, last, plast)
            row[st] = choice
        best.append(row)
    last_i = len(jebb) - 1
    st = min(best[-1], key=lambda k: best[-1][k][0] + check_cost(last_i, k, best[-1][k][3], None))
    path = [st]
    for i in range(len(jebb) - 1, 0, -1):
        st = best[i][st][1]
        path.append(st)
    path.reverse()
    # A fixed line's checkpoints the fix leaves unmet.
    for i, (line, st) in enumerate(zip(jebb, path)):
        if st == "F":
            after = _num(options[i + 1][path[i + 1]][0]) if i + 1 < len(jebb) and path[i + 1] != "X" else None
            line["fix_conflicts"] = [(n, kind) for n, _, kind in unmet(i, st, best[i][st][3], after)]
    for i, (line, st) in enumerate(zip(jebb, path)):
        if st == "X":
            line["n"] = None
            continue
        line["n"] = options[i][st][0]
        line["n_how"] = {"S": "storr", "T": "tlg", "F": "fix", "C": "checkpoint"}[st[0]]
        if st == "F":
            line["n_how"] = "fix: " + fixes[line["src"]][1]
        if st == "S":
            line["ref_parts"] = refs["S"][covers["S"][i][0]]["parts"]
    used = {line["n"] for line in jebb if line["n"]}
    # unmatched lines: the next free number after the line before, else a letter
    for i, line in enumerate(jebb):
        if line["n"] is not None:
            continue
        prev = next((jebb[k]["n"] for k in range(i - 1, -1, -1) if jebb[k]["n"]), "0")
        nxt = next((jebb[k]["n"] for k in range(i + 1, len(jebb)) if jebb[k]["n"]), None)
        pn, _ = _num(prev)
        cand_n = str(pn + 1)
        if (nxt is None or _num(nxt)[0] > pn + 1) and cand_n not in used:
            line["n"], line["n_how"] = cand_n, "next free number"
        else:
            letter = "a"
            while f"{pn}{letter}" in used:
                letter = chr(ord(letter) + 1)
            line["n"], line["n_how"] = f"{pn}{letter}", "lettered"
        used.add(line["n"])


def check_margins(slug: str, jebb: list[dict]) -> list[dict]:
    """Every printed number is a checkpoint; returns the disagreements. A
    line holds its own printed number and, when a joined turn-over row printed
    one too, that as well (printed_more)."""
    notes = MARGIN_NOTES.get(slug, {})
    bad = []
    for i, line in enumerate(jebb):
        numbers = ([] if line.get("printed") is None else [(line["printed"], bool(line.get("printed_from_turn")))]) \
            + [(p, True) for p in line.get("printed_more") or []]
        if not numbers:
            continue
        n, _ = _num(line["n"])
        nxt = next((_num(jebb[k]["n"])[0] for k in range(i + 1, len(jebb)) if _num(jebb[k]["n"])[0] > n), None)
        statuses = []
        for p, from_turn in numbers:
            if n == p and not _num(line["n"])[1]:
                ok = "equal"
            elif n < p and nxt is not None and p < nxt and (line.get("colon") is not None or line.get("strophe") is not None or line.get("turnovers")):
                ok = "inside"   # a lyric line carrying several traditional numbers
            elif from_turn and i + 1 < len(jebb) and jebb[i + 1]["n"] == str(p):
                ok = "turn"     # printed on a turn-over row where the next line's number begins
            elif line["src"] in notes:
                ok = "noted: " + notes[line["src"]]
            else:
                ok = None
                bad.append({"src": line["src"], "page": line["page"], "n": line["n"], "printed": p,
                            "text": line["text"][:60], "how": line.get("n_how")})
            statuses.append(ok)
        line["margin_ok"] = statuses[0] if all(statuses) else None
    # Numbers printed apart from their lines check against the page: each
    # must fall within the numbers the page's lines carry.
    for i, line in enumerate(jebb):
        for p in line.get("detached") or []:
            on_page = [_num(x["n"])[0] for x in jebb if x["page"] == line["page"]]
            after = next((_num(jebb[k]["n"])[0] for k in range(i + 1, len(jebb)) if jebb[k]["page"] != line["page"]), None)
            if on_page and min(on_page) <= p and (p <= max(on_page) or (after is not None and p < after)):
                line.setdefault("detached_ok", []).append(p)
            elif line["src"] in notes:
                line.setdefault("detached_ok", []).append(p)
            else:
                bad.append({"src": line["src"], "page": line["page"], "n": line["n"], "printed": p,
                            "text": "(printed apart) " + line["text"][:45], "how": line.get("n_how")})
    return bad


# ------------------------------------------------------------------- TEI
def to_tei_text(s: str) -> str:
    """Escape, then Jebb's brackets as elements: [x] -> <del>, <x> -> <add>."""
    out = escape(s, {'"': "&quot;"})
    out = re.sub(r"&lt;([^&]*?)&gt;", r"<add>\1</add>", out)
    out = re.sub(r"\[([^\[\]]*?)\]", r"<del>\1</del>", out)
    return out


def write_tei(slug: str, jebb: list[dict]) -> str:
    fname, tlg, ident, _, _ = PLAYS[slug]
    title = {"oedipus-tyrannus": "Οἰδίπους Τύραννος", "oedipus-coloneus": "Οἰδίπους ἐπὶ Κολωνῷ",
             "antigone": "Ἀντιγόνη", "philoctetes": "Φιλοκτήτης", "trachiniae": "Τραχίνιαι",
             "electra-soph": "Ἠλέκτρα", "ajax": "Αἴας"}[slug]
    leaf = _leaves(ident)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<TEI xmlns="http://www.tei-c.org/ns/1.0">',
           '<teiHeader><fileDesc>',
           f'<titleStmt><title>{title}</title><author>Sophocles</author><editor>R. C. Jebb</editor></titleStmt>',
           '<publicationStmt><p>Generated by scripts/ocr/jebb_to_tei.py from a Genie OCR of the scan below. Not for redistribution until the owner rules on it.</p></publicationStmt>',
           f'<sourceDesc><bibl><title>Sophocles: The Plays and Fragments</title><editor>R. C. Jebb</editor><publisher>Cambridge University Press</publisher><idno type="archive.org">{ident}</idno><idno type="ocr">{escape(fname)}</idno></bibl></sourceDesc>',
           '</fileDesc></teiHeader>', '<text><body>']
    page = None
    div_open = False
    sp_open = False
    cur_speaker = None
    for line in jebb:
        if line["page"] != page:
            page = line["page"]
            n_leaf = leaf.get(str(page))
            facs = f' facs="https://archive.org/details/{ident}/page/n{n_leaf - 1}"' if n_leaf else ""
            out.append(f'<pb n="{page}"{facs}/>')
        if line.get("strophe"):
            if sp_open:
                out.append("</sp>")
                sp_open = False
            if div_open:
                out.append("</div>")
            subtype, num = line["strophe"]
            out.append(f'<div type="textpart" subtype="{subtype}"' + (f' n="{num}"' if num else "") + ">")
            div_open = True
            cur_speaker = None  # a new div re-opens its speech
        shares = line["shares"]
        parts = [line["n"]] + _share_refs(line, len(shares) - 1)
        for k, (spk, text) in enumerate(shares):
            if spk is not None and (spk != cur_speaker or k > 0 or not sp_open):
                if sp_open:
                    out.append("</sp>")
                out.append(f"<sp><speaker>{escape(spk)}</speaker>")
                sp_open, cur_speaker = True, spk
            elif not sp_open:
                out.append("<sp>")
                sp_open = True
            attrs = [f'n="{parts[k]}"']
            if len(shares) > 1:
                attrs.append('part="%s"' % ("I" if k == 0 else "F" if k == len(shares) - 1 else "M"))
            rend = []
            if k == 0 and line.get("colon"):
                rend.append(f"colon-{line['colon']}")
            if k == 0 and line.get("printed") is not None:
                rend.append(f"margin-{line['printed']}")
            if k == 0:
                rend.extend(f"margin-{p}" for p in line.get("printed_more") or [])
            if k == 0:
                rend.extend(f"margin-apart-{p}" for p in line.get("detached") or [])
            if k == 0 and line.get("turnovers"):
                rend.append("turn")
            if rend:
                attrs.append('rend="%s"' % " ".join(rend))
            if line.get("lacuna") is not None:
                out.append(f"<l {' '.join(attrs)}><gap reason=\"lost\" rend=\"{escape(' '.join(line['lacuna'].replace(' ', '')))}\"/></l>")
            else:
                out.append(f"<l {' '.join(attrs)}>{to_tei_text(text)}</l>")
    if sp_open:
        out.append("</sp>")
    if div_open:
        out.append("</div>")
    out.append("</body></text></TEI>")
    return "\n".join(out) + "\n"


def _share_refs(line: dict, extra: int) -> list[str]:
    if extra <= 0:
        return []
    have = list(line.get("ref_parts") or [])
    out = []
    for k in range(extra):
        out.append(have[k] if k < len(have) else f"{line['n']}{'abcdefgh'[k]}")
    return out


_LEAVES: dict[str, dict[str, int]] = {}


def _leaves(ident: str) -> dict[str, int]:
    """Printed page -> archive.org leaf, from the item's page_numbers.json
    (fetched once into build/sweeps/jebb-ocr/)."""
    if ident in _LEAVES:
        return _LEAVES[ident]
    path = ROOT / "build/sweeps/jebb-ocr" / f"{ident}_page_numbers.json"
    table: dict[str, int] = {}
    if path.exists():
        for p in json.loads(path.read_text())["pages"]:
            if p.get("pageNumber"):
                table.setdefault(p["pageNumber"], p["leafNum"])
    _LEAVES[ident] = table
    return table


# -------------------------------------------------------------------- QA
ALLOWED_PUNCT = set(" .,·;:!—–-'’᾽ʼ()[]<>†*…\"“”‘«»")


def char_check(tei: str) -> dict:
    root = ET.fromstring(tei)
    bad: dict[str, int] = {}
    for el in root.iter(f"{TEI_NS}l"):
        for c in "".join(el.itertext()):
            d = unicodedata.normalize("NFD", c)
            base = d[0]
            if GREEK_RE.match(base) or base in ALLOWED_PUNCT or all(x in COMB or x == "ͅ" for x in d[1:]) and GREEK_RE.match(base):
                continue
            bad[c] = bad.get(c, 0) + 1
    return bad


LEMMA = re.compile(r"\*\*(\d{1,4})(?:\s*ff?\.)?\s+([^*\d][^*]*?)\*\*")


def lemma_check(slug: str, jebb: list[dict]) -> dict:
    """Jebb's commentary notes open with '**N lemma**': his own number for
    the words. Each lemma found in the text checks the line numbering: the
    line holding the lemma's first words must be N, or cover N."""
    fname, _, _, first, last = PLAYS[slug]
    lines = (GENIE / fname).read_text(encoding="utf-8").split("\n")[first - 1:last]
    keyed = [(i, _num(x["n"])[0], key(x["text"])) for i, x in enumerate(jebb)]
    agree = inside = 0
    bad = []
    seen = set()
    for row in lines:
        for m in LEMMA.finditer(nfc(row)):
            n, lemma = int(m.group(1)), m.group(2)
            lemma = re.split(r"\.\.\.|…|—|:|,|\(", lemma)[0]
            if greek_share(lemma) < 0.9 or (n, lemma) in seen:
                continue
            k = key(lemma)
            if len(k) < 5:
                continue
            seen.add((n, lemma))
            hits = [(i, v) for i, v, lk in keyed if k in lk and abs(v - n) <= 6]
            if not hits:
                continue
            i, v = min(hits, key=lambda h: abs(h[1] - n))
            nxt = next((keyed[j][1] for j in range(i + 1, len(keyed)) if keyed[j][1] > v), v + 1)
            if v == n:
                agree += 1
            elif v < n < nxt:
                inside += 1
            else:
                bad.append({"note": n, "lemma": lemma.strip()[:30], "line_n": jebb[i]["n"], "src": jebb[i]["src"]})
    return {"agree": agree, "inside": inside, "disagree": len(bad), "cases": bad}


def english_anchor_check(tlg_work: str, jebb: list[dict]) -> tuple[int, int, list[str]]:
    text = sorted(PERSEUS.glob(f"tlg0011.tlg{tlg_work}.perseus-eng*.xml"))[0].read_text(encoding="utf-8")
    anchors = re.findall(r'<l n="([^"]+)"', text)
    have = set()
    for line in jebb:
        have.add(line["n"])
        have.update(_share_refs(line, len(line["shares"]) - 1))
    missing = [a for a in anchors if a not in have]
    return len(anchors) - len(missing), len(anchors), missing


# ------------------------------------------------------------------ main
def convert(slug: str, qa: bool = False) -> dict:
    fname, tlg, ident, first, last = PLAYS[slug]
    if first is None:
        raise SystemExit(f"{slug}: set the play's .txt line range in PLAYS")
    ref = storr_lines(tlg)
    ref_t = tlg_lines(slug)
    ref_keys = [key(r["text"]) for r in ref + ref_t if r["text"]]
    rows, log, stops = extract(slug, ref_keys)
    rows = join_turnovers(rows, ref_keys)
    jebb = build_lines(rows)
    refs = {"S": ref, "T": ref_t}
    covers = {"S": align(jebb, ref), "T": align(jebb, ref_t)}
    number_lines(slug, jebb, refs, covers)
    bad = check_margins(slug, jebb)
    seen: dict[str, int] = {}
    dups = []
    for line in jebb:
        if line["n"] in seen:
            dups.append((line["n"], seen[line["n"]], line["src"]))
        seen[line["n"]] = line["src"]
    tei = write_tei(slug, jebb)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{slug}.xml").write_text(tei, encoding="utf-8")
    _write_sums()
    report = {"slug": slug, "lines": len(jebb), "ref_lines": len(ref), "log": log,
              "margin_checkpoints": sum((x.get("printed") is not None) + len(x.get("printed_more") or []) for x in jebb),
              "margin_equal": sum(1 for x in jebb if x.get("margin_ok") == "equal"),
              "margin_inside": sum(1 for x in jebb if x.get("margin_ok") == "inside"),
              "margin_turn": sum(1 for x in jebb if x.get("margin_ok") == "turn"),
              "margin_noted": sum(1 for x in jebb if (x.get("margin_ok") or "").startswith("noted")),
              "margin_bad": bad, "duplicate_refs": dups,
              "numbered_by": {h: sum(1 for x in jebb if x.get("n_how") == h) for h in ("storr", "tlg", "checkpoint", "next free number", "lettered")},
              "not_storr": [(x["src"], x["n"], x["n_how"], x["cand"]["S"], x["text"][:40]) for x in jebb if x.get("n_how") != "storr"],
              "turnovers": sum(len(x.get("turnovers") or []) for x in jebb)}
    # Every stop of a page's verse block; 'stops_suspect' are those that
    # resumed or dropped rows that look like verse (a slip to look at).
    report["stops"] = [{**st, "dropped": [st["dropped"][0], st["dropped"][-1], len(st["dropped"])]} for st in stops]
    report["stops_suspect"] = [st for st in stops if st["resumed_at"] is not None or st["suspect"]]
    # A hand fix (NUMBER_FIXES) that leaves a printed number or commentary
    # lemma unmet, and the lemma checks of the whole numbering.
    report["fix_conflicts"] = [{"src": x["src"], "page": x["page"], "fix": x["n"], "checkpoint": n, "kind": kind,
                                "text": x["text"][:40]}
                               for x in jebb for n, kind in x.get("fix_conflicts") or []]
    report["commentary_lemmas"] = lemma_check(slug, jebb)
    if qa:
        report["bad_chars"] = char_check(tei)
        present, total, missing = english_anchor_check(tlg, jebb)
        report["english_anchors"] = {"present": present, "total": total, "missing": missing}
    dump = ROOT / "build/sweeps/jebb-ocr" / f"{slug}-lines.json"
    dump.parent.mkdir(parents=True, exist_ok=True)
    dump.write_text(json.dumps([{k: v for k, v in x.items()} for x in jebb], ensure_ascii=False, indent=0), encoding="utf-8")
    return report


def _write_sums() -> None:
    rows = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(OUT.glob("*.xml"))]
    (OUT / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("play", help="play slug, or 'all'")
    ap.add_argument("--qa", action="store_true", help="also run the character and English-anchor checks")
    args = ap.parse_args(argv)
    slugs = list(PLAYS) if args.play == "all" else [args.play]
    failed = False
    for slug in slugs:
        rep = convert(slug, args.qa)
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        failed |= bool(rep["margin_bad"] or rep["duplicate_refs"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
