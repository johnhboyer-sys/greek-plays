"""Clean an English-only verse OCR volume into Lindsay-style turn-text.

Morshead's Aeschylus (Archive.org DJVU): speaker names on their own line
in small caps (OCR as title-case, all-caps, or italic junk), verse below,
running heads and page numbers, italic stage directions. Not a Loeb
facing-page scan — no Greek pages to drop.

Emits ``NAME`` on its own line and verse beneath so
``stage1_turn_english._parse_lindsay_speeches`` can read it
(``format: verse-own-line``). Leading A/AN/THE are stripped because the
Lindsay parser rejects ``THE …`` speaker lines.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .bench_clean import rejoin_hyphens
from .config import BUILD_DIR, REPO_ROOT, SOURCES_DIR
from .stage1_turn_english import _split_lindsay_speaker_line


PLAY_TITLES = (
    "AGAMEMNON",
    "THE LIBATION-BEARERS",
    "THE FURIES",
    "THE SUPPLIANT MAIDENS",
    "THE PERSIANS",
    "THE SEVEN AGAINST THEBES",
    "PROMETHEUS BOUND",
    "THE PROMETHEUS BOUND",
)
PLAY_HEADING_SET = {t.upper() for t in PLAY_TITLES}

FRONT_HEADS = {
    "ARGUMENT",
    "DRAMATIS PERSONAE",
    "DRAMATIS PERSONS",
    "INTRODUCTION",
    "PREFACE",
    "CONTENTS",
    "APPENDIX",
}

STOP_HEADS = {
    "APPENDIX",
    "NOTES",
    "NOTE",
    "INTRODUCTION",
}

# Canonical names the Lindsay parser accepts (no leading THE/A/AN).
SPEAKER_CANON = {
    "WATCHMAN",
    "CHORUS",
    "CLYTEMNESTRA",
    "HERALD",
    "AGAMEMNON",
    "CASSANDRA",
    "AEGISTHUS",
    "VOICE OF AGAMEMNON",
    "VOICE OF AEGISTHUS",
    "ONE OF THE CHORUS",
    "LEADER OF THE CHORUS",
    "ORESTES",
    "ELECTRA",
    "KILISSA",
    "SLAVE",
    "PYLADES",
    "ATTENDANT",
    "PYTHIAN PRIESTESS",
    "APOLLO",
    "GHOST OF CLYTEMNESTRA",
    "GHOST",
    "ATHENA",
    "CHORUS OF FURIES",
    "CHANT",
    "DANAUS",
    "KING OF ARGOS",
    "HERALD OF AEGYPTUS",
    "SEMI-CHORUS",
    "ATOSSA",
    "MESSENGER",
    "GHOST OF DARIUS",
    "XERXES",
    "ETEOCLES",
    "SPY",
    "ANTIGONE",
    "ISMENE",
    "ANTIGONE ISMENE AND CHORUS",
    "PROMETHEUS",
    "STRENGTH",
    "HEPHAESTUS",
    "OCEANUS",
    "IO",
    "HERMES",
    "CHORUS OF CAPTIVE WOMEN",
    "CHORUS OF PERSIAN ELDERS",
    "CHORUS OF CADMEAN MAIDENS",
    "CHORUS OF MAIDENS",
    "CHORUS OF ARGIVE ELDERS",
    "FIRST HALF-CHORUS",
    "SECOND HALF-CHORUS",
    "HALF-CHORUS",
}

# Print / OCR variants → canon (applied after uppercasing and punct strip).
SPEAKER_OCR = {
    "A WATCHMAN": "WATCHMAN",
    "THE WATCHMAN": "WATCHMAN",
    "A HERALD": "HERALD",
    "THE HERALD": "HERALD",
    "ENTER HERALD": "HERALD",
    "A MESSENGER": "MESSENGER",
    "THE MESSENGER": "MESSENGER",
    "A SPY": "SPY",
    "THE SPY": "SPY",
    "AN ATTENDANT": "ATTENDANT",
    "A NURSE": "KILISSA",
    "NURSE": "KILISSA",
    "THE PYTHIAN PRIESTESS": "PYTHIAN PRIESTESS",
    "THE GHOST OF CLYTEMNESTRA": "GHOST OF CLYTEMNESTRA",
    "THE GHOST OF DARIUS": "GHOST OF DARIUS",
    "THE KING OF ARGOS": "KING OF ARGOS",
    "SEMI CHORUS": "SEMI-CHORUS",
    "SEMICHORUS": "SEMI-CHORUS",
    "FIRST HALF CHORUS": "FIRST HALF-CHORUS",
    "SECOND HALF CHORUS": "SECOND HALF-CHORUS",
    "HALF CHORUS": "HALF-CHORUS",
    "LO": "IO",
    "ID": "IO",
    "STRENGTH AND FORCE": "STRENGTH",
    "CHORUS OF THE DAUGHTERS OF DANAUS": "CHORUS",
    "CHORUS OF THE DAIIGHTEIS OF DANAUS": "CHORUS",
}

AEGISTHUS_LETTERS = {
    "AEGISTHUS",
    "EGISTHUS",
    "TEGISTHUS",
    "HIGISTHUS",
    "JEGISTHUS",
    "IEGISTHUS",
    "AEGISTHU",
}

PROMETHEUS_OCR = {
    "PROINIETHEUS",
    "IROMETHKUS",
    "PROMFTHEUS",
    "PROMETHEUS",
    "PRONIETHEUS",
    "PROMETHEVS",
}

OCEANUS_OCR = {
    "OCEANUS",
    "OCEAXUS",
    "OCEANVS",
}

PAGE_NUM_RE = re.compile(
    r"^(?:\d{1,4}|[xvi]{1,6}|[il\d]{1,4}|[\"'*]?\d{1,3}|i[o0]\d?)$",
    re.I,
)
PRINTED_BY_RE = re.compile(r"^Printed by\b", re.I)
STAGE_OPEN_RE = re.compile(r"^[\[\{]|^\(")
ENTER_RE = re.compile(r"^Enter\s+(.+)$", re.I)
HYPHEN_END_RE = re.compile(r"[A-Za-z]-$")


def collapse_spaces(line: str) -> str:
    return re.sub(r"[ \t]+", " ", line).strip()


def _fold_title_ocr(s: str) -> str:
    s = s.replace("Æ", "AE").replace("æ", "AE").replace("Œ", "OE").replace("œ", "OE")
    s = s.upper()
    s = s.replace("^E", "AE").replace("/E", "AE")
    s = s.replace("SF.VEN", "SEVEN").replace("SFVEN", "SEVEN")
    s = s.replace("THELIES", "THEBES").replace("THELI ES", "THEBES")
    s = s.replace("T^FURIES", "THE FURIES")
    s = s.replace("DRAiNIATIS", "DRAMATIS").replace("DRAINIATIS", "DRAMATIS")
    s = re.sub(r"[©®*]+", "", s)
    s = re.sub(r"^[\-–—_|.:\s]+", "", s)
    s = re.sub(r"[\-–—_|.:\s]+$", "", s)
    s = re.sub(r"[^A-Z0-9 \-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_heading(line: str) -> str:
    return _fold_title_ocr(collapse_spaces(line))


def _heading_without_page(normed: str) -> str:
    s = re.sub(r"^(?:\d+|[IVXLC]+|[IOL\d]{1,4})\s+", "", normed)
    s = re.sub(r"\s+(?:\d+|[IVXLC]+|[IOL\d]{1,4})$", "", s)
    return s.strip()


def _is_all_caps_line(line: str) -> bool:
    """Running heads and play titles are caps; speakers are title-case."""
    s = collapse_spaces(line)
    letters = [ch for ch in s if ch.isalpha()]
    if not letters:
        return False
    return not any(ch.islower() for ch in letters)


def _is_play_heading(line: str, title: str) -> bool:
    if not _is_all_caps_line(line) and not re.search(r"\d", collapse_spaces(line)):
        return False
    n = _norm_heading(line)
    want = _norm_heading(title)
    if n == want:
        return True
    if want.startswith("THE ") and n == want[4:]:
        return True
    if not want.startswith("THE ") and n == "THE " + want:
        return True
    return False


def _followed_by_front_matter(lines: list[str], i: int, window: int = 40) -> bool:
    for j in range(i + 1, min(len(lines), i + 1 + window)):
        s = _norm_heading(lines[j])
        if not s:
            continue
        if s.startswith("DRAMATIS PERSON") or s == "ARGUMENT":
            return True
        if _heading_without_page(s) in PLAY_HEADING_SET and j > i:
            return False
        if s in STOP_HEADS or PRINTED_BY_RE.match(lines[j].strip()):
            return False
    return False


def _preceded_by_front_matter(lines: list[str], i: int, window: int = 80) -> bool:
    for j in range(i - 1, max(-1, i - 1 - window), -1):
        s = _norm_heading(lines[j])
        if s.startswith("DRAMATIS PERSON") or s == "ARGUMENT":
            return True
    return False


def _followed_by_speaker(lines: list[str], i: int, window: int = 10) -> bool:
    """Body title sits immediately above the first speaker, not above verse."""
    for j in range(i + 1, min(len(lines), i + 1 + window * 3)):
        s = collapse_spaces(lines[j])
        if not s or _is_page_number(s) or _is_signature(s):
            continue
        if speaker_from_line(s):
            return True
        return False
    return False


def locate_play(
    lines: list[str],
    title: str,
    next_title: str | None = None,
    catalog: tuple[str, ...] = PLAY_TITLES,
) -> tuple[int, int]:
    want = title
    hits_front = [
        i
        for i, line in enumerate(lines)
        if _is_play_heading(line, want) and _followed_by_front_matter(lines, i)
    ]
    hits_body = [
        i
        for i, line in enumerate(lines)
        if _is_play_heading(line, want)
        and _followed_by_speaker(lines, i)
        and _preceded_by_front_matter(lines, i)
    ]
    if hits_front:
        start = hits_front[-1]
    elif hits_body:
        start = hits_body[0]
    else:
        raise ValueError(f"play title {title!r} not found (no ARGUMENT/DRAMATIS near heading)")
    end = len(lines)
    rest = [_norm_heading(t) for t in catalog if _norm_heading(t) != _norm_heading(want)]
    if next_title:
        rest = [_norm_heading(next_title)] + rest
    rest_set = set(rest)
    for i, line in enumerate(lines[start + 1 :], start + 1):
        n = _norm_heading(line)
        if n in STOP_HEADS and n != "INTRODUCTION":
            end = i
            break
        if n == "APPENDIX":
            end = i
            break
        if PRINTED_BY_RE.match(line.strip()):
            end = i
            break
        # Next-play titles are caps headings, not title-case speaker lines
        # (`Agamemnon.`) that happen to share a catalog name.
        if not _is_all_caps_line(line):
            continue
        head = _heading_without_page(n)
        if n in rest_set or head in rest_set:
            if _followed_by_front_matter(lines, i):
                end = i
                break
            nxt = ""
            for later in lines[i + 1 : i + 12]:
                if later.strip():
                    nxt = _norm_heading(later)
                    break
            if nxt == "ARGUMENT" or nxt.startswith("DRAMATIS"):
                end = i
                break
    return start, end


def _is_page_number(line: str) -> bool:
    s = collapse_spaces(line)
    if not s or len(s) > 8:
        return False
    # Io the character is title-case / ell-OCR (`lo`, `Io`, `Id`), not all-caps
    # `IO` (page 10 in the House of Atreus scan).
    if s in {"lo", "lO", "Io", "Id"}:
        return False
    if PAGE_NUM_RE.match(s):
        return True
    if re.fullmatch(r"[IVXLCDM]+S?", s, re.I):
        return True
    ocr = s.upper().translate(str.maketrans("OIL", "011"))
    if ocr.isdigit() and 1 <= len(ocr) <= 4:
        return True
    compact = re.sub(r"[^\d]", "", s)
    letters = re.sub(r"[^A-Za-z]", "", s)
    if compact and 1 <= len(compact) <= 4 and len(s) <= 6 and len(letters) <= 2:
        return True
    return False


def _is_signature(line: str) -> bool:
    s = collapse_spaces(line)
    if re.fullmatch(r"[A-Z]", s):
        return True
    # Gathered signatures / OCR crumbs (`US`, `IIS` already page-like).
    if re.fullmatch(r"[A-Z]{2,3}", s) and s not in SPEAKER_CANON:
        return True
    return False


def _is_running_head(line: str, title: str) -> bool:
    s = collapse_spaces(line)
    n = _norm_heading(s)
    if not n:
        return False
    # Speakers are title-case in this OCR; running heads are caps, often
    # glued to a page number (`62 THE PERSIANS`, `i66 PROMETHEUS BOUND`).
    letters = [ch for ch in s if ch.isalpha()]
    has_lower = any(ch.islower() for ch in letters)
    if has_lower and not re.search(r"\d", s):
        return False
    head = _heading_without_page(n)
    want = _norm_heading(title)
    alts = {want}
    if want.startswith("THE "):
        alts.add(want[4:])
    else:
        alts.add("THE " + want)
    if want in {"PROMETHEUS BOUND", "THE PROMETHEUS BOUND"}:
        alts.update({"PROMETHEUS BOUND", "THE PROMETHEUS BOUND"})
    return n in alts or head in alts


def _is_stage_direction(line: str) -> bool:
    s = collapse_spaces(line)
    if not s:
        return False
    if STAGE_OPEN_RE.match(s):
        return True
    if re.match(r"^\\?\[", s):
        return True
    if re.match(r"^\\?(Exit|Exeunt|lxeunt|Eveunt|Exetin)", s, re.I):
        return True
    if re.match(r"^(Scene|Srene|The Scene)\b", s, re.I):
        return True
    return False


def _letters_only(s: str) -> str:
    return re.sub(r"[^A-Za-z]", "", s).upper()


def _strip_speaker_tail(s: str) -> str:
    s = collapse_spaces(s)
    s = re.sub(r"\s*[\(\[\{].*$", "", s).strip()
    s = s.rstrip(".,;:").strip()
    return s


def _canon_speaker(raw: str) -> str | None:
    if not raw:
        return None
    # Io OCR: lowercase L + o, before uppercasing.
    if raw in {"lo", "lo.", "lO", "Io", "Id", "Id."}:
        return "IO"
    folded = raw.replace("Æ", "Ae").replace("æ", "ae")
    folded = folded.replace("^E", "Ae").replace("/E", "Ae").replace("jE", "Ae")
    letters = _letters_only(folded)
    if letters in AEGISTHUS_LETTERS:
        if re.search(r"VOICE", folded, re.I):
            return "VOICE OF AEGISTHUS"
        return "AEGISTHUS"
    if letters in PROMETHEUS_OCR or letters.replace("K", "C") == "PROMETHEUS":
        if "PROMETHEUS" in letters or letters in PROMETHEUS_OCR:
            return "PROMETHEUS"
    if letters.replace(" ", "") in OCEANUS_OCR or letters in OCEANUS_OCR:
        return "OCEANUS"
    if letters in {"ISMENE", "TSMENE", "ISMKNE", "ISMENA"}:
        return "ISMENE"
    u = _fold_title_ocr(folded)
    u = re.sub(r"[,.]+", " ", u)
    u = re.sub(r"\s+", " ", u).strip()
    u = u.replace("ISMKNE", "ISMENE").replace("TSMENE", "ISMENE")
    if u in SPEAKER_OCR:
        return SPEAKER_OCR[u]
    stripped = u
    for art in ("A ", "AN ", "THE "):
        if stripped.startswith(art):
            stripped = stripped[len(art) :]
            break
    if stripped in SPEAKER_OCR:
        return SPEAKER_OCR[stripped]
    if u in SPEAKER_CANON:
        return u
    if stripped in SPEAKER_CANON:
        return stripped
    if u.startswith("VOICE OF AGAMEMNON"):
        return "VOICE OF AGAMEMNON"
    if "ISMENE" in u and "ANTIGONE" in u and "CHORUS" in u:
        return "ANTIGONE ISMENE AND CHORUS"
    if u.startswith("CHORUS OF"):
        return "CHORUS"
    return None


def speaker_from_line(line: str) -> str | None:
    s = collapse_spaces(line)
    if not s or _is_signature(s):
        return None
    if _is_page_number(s):
        return None
    if _is_stage_direction(s) and not ENTER_RE.match(s):
        return None
    # Verse fragments: "slave ! —" is not a speaker. A trailing comma on a
    # long line is a wrap (`strength,`); on a short name (`Pylades,`) it is OCR.
    if re.search(r"[!?;—–]", s):
        return None
    if s.endswith(",") and len(s.split()) > 2:
        return None
    entered = ENTER_RE.match(s)
    if entered and not STAGE_OPEN_RE.match(s):
        name = _canon_speaker(_strip_speaker_tail(entered.group(1)))
        if name:
            return name
    if _is_stage_direction(s):
        return None
    stripped = _strip_speaker_tail(s)
    if not stripped:
        return None
    # Lowercase verse (`strength,`) is not a speaker. OCR may lowercase
    # only the first glyph (`iEGISTHUS`).
    if stripped.islower() and stripped not in {"lo"}:
        return None
    return _canon_speaker(stripped)


def _is_footnote_line(line: str) -> bool:
    s = collapse_spaces(line)
    return bool(
        re.match(
            r"^\d+\s+(This |These |Reading |I have |The cries |The whole of this "
            r"|The flameless |I would |In the first place |Kennedy)",
            s,
        )
    )


def _looks_like_verse(line: str) -> bool:
    s = collapse_spaces(line)
    if not s or speaker_from_line(s):
        return False
    words = s.split()
    return (len(words) >= 4 or len(s) >= 24) and any(ch.islower() for ch in s)


def _skip_front_matter(lines: list[str]) -> list[str]:
    start = 0
    for i, line in enumerate(lines):
        n = _norm_heading(line)
        if n.startswith("DRAMATIS PERSON"):
            start = i + 1
            break
    body = lines[start:]
    for i, line in enumerate(body[:160]):
        s = collapse_spaces(line)
        if re.match(r"^(Scene|Srene|The Scene)\b", s, re.I):
            body = body[i + 1 :]
            break
    for i, line in enumerate(body):
        name = speaker_from_line(line)
        if not name:
            continue
        nxt = ""
        for later in body[i + 1 :]:
            if collapse_spaces(later):
                nxt = later
                break
        if _looks_like_verse(nxt) and not speaker_from_line(nxt):
            return body[i:]
    return body


def clean_lines(lines: list[str], title: str) -> tuple[list[str], list[str], list[str]]:
    """Drop heads/pages/stage-dirs; keep speakers and verse. Return body, speakers, suspicious."""
    out: list[str] = []
    speakers: list[str] = []
    suspicious: list[str] = []
    current: str | None = None
    in_stage = False

    for raw in lines:
        s = collapse_spaces(raw)
        if not s:
            in_stage = False
            continue
        n = _norm_heading(s)
        if in_stage:
            if "]" in s or "}" in s:
                in_stage = False
            continue
        # Caps title lines are running heads, even when they coincide with a
        # character name (AGAMEMNON). Title-case `Agamemnon` is the speaker.
        if _is_running_head(s, title) or _is_page_number(s) or _is_signature(s):
            continue
        name = speaker_from_line(s)
        if name:
            current = name
            speakers.append(name)
            out.append(name)
            continue
        if n in FRONT_HEADS or n.startswith("DRAMATIS"):
            continue
        if _is_footnote_line(s):
            continue
        if greek_ratio_local(s) > 0.3:
            continue
        if _is_stage_direction(s):
            in_stage = "]" not in s and "}" not in s
            continue
        if n in STOP_HEADS:
            break
        if PRINTED_BY_RE.match(s):
            break
        # Verse. Strip a trailing stage-dir stub; rejoin dangling hyphens.
        s = re.sub(r"\s*[\[\\].*$", "", s).strip()
        if not s:
            continue
        if current is None:
            if any(ch.islower() for ch in s) and len(s.split()) >= 5:
                suspicious.append(s)
            continue
        if out and HYPHEN_END_RE.search(out[-1]) and s and s[0].isalpha() and not s.isupper():
            out[-1] = out[-1][:-1] + s
        else:
            out.append(s)
    return out, speakers, suspicious


def greek_ratio_local(text: str) -> float:
    greek = len(re.findall(r"[\u0370-\u03ff\u1f00-\u1fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    total = greek + latin
    return (greek / total) if total else 0.0


def clean_play(
    text: str,
    title: str,
    *,
    next_title: str | None = None,
) -> tuple[str, dict]:
    lines = [collapse_spaces(ln) for ln in text.splitlines()]
    start, end = locate_play(lines, title, next_title=next_title)
    slice_lines = lines[start:end]
    body_src = _skip_front_matter(slice_lines)
    body, speakers, suspicious = clean_lines(body_src, title)
    body = rejoin_hyphens(body)
    emit_title = _norm_heading(title)
    if emit_title.startswith("THE ") and title.upper() == "AGAMEMNON":
        emit_title = "AGAMEMNON"
    out_lines = [emit_title, ""]
    for line in body:
        is_spk = line in SPEAKER_CANON
        if is_spk:
            if out_lines[-1] != "":
                out_lines.append("")
            out_lines.append(line)
            continue
        out_lines.append(line)
    while out_lines and out_lines[-1] == "":
        out_lines.pop()
    out_lines.append("")
    found: list[str] = []
    seen: set[str] = set()
    for name in speakers:
        if name not in seen:
            seen.add(name)
            found.append(name)
    report = {
        "title": emit_title,
        "start_line": start,
        "end_line": end,
        "lines_kept": sum(1 for ln in out_lines if ln and ln != emit_title),
        "pages_kept": 0,
        "pages_dropped": 0,
        "speakers_found": found,
        "speaker_events": len(speakers),
        "suspicious": suspicious[:80],
        "suspicious_count": len(suspicious),
    }
    return "\n".join(out_lines), report


# --- prose-inline (Hickie Bohn 1853): English-only prose, inline `Dic.` labels.

HICKIE_TITLES = (
    "THE ACHARNIANS",
    "THE KNIGHTS",
    "THE CLOUDS",
    "THE WASPS",
    "PEACE",
    "THE PEACE",
    "THE BIRDS",
    "LYSISTRATA",
    "THE THESMOPHORIAZUSAE",
    "THE FROGS",
    "THE ECCLESIAZUSAE",
    "PLUTUS",
    "THE PLUTUS",
)
HICKIE_HEADING_SET = {t.upper() for t in HICKIE_TITLES}

# Footnote / scholia openers that are never speakers.
PROSE_NOTE_STOP = {
    "CF", "COMP", "VIDE", "SEE", "IBID", "IB", "EQUIT", "NUB", "VESP",
    "RAN", "AV", "PAC", "THESM", "ECCLES", "ACHARN", "SOPH", "AESCH",
    "DROY SEN", "DROYSEN", "FRITZSCHE", "FRAGM", "ANAB", "HIPPOL",
    "CHOEPH", "ALCEST", "ENGER", "SCHOLIAST", "WHEELWRIGHT", "MITCHELL",
    "BENTLEY", "ELMSL", "ELMSLEY", "KRUGER", "KRIIGER", "LIDD", "NOTE",
    "VOL", "PP", "ED", "ARG", "SCHOL", "INTROD", "PREF",
}

# OCR of Cho./Chorus.
CHORUS_OCR_KEYS = {
    "CHO", "CH", "CUO", "CXO", "CXOR", "CXUO", "CAO", "CHOR", "CHU",
    "CNOR", "CHQ", "C0", "CUOR", "CXU", "CH0", "CNO",
}

_PROSE_SPEAKER_RE = re.compile(
    r"^(?P<lead>[-–—'\"“”\s]*)"
    r"(?P<name>[A-Z][A-Za-zÆæŒœZz0]{1,16})"
    r"\.\s*"
    r"(?:or\s+(?P<which>Men|Wom|Women|Man|MEN|WOM)\.?\s*)?"
    r"(?P<rest>.*)$"
)
_PROSE_FULL_NAME_RE = re.compile(
    r"^(?P<name>[A-Z][A-Za-zÆæŒœZz0.][A-Za-zÆæŒœZz0.\s\-']{1,48})"
    r"(?:\s*\([^)]*\))?"
    r"\.\s*$"
)
_PROSE_OCR_KEY = str.maketrans({
    "0": "O", "1": "I", "5": "S",
    "U": "N", "R": "N", "H": "N",
    "L": "I", "T": "I", "J": "I",
    "E": "A",
    "G": "C", "Q": "C",
    "Y": "V",
    "Z": "S",
})


def _fold_ae(text: str) -> str:
    s = text.replace("Æ", "AE").replace("æ", "AE").replace("Œ", "OE").replace("œ", "OE")
    s = s.replace("CZ", "CAE").replace("Cz", "Cae").replace("cz", "cae")
    return s


def _prose_norm_title(line: str) -> str:
    s = _fold_ae(collapse_spaces(line)).upper()
    s = re.sub(r"^END OF\s+", "", s)
    s = re.sub(r"[^A-Z ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if "THESMOPHOR" in s:
        return "THE THESMOPHORIAZUSAE"
    if "ECCLESIAZ" in s:
        return "THE ECCLESIAZUSAE"
    if s in {"PEACE", "THE PEACE"}:
        return "PEACE"
    if s in {"PLUTUS", "THE PLUTUS"}:
        return "PLUTUS"
    return s


def _is_hickie_title(line: str, title: str | None = None) -> bool:
    n = _prose_norm_title(line)
    if not n:
        return False
    letters = [ch for ch in collapse_spaces(line) if ch.isalpha()]
    if letters and any(ch.islower() for ch in letters) and not re.search(r"\d", line):
        return False
    if title is not None:
        want = _prose_norm_title(title)
        return n == want or n == "THE " + want or (want.startswith("THE ") and n == want[4:])
    return n in HICKIE_HEADING_SET or n in {
        "THE THESMOPHORIAZUSAE", "THE ECCLESIAZUSAE", "PEACE", "PLUTUS",
    }


def _is_dramatis_line(line: str) -> bool:
    n = _norm_heading(line)
    return n.startswith("DRAMATIS PERSON")


def _is_argument_line(line: str) -> bool:
    n = _norm_heading(line)
    return n in {"ARGUMENT", "THE ARGUMENT"}


def _prose_running_head(line: str, title: str) -> bool:
    s = collapse_spaces(line)
    if not s:
        return False
    n = _prose_norm_title(s)
    want = _prose_norm_title(title)
    alts = {want}
    if want.startswith("THE "):
        alts.add(want[4:])
    else:
        alts.add("THE " + want)
    if n in alts:
        return True
    # `4 THE ACHARNIANS. 27—55.` / `27—55. THE ACHARNIANS. 5`
    if re.search(r"\d", s) and any(a in n for a in alts if len(a) >= 5):
        head = re.sub(r"\d+", " ", n)
        head = re.sub(r"\s+", " ", head).strip()
        if head in alts or any(a in head for a in alts):
            return True
    return False


def _prose_page_or_sig(line: str) -> bool:
    s = collapse_spaces(line)
    if not s:
        return True
    if re.fullmatch(r"\d{1,4}", s):
        return True
    if re.fullmatch(r"[A-Z]", s):
        return True
    if re.fullmatch(r"[A-Z]{1,3}\d?", s) and s not in {"WAR"}:
        return True
    return False


def _prose_footnote(line: str) -> bool:
    s = collapse_spaces(line)
    if not s:
        return False
    if greek_ratio_local(s) > 0.25:
        return True
    if re.match(r"^[0-9*'\"“”‘’†‡§¶]+[\s.]", s):
        return True
    if re.match(r"^(See |Comp\.|Cf\.|Vide |Note |Schol)", s, re.I):
        return True
    return False


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def _ocr_key(token: str) -> str:
    return _fold_ae(token).upper().translate(_PROSE_OCR_KEY)


def _canon_cast_name(raw: str) -> str:
    s = _fold_ae(raw)
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"[^A-Za-z\s\-']", " ", s)
    s = re.sub(r"\s+", " ", s).strip().upper()
    s = re.sub(r"[-']+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for art in ("A ", "AN ", "THE "):
        if s.startswith(art) and not s.startswith("THEOR"):
            # Keep THEORUS; drop a leading article on "A CHILD".
            if s.split()[0] not in {"THEORUS", "THEOR"}:
                s = s[len(art):]
            break
    return s


def parse_dramatis(lines: list[str], title: str | None = None) -> list[str]:
    """Cast names from the DRAMATIS PERSONAE block, canonical caps."""
    start = None
    for i, line in enumerate(lines):
        if _is_dramatis_line(line):
            start = i + 1
            break
    if start is None:
        return []
    names: list[str] = []
    for line in lines[start:start + 80]:
        s = collapse_spaces(line)
        if not s:
            continue
        n = _norm_heading(s)
        if n in {"SCENE", "THE ARGUMENT", "ARGUMENT"} or n.startswith("SCENE"):
            break
        if _is_argument_line(s):
            break
        if title and _is_hickie_title(s, title):
            # The play's own title can be a character (Lysistrata, Plutus).
            pass
        elif _is_hickie_title(s):
            break
        if re.match(r"^(Scene|The Scene)\b", s, re.I):
            break
        if s[:1].islower():
            continue
        head = re.split(r"[,;(]|\.\s", s, 1)[0].rstrip(".")
        canon = _canon_cast_name(head)
        letters = [ch for ch in s if ch.isalpha()]
        lower_ratio = (
            sum(ch.islower() for ch in letters) / len(letters) if letters else 0.0
        )
        if not canon and lower_ratio > 0.55 and len(s.split()) > 6:
            break
        if not canon or len(canon) < 3 or len(canon.split()) > 6:
            continue
        if canon in {"SCENE", "ARGUMENT"}:
            continue
        if any(len(w) <= 2 and w not in {"OF", "A", "AN"} for w in canon.split()):
            continue
        if (
            len(canon.split()) > 3
            and "OF" not in canon.split()
            and not canon.startswith("CHORUS")
        ):
            continue
        names.append(canon)
        alt = re.search(r"\((?:afterwards\s+)?([A-Za-zÆæ\- ,]+)\)", s, re.I)
        if alt:
            alt_canon = _canon_cast_name(alt.group(1))
            if alt_canon and len(alt_canon.split()) <= 3:
                names.append(alt_canon)
    # Unique, stable order.
    out: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _abbr_table(names: list[str]) -> dict[str, str]:
    """Map uppercase abbreviation keys to a unique dramatis name."""
    buckets: dict[str, set[str]] = {}
    for name in names:
        words = name.split()
        first = words[0]
        keys = {first, first[:3], first[:4], first[:5], first[:6]}
        if name.startswith("CHORUS"):
            keys.update({"CHO", "CHOR", "CHORUS", "CH"})
        if name.startswith("COMMITTEE"):
            keys.add("COM")
        for key in keys:
            if len(key) < 2:
                continue
            buckets.setdefault(key, set()).add(name)
    table: dict[str, str] = {}
    for key, hits in buckets.items():
        if len(hits) == 1:
            table[key] = next(iter(hits))
    return table


def expand_prose_speaker(
    token: str,
    names: list[str],
    table: dict[str, str],
    *,
    which: str | None = None,
) -> str | None:
    t = re.sub(r"[^A-Za-z]", "", _fold_ae(token)).upper()
    if not t or t in PROSE_NOTE_STOP:
        return None
    if which:
        w = which.upper()
        if w.startswith("WOM"):
            for name in names:
                if "WOM" in name and "CHORUS" in name:
                    return name
            return "CHORUS OF OLD WOMEN"
        if w.startswith("MEN") or w.startswith("MAN"):
            for name in names:
                if "MEN" in name and "CHORUS" in name:
                    return name
            return "CHORUS OF OLD MEN"
    if t in table:
        return table[t]
    hits = [n for n in names if n.startswith(t) and len(t) >= 3]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        exact = [n for n in hits if n.split()[0] == t]
        if len(exact) == 1:
            return exact[0]
        # Dem. → DEMOSTHENES not DEMUS; Demus. → DEMUS.
        return max(hits, key=lambda n: len(n.split()[0]))
    # OCR-folded prefix.
    tk = _ocr_key(t)
    folded_hits = [
        n for n in names
        if _ocr_key(n[:len(t)]) == tk and len(t) >= 3
    ]
    if len(set(folded_hits)) == 1:
        return folded_hits[0]
    fuzzy: list[str] = []
    for name in names:
        pref = re.sub(r"[^A-Z]", "", name)[: max(len(t), 3)]
        if len(t) >= 3 and _levenshtein(t, pref[:len(t)]) <= 1:
            fuzzy.append(name)
        elif len(t) >= 4 and _levenshtein(_ocr_key(t), _ocr_key(pref[:len(t)])) <= 1:
            fuzzy.append(name)
    if len(set(fuzzy)) == 1:
        return fuzzy[0]
    if t in CHORUS_OCR_KEYS or _ocr_key(t) in {_ocr_key(x) for x in CHORUS_OCR_KEYS}:
        chorus = [n for n in names if n.startswith("CHORUS")]
        if len(chorus) == 1:
            return chorus[0]
        return "CHORUS"
    return None


def _emit_speaker_name(name: str) -> str:
    """Caps name the Gutenberg `NAME. text` parser accepts."""
    if name.startswith("CHORUS OF OLD MEN"):
        return "CHORUS OF OLD MEN"
    if name.startswith("CHORUS OF OLD WOMEN"):
        return "CHORUS OF OLD WOMEN"
    if name.startswith("CHORUS"):
        return "CHORUS"
    return name


def locate_prose_play(
    lines: list[str],
    title: str,
    next_title: str | None = None,
) -> tuple[int, int]:
    want = _prose_norm_title(title)
    hits = [
        i
        for i, line in enumerate(lines)
        if _is_hickie_title(line, title) and (
            any(_is_dramatis_line(lines[j]) for j in range(i, min(len(lines), i + 20)))
        )
    ]
    if not hits:
        hits = [i for i, line in enumerate(lines) if _is_hickie_title(line, title)]
    if not hits:
        raise ValueError(f"play title {title!r} not found")
    start = hits[0]
    end = len(lines)
    next_want = _prose_norm_title(next_title) if next_title else None
    for i, line in enumerate(lines[start + 5 :], start + 5):
        s = collapse_spaces(line)
        n = _prose_norm_title(s)
        if s.upper().startswith("END OF") and want in n:
            end = i
            break
        if _is_hickie_title(line) and n != want and n != "THE " + want:
            if next_want and n != next_want and n != "THE " + next_want:
                # Another play's title; cut if dramatis follows.
                if any(_is_dramatis_line(lines[j]) for j in range(i, min(len(lines), i + 12))):
                    end = i
                    break
            elif next_want is None or n == next_want or n == "THE " + next_want:
                if any(_is_dramatis_line(lines[j]) for j in range(i, min(len(lines), i + 12))):
                    end = i
                    break
    return start, end


def _rest_is_citation(rest: str) -> bool:
    s = collapse_spaces(rest)
    if not s:
        return False
    if re.match(r"^(vs\.?|vss\.?|p\.|pp\.|ad |cf\.?|vol\.?)\b", s, re.I):
        return True
    if re.fullmatch(r"[\d.\-—–,;\s]+", s):
        return True
    return False


def clean_prose_lines(
    lines: list[str],
    title: str,
    names: list[str],
) -> tuple[list[str], list[str], list[str]]:
    table = _abbr_table(names)
    out: list[str] = []
    speakers: list[str] = []
    suspicious: list[str] = []
    current: str | None = None
    past_argument = False
    in_argument = False

    def flush_hyphen(piece: str) -> None:
        if (
            out
            and HYPHEN_END_RE.search(out[-1])
            and piece
            and piece[0].isalpha()
            and not piece.isupper()
        ):
            out[-1] = out[-1][:-1] + piece
        else:
            out.append(piece)

    for raw in lines:
        s = collapse_spaces(raw)
        if not s:
            continue
        if _is_dramatis_line(s):
            continue
        if _is_argument_line(s):
            in_argument = True
            continue
        if in_argument:
            if _is_hickie_title(s, title) or (
                past_argument is False
                and _PROSE_FULL_NAME_RE.match(s)
            ):
                in_argument = False
            else:
                if re.match(r"^(Scene|The Scene)\b", s, re.I):
                    continue
                continue
        if _is_hickie_title(s, title):
            past_argument = True
            continue
        if re.match(r"^(Scene|The Scene|\[ ?Scene)\b", s, re.I):
            continue
        if _prose_running_head(s, title) or _prose_page_or_sig(s):
            continue
        if _prose_footnote(s):
            continue
        full = _PROSE_FULL_NAME_RE.match(s)
        if full and not any(ch.islower() for ch in full.group("name")):
            canon = _canon_cast_name(full.group("name"))
            expanded = expand_prose_speaker(canon.split()[0], names, table) if canon else None
            if expanded or canon in names:
                current = _emit_speaker_name(expanded or canon)
                speakers.append(current)
                continue
        m = _PROSE_SPEAKER_RE.match(s)
        if m:
            token = m.group("name")
            rest = m.group("rest") or ""
            if _rest_is_citation(rest):
                continue
            expanded = expand_prose_speaker(
                token, names, table, which=m.group("which")
            )
            if expanded:
                current = _emit_speaker_name(expanded)
                speakers.append(current)
                rest = rest.strip()
                if rest and not _prose_footnote(rest):
                    flush_hyphen(rest) if current and out else out.append(rest) if rest else None
                    if rest and current:
                        # First speech line after a new speaker: always a new buffer line.
                        if not out or not HYPHEN_END_RE.search(out[-1] if out else ""):
                            pass
                continue
        if current is None:
            if any(ch.islower() for ch in s) and len(s.split()) >= 6:
                suspicious.append(s)
            continue
        s = re.sub(r"\s*[\[\\].*$", "", s).strip()
        if not s or _prose_footnote(s):
            continue
        flush_hyphen(s)
    return out, speakers, suspicious


def clean_play_prose(
    text: str,
    title: str,
    *,
    next_title: str | None = None,
) -> tuple[str, dict]:
    lines = [collapse_spaces(ln) for ln in text.splitlines()]
    start, end = locate_prose_play(lines, title, next_title=next_title)
    slice_lines = lines[start:end]
    names = parse_dramatis(slice_lines, title)
    tagged = _prose_tagged(slice_lines, title, names)
    found_speakers = [payload for kind, payload in tagged if kind == "speaker"]
    suspicious = [payload for kind, payload in tagged if kind == "text"][:0]
    emit_title = _prose_norm_title(title)
    emit = [emit_title, ""]
    buf_name: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf_name, buf
        if buf_name and buf:
            first, *rest = buf
            emit.append(f"{buf_name}. {first}")
            emit.extend(rest)
            emit.append("")
        buf_name = None
        buf = []

    for kind, payload in tagged:
        if kind == "speaker":
            flush()
            buf_name = payload
            buf = []
        else:
            if buf_name is None:
                continue
            if buf and HYPHEN_END_RE.search(buf[-1]) and payload[:1].isalpha():
                buf[-1] = buf[-1][:-1] + payload
            else:
                buf.append(payload)
    flush()
    while emit and emit[-1] == "":
        emit.pop()
    emit.append("")
    found: list[str] = []
    seen: set[str] = set()
    for name in found_speakers:
        if name not in seen:
            seen.add(name)
            found.append(name)
    report = {
        "title": emit_title,
        "start_line": start,
        "end_line": end,
        "lines_kept": sum(1 for ln in emit if ln and ln != emit_title),
        "pages_kept": 0,
        "pages_dropped": 0,
        "speakers_found": found,
        "speaker_events": len(found_speakers),
        "dramatis": names,
        "suspicious": suspicious[:80],
        "suspicious_count": len(suspicious),
    }
    return "\n".join(emit), report


def _prose_tagged(
    lines: list[str],
    title: str,
    names: list[str],
) -> list[tuple[str, str]]:
    """Tagged stream of ('speaker', NAME) / ('text', line)."""
    table = _abbr_table(names)
    tagged: list[tuple[str, str]] = []
    in_argument = False
    in_dramatis = False
    for raw in lines:
        s = collapse_spaces(raw)
        if not s:
            continue
        if _is_dramatis_line(s):
            in_dramatis = True
            continue
        if in_dramatis:
            if _is_argument_line(s) or re.match(
                r"^(Scene|The Scene|\[ ?Scene)\b", s, re.I
            ):
                in_dramatis = False
            elif _is_hickie_title(s) and not _is_hickie_title(s, title):
                in_dramatis = False
            else:
                continue
        if _is_argument_line(s):
            in_argument = True
            continue
        if in_argument:
            if _is_hickie_title(s, title):
                in_argument = False
                continue
            full = _PROSE_FULL_NAME_RE.match(s)
            if full:
                in_argument = False
            else:
                continue
        if _is_hickie_title(s, title):
            continue
        if re.match(r"^(Scene|The Scene|\[ ?Scene)\b", s, re.I):
            continue
        if _prose_running_head(s, title) or _prose_page_or_sig(s):
            continue
        if _prose_footnote(s):
            continue
        full = _PROSE_FULL_NAME_RE.match(s)
        if full:
            letters = full.group("name")
            if not any(ch.islower() for ch in letters) or "(" in s:
                canon = _canon_cast_name(letters)
                token = canon.split()[0] if canon else ""
                expanded = expand_prose_speaker(token, names, table) if token else None
                if expanded or canon in names:
                    tagged.append(("speaker", _emit_speaker_name(expanded or canon)))
                    continue
        ss = re.match(r"^[-–—'\"\s]*S\.\s*S\.\s*(.*)$", s)
        if ss and any("SAUSAGE" in n for n in names):
            tagged.append(("speaker", "SAUSAGE SELLER"))
            rest = (ss.group(1) or "").strip()
            if rest and not _prose_footnote(rest):
                tagged.append(("text", rest))
            continue
        m = _PROSE_SPEAKER_RE.match(s)
        if m:
            rest = (m.group("rest") or "").strip()
            if _rest_is_citation(rest):
                continue
            token = m.group("name")
            expanded = expand_prose_speaker(
                token, names, table, which=m.group("which")
            )
            if token.upper() in {"DEUVS", "DEMUS", "DEMOS"} and any(
                n == "DEMUS" for n in names
            ):
                expanded = "DEMUS"
            if (
                expanded == "DEMOSTHENES"
                and any(kind == "speaker" and payload == "DEMUS" for kind, payload in tagged)
                and token.upper() == "DEM"
            ):
                expanded = "DEMUS"
            if expanded:
                tagged.append(("speaker", _emit_speaker_name(expanded)))
                if rest and not _prose_footnote(rest):
                    tagged.append(("text", rest))
                continue
        if tagged:
            s = re.sub(r"\s*[\[\\].*$", "", s).strip()
            if s and not _prose_footnote(s):
                tagged.append(("text", s))
    return tagged


def write_clean(
    volume: Path,
    translator: str,
    play: str,
    title: str,
    *,
    next_title: str | None = None,
    out_dir: Path | None = None,
    layout: str = "verse-own-line",
) -> tuple[Path, dict]:
    text = volume.read_text(encoding="utf-8", errors="replace")
    if layout == "prose-inline":
        cleaned, report = clean_play_prose(text, title, next_title=next_title)
    else:
        cleaned, report = clean_play(text, title, next_title=next_title)
    dest_dir = out_dir or (SOURCES_DIR / "bench" / translator)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{play}.txt"
    dest.write_text(cleaned, encoding="utf-8")
    report_dir = BUILD_DIR / "bench" / translator
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{play}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        report["output"] = str(dest.relative_to(REPO_ROOT))
    except ValueError:
        report["output"] = str(dest)
    try:
        report["report"] = str(report_path.relative_to(REPO_ROOT))
    except ValueError:
        report["report"] = str(report_path)
    return dest, report


# --- Genie OCR HTML (Arrowsmith's Aristophanes: the owner's docx, converted
# `textutil -convert html` so italic runs survive as `<i>...</i>`).
#
# History Genie OCR of the owner's Fulcrum PDF purchase. Layout per paragraph
# (`<p class="p1|p2">...</p>`, one printed line each): speaker names on their
# own bare line; footers ("Aristophanes, and William Arrowsmith...", the
# e-book/DOI line, "Downloaded on behalf of Unknown Institution", a page
# number, then "---") repeat after every page; a shared line's staggered
# halves are indented with runs of regular or non-breaking spaces; footnote
# markers are a bare trailing "*"; a few mid-line indents survive as literal
# `$\qquad...$` (a LaTeX artifact of Genie's own rendering).
#
# The same fully-italic-paragraph markup carries THREE different things:
# Arrowsmith's own stage directions (prose narration -- dropped, as the
# verse-own-line format has no channel for them, same as Morshead), whole
# choral odes/invocations set in italics as sung verse, and a handful of
# emphasised one-line dialogue exclamations. Telling them apart by shape
# alone is unreliable (a stage direction and a sung line can both be a bare
# short sentence); `GENIE_DIALOGUE_OVERRIDES` is the reviewed list of
# paragraph indices (0-based, in document order over the raw `<p>` matches)
# where a fully-italic paragraph is actually dialogue and must be kept, each
# checked against the printed page image rather than guessed.

GENIE_ROSTERS: dict[str, frozenset[str]] = {
    "clouds": frozenset(
        {
            "STREPSIADES", "PHEIDIPPIDES", "XANTHIAS", "SOKRATES", "CHORUS",
            "KORYPHAIOS", "PHILOSOPHY", "SOPHISTRY", "PASIAS", "AMYNIAS",
            "STUDENT", "FIRST STUDENT", "SECOND STUDENT", "ARISTOPHANES",
            "CHAIREPHON",
        }
    ),
    "birds": frozenset(
        {
            "PISTHETAIROS", "EUELPIDES", "HOOPOE", "KORYPHAIOS", "HERAKLES",
            "CHORUS", "INFORMER", "PROMETHEUS", "POSEIDON", "IRIS",
            "MESSENGER", "PROPHET", "SANDPIPER", "METON", "KINESIAS",
            "POET", "INSPECTOR", "LEGISLATOR", "PRIEST", "DELINQUENT",
            "SENTRY", "TRIBALLOS", "HERALD",
        }
    ),
}

# Reviewed against build/arrowsmith/genie-clouds.html / genie-birds.html and
# the Fulcrum PDF page images (2026-09-11): every fully-italic paragraph in
# the play, checked one by one, that is sung verse or emphasised dialogue
# rather than narration (a plain narration paragraph is dropped by default
# and needs no entry here -- see `clean_genie_html`). This is every such
# paragraph, not just the hard-to-call ones: the cleaner has no way to keep
# a fully-italic line except by its index being listed.
GENIE_DIALOGUE_OVERRIDES: dict[str, frozenset[int]] = {
    "clouds": frozenset(
        {
            179,  # "That's it." -- Strepsiades' own aside, not a stage direction
            305,  # "Please." -- end of Strepsiades' plea to Pheidippides
            351,  # "Yes, but what are their names?"
            # the invocation to the Clouds (738-758 is one italic run; only
            # 738 itself, "He stretches out his hands to heaven and prays.",
            # is narration)
            739, 740, 741, 742, 743, 749, 750, 751, 752, 753, 754, 755,
            756, 757, 758,
            882, 884, 886, 888, 889, 891, 892,  # the parodos ode
            # Sokrates' list of a sophist's virtues, "-To wrangle -niggle..."
            1081, 1082, 1083, 1084, 1085, 1086,
            1155,  # "Yes, you can serve me up as salami!"
            1344, 1349, 1353, 1358, 1412, 1416, 1422, 1427,  # the gods' invocation ode
            # "and hard on the heels of the Levin rattled the steeds of
            # Thunder?" -- Strepsiades quotes mock-epic parody; a footnote
            # mark just outside the italics hid this from the fully-italic
            # check until that check learned to ignore a trailing note mark
            # (Codex review finding 3, 2026-09-11 -- same for every other
            # newly-visible index added below).
            1386,
            1559,  # "A duchess?"
            1664,  # "Now hence, ye Syrops of Sleep! Come hither, O Pain!"
            1788, 1797, 1801, 1806, 1811,  # Strepsiades and Sokrates' exchange
            2058,  # "No comment." -- Strepsiades' own aside
            2471,  # "Q.E.D.! This is the rubbish I mean! ..."
            # Strepsiades' mock-heroic song about his son, "Then let my loud
            # falsetto peal..."
            2685, 2686, 2687, 2688, 2689, 2690, 2691, 2692, 2693, 2694,
            2695, 2696, 2697, 2698, 2699, 2700, 2701,
            # Chorus's mocking song, "He went to school with Sokrates" (2814)
            # missed by the original review -- Codex review finding 2,
            # 2026-09-11.
            2812, 2813, 2814, 2815, 2816, 2817, 2818, 2819, 2820, 2821,
            2886, 2889, 2900,  # Pasias exchange
            # Amynias' mock-tragic archaism, "Alackaday! Woe is me! ..."
            2973, 2974, 2975, 2984, 2985, 2986, 2990, 2991, 2992, 2993,
            2994, 2995,
            3205,  # "Ouuch!"
            3254,  # "Either which?"
            3299,  # "Shearin' o' the Ram." -- the song Strepsiades' guest sang
            3317,  # "A cricket-concert!"
            3363,  # "Got it coming, do I?"
            3379,  # "Yes, to do it on the floor!"
            3452,  # "Spare the Rod and Spoil the Child?"
            3462,  # "Honor your father and mother." -- Strepsiades quotes the maxim
            3525,  # "HORSEWHIP YOUR OWN MOTHER?"
        }
    ),
    # Reviewed against build/arrowsmith/genie-birds.html and the Fulcrum PDF
    # page images (2026-09-11).
    "birds": frozenset(
        {
            668, 682, 686, 691, 694,  # the Nightingale's "Itys, Itys!" call
            # the Hoopoe's bird-call, "tio tio tio tio..."/"Toro toro toro tix..."
            729, 735, 756, 757, 758, 759, 774,
            800, 801,  # "Prithee, sir, / how is yon strange ... Bird yclept?"
            1160,  # "Viz." -- opens the Chorus's promise-list ("all shall be yours...")
            1269,  # "Older than Earth?"
            1415, 1420,  # "Yes, they pour it over you!" / "Yes, to sterilize the rot!"
            1450,  # "et cet." -- closes the Chorus's dedication list
            1600,  # "Amen, we say." -- the Chorus's prayer response
            1898, 1907, 1911, 1915, 1949, 1953, 1955, 1959, 1964,  # bird-call refrains
            # the Chorus's mocking song about the Poet, "Undressed amidst..."
            2247, 2248, 2249, 2284, 2285, 2286, 2287, 2288, 2289, 2290,
            2291, 2304, 2305, 2306, 2307, 2308, 2309, 2310, 2311,
            2312,  # "G'bye." -- the Poet's own parting word
            3029, 3030, 3031, 3032,  # Pisthetairos quotes "the poet" in mock-epic verse
            3215, 3216,  # "If I had the wings of an Eagle..."
            # Kinesias' dithyrambic song parody, "delicately wending..."
            3278, 3279, 3280, 3281, 3286, 3287, 3297, 3298,
            3323, 3324, 3325, 3330, 3341, 3342, 3343, 3344,  # same song, continued
            3363, 3364, 3365, 3372,  # the Informer's sung entrance
            3431, 3450,  # "Your words are wings?" exchange
            3841,  # "Fapple gleep." (Triballos' gibberish, a running joke)
            3849,  # "well, so do mine."
            3870, 3871,  # more Triballos gibberish
            3929,  # "I'm a bastard?"
            3988, 3989,  # more Triballos gibberish
            4085, 4092, 4098, 4133,  # "O Hymen! Hymenaios O!" refrain
            4148, 4149, 4150, 4152,  # "Alalalai! / Io! / Paion! / ... Kallinikos O!"
        }
    ),
}

# Birds prints "MESSENGER" for three Greek roles the Dover edition keeps
# distinct: the wall-building report (First Messenger, ΑΓ. Αʹ), the
# crown-bringer (the Herald, ΚΗΡΥΞ -- Arrowsmith drops the separate Herald
# label and gives his lines to a generic Messenger), and the closing
# ascension announcement (the one unlabelled ΑΓΓΕΛΟΣ at 1706, left as
# plain "MESSENGER"). Checked against build/stage1/greek_spine.json
# (2026-09-11): the three scenes fall in that order and match those three
# Greek speakers one for one.
GENIE_SPEAKER_RELABELS: dict[str, dict[int, str]] = {
    "birds": {
        # wall-building report -> First Messenger
        2748: "FIRST MESSENGER", 2753: "FIRST MESSENGER", 2757: "FIRST MESSENGER",
        2765: "FIRST MESSENGER", 2771: "FIRST MESSENGER", 2791: "FIRST MESSENGER",
        2796: "FIRST MESSENGER", 2804: "FIRST MESSENGER", 2815: "FIRST MESSENGER",
        # crown-bringer -> Herald
        3081: "HERALD", 3092: "HERALD", 3100: "HERALD",
    },
}

# Paragraphs that are stage direction in full but only PARTLY italic in the
# markup (Genie italicises the first clause of the sentence and leaves the
# rest plain), so the fully-italic rule never sees them as narration.
# Reviewed against build/arrowsmith/genie-birds.html and the Fulcrum PDF
# page images (2026-09-11): checked every paragraph in both plays that
# opens in italics and still has real text after the closing `</i>`; these
# two are the only ones that are narration rather than dialogue with an
# italicised opening word or phrase (Codex review finding 3, 2026-09-11).
GENIE_STAGE_DIRECTION_OVERRIDES: dict[str, frozenset[int]] = {
    "birds": frozenset(
        {
            2521,  # "Exit Meton. From the other side enters an Inspector,"...
            2567,  # "Enter an itinerant Legislator" reading from a huge volume of laws.
        }
    ),
}


_GENIE_TAG_RE = re.compile(r"<[^>]+>")
_GENIE_ITALIC_SPAN_RE = re.compile(r"<i>.*?</i>", re.I | re.S)
# A LaTeX spacing fragment Genie's own rendering leaves behind where the
# source used an indent: `$\qquad\qquad$` (a Clouds/Birds page's italic
# indent) and `$\hspace{18em}$` (Clouds' prose-rhetoric scene, ~2553) are
# both artifacts, never content -- and a `$\hspace{...}$` prefix on a bare
# speaker cue (`$\hspace{4em}$ SOKRATES`) hides the cue from name matching
# entirely if left in place (Codex re-review finding 2, 2026-09-11).
_GENIE_TEX_SPACING_RE = re.compile(r"\$(?:\\hspace\{[^}]*\}|\\qquad)+\$\s*")
_GENIE_PAGE_NUM_RE = re.compile(r"^\d{1,4}$")
_GENIE_NOTE_MARK_RE = re.compile(r"\*+$")
# The footer's wording OCRs inconsistently (no comma, a stray page number
# inserted mid-line, "Edited by" recast, three footer lines glued together
# with no space) -- an exact-prefix match misses variants and leaves
# publication credits in dialogue (Codex review finding 4, 2026-09-11). Any
# of these phrases appearing anywhere in the paragraph is footer, never
# genuine Aristophanes dialogue.
_GENIE_FOOTER_MARKERS = ("William Arrowsmith", "Ann Arbor", "Downloaded on behalf")


def _genie_strip_tags(s: str) -> str:
    return _GENIE_TAG_RE.sub("", s)


def _genie_is_fully_italic(inner_html: str) -> bool:
    """True if every non-blank character sits inside an `<i>` span or is a
    trailing footnote mark (a bare `*` right after the closing `</i>`,
    outside it, still means the whole line is the same sung/narrated unit --
    Codex review finding 3, 2026-09-11)."""
    if not re.search(r"<i>", inner_html, re.I):
        return False
    without = _GENIE_ITALIC_SPAN_RE.sub("", inner_html)
    remainder = _genie_strip_tags(without).strip()
    return remainder == "" or _GENIE_NOTE_MARK_RE.fullmatch(remainder) is not None


def _genie_is_footer(text: str) -> bool:
    return (
        text == "---"
        or bool(_GENIE_PAGE_NUM_RE.match(text))
        or any(marker in text for marker in _GENIE_FOOTER_MARKERS)
    )


def clean_genie_html(
    html_text: str,
    title: str,
    speakers: frozenset[str],
    *,
    dialogue_overrides: frozenset[int] = frozenset(),
    speaker_relabels: dict[int, str] | None = None,
    stage_direction_overrides: frozenset[int] = frozenset(),
) -> tuple[str, dict]:
    """Clean a History Genie docx->html OCR into verse-own-line text.

    Bounds the play at its "SCENE:" opening (after the front-matter
    "Characters of the Play" list) and its "Notes" end matter. Paragraph
    index (0-based over every ``<p class="pN">`` match, document order) is
    the key `dialogue_overrides` uses, so it stays stable for a given html
    file.

    `speaker_relabels` swaps the EMITTED name for one printed speaker cue
    (by its paragraph index) without touching the roster check: Arrowsmith
    reuses one printed label ("MESSENGER") for three Greek roles the Dover
    edition keeps distinct (First Messenger, the Herald, and the unlabelled
    Messenger at 1706) -- the alias map alone can't tell those apart since
    it maps by printed text, not by occurrence.

    `stage_direction_overrides` force-drops a paragraph by index regardless
    of how much of it is italic: a stage direction can be split across a
    partial italic run ("Exit Meton. From the other side enters an
    Inspector," dressed in a magnificent uniform.) with real, non-footnote
    text outside the `<i>` span, so the fully-italic rule below never sees
    it as narration (Codex review finding 3, 2026-09-11).
    """
    speaker_relabels = speaker_relabels or {}
    paras = re.findall(r'<p class="p\d+">(.*?)</p>', html_text, re.S)
    start = None
    for i, p in enumerate(paras):
        if _genie_strip_tags(p).strip().upper().startswith("SCENE"):
            start = i
            break
    if start is None:
        raise ValueError(f"{title}: SCENE start not found")
    end = None
    for i in range(start + 1, len(paras)):
        if _genie_strip_tags(paras[i]).strip() == "Notes":
            end = i
            break
    if end is None:
        raise ValueError(f"{title}: Notes end not found")

    # kind is "speaker" or "verse" ("" text marks a blank separator, kept
    # inline in `out` once the merge pass below is done).
    rows: list[tuple[str, str]] = []
    current: str | None = None
    speakers_found: list[str] = []
    dropped_stage = 0
    kept_lines = 0
    overrides_used = 0

    for idx in range(start, end):
        p = paras[idx]
        # Strip a TeX spacing fragment before any matching below -- a
        # speaker cue prefixed with `$\hspace{4em}$` is not `in speakers`
        # verbatim, so it would otherwise fall through as dialogue instead
        # of opening its own speech (Codex re-review finding 2, 2026-09-11).
        raw_txt = _GENIE_TEX_SPACING_RE.sub("", _genie_strip_tags(p)).strip()
        if not raw_txt or _genie_is_footer(raw_txt):
            continue
        if idx in stage_direction_overrides:
            dropped_stage += 1
            continue
        if _genie_is_fully_italic(p):
            if idx not in dialogue_overrides:
                dropped_stage += 1
                continue
            overrides_used += 1
        # A footnote asterisk sits right after the printed name (`CHORUS*`);
        # strip it before matching, or the cue isn't `in speakers` and falls
        # through to become dialogue under the previous speaker instead of
        # opening its own speech (Codex review finding 1, 2026-09-11).
        noted = _GENIE_NOTE_MARK_RE.sub("", raw_txt).strip()
        bare = noted.rstrip(".:").strip()
        if bare in speakers and noted == bare:
            if current is not None and rows and rows[-1][0] != "blank":
                rows.append(("blank", ""))
            current = speaker_relabels.get(idx, bare)
            speakers_found.append(current)
            rows.append(("speaker", current))
            continue
        text = _GENIE_TEX_SPACING_RE.sub("", p)
        text = _genie_strip_tags(text)
        text = text.replace("*", "")
        text = re.sub(r"[ \t\xa0]+", " ", text).strip()
        if not text or current is None:
            continue
        rows.append(("verse", text))
        kept_lines += 1

    # Arrowsmith sets a few dialogue phrases in caps for emphasis (a Western
    # Union telegram, a shouted announcement). A bare all-caps line with no
    # punctuation is exactly what the shared verse-own-line reader
    # (`_split_lindsay_speaker_line`) takes for a NEW speaker cue, so any
    # such "verse" row would be misread as one. The format already joins
    # consecutive verse rows of one speech with a space (no blank line
    # between them survives), so folding a risky row into its neighbour
    # changes nothing about the rendered text -- it only keeps the row from
    # standing alone where the reader would misparse it.
    def _risky(kind: str, text: str) -> bool:
        return kind == "verse" and _split_lindsay_speaker_line(text) is not None

    # Pass 1: fold a risky row backward into the previous verse row.
    merged: list[list[str]] = []
    for kind, text in rows:
        if _risky(kind, text) and merged and merged[-1][0] == "verse":
            merged[-1][1] = f"{merged[-1][1]} {text}"
            continue
        merged.append([kind, text])
    # Pass 2: anything still risky (a risky row right after a speaker cue,
    # with no earlier verse row to join) folds forward into the next row
    # instead -- same reasoning, just the other direction.
    i = 0
    while i < len(merged):
        kind, text = merged[i]
        if _risky(kind, text) and i + 1 < len(merged) and merged[i + 1][0] == "verse":
            merged[i + 1][1] = f"{text} {merged[i + 1][1]}"
            del merged[i]
            continue
        i += 1

    out = [title, ""]
    for kind, text in merged:
        out.append("" if kind == "blank" else text)

    while out and out[-1] == "":
        out.pop()
    out.append("")

    found: list[str] = []
    seen: set[str] = set()
    for name in speakers_found:
        if name not in seen:
            seen.add(name)
            found.append(name)
    report = {
        "title": title,
        "start_line": start,
        "end_line": end,
        "lines_kept": kept_lines,
        "speakers_found": found,
        "speaker_events": len(speakers_found),
        "stage_directions_dropped": dropped_stage,
        "dialogue_overrides_used": overrides_used,
        "dialogue_overrides_declared": len(dialogue_overrides),
    }
    return "\n".join(out), report


def write_clean_genie_html(
    html_path: Path,
    translator: str,
    play: str,
    title: str,
    *,
    out_dir: Path | None = None,
) -> tuple[Path, dict]:
    html_text = html_path.read_text(encoding="utf-8", errors="replace")
    speakers = GENIE_ROSTERS[play]
    overrides = GENIE_DIALOGUE_OVERRIDES.get(play, frozenset())
    relabels = GENIE_SPEAKER_RELABELS.get(play, {})
    stage_overrides = GENIE_STAGE_DIRECTION_OVERRIDES.get(play, frozenset())
    cleaned, report = clean_genie_html(
        html_text,
        title,
        speakers,
        dialogue_overrides=overrides,
        speaker_relabels=relabels,
        stage_direction_overrides=stage_overrides,
    )
    dest_dir = out_dir or (SOURCES_DIR / "bench" / translator)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{play}.txt"
    dest.write_text(cleaned, encoding="utf-8")
    report_dir = BUILD_DIR / "bench" / translator
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{play}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        report["output"] = str(dest.relative_to(REPO_ROOT))
    except ValueError:
        report["output"] = str(dest)
    return dest, report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bench_clean_verse")
    p.add_argument("--volume", required=True, type=Path)
    p.add_argument("--translator", required=True)
    p.add_argument("--play", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--next-title", default=None)
    p.add_argument(
        "--layout",
        default="verse-own-line",
        choices=("verse-own-line", "prose-inline", "genie-html"),
    )
    args = p.parse_args(argv)
    if args.layout == "genie-html":
        dest, report = write_clean_genie_html(
            args.volume, args.translator, args.play, args.title
        )
        print(f"wrote {dest}")
        print(
            f"  lines_kept={report['lines_kept']} "
            f"speakers={report['speakers_found']} events={report['speaker_events']} "
            f"stage_directions_dropped={report['stage_directions_dropped']}"
        )
        return 0
    dest, report = write_clean(
        args.volume,
        args.translator,
        args.play,
        args.title,
        next_title=args.next_title,
        layout=args.layout,
    )
    print(f"wrote {dest}")
    print(
        f"  lines_kept={report['lines_kept']} "
        f"speakers={report['speakers_found']} events={report['speaker_events']} "
        f"suspicious={report['suspicious_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
