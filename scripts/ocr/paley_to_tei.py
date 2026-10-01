#!/usr/bin/env python3
"""Paley's Euripides (Genie OCR .txt) -> drama TEI (edition-picker plan §3.1).

    pipeline/.venv/bin/python scripts/ocr/paley_to_tei.py medea [--qa]

Writes sources/ocr/paley/<play>.xml, refreshes sources/ocr/paley/SHA256SUMS,
and dumps its line records and report to build/sweeps/paley-ocr/. Run it with
the pipeline's venv: it reads the TLG text through the pipeline. The Genie
files are build/genie/editions/Paley Euripides Text 0N.txt (git-ignored).

It is jebb_to_tei.py's sibling and imports its helpers (the alignment, the
numbering, the margin check, the character check); what differs is here:

1. Pages. The OCR splits pages at '---'. Every page of a play is text (the
   Harper volumes print no notes beside the Greek); its running head
   (ΕΥΡΙΠΙΔΟΥ or the play's name, in Greek or Latin letters, with the page
   number before or after, on one row or two, or as a table row) is dropped.
   A row longer than 90 characters or mostly Latin is not verse: it is
   dropped and reported (the hypothesis, if the range ever reaches it).
2. Rows. Speaker labels open a row (ΧΟ., bold **ΤΡ.**, Latin TP. or MH.),
   with a numbered son or chorus member after them (ΠΑ. α΄.); a name on a
   row of its own (ΚΡΕΩΝ., ### ΑΙΓΕΥΣ.) opens the next speech. A label inside
   a row is an antilabe share. Paley's strophe marks stand at the row's end
   (στρ. α΄., *στρ. α'.*, [στρ. β΄., | ἀντ.). His printed line numbers come in
   five forms: after the row (space or tab), in <span style="float:right">,
   in [465] brackets, in a table's last column, and on rows of their own.
3. Numbers on rows of their own. A single number sits next to the line it
   numbers, before or after it; it goes to the neighbour the count from the
   last printed number puts it on (dialogue counts exactly), else to the
   neighbour a reference numbers so. A run of numbers after a block
   ('30 35 40 45', Medea p. 40) goes to the block's lines by the count from
   the printed number before the block. A lone digit at a page's foot is the
   printer's signature mark ('5' on p. 43), not a line number.
4. Numbering, as for Jebb (John, 2026-09-30): Paley's printed numbers
   govern; between them each line takes Murray's number (Perseus, the text
   Coleridge's English is keyed to) or the TLG's (jebb_to_tei.number_lines).
   PRINTED_FIXES moves a number the OCR set on the wrong row to the row the
   scan prints it on; every other disagreement is reported.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jebb_to_tei as J  # noqa: E402

ROOT = J.ROOT
GENIE = J.GENIE
PERSEUS = J.PERSEUS
OUT = ROOT / "sources/ocr/paley"
DUMP = ROOT / "build/sweeps/paley-ocr"

# slug: (OCR file, Perseus work (Murray's Greek, tlg0006.tlgNNN), archive.org
# id, leaf of printed page 0 (leaf = page + offset), first and last .txt line
# of the play text, the running head's play name, the TEI title)
PLAYS = {
    "medea": ("Paley Euripides Text 01.txt", "003", "euripidesexrecen01euri", 12, 1454, 3110, "ΜΗΔΕΙΑ", "Μήδεια"),
}
VOLUME = {"euripidesexrecen01euri": ("I", "1878")}

# OCR rows mended before parsing, as the scan prints them: {slug: {ocr .txt
# line: (find, replace, reason)}}.
ROW_FIXES: dict[str, dict[int, tuple[str, str, str]]] = {
    "medea": {
        # Strophe marks Paley sets on a stanza's second row, its first row
        # being full: the stanza opens a row above.
        2209: ("δώρημα κάλλιστον", "δώρημα κάλλιστον ἀντ. α΄.", "scan p. 57: the antistrophe opens with στέργοι δέ με; ἀντ. α΄. stands on its turned-over θεῶν·"),
        2210: (" *ἀντ. α'.*", "", "scan p. 57: the mark belongs to the row above"),
        2610: ("κηδεμὼν τυράννων,", "κηδεμὼν τυράννων, στρ. β΄.", "scan p. 66: the second strophe opens with σὺ δ’, ὦ τάλαν; στρ. β΄. stands on the next row"),
        2611: ("[στρ. β΄.", "", "scan p. 66: the mark belongs to the row above"),
        2616: ("τάλαινα παίδων", "τάλαινα παίδων ἀντ. β΄.", "scan p. 66: the antistrophe opens with μεταστένομαι; ἀντ. β΄. stands on the next row"),
        2617: ("[ἀντ. β΄.", "", "scan p. 66: the mark belongs to the row above"),
    },
}
# Printed numbers the OCR set on the wrong row or misread, as the scan
# prints them: {slug: {ocr .txt line: (number or None, reason)}}. A number on
# a row of its own is fixed on that row.
PRINTED_FIXES: dict[str, dict[int, tuple[int | None, str]]] = {
    "medea": {
        # Scan p. 50 (leaf 62): from 390 on, the OCR set each number one row
        # early. Paley counts one line fewer than Murray from 386 to 464.
        1929: (None, "scan p. 50: no number on ἢν μέν τις (the OCR moved 390 here)"),
        1930: (390, "scan p. 50 prints 390 against δόλῳ μέτειμι"),
        1934: (None, "scan p. 50: no number on οὐ γὰρ μὰ (the OCR moved 395 here)"),
        1935: (395, "scan p. 50 prints 395 against μάλιστα πάντων"),
        1939: (None, "scan p. 50: no number on πικρὸν δὲ κῆδος (the OCR moved 400 here)"),
        1940: (400, "scan p. 50 prints 400 against ἀλλ’ εἶα"),
        1944: (None, "scan p. 50: no number on τοῖς Σισυφείοις (the OCR moved 405 here)"),
        1945: (405, "scan p. 50 prints 405 against γεγῶσαν"),
        1964: (424, "scan p. 51 prints 424 against ὤπασε θέσπιν ἀοιδὰν (the OCR read 421)"),
        # Scan p. 69 (leaf 81): after the short row εἴτ’ ἐπὶ χρηστοῖς the OCR
        # set each number one row early, as on p. 50.
        2743: (None, "scan p. 69: no number on μοχθοῦσι (the OCR moved 1105 here)"),
        2744: (1105, "scan p. 69 prints 1105 against ἓν δὲ τὸ πάντων"),
        2748: (None, "scan p. 69: no number on χρηστοί τ’ ἐγένοντ’ (the OCR moved 1110 here)"),
        2749: (1110, "scan p. 69 prints 1110 against δαίμων οὗτος"),
        # Scan p. 55 (leaf 67): the numbers stand on rows of their own.
        2119: (560, "scan p. 55 prints 560 against καὶ μὴ σπανιζοίμεσθα (its 0 broken; the OCR read 561)"),
        2125: (565, "scan p. 55 prints 565 against εὐδαιμονοίην (the OCR read 535)"),
    },
}
# Hand numbering: {slug: {ocr .txt line: (n, reason)}} (jebb_to_tei.number_lines).
NUMBER_FIXES: dict[str, dict[int, tuple[str, str]]] = {
    "medea": {
        # Scan p. 50: Paley prints 385 against σοφαὶ μάλιστα and 390 against
        # δόλῳ μέτειμι, six lines apart, with εἶεν· on a row of its own
        # between. Four numbers for six rows: εἶεν· takes a letter (as an
        # extra-metrical cry), and so must one whole line; his count then
        # runs one below Murray's to 464 (465 again Murray's, scan p. 52).
        # Scan p. 44: Paley prints τοὺς ἔσω· as a colon of its own, the end
        # of Murray's 183, and then Murray's 183a; the letters go in order.
        1686: ("183a", "scan p. 44: τοὺς ἔσω·, a row of its own, ends Murray's 183"),
        1687: ("183b", "scan p. 44: Murray's 183a, after Paley's extra row"),
        1929: ("389a","scan p. 50: Paley's printed 385 and 390 leave four numbers for six rows; ἢν μέν τις, the row before his 390, takes the letter"),
    },
}
# Printed numbers that disagree with the numbering for a stated reason.
MARGIN_NOTES: dict[str, dict[int, str]] = {}

GREEK_RE = J.GREEK_RE
LAT2GRK = J.LAT2GRK
HEAD_GREEK = "ΕΥΡΙΠΙΔΟΥ"
PRIME = "\u02b9"   # the numeral sign (U+0374 is NFC U+02B9) the TEI writes on a numbered speaker ('ΠΑ. αʹ.')
MARKS = "΄'ʹ’`´ʹ΄"
MEMBER = re.compile(r"([α-θι][α-θ]?)\s*[%s]\s*\.?(?:\s+|$)" % MARKS)
END_STROPHE = re.compile(
    r"(?:^|\s)[\[|*]?\s*(στρ|ἀντισύστ|σύστ|ἀντ|ἐπῳδ|ἐπωδ|μεσῳδ)(?:οφή|ιστροφή|ός|ημα)?\.?\s*"
    r"(?:([α-θ])\s*[%s]?\s*\.?)?\s*\**\s*$" % MARKS)
TAGS = re.compile(r"</?(?:small|sup|sub|span|i|b|em|strong|br|center|u)\b[^>]*>")


def head_key(s: str) -> str:
    """A running-head row, markup gone, Latin lookalikes in Greek."""
    s = J.SPACE_ENT.sub(" ", s)
    s = TAGS.sub(" ", s).replace("|", " ").replace("*", "").replace("#", "")
    s = s.translate(LAT2GRK)
    s = re.sub(r"\s+\.", ".", s)
    return " ".join(s.split())


def read_head(ne: list[tuple[int, str]], play_head: str, expected: int | None) -> tuple[bool, int | None, int]:
    """(a running head was read, its page number, rows used).

    The head is ΕΥΡΙΠΙΔΟΥ or the play's name, with the page number before
    or after it on the same row or on the row before it (p. 40 '40' /
    'EYPIΠIΔOY'; p. 55 '55' / 'ΜΗΔΕΙΑ.'), or a table row with its separator
    ('74 | ΕΥΡΙΠΙΔΟΥ' / '---|---'). A bare number is the page's only where a
    head word follows it."""
    word = r"(?:%s|%s)" % (HEAD_GREEK, play_head)
    pat = re.compile(r"(\d{1,3})?\s*%s\.?(?:\s*%s\.?)?\s*(\d{1,3})?" % (word, word))
    number = None
    for k, (_, s) in enumerate(ne[:3]):
        c = head_key(s)
        if not c or re.fullmatch(r"[-:\s]+", c):
            continue
        m = pat.fullmatch(c)
        if m:
            for g in (m.group(1), m.group(2)):
                if g:
                    number = int(g)
            used = k + 1
            if used < len(ne) and re.fullmatch(r"[-:|\s]{3,}", ne[used][1].strip()):
                used += 1   # a table head's separator row
            if number is None and k > 0 and re.fullmatch(r"\d{1,3}", head_key(ne[k - 1][1])):
                number = int(head_key(ne[k - 1][1]))
            return True, number, used
        if re.fullmatch(r"\d{1,3}", c) and k == 0 and (expected is None or abs(int(c) - expected) <= 2):
            continue   # the page number, its head word on the next row
        break
    return False, None, 0


def parse_row(s: str) -> dict | None:
    """One OCR row -> {kind: verse|name|num|label, ...} or None."""
    s = J.table_text(J.nfc(s))
    if not s.strip():
        return None
    s = J.SPACE_ENT.sub(" ", s)
    s = TAGS.sub(" ", s)
    s = re.sub(r"\\\s*$", "", s)        # a markdown line break
    s = re.sub(r"^\s*>(?=\s|$)", "", s)  # a blockquote mark
    s = s.replace("\\*", "*").replace("**", "").replace("__", "").strip()
    head = s.lstrip("#").strip().replace("*", "").strip()
    g = head.translate(LAT2GRK)
    if g and J.NAME_LINE.fullmatch(g) and len(g) < 40:
        return {"kind": "name", "text": g.rstrip(".").strip()}
    if re.fullmatch(r"\d{1,4}(\s+\d{1,4})*", head):
        return {"kind": "num", "numbers": [int(x) for x in head.split()]}
    s = s.lstrip("#").strip()
    printed = strophe = None
    for _ in range(3):
        m = J.TRAIL_NUM.search(s)
        if m and printed is None and GREEK_RE.search(s[:m.start()] or ""):
            printed, s = int(m.group(1)), s[:m.start()].rstrip()
            continue
        m = END_STROPHE.search(s)
        if m and strophe is None and m.start() > 0:
            strophe = (J.SUBTYPE[m.group(1)], J.NUMERAL.get(m.group(2) or "", None))
            s = s[:m.start()].rstrip()
            continue
        break
    speaker = None
    for _ in range(3):
        s = s.lstrip()
        m = J.LEAD_SPK.match(s.translate(LAT2GRK)[:6] + s[6:]) if s[:1].isupper() else None
        if m and speaker is None:
            speaker = m.group(1).translate(LAT2GRK)
            s = s[m.end():]
            mm = MEMBER.match(s)
            if mm:   # a numbered son or chorus member, 'ΠΑ. α΄.'
                speaker, s = f"{speaker} {mm.group(1)}{PRIME}.", s[mm.end():]
            continue
        mm = MEMBER.match(s)
        if mm and speaker is None and len(s) > mm.end():   # a chorus member alone, 'α΄.'
            speaker, s = f"{mm.group(1)}{PRIME}.", s[mm.end():]
            continue
        m = J.STROPHE.match(s)
        if m and strophe is None:
            strophe = (J.SUBTYPE[m.group(2)], J.NUMERAL.get(m.group(3) or "", None))
            s = s[m.end():]
            continue
        break
    if re.fullmatch(r"[*\s]+", s) and "*" in s:
        return {"kind": "verse", "text": "", "lacuna": "* * *", "printed": printed, "colon": None,
                "strophe": strophe, "speaker": speaker, "turn": False}
    s = s.replace("*", "")   # the OCR's italic marks; Paley prints no asterisk
    s = s.replace("˙", "·").replace("ϐ", "β")
    s = re.sub(r"([᾿῾῍-῏῝-῟][̀́͂]?)([ΑΕΗΙΟΥΩ])",
               lambda m: J.nfc(m.group(2) + J.unicodedata.normalize("NFD", m.group(1))
                               .replace("᾿", "̓").replace("῾", "̔")), s)
    s = re.sub("[᾿᾽ʼ'‘]", "’", s)
    s = re.sub(r"\S+", lambda t: J._greek_lookalikes(t.group(0)) if GREEK_RE.search(t.group(0)) else t.group(0), s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s and strophe and not speaker:
        return {"kind": "label", "strophe": strophe}
    if not s and speaker:
        return {"kind": "name", "text": speaker}
    return {"kind": "verse", "text": s, "printed": printed, "colon": None, "strophe": strophe,
            "speaker": speaker, "turn": False}


def stop_reason(row: str) -> str | None:
    p = J.plain(J.table_text(row))
    if len(p) > 90:
        return "row over 90 characters"
    letters = [c for c in p if c.isalpha()]
    if len(letters) >= 10 and J.greek_share(p) < 0.5:
        return "mostly Latin letters"
    return None


def extract(slug: str) -> tuple[list[dict], list[str], list[dict]]:
    """Rows of the Greek text ({kind, src, page, ...}), the page log, and
    every dropped row."""
    fname, _, _, _, first, last, play_head, _ = PLAYS[slug]
    lines = (GENIE / fname).read_text(encoding="utf-8").split("\n")
    fixes = ROW_FIXES.get(slug, {})
    printed_fixes = PRINTED_FIXES.get(slug, {})
    rows: list[dict] = []
    log: list[str] = []
    dropped: list[dict] = []
    pages = []
    for pg in J.pages_of(lines, first, last):
        ne = [(i, s) for i, s in pg if s.strip()]
        if ne:
            pages.append(ne)
    last_page = None
    for k, ne in enumerate(pages):
        expected = last_page + 1 if last_page else None
        head, number, used = read_head(ne, play_head, expected)
        if not head:
            log.append(f"page at .txt {ne[0][0]}: no running head read ({ne[0][1][:30]!r})")
        if number is None:
            if expected is not None:
                number = expected
            else:   # the play's first page: the next page's number less one
                nxt = read_head(pages[k + 1], play_head, None)[1] if k + 1 < len(pages) else None
                number = nxt - 1 if nxt else None
            log.append(f"page at .txt {ne[0][0]}: no page number read, inferred {number}")
        elif expected is not None and number != expected:
            log.append(f"page at .txt {ne[0][0]}: page {number} follows {last_page}")
        last_page = number
        body = ne[used:]
        for j, (i, s) in enumerate(body):
            if i in fixes:
                find, replace, _ = fixes[i]
                assert find in s, (i, find)
                s = s.replace(find, replace, 1)
            reason = stop_reason(s)
            if reason:
                dropped.append({"src": i, "page": number, "reason": reason, "text": J.plain(s)[:40]})
                continue
            row = parse_row(s)
            if row is None:
                continue
            row.update(src=i, page=number)
            if row["kind"] == "num" and j == len(body) - 1 and len(row["numbers"]) == 1 and row["numbers"][0] < 20:
                dropped.append({"src": i, "page": number, "reason": "signature mark at the page's foot",
                                "text": str(row["numbers"][0])})
                continue
            if i in printed_fixes:
                value, why = printed_fixes[i]
                if row["kind"] == "num":
                    row["numbers"] = [value] if value is not None else []
                else:
                    row["printed"] = value
                row["printed_fix"] = why
            rows.append(row)
    return rows, log, dropped


def build_lines(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Rows -> logical lines (speakers, strophe labels, antilabe shares), and
    the numbers printed on rows of their own: [{at, numbers, src, page}],
    'at' the index of the line after them."""
    lines: list[dict] = []
    runs: list[dict] = []
    pending_name = pending_strophe = None
    for r in rows:
        if r["kind"] == "name":
            pending_name = r["text"]
            continue
        if r["kind"] == "label":
            pending_strophe = r["strophe"]
            continue
        if r["kind"] == "num":
            if not r["numbers"]:
                continue
            if runs and runs[-1]["at"] == len(lines) and runs[-1]["page"] == r["page"]:
                # numbers on consecutive rows of their own: one run
                runs[-1]["numbers"] += r["numbers"]
                runs[-1]["srcs"].append(r["src"])
            else:
                runs.append({"at": len(lines), "numbers": list(r["numbers"]), "src": r["src"], "srcs": [r["src"]],
                             "page": r["page"], "fix": r.get("printed_fix")})
            continue
        if pending_strophe and not r["strophe"]:
            r["strophe"] = pending_strophe
        pending_strophe = None
        spk = r["speaker"] or pending_name
        pending_name = None
        shares = J.split_shares(r["text"], spk) if r.get("lacuna") is None else [(spk, "")]
        lines.append({**r, "shares": shares or [(spk, "")]})
    return lines, runs


def attach_runs(lines: list[dict], runs: list[dict], refs: dict, covers: dict) -> list[dict]:
    """Give each number printed on a row of its own to the line it numbers.

    A run of several numbers follows the block it numbers: each number N
    goes to the line the count from the printed number before the block
    reaches (dialogue counts exactly). A single number stands beside its
    line: it goes to the neighbour (before or after) the count reaches,
    else to the neighbour whose reference number is N. A number neither
    rule places stays apart (rend margin-apart-N), checked against its page.
    Returns the report: one entry per number."""
    def ref_n(i: int) -> set[int]:
        out = set()
        for x in ("S", "T"):
            cov = covers[x][i]
            if cov:
                out.add(J._num(refs[x][cov[0]]["n"])[0])
        return out

    report = []
    for run in runs:
        at = run["at"]
        # the last printed number before the run (on its line or attached)
        q = next((k for k in range(at - 1, -1, -1) if lines[k].get("printed") is not None), None)
        P = lines[q]["printed"] if q is not None else None
        for N in run["numbers"]:
            target, how = None, None
            if P is not None and N > P:
                idx = q + (N - P)
                if len(run["numbers"]) > 1:
                    if q < idx < at and lines[idx]["page"] == run["page"]:
                        target, how = idx, "count from the number before the block"
                elif idx in (at - 1, at) and idx < len(lines):
                    target, how = idx, "count from the number before"
            if target is None and len(run["numbers"]) == 1:
                hits = [k for k in (at - 1, at) if 0 <= k < len(lines) and N in ref_n(k)]
                if len(hits) == 1:
                    target, how = hits[0], "the neighbour a reference numbers so"
            entry = {"src": run["src"], "page": run["page"], "number": N, "how": how}
            if run.get("fix"):
                entry["fix"] = run["fix"]
            if target is None or lines[target].get("printed") is not None:
                host = lines[at - 1] if at > 0 else lines[0]
                host.setdefault("detached", []).append(N)
                entry.update(line=None, how="left apart")
            else:
                lines[target]["printed"] = N
                lines[target]["printed_from_row"] = run["src"]
                entry["line"] = lines[target]["text"][:40]
            report.append(entry)
    return report


def count_breaks(lines: list[dict]) -> list[dict]:
    """Each pair of consecutive printed numbers whose line count disagrees:
    where the OCR may have set a number on the wrong row (the scan queue),
    or Paley counts a line otherwise than he prints it."""
    marks = [(i, x["printed"]) for i, x in enumerate(lines) if x.get("printed") is not None]
    out = []
    for (i, a), (j, b) in zip(marks, marks[1:]):
        if b - a != j - i:
            lyric = any(lines[k].get("strophe") or len(J.key(lines[k]["text"])) < 22 for k in range(i, j + 1))
            out.append({"from": a, "to": b, "rows": j - i, "pages": sorted({lines[i]["page"], lines[j]["page"]}),
                        "lyric": lyric, "src": [lines[i]["src"], lines[j]["src"]], "text": lines[j]["text"][:40]})
    return out


def perseus_lines(path: Path) -> list[dict]:
    """A Perseus Greek play's lines, antilabe shares merged: [{n, text, parts}]."""
    root = ET.parse(path).getroot()
    out: list[dict] = []
    for el in root.find(f".//{J.TEI_NS}body").iter(f"{J.TEI_NS}l"):
        if el.get("style") == "hidden" or el.get("n") in (None, "0"):
            continue
        text = J.nfc(J._tei_text(el))
        if el.get("part") in ("M", "F") and out:
            out[-1]["text"] += " " + text
            out[-1]["parts"].append(el.get("n"))
        else:
            out.append({"n": el.get("n"), "text": text, "parts": []})
    return out


def number(slug: str, lines: list[dict], refs: dict, covers: dict) -> list[dict]:
    """jebb_to_tei.number_lines and check_margins over Paley's lines.

    Those read their hand fixes from jebb_to_tei's own tables, keyed by
    slug, and Jebb's commentary lemmas from his OCR. Paley's volumes print
    no commentary, so the lemma checkpoints are none; the fixes are this
    module's. Both are lent for the call and taken back after it."""
    saved = J.lemma_checkpoints
    J.NUMBER_FIXES[slug] = NUMBER_FIXES.get(slug, {})
    J.MARGIN_NOTES[slug] = MARGIN_NOTES.get(slug, {})
    J.lemma_checkpoints = lambda _slug, _lines: {}
    try:
        J.number_lines(slug, lines, refs, covers)
        return J.check_margins(slug, lines)
    finally:
        J.lemma_checkpoints = saved
        J.NUMBER_FIXES.pop(slug, None)
        J.MARGIN_NOTES.pop(slug, None)


# ------------------------------------------------------------------- TEI
def write_tei(slug: str, lines: list[dict]) -> str:
    """The §3.1 TEI. Copied from jebb_to_tei.write_tei, whose header and
    titles are Jebb's; the body is the same."""
    fname, _, ident, offset, _, _, _, title = PLAYS[slug]
    vol, year = VOLUME[ident]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<TEI xmlns="http://www.tei-c.org/ns/1.0">',
           '<teiHeader><fileDesc>',
           f'<titleStmt><title>{title}</title><author>Euripides</author><editor>F. A. Paley</editor></titleStmt>',
           '<publicationStmt><p>Generated by scripts/ocr/paley_to_tei.py from a Genie OCR of the scan below.</p></publicationStmt>',
           f'<sourceDesc><bibl><title>Euripides ex recensione Frederici A. Paley, vol. {vol}</title><editor>F. A. Paley</editor>'
           f'<publisher>Harper &amp; Brothers</publisher><pubPlace>New York</pubPlace><date>{year}</date>'
           f'<idno type="archive.org">{ident}</idno><idno type="ocr">{escape(fname)}</idno></bibl></sourceDesc>',
           '</fileDesc></teiHeader>', '<text><body>']
    page = None
    div_open = sp_open = False
    cur_speaker = None
    for line in lines:
        if line["page"] != page:
            page = line["page"]
            out.append(f'<pb n="{page}" facs="https://archive.org/details/{ident}/page/n{page + offset - 1}"/>')
        if line.get("strophe"):
            if sp_open:
                out.append("</sp>")
                sp_open = False
            if div_open:
                out.append("</div>")
            subtype, num = line["strophe"]
            out.append(f'<div type="textpart" subtype="{subtype}"' + (f' n="{num}"' if num else "") + ">")
            div_open = True
            cur_speaker = None
        shares = line["shares"]
        parts = [line["n"]] + J._share_refs(line, len(shares) - 1)
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
            if k == 0 and line.get("printed") is not None:
                rend.append(f"margin-{line['printed']}")
            if k == 0:
                rend.extend(f"margin-apart-{p}" for p in line.get("detached") or [])
            if rend:
                attrs.append('rend="%s"' % " ".join(rend))
            if line.get("lacuna") is not None:
                out.append(f"<l {' '.join(attrs)}><gap reason=\"lost\" rend=\"{escape(line['lacuna'])}\"/></l>")
            else:
                out.append(f"<l {' '.join(attrs)}>{J.to_tei_text(text)}</l>")
    if sp_open:
        out.append("</sp>")
    if div_open:
        out.append("</div>")
    out.append("</body></text></TEI>")
    return "\n".join(out) + "\n"


# -------------------------------------------------------------------- QA
def english_anchors(perseus_work: str, lines: list[dict]) -> dict:
    """Coleridge's Perseus anchors (Murray's numbers) found as refs of
    Paley's Greek, before any re-keying."""
    text = (PERSEUS / f"tlg0006.tlg{perseus_work}.perseus-eng2.xml").read_text(encoding="utf-8")
    anchors = [a for a in re.findall(r'<l [^>]*\bn="([^"]+)"', text) if a != "0"]
    have = set()
    for line in lines:
        have.add(line["n"])
        have.update(J._share_refs(line, len(line["shares"]) - 1))
    missing = [a for a in anchors if a not in have and re.sub(r"[a-z]+$", "", a) not in have]
    return {"total": len(anchors), "present": len(anchors) - len(missing), "missing": missing}


def convert(slug: str, qa: bool = False) -> dict:
    fname, perseus_work, ident, _, first, last, _, _ = PLAYS[slug]
    murray = perseus_lines(PERSEUS / f"tlg0006.tlg{perseus_work}.perseus-grc2.xml")
    tlg = J.tlg_lines(slug)
    rows, log, dropped = extract(slug)
    lines, runs = build_lines(rows)
    refs = {"S": murray, "T": tlg}
    covers = {"S": J.align(lines, murray), "T": J.align(lines, tlg)}
    attached = attach_runs(lines, runs, refs, covers)
    breaks = count_breaks(lines)
    bad = number(slug, lines, refs, covers)
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
    how = Counter("fix" if x["n_how"].startswith("fix") else x["n_how"] for x in lines)
    report = {
        "slug": slug, "lines": len(lines), "murray_lines": len(murray), "log": log, "dropped": dropped,
        "margin_checkpoints": sum(x.get("printed") is not None for x in lines),
        "margin_equal": sum(1 for x in lines if x.get("margin_ok") == "equal"),
        "margin_inside": sum(1 for x in lines if x.get("margin_ok") == "inside"),
        "margin_noted": sum(1 for x in lines if (x.get("margin_ok") or "").startswith("noted")),
        "margin_bad": bad, "duplicate_refs": dups, "numbered_by": dict(how),
        "printed_not_murray": [{"src": x["src"], "page": x["page"], "printed": x["printed"], "n": x["n"],
                                "murray": x["cand"]["S"], "text": x["text"][:40]}
                               for x in lines if x.get("printed") is not None and x["cand"]["S"] != str(x["printed"])],
        "not_murray": [(x["src"], x["n"], x.get("n_how"), x["cand"]["S"], x["text"][:40])
                       for x in lines if x.get("n_how") != "storr"],
        "runs": attached, "count_breaks": breaks,
        "unmet_checkpoints": [{"src": x["src"], "page": x["page"], "n": x["n"], "checkpoint": n, "kind": kind,
                               "text": x["text"][:40]} for x in lines for n, kind in x.get("unmet") or []],
        "gaps": [{"src": x["src"], "page": x["page"], "after": g["after"], "before": g["before"],
                  "missing": g["missing"], "text": x["text"][:40]} for x in lines for g in x.get("gaps") or []],
        "fix_conflicts": [{"src": x["src"], "fix": x["n"], "checkpoint": n, "kind": kind}
                          for x in lines for n, kind in x.get("fix_conflicts") or []],
    }
    if qa:
        report["bad_chars"] = J.char_check(tei)
        report["english_anchors"] = english_anchors(perseus_work, lines)
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
    slugs = list(PLAYS) if args.play == "all" else [args.play]
    failed = False
    for slug in slugs:
        rep = convert(slug, args.qa)
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        failed |= bool(rep["margin_bad"] or rep["duplicate_refs"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
