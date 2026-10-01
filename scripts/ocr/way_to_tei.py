#!/usr/bin/env python3
"""Way's Loeb Euripides (Genie OCR .txt) -> drama TEI (edition-picker plan §3.1).

    pipeline/.venv/bin/python scripts/ocr/way_to_tei.py medea [--qa]

Writes sources/ocr/way-loeb/<play>.xml, refreshes sources/ocr/way-loeb/SHA256SUMS,
and dumps its line records to build/sweeps/way-ocr/<play>-lines.json. Run it
with the pipeline's venv: it reads Murray's Greek and the TLG text through the
pipeline. The OCR is build/genie/<volume>.txt (git-ignored; never committed).

The shape is jebb_to_tei.py's, and its helpers are imported, not copied:
the letter key, the reference index and score, the alignment, the numbering
(number_lines: printed numbers govern, the references fill between them),
the margin check, the TEI escaping, and the character check. What differs
for Way (build/sweeps/way-loeb-ocr-quality-2026-10-01.md):

1. Separation. A page (between '---' lines) is Greek when its first line is
   the play's Greek running head (Latin lookalikes mapped to Greek; a fuzzy
   match, edit distance at most a fifth of the title). The OCR page index is
   the archive.org leaf. The head and the folio at the foot are dropped; from
   the first footnote-marker row ('$^1$', '¹', '<sup>1</sup>', '1 Latin') to
   the foot is apparatus and is dropped. A row of mostly Latin letters stops
   the page's verse too; every stop is reported. A page without the head is
   skipped and its leaf logged; one whose rows are Greek verse all the same
   (a misread head) is a stop that fails the run.
2. Rows. A row of Greek capitals is a speaker (a numeral may follow, 'ΠΑΙΣ
   αʹ'); a row of digits is Way's margin number for the next verse row; a
   strophe mark on a row of its own labels the verse row above it when that
   row does not end a sentence, else the row below (the OCR sets the margin
   label on either side of its line). A number before a row (Way's margin), or
   after it, is its printed number (rend="margin-N"); a strophe mark at a
   row's end labels it. Markdown, italics, and footnote markers are removed;
   a breathing set as a spacing mark before a capital is joined to it
   (counted in the report); elision marks become ’.
3. Joins. A shared line (antilabe) is printed as two or more labelled rows:
   rows under different speakers join into one <l> with part I/M/F when
   together they match a reference line better than either alone. A
   turn-over (the end of a long line on a row of its own, under it) joins the
   row above when the two together lie within one reference line.
4. Numbering: jebb_to_tei.number_lines with Murray's Greek (the 'S'
   reference; his Perseus TEI as the pipeline reads it) and the TLG text
   ('T'). Way prints no commentary, so there are no lemma checkpoints.
   NUMBER_FIXES and MARGIN_NOTES hold hand fixes and noted disagreements,
   each with its reason; they are handed to jebb_to_tei by play slug.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jebb_to_tei as J  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GENIE = ROOT / "build/genie"
OUT = ROOT / "sources/ocr/way-loeb"
DUMP = ROOT / "build/sweeps/way-ocr"

# slug: OCR file, archive.org item, first and last .txt line of the play,
# the Greek running head, the TEI title, the manifest's Murray edition id.
PLAYS = {
    "medea": {"ocr": "euripidesway04euriuoft.txt", "ident": "euripidesway04euriuoft",
              "first": 9331, "last": 13336, "head": "ΜΗΔΕΙΑ", "title": "Μήδεια",
              "murray": "murray-oct"},
}

# Per-play numbering exceptions: {ocr .txt line: (n, reason)} (jebb_to_tei's form).
NUMBER_FIXES: dict[str, dict[int, tuple[str, str]]] = {}
# Printed numbers that disagree with the numbering for a stated reason.
MARGIN_NOTES: dict[str, dict[int, str]] = {}
# Printed margin numbers the OCR set on the wrong row, as the scan prints
# them: {slug: {ocr .txt line: (printed number or None, reason)}}.
PRINTED_FIXES: dict[str, dict[int, tuple[int | None, str]]] = {
    "medea": {
        10208: (None, "scan p. 308 (leaf 320): no number on τί γὰρ σύ μ’ ἠδίκηκας (the OCR moved 310 here)"),
        10209: (310, "scan p. 308 (leaf 320) prints 310 against ὅτῳ σε θυμὸς"),
        12994: (1320, "scan p. 386 (leaf 398) prints 1320 against λέγ’ εἴ τι βούλει"),
        12995: (None, "scan p. 386 (leaf 398): no number on τοιόνδ’ ὄχημα (the OCR moved 1320 here)"),
    },
}

CAPS = J.CAPS
NAME = re.compile(r"^([%s][%s ]{2,}?)(?:\s+([α-ι]{1,2})\s*[ʹ΄'’])?(\s*\([^)]*\))?\.?$" % (CAPS, CAPS))
STROPHE_ONLY = re.compile(r"^(στρ|ἀντ|ἐπῳδ|ἐπωδ|μεσῳδ)\.?\s*(?:([α-θ])\s*[΄'ʹ’`´᾽᾿]?)?\.?$")
STROPHE_END = re.compile(r"\s+(στρ|ἀντ|ἐπῳδ|ἐπωδ|μεσῳδ)\.?\s*(?:([α-θ])\s*[΄'ʹ’`´᾽᾿]?)?\.?$")
SUBTYPE = {"στρ": "strophe", "ἀντ": "antistrophe", "ἐπῳδ": "epode", "ἐπωδ": "epode", "μεσῳδ": "mesode"}
NUMERAL = {c: i for i, c in enumerate("αβγδεζηθ", 1)}
FOOTNOTE_ROW = re.compile(r"^\s*(\$\^\{?\d+\}?\$|[¹²³⁴⁵]|<sup>\s*\d+\s*</sup>|\d\s+[A-Z][a-z])")
FOOTNOTE_MARK = re.compile(r"\s*(\$\^\{?\d+\}?\$|<sup>\s*\d+\s*</sup>|[¹²³⁴⁵])")
LEAD_NUM = re.compile(r"^(\d{1,4})\s+(?=\S)")
TRAIL_NUM = re.compile(r"\s+(\d{1,4})$")
# A breathing (and accent) set as a spacing mark before a capital: '῞Αιδα',
# '᾿Αχαιούς', and the apostrophe forms ''Αργεῖος', '’Αγάμεμνον' (a smooth
# breathing) at a word's start.
SPACING_BREATHING = re.compile(r"(?:(?<=^)|(?<=[\s(\[—]))([᾿῾῍-῏῝-῟'’][̀́͂]?)([ΑΕΗΙΟΥΩΡ])")
BREATHING = {"᾿": "̓", "'": "̓", "’": "̓", "῾": "̔"}


def edit_distance(a: str, b: str) -> int:
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, cb in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (ca != cb))
    return row[-1]


def strip_markup(s: str) -> str:
    """The row without OCR markup: spaces and entities, tags, bold, italics,
    headings, footnote markers, LaTeX numbers."""
    s = J.SPACE_ENT.sub(" ", s)
    s = FOOTNOTE_MARK.sub("", s)
    s = re.sub(r"</?[A-Za-z][^>]*>", "", s)
    s = re.sub(r"\$\s*(\d{1,4})\s*\$", r" \1", s)
    s = s.replace("\\*", "").replace("*", "").replace("__", "")
    return " ".join(s.lstrip("#").split())


def is_head(s: str, title: str) -> bool:
    t = strip_markup(s).translate(J.LAT2GRK).replace(" ", "")
    return edit_distance(t, title.replace(" ", "")) <= max(1, len(title) // 5)


def normalise(s: str, counts: dict) -> str:
    """A verse row's text as the pipeline reads it."""
    s = unicodedata.normalize("NFC", s)

    def join(m):
        counts["capital_breathing"] = counts.get("capital_breathing", 0) + 1
        mark = unicodedata.normalize("NFD", m.group(1))
        return unicodedata.normalize("NFC", m.group(2) + BREATHING.get(mark[0], unicodedata.normalize("NFD", mark[0])[-1:]) + mark[1:])

    def spacing(m):
        # '῞' (U+1FDD) is rough + acute, '῎' smooth + acute, and so on.
        return join(m)

    s = SPACING_BREATHING.sub(spacing, s)
    s = s.replace("˙", "·")
    s = s.replace("ϐ", "β")
    s = re.sub("[᾿᾽ʼ']", "’", s)
    s = re.sub(r"\S+", lambda t: J._greek_lookalikes(t.group(0)) if J.GREEK_RE.search(t.group(0)) else t.group(0), s)
    return re.sub(r"\s+", " ", s).strip()


def parse_row(raw: str, counts: dict) -> dict | None:
    s = strip_markup(raw)
    if not s:
        return None
    if re.fullmatch(r"\d{1,4}", s):
        return {"kind": "num", "number": int(s)}
    probe = s.translate(J.LAT2GRK) if re.fullmatch(r"[A-Z%s ]+.*" % CAPS, s) else s
    m = NAME.match(probe)
    if m and not J.GREEK_RE.search(re.sub(r"[%s]" % CAPS, "", m.group(1))):
        name = m.group(1).strip()
        if m.group(2):
            name += " " + m.group(2) + "ʹ"
        if m.group(3):
            name += " " + m.group(3).strip()
        return {"kind": "name", "text": name}
    m = STROPHE_ONLY.match(s)
    if m:
        return {"kind": "label", "strophe": (SUBTYPE[m.group(1)], NUMERAL.get(m.group(2) or ""))}
    printed = strophe = None
    m = LEAD_NUM.match(s)
    if m:
        printed, s = int(m.group(1)), s[m.end():]
    m = STROPHE_END.search(s)
    if m:
        strophe, s = (SUBTYPE[m.group(1)], NUMERAL.get(m.group(2) or "")), s[:m.start()]
    m = TRAIL_NUM.search(s)
    if m and printed is None and J.GREEK_RE.search(s[:m.start()]):
        printed, s = int(m.group(1)), s[:m.start()]
    return {"kind": "verse", "text": normalise(s, counts), "printed": printed, "strophe": strophe,
            "colon": None, "speaker": None, "turn": False, "lacuna": None}


# ------------------------------------------------------------------ pages
def pages(slug: str) -> list[tuple[int, list[tuple[int, str]]]]:
    """(leaf, rows) for every OCR page of the play's span: the OCR page index
    (pages between '---' lines, counted from the file's start) is the leaf."""
    play = PLAYS[slug]
    lines = (GENIE / play["ocr"]).read_text(encoding="utf-8").split("\n")
    out, cur, leaf = [], [], 1
    for i, s in enumerate(lines, 1):
        if s.strip() == "---":
            if cur and play["first"] <= cur[0][0] <= play["last"]:
                out.append((leaf, cur))
            cur, leaf = [], leaf + 1
        elif s.strip():
            cur.append((i, s))
    if cur and play["first"] <= cur[0][0] <= play["last"]:
        out.append((leaf, cur))
    return out


def extract(slug: str, counts: dict) -> tuple[list[dict], list[str], list[dict]]:
    """The rows of every Greek page, the page log, and every stop."""
    play = PLAYS[slug]
    rows: list[dict] = []
    log: list[str] = []
    stops: list[dict] = []
    last_page = None
    skipped = []
    for leaf, ne in pages(slug):
        if not is_head(ne[0][1], play["head"]):
            # Not Greek by its head (the English facing page, the argument,
            # the cast list). A page whose rows are Greek verse all the same
            # has a misread head: it is a stop, and fails the conversion.
            skipped.append(leaf)
            verse = [i for i, s in ne[1:] if is_verse_row(s)]
            if len(verse) >= 3:
                stops.append({"leaf": leaf, "page": None, "src": ne[0][0],
                              "reason": "no running head read; the page holds Greek verse",
                              "text": J.plain(ne[0][1])[:50], "verse_rows": len(verse),
                              "dropped": [x for x, _ in ne]})
            continue
        body = ne[1:]
        folio = strip_markup(body[-1][1]) if body else ""
        page = int(folio) if re.fullmatch(r"\d{1,4}", folio) else None
        if page is not None:
            body = body[:-1]
        else:
            page = last_page + 2 if last_page else None
            log.append(f"leaf {leaf}: no folio read, page {page} inferred")
        if last_page and page != last_page + 2:
            log.append(f"leaf {leaf}: page {page} follows {last_page}")
        last_page = page
        for k, (i, s) in enumerate(body):
            p = J.plain(s)
            letters = [c for c in p if c.isalpha()]
            reason = None
            if FOOTNOTE_ROW.match(J.SPACE_ENT.sub(" ", s)):
                reason = "footnote"
            elif len(letters) >= 10 and J.greek_share(p) < 0.5:
                reason = "mostly Latin letters"
            if reason:
                stops.append({"leaf": leaf, "page": page, "src": i, "reason": reason, "text": p[:50],
                              "dropped": [x for x, _ in body[k:]]})
                break
            row = parse_row(s, counts)
            if row is not None:
                row.update(src=i, page=page, leaf=leaf)
                rows.append(row)
    if skipped:
        log.append(f"{len(skipped)} pages without the Greek running head skipped: leaves {', '.join(map(str, skipped))}")
    return rows, log, stops


def is_verse_row(s: str) -> bool:
    """A row of Greek verse: mostly Greek, with ten lower-case Greek letters
    or more (a cast list's names are capitals)."""
    p = strip_markup(s)
    return J.greek_share(p) >= 0.8 and sum(1 for c in p if J.GREEK_RE.match(c) and c.islower()) >= 10


def place_numbers_and_labels(rows: list[dict]) -> list[dict]:
    """Way's own-row margin numbers go to the next verse row; own-row strophe
    marks to the verse row above (when it does not end a sentence and no
    speaker name stands between) or else the row below. Where two numbers
    stand on rows of their own before one verse row, the last goes to it as
    before and the earlier cannot be placed by the rows: it stays a
    checkpoint apart (rend margin-apart-N, checked against its page), and so
    does a number left after the last verse row."""
    out: list[dict] = []
    pending: list[dict] = []
    pending_label = None
    for r in rows:
        if r["kind"] == "num":
            pending.append(r)
            continue
        if r["kind"] == "label":
            prev = out[-1] if out else None
            if (prev is not None and prev["kind"] == "verse" and prev["page"] == r["page"] and not prev["strophe"]
                    and not re.search(r"[.;·]\W*$", prev["text"])):
                prev["strophe"] = r["strophe"]
            else:
                pending_label = r["strophe"]
            continue
        if r["kind"] == "verse":
            if pending:
                # Set on the row below for now; resolve_apart may move it
                # to the row above.
                above = next((x for x in reversed(out) if x["kind"] == "verse"), None)
                r["apart"] = {"number": pending[-1]["number"], "src": pending[-1]["src"],
                              "above": above["src"] if above is not None and above["page"] == r["page"] else None}
                if len(pending) > 1:
                    r["unplaced"] = [{"number": x["number"], "src": x["src"]} for x in pending[:-1]]
                pending = []
            if pending_label is not None and not r["strophe"]:
                r["strophe"] = pending_label
            pending_label = None
        out.append(r)
    if pending:
        last = next((x for x in reversed(out) if x["kind"] == "verse"), None)
        if last is None:
            raise SystemExit(f"margin numbers {[x['number'] for x in pending]} with no verse row to stand beside")
        last.setdefault("unplaced", []).extend({"number": x["number"], "src": x["src"]} for x in pending)
    return out


TURN_MIN = 40   # a row this long may wrap; a shorter one is a lyric colon of Way's own


def join_turnovers(rows: list[dict], ref_keys: list[str]) -> list[dict]:
    """A short row with no printed number of its own joins the verse row
    above when that row is long enough to have wrapped (TURN_MIN), the two
    together lie within one reference line, and the short row is no
    reference line by itself (Way prints turn-overs under their line). Way's
    short lyric cola are his colometry and stay lines of their own."""
    out: list[dict] = []
    for r in rows:
        prev = out[-1] if out and out[-1]["kind"] == "verse" else None
        if (r["kind"] == "verse" and prev is not None and r["printed"] is None and not r["strophe"]
                and not r.get("apart") and len(r["text"]) <= 20 and len(prev["text"]) >= TURN_MIN
                and prev["page"] == r["page"]):
            frag = J.key(r["text"])
            span = max(16, len(frag) + 4)
            if frag and J._in_ref(J.key(prev["text"]) + frag, ref_keys, span) and not J._in_ref_whole(frag, ref_keys):
                prev.setdefault("turnovers", []).append({"text": r["text"], "src": r["src"], "printed": None})
                prev["text"] = (prev["text"][:-1] + r["text"]) if prev["text"].endswith("-") else (prev["text"] + " " + r["text"])
                continue
        out.append(r)
    return out


def merge_antilabe(lines: list[dict], ref_keys: list[str]) -> list[dict]:
    """Join the shares of one verse that Way prints as rows under their own
    speakers. A line that opens with a new speaker joins the line before when
    both are short and together they match a reference line better than
    either alone (jebb_to_tei's test: RESUME_SCORE and 0.1 better, or 0.95);
    a third share joins the same way. On different pages the match must be
    0.95. The joined line keeps the first share's printed number; a later
    share's number, if any, is kept beside it."""
    index = J.ref_index(ref_keys)
    out: list[dict] = []
    current = None   # the speaker of the line before (a line without a name continues it)
    for x in lines:
        prev = out[-1] if out else None
        spk = x["shares"][0][0]
        before, current = current, spk or current
        if (prev is not None and spk is not None and spk != before
                and prev.get("lacuna") is None and x.get("lacuna") is None
                and len(J.key(x["text"])) < 30 and len(J.key(prev["shares"][-1][1])) < 40
                and not prev["strophe"] and not x["strophe"]):
            joined = prev["text"] + " " + x["text"]
            score = J.ref_score(joined, index)
            alone = max(J.ref_score(prev["text"], index), J.ref_score(x["text"], index))
            if prev["page"] != x["page"] and score < 0.95:
                score = 0.0
            if (score >= J.RESUME_SCORE and score >= alone + 0.1) or (score >= 0.95 and score > alone):
                prev["text"] = joined
                prev["shares"] = prev["shares"] + x["shares"]
                prev.setdefault("antilabe_rows", []).append(x["src"])
                if x["printed"] is not None:
                    prev.setdefault("printed_more", []).append(x["printed"])
                # A number on a row of its own before the share has no row
                # of its own left to go to: a checkpoint apart.
                for u in ([x["apart"]] if x.get("apart") else []) + (x.get("unplaced") or []):
                    prev.setdefault("unplaced", []).append({"number": u["number"], "src": u["src"]})
                continue
        out.append(x)
    return out


def resolve_apart(lines: list[dict], refs: dict, covers: dict) -> None:
    """A margin number the OCR set on a row of its own belongs to the verse
    row just above it or just below (the OCR puts it on either side). It goes
    to the one a reference numbers so (Murray or the TLG), else below."""
    def cands(i: int) -> set[str]:
        return {refs[x][covers[x][i][0]]["n"] for x in ("S", "T") if covers[x][i]}

    for i, line in enumerate(lines):
        for x in line.get("unplaced") or []:
            line.setdefault("detached", []).append(x["number"])
        apart = line.pop("apart", None)
        if apart is None:
            continue
        n = apart["number"]
        up = i > 0 and lines[i - 1]["src"] == apart["above"]
        if up and str(n) in cands(i - 1) and str(n) not in cands(i) and lines[i - 1]["printed"] is None:
            target, where = lines[i - 1], "above"
        else:
            target, where = line, "below" if str(n) in cands(i) else "below (no reference numbers either row so)"
        if target["printed"] is None:
            target["printed"] = n
        else:
            target.setdefault("printed_more", []).append(n)
        target["printed_apart"] = {"src": apart["src"], "placed": where}


def follow_murray_cries(lines: list[dict], ref_s: list[dict]) -> list[tuple]:
    """Murray prints a cry outside the metre as a line of its own ('ἰώ,' 96,
    then 'δύστανος …' 96a), as Way does; the alignment can fold the cry into
    the line before and letter it (95a). Where Murray's line N is the cry and
    his Na the next line, Way's two lines take N and Na. Returns the moves."""
    murray = {r["n"]: J.key(r["text"]) for r in ref_s}
    moves = []
    for i in range(len(lines) - 1):
        x, y = lines[i], lines[i + 1]
        n = y["n"]
        if not (x.get("n_how") == "lettered" and n and n.isdigit() and len(J.key(x["text"])) <= 8
                and murray.get(n) == J.key(x["text"]) and n + "a" in murray and y.get("printed") is None):
            continue
        moves.append((x["src"], x["n"], n))
        moves.append((y["src"], n, n + "a"))
        x["n"], x["n_how"] = n, "storr"
        y["n"], y["n_how"] = n + "a", "storr"
    return moves


# ------------------------------------------------------------ references
def murray_lines(slug: str) -> list[dict]:
    """Murray's Greek as the pipeline reads it (stage1_tei_greek), antilabe
    shares merged: [{n, text, parts: [ref, ...]}]."""
    sys.path.insert(0, str(ROOT / "pipeline"))
    from drama_pipeline.config import Manifest, SOURCES_DIR
    from drama_pipeline import stage1_tei_greek
    view = Manifest.load(ROOT / "manifests" / f"{slug}.yaml").for_edition(PLAYS[slug]["murray"])
    spine = stage1_tei_greek.parse_spine(SOURCES_DIR / view.data["work"]["greek_source"]["path"], view)
    return [{"n": line["ref"], "text": J.nfc(line["text"]), "parts": [p["ref"] for p in line.get("parts") or []]}
            for seg in spine["segments"] for line in seg["lines"]]


# ------------------------------------------------------------------- TEI
def murray_stanzas(slug: str) -> dict[str, str]:
    """{Murray's ref: the lyric stanza of his Perseus TEI that holds it}
    (a strophe, antistrophe, epode, mesode, or astrophic lyric div)."""
    sys.path.insert(0, str(ROOT / "pipeline"))
    from drama_pipeline.config import Manifest, SOURCES_DIR
    view = Manifest.load(ROOT / "manifests" / f"{slug}.yaml").for_edition(PLAYS[slug]["murray"])
    root = ET.parse(SOURCES_DIR / view.data["work"]["greek_source"]["path"]).getroot()
    out = {}
    for k, div in enumerate(root.iter(f"{J.TEI_NS}div")):
        if div.get("subtype") in LYRIC:
            for el in div.iter(f"{J.TEI_NS}l"):
                out[el.get("n")] = f"{div.get('subtype')} {div.get('n') or ''} #{k}"
    return out


LYRIC = {"strophe", "antistrophe", "epode", "mesode", "ephymn", "lyric"}


def write_tei(slug: str, lines: list[dict]) -> str:
    """jebb_to_tei.write_tei's body, with Way's header and leaf links (the
    OCR page index is the leaf; archive.org's page_numbers.json is off for
    these items, so it is not used), and a strophe div closed where the
    lyric ends.

    Jebb's writer leaves a div open to the next strophe mark, so the last
    stanza of an ode takes in the dialogue after it. Here a stanza closes at
    the next mark, or at a change of voice (the speaker named last, carried
    into an unlabelled stanza) whose new speech is not in the stanza of
    Murray's text that the stanza's first line aligns with ('stanza', from
    murray_stanzas): the Paedagogus at 1002 is spoken, so the antistrophe
    at 996 closes before him, while the sons' cries inside a strophe that
    Murray prints as one stanza (1271-1278) stay in it."""
    play = PLAYS[slug]
    ident = play["ident"]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<TEI xmlns="http://www.tei-c.org/ns/1.0">',
           '<teiHeader><fileDesc>',
           f'<titleStmt><title>{play["title"]}</title><author>Euripides</author><editor>A. S. Way</editor></titleStmt>',
           '<publicationStmt><p>Generated by scripts/ocr/way_to_tei.py from a Genie OCR of the scan below.</p></publicationStmt>',
           f'<sourceDesc><bibl><title>Euripides, with an English translation by Arthur S. Way (Loeb Classical Library)</title><editor>A. S. Way</editor><publisher>William Heinemann</publisher><idno type="archive.org">{ident}</idno><idno type="ocr">{escape(play["ocr"])}</idno></bibl></sourceDesc>',
           '</fileDesc></teiHeader>', '<text><body>']
    page = None
    div_open = sp_open = False
    cur_speaker = voice = div_stanza = None
    for line in lines:
        if line["page"] != page:
            page = line["page"]
            out.append(f'<pb n="{page}" facs="https://archive.org/details/{ident}/page/n{line["leaf"] - 1}"/>')
        opens = bool(line.get("strophe"))
        if opens:
            if sp_open:
                out.append("</sp>")
                sp_open = False
            if div_open:
                out.append("</div>")
            subtype, num = line["strophe"]
            out.append(f'<div type="textpart" subtype="{subtype}"' + (f' n="{num}"' if num else "") + ">")
            div_open = True
            cur_speaker = None
            div_stanza = line.get("stanza")
        shares = line["shares"]
        parts = [line["n"]] + J._share_refs(line, len(shares) - 1)
        for k, (spk, text) in enumerate(shares):
            if spk is not None and (spk != cur_speaker or k > 0 or not sp_open):
                if sp_open:
                    out.append("</sp>")
                    sp_open = False
                if (div_open and voice is not None and spk != voice and not (opens and k == 0)
                        and (div_stanza is None or line.get("stanza") != div_stanza)):
                    # The lyric has ended: a new voice, outside the stanza.
                    out.append("</div>")
                    div_open = False
                out.append(f"<sp><speaker>{escape(spk)}</speaker>")
                sp_open, cur_speaker = True, spk
            if spk is not None:
                voice = spk
            if not sp_open:
                out.append("<sp>")
                sp_open = True
            attrs = [f'n="{parts[k]}"']
            if len(shares) > 1:
                attrs.append('part="%s"' % ("I" if k == 0 else "F" if k == len(shares) - 1 else "M"))
            rend = []
            if k == 0 and line.get("printed") is not None:
                rend.append(f"margin-{line['printed']}")
            if k == 0:
                rend.extend(f"margin-{p}" for p in line.get("printed_more") or [])
                rend.extend(f"margin-apart-{p}" for p in line.get("detached") or [])
            if k == 0 and line.get("turnovers"):
                rend.append("turn")
            if rend:
                attrs.append('rend="%s"' % " ".join(rend))
            out.append(f"<l {' '.join(attrs)}>{J.to_tei_text(text)}</l>")
    if sp_open:
        out.append("</sp>")
    if div_open:
        out.append("</div>")
    out.append("</body></text></TEI>")
    return "\n".join(out) + "\n"


# -------------------------------------------------------------------- QA
def english_anchor_check(slug: str, lines: list[dict]) -> dict:
    """Way's English (the facing pages of the same OCR, head = the English
    title) prints line numbers in the margin; each must be a line of his
    Greek."""
    play = PLAYS[slug]
    title = {"medea": "MEDEA"}[slug]
    have = {x["n"] for x in lines}
    printed = []
    for leaf, ne in pages(slug):
        if strip_markup(ne[0][1]) != title:
            continue
        for _, s in ne[1:-1]:
            m = re.search(r"(?:^|\s)(\d{2,4})\s*$", strip_markup(s))
            if m:
                printed.append(m.group(1))
    missing = [n for n in printed if n not in have]
    return {"present": len(printed) - len(missing), "total": len(printed), "missing": missing}


# ------------------------------------------------------------------ main
_ABSENT = object()


@contextmanager
def lent_to_jebb(slug: str):
    """For the length of the block, jebb_to_tei reads this module's hand
    fixes and margin notes for slug, and no commentary lemmas (Way prints
    none). Every global it borrows is put back exactly as it was, an entry
    jebb_to_tei already had for slug included, on an exception too."""
    tables = [(J.NUMBER_FIXES, NUMBER_FIXES), (J.MARGIN_NOTES, MARGIN_NOTES)]
    saved = [(theirs, theirs.get(slug, _ABSENT)) for theirs, _ in tables]
    saved_lemmas = J.lemma_checkpoints
    try:
        for theirs, ours in tables:
            theirs[slug] = ours.get(slug, {})
        J.lemma_checkpoints = lambda _slug, _lines: {}
        yield
    finally:
        J.lemma_checkpoints = saved_lemmas
        for theirs, old in saved:
            if old is _ABSENT:
                theirs.pop(slug, None)
            else:
                theirs[slug] = old


def convert(slug: str, qa: bool = False) -> dict:
    counts: dict[str, int] = {}
    ref_s = murray_lines(slug)
    ref_t = J.tlg_lines(slug)
    ref_keys = [J.key(r["text"]) for r in ref_s + ref_t if r["text"]]
    rows, log, stops = extract(slug, counts)
    for r in rows:
        fix = PRINTED_FIXES.get(slug, {}).get(r["src"])
        if fix is not None and r["kind"] == "verse":
            r["printed"], r["printed_fix"] = fix
    rows = place_numbers_and_labels(rows)
    rows = join_turnovers(rows, ref_keys)
    lines = J.build_lines(rows)
    for x in lines:
        x["shares"] = [(spk, t) for spk, t in x["shares"]]
    lines = merge_antilabe(lines, ref_keys)
    refs = {"S": ref_s, "T": ref_t}
    covers = {"S": J.align(lines, ref_s), "T": J.align(lines, ref_t)}
    resolve_apart(lines, refs, covers)
    # jebb_to_tei's numbering reads its hand fixes, margin notes, and
    # commentary lemmas by play slug: this module's are lent for the call.
    with lent_to_jebb(slug):
        J.number_lines(slug, lines, refs, covers)
        cries = follow_murray_cries(lines, ref_s)
        bad = J.check_margins(slug, lines)
    stanzas = murray_stanzas(slug)
    for x in lines:
        x["stanza"] = stanzas.get(x["cand"]["S"])
    seen: dict[str, int] = {}
    dups = []
    for line in lines:
        for n in [line["n"]] + J._share_refs(line, len(line["shares"]) - 1):
            if n in seen:
                dups.append((n, seen[n], line["src"]))
            seen[n] = line["src"]
    tei = write_tei(slug, lines)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{slug}.xml").write_text(tei, encoding="utf-8")
    _write_sums()
    how = {"storr": "murray", "tlg": "tlg", "checkpoint": "checkpoint", "jebb count": "way count",
           "next free number": "next free number", "lettered": "lettered"}
    report = {
        "slug": slug, "lines": len(lines), "murray_lines": len(ref_s), "tlg_lines": len(ref_t), "log": log,
        "normalised": counts,
        "margin_checkpoints": sum((x.get("printed") is not None) + len(x.get("printed_more") or []) for x in lines),
        "unplaced_numbers": [(x["n"], u["number"], u["src"]) for x in lines for u in x.get("unplaced") or []],
        "unheaded_greek_pages": [st for st in stops if st["reason"].startswith("no running head")],
        "margin_equal": sum(1 for x in lines if x.get("margin_ok") == "equal"),
        "margin_inside": sum(1 for x in lines if x.get("margin_ok") == "inside"),
        "margin_bad": bad, "duplicate_refs": dups,
        "numbered_by": {how[h]: sum(1 for x in lines if x.get("n_how") == h) for h in how},
        "not_murray": [(x["src"], x["n"], how.get(x.get("n_how"), x.get("n_how")), x["cand"]["S"], x["text"][:40])
                       for x in lines if x.get("n_how") != "storr"],
        "printed_apart": [(x["n"], x["printed"], x["printed_apart"]["src"], x["printed_apart"]["placed"])
                          for x in lines if x.get("printed_apart")],
        "printed_fixes": [(x["n"], x["src"], x["printed_fix"]) for x in lines if x.get("printed_fix")],
        "cries": cries,
        "antilabe": [(x["n"], x["src"], x["antilabe_rows"]) for x in lines if x.get("antilabe_rows")],
        "turnovers": [(x["n"], x["src"], [t["src"] for t in x["turnovers"]]) for x in lines if x.get("turnovers")],
        "stops": [{**st, "dropped": [st["dropped"][0], st["dropped"][-1], len(st["dropped"])]} for st in stops],
        "unmet_checkpoints": [{"src": x["src"], "page": x["page"], "n": x["n"], "checkpoint": n, "kind": kind,
                               "text": x["text"][:40]} for x in lines for n, kind in x.get("unmet") or []],
        "gaps": [{"src": x["src"], "page": x["page"], "after": g["after"], "before": g["before"],
                  "missing": g["missing"], "text": x["text"][:40]} for x in lines for g in x.get("gaps") or []],
    }
    if qa:
        report["bad_chars"] = J.char_check(tei)
        report["english_anchors"] = english_anchor_check(slug, lines)
    DUMP.mkdir(parents=True, exist_ok=True)
    (DUMP / f"{slug}-lines.json").write_text(json.dumps(lines, ensure_ascii=False, indent=0), encoding="utf-8")
    return report


def _write_sums() -> None:
    rows = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(OUT.glob("*.xml"))]
    (OUT / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("play", help="play slug, or 'all'")
    ap.add_argument("--qa", action="store_true", help="also run the character and English-anchor checks")
    args = ap.parse_args(argv)
    failed = False
    for slug in list(PLAYS) if args.play == "all" else [args.play]:
        rep = convert(slug, args.qa)
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        failed |= bool(rep["margin_bad"] or rep["duplicate_refs"] or rep["unheaded_greek_pages"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
