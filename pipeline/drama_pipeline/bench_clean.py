"""Clean a Loeb-OCR facing-page volume into turn-text for the bench.

Locates one play by its title heading (and the next play's heading), drops
mostly-Greek pages, strips running heads / page numbers / marginal line
numbers, rejoins hyphenated breaks, and writes speaker lines as
``NAME. text`` so ``stage1_turn_english`` can parse them.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .config import BUILD_DIR, REPO_ROOT, SOURCES_DIR


GREEK_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
LATIN_RE = re.compile(r"[A-Za-z]")
PAGE_NUM_RE = re.compile(r"^\d{1,4}$")
TRAILING_LINENUM_RE = re.compile(r"\s+\d{1,4}$")
VOL_SIG_RE = re.compile(r"^VOL\b", re.I)
SIGNATURE_RE = re.compile(r"^[A-Z](?:[\s.]+[A-Z]){1,4}$")
SHORT_GARBAGE = {
    "STS", "OER", "VOR", "GO", "G0", "BB", "DD", "AA", "EE", "LOL",
    "IOI", "LTS", "OI",
}
ODD_GARBAGE = {"“I", "} I", "a,", "\\!"}
STAGE_DIR_RE = re.compile(
    r"^[|.'\"\s]*\[?\s*(?:enter|erter|enfer|re-enter|exit|exeunt|lxeunt|eveunt|"
    r"fail|hatt|χε|before the palace)",
    re.I,
)
PAREN_ONLY_RE = re.compile(r"^\([^)]*\)\.?$")
CHORUS_MARK_RE = re.compile(
    r"\s*\((?:Str\.|Ant\.|Ep\.|Epode)[^)]*\)\s*",
    re.I,
)
SPEAKER_NAME_RE = re.compile(
    r"^[A-Z][A-Z0-9'’\-]*(?:\s+(?:AND\s+)?(?:[A-Z][A-Z0-9'’\-]*|[12]))*$"
)
LEADING_JUNK_RE = re.compile(r"^[\|\\./:{}\[\]\-–—ὴἢ᾿°'@®*_\s]+")
TRAILING_JUNK_RE = re.compile(r"[\|\\>\-–—'’\s]+$")
END_VOL_RE = re.compile(r"^END OF VOL", re.I)

# Headings that start a play when followed by ARGUMENT / DRAMATIS PERSONAE.
DEFAULT_PLAY_TITLES = (
    "THE KING",
    "OEDIPUS THE KING",
    "OEDIPUS AT COLONUS",
    "ANTIGONE",
    "AJAX",
    "ELECTRA",
    "TRACHINIAE",
    "THE TRACHINIAN WOMEN",
    "PHILOCTETES",
)
PLAY_HEADING_SET = {title.upper() for title in DEFAULT_PLAY_TITLES}

# OCR of Greek running heads / sigla — never English speakers.
GREEK_HEAD_OCR = {
    "ANTITONH",
    "ANTIFONH",
    "ANTIVONH",
    "ANTICVONH",
    "ANTILONH",
    "KPEQN",
    "AIMON",
    "AIMQN",
    "ISMHNH",
    "I3MHNH",
    "TEIPESIAS",
    "AITEAOS",
    "YAAE",
    "OIAINOTS",
    "OIAINOYS",
    "OIAITIOYS",
    "O1AINOTS",
    "OIAIMIOYS",
    "OIAITIOTS",
    "OIAINOYTS",
    "AIAS",
    "ATAS",
    "AIA",
    "ALAS",
    "TEKMHS3A",
    "HAEKTPA",
    "OPESTHS",
    "XOPOS",
    "AITIZOO3",
    "TPAXINIAI",
    "TPAXINIAT",
    "AHIANEIPA",
    "TPOSOS",
    "HPAKAHS",
    "SIAOKTHTHS",
    "NEONTOAEMOS",
    "NEONTOAEMOZ",
    "IAOKTHTHS",
    "TATA",
    "AIXAS",
    "TPAXINIAL",
    "IEPETS",
    "OIAINMOYS",
    "OIATMOY>",
    "IAOKTHTHS",
}

RUNNING_HEAD_OCR = {
    "OEDIPUS AT CQLONUS",
    "OEDIPUS AT COLONUS",
    "OEDIPUS AT GOLONUS",
    "OEDIPUS ΑἹ COQLONUS",
    "TRACHINIAR",
}

OCR_SPEAKER_FIXES = {
    "ORDIPUS": "OEDIPUS",
    "TECMESS A": "TECMESSA",
    "CLY TEMNESTRA": "CLYTEMNESTRA",
    "CH RYSOTHEMIS": "CHRYSOTHEMIS",
    "CHRYSOTHUEMIS": "CHRYSOTHEMIS",
    "KLECTRA": "ELECTRA",
    "DETANIRA": "DEIANIRA",
    "LICH AS": "LICHAS",
    "E DEIANIRA": "DEIANIRA",
    "HY LLUS": "HYLLUS",
    "HER ACLES": "HERACLES",
    "AGED SFRVANT": "AGED SERVANT",
    "DRFIANIRA": "DEIANIRA",
    "SMENE": "ISMENE",
    "UEDIPUS": "OEDIPUS",
    "TECMESS.AA": "TECMESSA",
    "H¥YLLUS": "HYLLUS",
    "OEDIPUS _": "OEDIPUS",
    "OEDIPUS ,": "OEDIPUS",
    "CHORUS ,": "CHORUS",
    "ISMENE ;": "ISMENE",
}

NOT_SPEAKERS = {
    "ARGUMENT",
    "DRAMATIS PERSONAE",
    "SOPHOCLES",
    "INTRODUCTION",
    "CONTENTS",
    "SCENE",
    "THE LOEB CLASSICAL LIBRARY",
    "VOR",
    "MSS",
    "M SS",
    "MAS",
} | GREEK_HEAD_OCR

GREEK_HEAD_RE = re.compile(
    r"^(ANTITONH|ANTIFONH|ANTIVONH|ANTICVONH|ANTILONH|ΑΝΤΙΓΟΝΗ|"
    r"OIAI[NMT]OYS?|ΟἸΔΙΠΟΥΣ|SOPHOCLES)\b",
    re.I,
)


def greek_ratio(text: str) -> float:
    greek = len(GREEK_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    total = greek + latin
    if not total:
        return 0.0
    return greek / total


def _norm_heading(line: str) -> str:
    s = line.strip()
    s = re.sub(r"^[\-–—_|.:\s]+", "", s)
    s = re.sub(r"[\-–—_|.:\s]+$", "", s)
    s = re.sub(r"[\-–—_|.~]+", " ", s)
    return re.sub(r"\s+", " ", s).upper()


def _is_play_heading(line: str, title: str) -> bool:
    return _norm_heading(line) == title.upper()


def _followed_by_front_matter(lines: list[str], i: int, window: int = 40) -> bool:
    for j in range(i + 1, min(len(lines), i + 1 + window)):
        s = lines[j].strip().upper()
        if s in {"ARGUMENT", "DRAMATIS PERSONAE"}:
            return True
        # A running head at the end of one play can sit within the look-ahead
        # window of the next play's ARGUMENT. Do not mistake it for a title.
        if _norm_heading(lines[j]) in PLAY_HEADING_SET:
            return False
        if s.startswith("END OF VOL"):
            return False
    return False


def _preceded_by_front_matter(lines: list[str], i: int, window: int = 120) -> bool:
    """Recognize a first running head when OCR omitted the title page."""
    for j in range(i - 1, max(-1, i - 1 - window), -1):
        if lines[j].strip().upper() == "DRAMATIS PERSONAE":
            return True
    return False


def _front_matter_start_before(lines: list[str], i: int, window: int = 220) -> int:
    """Return the first ARGUMENT page tied to a later cast/body heading."""
    arguments = [
        j
        for j in range(max(0, i - window), i)
        if lines[j].strip().upper() == "ARGUMENT"
    ]
    return arguments[0] if arguments else i


def locate_play(
    lines: list[str],
    title: str,
    next_title: str | None = None,
    catalog: tuple[str, ...] = DEFAULT_PLAY_TITLES,
) -> tuple[int, int]:
    """Return ``[start, end)`` line indices of ``title`` inside ``lines``."""
    want = title.upper()
    hits = [
        i
        for i, line in enumerate(lines)
        if _is_play_heading(line, want) and _followed_by_front_matter(lines, i)
    ]
    if not hits:
        # Volume I has no OCR text for the Oedipus at Colonus title page.
        # Its first English running head follows the cast and is a safe start.
        hits = [
            i
            for i, line in enumerate(lines)
            if _is_play_heading(line, want) and _preceded_by_front_matter(lines, i)
        ]
    if not hits:
        raise ValueError(f"play title {title!r} not found (no ARGUMENT/DRAMATIS after heading)")
    start = hits[-1]
    end = len(lines)
    nxt = next_title.upper() if next_title else None
    if nxt is None:
        rest = [t for t in catalog if t.upper() != want]
        # Next catalog title after this start, if it too is a play heading.
        later: list[tuple[int, str]] = []
        for i, line in enumerate(lines[start + 1 :], start + 1):
            head = _norm_heading(line)
            if head in {t.upper() for t in rest} and _followed_by_front_matter(lines, i):
                later.append((i, head))
                break
        if later:
            end = later[0][0]
        else:
            for i, line in enumerate(lines[start + 1 :], start + 1):
                if END_VOL_RE.match(line.strip()):
                    end = i + 1  # keep the end marker as a stop
                    break
    else:
        for i, line in enumerate(lines[start + 1 :], start + 1):
            if not _is_play_heading(line, nxt):
                continue
            if _followed_by_front_matter(lines, i):
                end = i
                break
            if _preceded_by_front_matter(lines, i):
                end = _front_matter_start_before(lines, i)
                break
    return start, end


def _is_page_number(line: str) -> bool:
    s = line.strip()
    if PAGE_NUM_RE.match(s):
        return True
    # OCR: "3%" "314 " with junk
    compact = re.sub(r"[^\d]", "", s)
    return bool(compact) and compact == re.sub(r"\D", "", s) and 1 <= len(compact) <= 4 and len(s) <= 6


def _is_greek_running_head(line: str) -> bool:
    s = _norm_heading(line)
    if s in GREEK_HEAD_OCR:
        return True
    return bool(GREEK_HEAD_RE.match(s))


def split_pages(lines: list[str], title: str = "") -> list[list[str]]:
    """Split on page numbers, Greek heads, and English after a Greek page."""
    pages: list[list[str]] = []
    cur: list[str] = []
    for line in lines:
        if cur and _is_greek_running_head(line):
            pages.append(cur)
            cur = [line]
            continue
        if (
            cur
            and _page_is_greek(cur)
            and line.strip()
            and (
                _is_running_head(line, title)
                or _speaker_candidate(line)[0] is not None
            )
        ):
            pages.append(cur)
            cur = [line]
            continue
        cur.append(line)
        if _is_page_number(line):
            pages.append(cur)
            cur = []
    if cur:
        pages.append(cur)
    return pages


def _page_is_greek(page: list[str], threshold: float = 0.3) -> bool:
    return greek_ratio("\n".join(page)) > threshold


def _is_running_head(line: str, title: str) -> bool:
    s = _norm_heading(line)
    if not s:
        return False
    if s == title.upper() or s == "SOPHOCLES":
        return True
    if title.upper() == "THE KING" and s == "OEDIPUS THE KING":
        return True
    if s in RUNNING_HEAD_OCR:
        return True
    if VOL_SIG_RE.match(s) or s.startswith("VOL"):
        return True
    return s in GREEK_HEAD_OCR or bool(GREEK_HEAD_RE.match(s))


def _is_marginal_linenum(line: str) -> bool:
    s = line.strip()
    return bool(PAGE_NUM_RE.match(s)) or s in {"GO", "G0"}  # OCR of 60


def _strip_trailing_linenum(line: str) -> str:
    # Keep real verse; only strip a trailing 1-4 digit token on a short tail.
    s = line.rstrip()
    if re.match(r"^SEMI-CHORUS\s+[12]$", s, re.I):
        return s
    m = TRAILING_LINENUM_RE.search(s)
    if not m:
        return s
    head = s[: m.start()]
    if not head.strip():
        return ""
    return head.rstrip()


def _is_slash_garbage(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s in ODD_GARBAGE or s.upper() in SHORT_GARBAGE or SIGNATURE_RE.match(s):
        return True
    letters = LATIN_RE.findall(s) + GREEK_RE.findall(s)
    slashes = s.count("/") + s.count("\\")
    if slashes >= 2 and len(letters) <= 8:
        return True
    if not letters:
        return slashes >= 2 or all(ch in "/\\|'\"“”‘’.,;:*-–—_ []()<>" for ch in s)
    return False


def clean_page_lines(page: list[str], title: str) -> list[str]:
    """Drop running heads, page/line numbers, stage-dir stubs, garbage."""
    out: list[str] = []
    seen_head = False
    for raw in page:
        s = raw.strip()
        if not s:
            if out and out[-1] != "":
                out.append("")
            continue
        if not seen_head and _is_running_head(s, title):
            seen_head = True
            continue
        seen_head = True
        # These headings cannot also be speaker names in their plays, so an
        # OCR-shifted copy is safe to drop even when page splitting missed it.
        if _norm_heading(s) in RUNNING_HEAD_OCR:
            continue
        if title.upper() in {"THE KING", "OEDIPUS AT COLONUS", "TRACHINIAE"}:
            if _is_running_head(s, title):
                continue
        if _is_page_number(s) or _is_marginal_linenum(s):
            continue
        if VOL_SIG_RE.match(s) or END_VOL_RE.match(s):
            continue
        if _is_slash_garbage(s):
            continue
        if PAREN_ONLY_RE.match(s) or CHORUS_MARK_RE.fullmatch(s):
            continue
        if STAGE_DIR_RE.match(s):
            continue
        stem_line = LEADING_JUNK_RE.sub("", s)
        stem = re.split(r"[.\s]", stem_line, 1)[0].upper()
        if stem in SHORT_GARBAGE or stem in GREEK_HEAD_OCR:
            continue
        if greek_ratio(s) > 0.3:
            continue
        s = _strip_trailing_linenum(s)
        s = re.sub(
            r"\s*\[\s*(?:Exit|Hail)\s+[A-Z][A-Z ]*\.\s*$",
            "",
            s,
            flags=re.I,
        )
        s = CHORUS_MARK_RE.sub(" ", s)
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            out.append(s)
    return out


def rejoin_hyphens(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        s = lines[i]
        if s.endswith("-") and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt and nxt[0].isalpha() and not nxt.isupper():
                out.append(s[:-1] + nxt)
                i += 2
                continue
        out.append(s)
        i += 1
    return out


def _speaker_candidate(line: str) -> tuple[str | None, str]:
    """Return (NAME, rest) if this line opens a speech, else (None, line).

    A speaker is an all-caps name on its own line (optional period / Loeb
    parenthetical) or ``NAME. verse``. A mixed-case verse line that happens
    to start with a capital is not a speaker.
    """
    s = line.strip()
    if not s:
        return None, s
    s = LEADING_JUNK_RE.sub("", s)
    s = re.sub(
        r"^[0-9*\"“‘,;=ΑΝ]+\s*(?=[A-Z][A-Z0-9'’\-]{2})",
        "",
        s,
    )
    s = re.sub(r"^(?:Ὡς|Ὁ|Η|ὦ|ὲ|ὰ)\s+", "", s)
    semi = re.fullmatch(r"SEMI-(?:CHORUS|cHoRUS|cHORUS)\s+([12|\]])\s*", s)
    if semi:
        number = "1" if semi.group(1) in {"|", "]"} else semi.group(1)
        s = f"SEMI-CHORUS {number}"
    s = s.strip("|").strip()
    s = TRAILING_JUNK_RE.sub("", s).strip()
    s = re.sub(r"\s+\.$", ".", s)
    s = OCR_SPEAKER_FIXES.get(s, s)
    if not s:
        return None, line.strip()
    m = re.match(
        r"^(?P<name>[A-Z][A-Z0-9'’\-]*(?:\s+(?:AND\s+)?(?:[A-Z][A-Z0-9'’\-]*|[12]))*)"
        r"(?![a-z])"
        r"(?:\s*\([^)]*\))?"
        r"\s*"
        r"(?P<dot>\.)?"
        r"\s*"
        r"(?P<rest>.*)$",
        s,
    )
    if not m:
        return None, s
    name = m.group("name").strip()
    rest = m.group("rest").strip().strip("|").strip()
    if name in NOT_SPEAKERS or name in {"AND", "THE", "A", "AN", "OF"}:
        return None, s
    if not SPEAKER_NAME_RE.match(name) or len(name) < 3:
        return None, s
    if not rest:
        return name, ""
    if m.group("dot") and any(ch.islower() for ch in rest):
        return name, rest
    return None, s


def normalize_speakers(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Fold own-line caps names into ``NAME. text``. Return lines, speakers, suspicious."""
    speeches: list[str] = []
    speakers: list[str] = []
    suspicious: list[str] = []
    current_name: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal current_name, buf
        if current_name and buf:
            first, *rest = buf
            speeches.append(f"{current_name}. {first}")
            speeches.extend(rest)
            speeches.append("")
        elif buf:
            for piece in buf:
                suspicious.append(piece)
        current_name = None
        buf = []

    for line in lines:
        s = line.strip()
        if not s:
            continue
        name, rest = _speaker_candidate(s)
        if name is not None:
            flush()
            current_name = name
            speakers.append(name)
            buf = [rest] if rest else []
            continue
        if current_name:
            buf.append(s)
        else:
            if any(ch.islower() for ch in s) and len(s.split()) >= 5:
                suspicious.append(s)
            elif s.upper() not in NOT_SPEAKERS and not _is_running_head(s, ""):
                suspicious.append(s)
    flush()
    return speeches, speakers, suspicious


def _skip_front_matter(lines: list[str]) -> list[str]:
    """Drop ARGUMENT / DRAMATIS PERSONAE so only the play body remains."""
    start = 0
    for i, line in enumerate(lines):
        if line.strip().upper() == "DRAMATIS PERSONAE":
            start = i + 1
            break
    body = lines[start:]
    # Cast lists end with a Scene line in these Loeb volumes. Start the
    # speaker search after it so cast names cannot open a false speech.
    for i, line in enumerate(body[:100]):
        if re.match(r"^scene\s*:", line.strip(), re.I):
            body = body[i + 1 :]
            break
    # Advance to the first speaker-like line followed by verse.
    for i, line in enumerate(body):
        name, rest = _speaker_candidate(line)
        if not name:
            continue
        nxt = ""
        if rest and any(ch.islower() for ch in rest) and len(rest.split()) >= 4:
            nxt = rest
        else:
            for later in body[i + 1 :]:
                if later.strip():
                    nxt = later.strip()
                    break
        if nxt and any(ch.islower() for ch in nxt) and len(nxt.split()) >= 4:
            return body[i:]
    return body


def clean_play(
    text: str,
    title: str,
    *,
    next_title: str | None = None,
    greek_threshold: float = 0.3,
) -> tuple[str, dict]:
    lines = text.splitlines()
    start, end = locate_play(lines, title, next_title=next_title)
    slice_lines = lines[start:end]
    pages = split_pages(slice_lines, title)
    kept: list[list[str]] = []
    dropped = 0
    for page in pages:
        if not any(p.strip() for p in page):
            continue
        if _page_is_greek(page, greek_threshold):
            dropped += 1
            continue
        kept.append(page)
    cleaned_pages: list[str] = []
    for page in kept:
        cleaned_pages.extend(clean_page_lines(page, title))
    cleaned_pages = _skip_front_matter(cleaned_pages)
    cleaned_pages = rejoin_hyphens(cleaned_pages)
    body, speakers, suspicious = normalize_speakers(cleaned_pages)
    # Dedupe adjacent blanks; prefix the title for the turn-text locator.
    out_lines = [title.upper(), ""]
    for line in body:
        if line == "" and out_lines[-1] == "":
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
        "title": title.upper(),
        "start_line": start,
        "end_line": end,
        "pages_kept": len(kept),
        "pages_dropped": dropped,
        "speakers_found": found,
        "speaker_events": len(speakers),
        "suspicious": suspicious[:80],
        "suspicious_count": len(suspicious),
    }
    return "\n".join(out_lines), report


def write_clean(
    volume: Path,
    translator: str,
    play: str,
    title: str,
    *,
    next_title: str | None = None,
    out_dir: Path | None = None,
) -> tuple[Path, dict]:
    text = volume.read_text(encoding="utf-8", errors="replace")
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bench_clean")
    p.add_argument("--volume", required=True, type=Path)
    p.add_argument("--translator", required=True)
    p.add_argument("--play", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--next-title", default=None)
    args = p.parse_args(argv)
    dest, report = write_clean(
        args.volume, args.translator, args.play, args.title, next_title=args.next_title
    )
    print(f"wrote {dest}")
    print(
        f"  pages_kept={report['pages_kept']} pages_dropped={report['pages_dropped']} "
        f"speakers={report['speakers_found']} events={report['speaker_events']} "
        f"suspicious={report['suspicious_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
