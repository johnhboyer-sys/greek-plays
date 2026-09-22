r"""B. B. Rogers's Loeb Aristophanes vol. 3 (1924) -- History Genie's OCR of
the vendored scan (``aristophanes0003benj_r6k0``), read fresh, replaces the
old ABBYY-patched bench for the four plays that carry Rogers as a comparison
column: Lysistrata (``overlay``), Thesmophoriazusae, Ecclesiazusae and Wealth
(``third``).

Why a full rebuild and not another patch: the old bench (built from ABBYY OCR
of the Internet Archive scan) collapsed whole stichomythia bursts into one
speech and printed bare cues with no words after them -- 155 lines flagged
across the four plays (``build/genie/flagged-<id>-2026-09-17.tsv``), beyond
mechanical repair. Genie's own export already carries loeb-ocr's shape almost
verbatim -- a bold cue and its verse on one physical line, a plain
continuation line below, a whole-italic paragraph for a stage direction, a
lettered footnote call and its page-foot definition -- so this reads
``genie_text.paragraphs()`` and rebuilds each play's speech stream from
scratch rather than patching the old text line by line.

Two things specific to this volume, out of ``genie_text.py``'s own blast
radius (it is written from the Sophocles/Way volumes, whose footnote calls
are digits): the LETTERED footnote convention here survives cleaning as one
of three raw shapes -- ``^b``, ``$^b$``, ``<sup>b</sup>`` -- resolved here
against a page-foot definition on the same or an adjacent page
(``_resolve_footnotes``); and Rogers's habit of abbreviating a speaker's cue
after its first full spelling, sometimes down to a single OCR'd letter
(``_ABBREV`` per play) -- expanded back to the roster's full form so every
cue matches a ``speakers.*`` alias key, the same way Way's and Storr's own
bench files always print the full name.

Genie's OCR truly drops a few physical pages outright in this volume (their
running head, if it survives at all, has no dialogue under it): detected
here as a jump in the printed line-range running heads themselves
(``_find_gaps``), not from a fixed list, since three of the six stretches
flagged going into this lane turned out, on inspection, to be present and
readable in Genie's text after all (Lysistrata 939-964; Ecclesiazusae
443-468 and 552-571 -- see the module return value / commit message). Where
a gap is real, the old (already-cleaned) bench text is spliced in at the
point where the two streams stop lining up, by a plain difflib alignment of
normalised text (``_splice_gaps``) -- the same technique the sibling Way/Storr
lane used.

    python -m drama_pipeline.rogers_clean   # rewrite sources/bench/rogers/*.txt
"""

from __future__ import annotations

import difflib
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from .config import REPO_ROOT, SOURCES_DIR
from . import genie_text as gt
from .stage1_turn_english import parse_play_speeches

# History Genie's OCR of the vendored scan (John's second, independent OCR
# pass; see build/review/fix-genie-loeb-brief.md for the sibling Way/Storr
# lane). Lives only in the main checkout's build/ scratch, never vendored
# into sources/, so this is an absolute path rather than SOURCES_DIR/BUILD_DIR
# -- the same posture as that sibling lane's `build/genie/<item>.docx` inputs.
GENIE_TEXT = Path("/Users/johnboyer/Developer/greek-plays/build/genie/aristophanes0003benj_r6k0.txt")


class Converted(NamedTuple):
    text: str  # loeb-ocr turn-text
    speeches: int  # speaker cues written
    footnotes: int  # Footnotes: block entries written
    log: list[str]  # splices, uncertain footnote calls, dropped asides


@dataclass(frozen=True)
class _Play:
    title: str  # manifest `play:` heading, e.g. "THE LYSISTRATA"
    word: str  # bare uppercase play word for heading/furniture matching
    bench: str  # sources/bench/rogers/<bench>.txt
    # Genie's printed cue, expanded to the full form a `speakers.*` alias
    # key recognises. Covers both true abbreviations (Rogers's own habit of
    # shortening a cue after its first full spelling) and a handful of
    # single-letter-dropped OCR artefacts (the bold run's opening letter
    # lost against the page background) -- confirmed, not guessed, against
    # the facing Greek sigla for every occurrence (2026-09-17 Genie check).
    abbrev: dict[str, str]
    # A two-period compound Genie/Rogers prints as two short cues on one
    # line ("M. CH.", "T. W.") -- `_SPEAKER_LINE"'s grammar only tolerates
    # ONE period in a cue, so these are merged and expanded together.
    compounds: dict[tuple[str, str], str] = field(default_factory=dict)
    # Paragraph text prefixes dropped outright: Rogers's own editorial
    # choice not to translate a stretch (a Latin-only footnote standing in
    # for lines he declined to put into English verse), not an OCR gap --
    # nothing to splice, nothing lost that Rogers himself supplied.
    drop_prefixes: tuple[str, ...] = ()
    # A one-off footnote-shaped paragraph that is really the continuation of
    # the previous footnote's text, not a fresh call -- folded into it
    # rather than read as a new note.
    fold_into_previous_note: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Per-play cue tables (History Genie check, 2026-09-17): every short or
# garbled form Genie prints for these four plays, matched against the facing
# Greek sigla wherever the printed form alone was ambiguous.

_LYSISTRATA = _Play(
    title="THE LYSISTRATA",
    word="LYSISTRATA",
    bench="lysistrata",
    abbrev={
        "LY": "LYSISTRATA",
        "Y": "LYSISTRATA",  # dropped-L OCR artefact ("LY." -> "Y."), Greek ΛΥ. at that point
        "CA": "CALONICE",
        "MY": "MYRRHINA",  # Rogers spells the roster entry "Myrrhina" on first cue
        "MAG": "MAGISTRATE",
        "CI": "CINESIAS",
        "LA": "LAMPITO",
        "ATH": "ATHENIAN",
        "TH": "ATHENIAN",  # dropped-A OCR artefact ("ATH." -> "TH."), Greek ΑΘ. at that point
        "LAC": "LACONIAN",
        "AC": "LACONIAN",  # dropped-L OCR artefact ("LAC." -> "AC."), Greek ΛΑΚ. at that point
        "HER": "HERALD",
        "CH": "CHORUS",
        "H": "CHORUS",  # dropped-C OCR artefact ("CH." -> "H."), Greek ΧΟ. at that point
        "JOINT CH": "CHORUS",  # the men's and women's semichoruses reunite; Greek ΧΟ. bare
        # The banquet cross-talk (page 164) boxes its cues as small marginal
        # type; "OR." and "D." there are not otherwise attested anywhere
        # else in the play and the scene's own Greek is one continuous
        # Athenian speech at that point -- read as further Athenian voices
        # rather than left unaliased (uncertain call, logged; John/Fable
        # to confirm against the Loeb page image).
        "OR": "ATHENIAN",
        "D": "ATHENIAN",
        "EC ATH": "ATHENIAN",  # likely a mis-split "SEC. ATH." (a second Athenian voice)
        "ST": "STRATYLLIS",
        "ID": "IDLER",
        "POR": "PORTER",
        "MAN": "MEN",  # the "Melanion" song's alternating male voice
        "WOMAN": "WOMEN",  # its alternating female voice
        "M": "MEN",  # the same voice abbreviated one letter further
        "W": "WOMEN",  # ditto
        "M CH": "MEN",  # the well-formed (one-period) spelling of the same compound
    },
    compounds={
        ("M", "CH"): "MEN",
        ("W", "CH"): "WOMEN",
        ("T", "W"): "THIRD W",
        ("F", "W"): "FIRST W",
        ("S", "W"): "SECOND W",
    },
)

_THESMOPHORIAZUSAE = _Play(
    title="THE THESMOPHORIAZUSAE",
    word="THESMOPHORIAZUSAE",
    bench="thesmophoriazusae",
    abbrev={
        "MN": "MNESILOCHUS",
        "M": "MNESILOCHUS",  # dropped-N OCR artefact ("MN." -> "M."), context confirms Mnesilochus
        "EU": "EURIPIDES",
        "CH": "CHORUS",
        "SC": "SCYTHIAN",
        "CL": "CLEISTHENES",
        "AG": "AGATHON",
        "CR": "CRITYLLA",
        "CRI": "CRITYLLA",
        "SER": "SERVANT",
        "PO": "POLICEMAN",
        "F W": "FIRST WOMAN",  # the well-formed (one-period) spelling of the compound below
        # The Bidding Prayer's officiant (295ff.): not in the Greek roster
        # under any name of her own (the scene is all-women; no Prytanis
        # here), read as the generic "Woman" the roster's own bare ΓΥ. gets.
        "CRIERESS": "WOMAN",
    },
    compounds={
        ("F", "W"): "FIRST WOMAN",
    },
    # Rogers declined to put Aristophanes' most explicit lines (643-648)
    # into English at all, footnoting a Latin paraphrase instead ("635-648
    # are not in R.'s translation. 643-648 are literally: ..."); the Latin
    # itself is not dialogue and nothing English was ever printed for it --
    # dropped, not spliced.
    drop_prefixes=(
        "CL. Sta erectus.",
        "MU. I. Ecce subit ille",
        "CL. Ubi est? MU. I. Rursus",
        "CL. Non hic quidem est. MU. I.",
        "CL. Habes isthmum",
    ),
    fold_into_previous_note=(
        "N. like the others (except Salabaccho) is chosen for its meaning.",
    ),
)

_ECCLESIAZUSAE = _Play(
    title="THE ECCLESIAZUSAE",
    word="ECCLESIAZUSAE",
    bench="ecclesiazusae",
    abbrev={
        "BL": "BLEPYRUS",
        "CHR": "CHREMES",
        "PR": "PRAXAGORA",
        "CIT": "CITIZEN",
        "CH": "CHORUS",
        "SEMICHORUS": "CHORUS",  # Greek roster has no separate semichorus entity
    },
    compounds={
        ("F", "W"): "FIRST WOMAN",
        ("S", "W"): "SECOND WOMAN",
        ("S", "CH"): "CHORUS",  # "Semichorus" abbreviated the same two-period way
        ("S", "H"): "SECOND H",  # Second Old Woman, abbreviated one letter further
        ("T", "H"): "THIRD H",
    },
)

_WEALTH = _Play(
    title="THE PLUTUS",
    word="PLUTUS",
    bench="wealth",
    abbrev={
        "CHR": "CHREMYLUS",
        "CA": "CARIO",
        "BL": "BLEPSIDEMUS",
        "WE": "WEALTH",
        "POV": "POVERTY",
        "IN": "INFORMER",
        "HER": "HERMES",
        "CH": "CHORUS",
        "PR": "PRIEST",
    },
    compounds={
        ("G", "M"): "GOOD MAN",  # the Greek roster's "Just Man" (ΔΙ./ΔΙΚΑΙΟΣ)
        ("O", "L"): "OLD LADY",  # the well-formed spelling already carries the alias
    },
)

PLAYS: dict[str, _Play] = {
    "lysistrata": _LYSISTRATA,
    "thesmophoriazusae": _THESMOPHORIAZUSAE,
    "ecclesiazusae": _ECCLESIAZUSAE,
    "wealth": _WEALTH,
}
# The order the four plays print in the volume -- how `_play_bounds` finds
# where one play's body ends and the next's front matter begins.
_PLAY_ORDER = ["lysistrata", "thesmophoriazusae", "ecclesiazusae", "wealth"]


# ---------------------------------------------------------------------------
# Furniture: running heads, page numbers, volume signatures -- never dialogue.

# `genie_text._clean_line`'s own `_QUAD_RE` strips a SINGLE `$\qquad$`
# indentation macro; a run of several, space-separated inside one pair of
# dollars (`$\qquad \qquad \qquad$`, a multi-person aside spaced out on the
# page), is not one it was written to match -- cleaned up here instead of
# in `genie_text.py` (out of this converter's blast radius).
_QUAD_LEFTOVER = re.compile(r"\$?(?:\\q{1,2}uad\s*)+\$?")

_VOL_SIG = re.compile(r"^VOL\.?\s+[IVXLC]+\b")
_PAGE_NUM = re.compile(r"^\d{1,4}$")
_ARISTOPHANES_HEAD = re.compile(r"^ARISTOPHANES$")


def _heading_re(word: str) -> re.Pattern[str]:
    # A heading is the bare play word, "THE " plus the word, either with a
    # trailing printed-line range or a footnote call on the title page, and
    # NOTHING ELSE -- anchored at both ends, so a genuine cue that happens
    # to open with the play's own name (Lysistrata is both the title and a
    # character) never matches (2026-09-17 regression: the play's own first
    # line disappeared as "furniture" without the end anchor).
    return re.compile(
        rf"^(?:THE\s+)?{word}"
        r"(?:\s*,?\s*\d+\s*[–—\- ]+\s*\d+)?"
        r"(?:\s*\$\^\{?[a-zA-Z]\}?\$|\s*\^[a-zA-Z]\b)?"
        r"$"
    )


def _heading_range_re(word: str) -> re.Pattern[str]:
    return re.compile(
        rf"^(?:THE\s+)?{word}\s*,?\s*(\d+)\s*[–—\- ]+\s*(\d+)"
    )


def _is_furniture(text: str, word: str) -> bool:
    return bool(
        _VOL_SIG.match(text)
        or _PAGE_NUM.match(text)
        or _ARISTOPHANES_HEAD.match(text)
        or _heading_re(word).match(text)
    )


# Compiled once. A note body stops at any play's running head, not only the
# play currently being converted: the join runs on the whole volume.
_PAGE_HEADINGS = tuple(_heading_re(cfg.word) for cfg in PLAYS.values())


# ---------------------------------------------------------------------------
# Cues, verse, directions.

# A real cue in this roster never runs past "SECOND IDLER" (12 chars); the
# bound keeps an all-caps SHOUTED refrain that ends in a full stop and a
# trailing footnote call ("WAR IS THE CARE AND THE BUSINESS OF WOMEN. [55]")
# from being read as a cue itself once the call is resolved to a bracket
# with the space `_resolve_calls` guarantees (2026-09-17 regression).
_CUE_RE = re.compile(r"^([A-Z][A-Z .'’\-]{0,19})\.\s+(\S.*)$")
_COMPOUND_RE = re.compile(r"^([A-Z]{1,3})\.\s*([A-Z]{1,3})\.\s+(\S.*)$")
# A bare multi-word all-caps phrase with nothing spoken after it -- a scene
# heading Rogers prints in running text ("CHORUS OF MEN.", introducing the
# semichorus's parodos), not a cue: a REAL cue this bare never has words to
# say, so it produces no speech either way, but left unrecognised it reads
# as an extra line of whatever speech is still open when it turns up. A
# single bare word ("I.", Cinesias's one-word reply mid-stichomythia) is
# never caught by this -- it needs at least two capitalised words.
_BARE_HEADING = re.compile(r"^[A-Z][A-Z’'\-]*(?:\s+[A-Z][A-Z’'\-]*)+\.$")
# A stray citation fragment ("F. 366.", short for a fragment or line number)
# left over from a footnote whose call sat on an earlier paragraph -- never
# a cue, and never verse of Rogers's own (2026-09-17 check).
_CITATION_FRAGMENT = re.compile(r"^[A-Z]\.\s*\d+[a-z]?\.?$")
# A shouted all-caps refrain, printed as its own line and ending in a full
# stop with no lowercase letters at all -- `_SPEAKER_LINE` cannot tell this
# apart from a genuine cue when it opens a raw line by itself, so it is
# joined onto the previous printed line instead (`_Writer.line_joined`).
_ALL_CAPS_SHOUT = re.compile(r"^[A-Z][A-Z0-9 !?.,;:'’\-\[\]]*\.\s*(?:\[\d+\])?$")

# Four OCR renderings of the same printed lettered footnote call: a plain
# caret (the italic markup around it stripped by `genie_text._clean_line`,
# leaving the letter bare), a dollar-wrapped digit-only form reused for a
# letter (that regex requires `\d`, so a letter survives verbatim), a
# literal `<sup>` tag (`genie_text._clean_line` only unwraps a DIGIT one),
# and a bare Unicode superscript-letter modifier character Genie sometimes
# reads straight off the page with no markup around it at all (seen 2026-09-17:
# a-g, one of them the Greek-alphabet lookalike U+1D45 MODIFIER LETTER SMALL
# ALPHA for a page's "a" note).
_SUP_LETTER = {
    "ᵃ": "a", "ᵅ": "a", "ᵇ": "b", "ᶜ": "c",
    "ᵈ": "d", "ᵉ": "e", "ᶠ": "f", "ᵍ": "g",
}
_FN_CALL = re.compile(
    r"\^([a-zA-Z])\b"
    r"|\$\^\{?([a-zA-Z])\}?\$"
    r"|<sup>\$?([a-zA-Z])\$?</sup>"  # a `<sup>` tag wrapping the dollar form too
    rf"|([{''.join(_SUP_LETTER)}])"
    r"|\$\^\\([a-zA-Z]+)\$"  # a LaTeX symbol name ("\ddagger") standing in for a call
    r"|\^\(\$([a-zA-Z])\$\)"  # a caret-and-parenthesised dollar form, "^($a$)"
)
# A LaTeX math span Genie renders some Greek-quoting or small-type marginal
# text as (`$\text{...}$`, `$\alpha\beta$`) -- never appears in Rogers's own
# English verse, only in scholarly apparatus or a mis-boxed marginal cue
# (`_LATEX_SMALL_CUE`); a bare span left over after call resolution marks a
# paragraph as apparatus, not dialogue.
_LATEX_SPAN = re.compile(r"\$[^$]*\$")
# Rogers ends explanatory notes with an attribution to himself.  That form
# never occurs in his translated dialogue.  Genie can lose the note call or
# split the note over several paragraphs, so this is the dependable boundary
# for an otherwise unattached note body.
_ROGERS_NOTE_ATTRIBUTION = re.compile(r"[”\"]?\s*:\s*R\.")
_OUTPUT_NOTE_CALL = re.compile(r"\s*\[\d+\]")
_GREEK_LETTER = re.compile(r"[Ͱ-Ͽἀ-῿]")
# A speaker cue Genie boxes as small marginal type during the banquet
# scene's cross-talk (`$\text{\footnotesize ATH.}$ Well, if...`) instead of
# printing plainly -- unwrapped back to an ordinary "CUE. text" line before
# the usual cue grammar ever sees it.
_LATEX_SMALL_CUE = re.compile(r"^\$\\text\{\\footnotesize\s+([^}]+)\}\$\s*(.*)$")
_STAGE_NOTE = re.compile(r"^(Exit|Exeunt|Enter|Enters|Re-enters?)\b", re.I)
# Genie wraps a few Ecclesiazusae cues in a small-caps span ("bl.", "pr.",
# "chr."). genie_text._clean_line deletes every <span> together with what
# is inside it, so the cue vanished and the verse stayed in the previous
# speech. Lift those cues out before paragraphs() runs. A span that is not
# one of these cues (a footnote letter, a Greek siglum) is left for that
# strip. Only a span that opens the line is a cue; the same abbrevs inside
# a footnote stay put.
_SMALLCAPS_CUE_LINE = re.compile(
    r"^(?P<indent>\s*)<span[^>]*font-variant:\s*small-caps[^>]*>"
    r"\s*(?P<cue>bl|pr|chr)\.?\s*</span>(?P<rest>.*)$",
    re.I,
)
# The same scene's next page is a markdown table, one speaker per row
# ("| BL. | Right. |", "| | But what will you do |"). A Greek table
# (Thesmophoriazusae's "| MN. | τί δ᾽ ἔστιν |") is not English dialogue.
_TABLE_ROW = re.compile(r"^\|\s*([^|]*)\|\s*([^|]*)\|")
_TABLE_RULE_CELL = re.compile(r"^:?-+:?$")


def _call_letter(m: "re.Match[str]") -> str:
    g = next(g for g in m.groups() if g)
    return _SUP_LETTER.get(g, g).lower()


def _split_definitions(text: str) -> list[tuple[str, str]] | None:
    """``[(letter, note_text), ...]`` if ``text`` opens with a footnote call
    (one or more, run together on a single printed line), else ``None``."""
    matches = list(_FN_CALL.finditer(text))
    if not matches or matches[0].start() != 0:
        return None
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((_call_letter(m), text[m.end() : end].strip()))
    return out


# ---------------------------------------------------------------------------
# The output writer: a flat stream of printed lines. Bracket directions and
# a cue's own leading/trailing bracket are left as printed text for
# `stage1_turn_english._parse_as_speeches` to split out itself (its
# `_loeb_direction` / `_split_leading_direction` / `_split_trailing_direction`
# already do that job); this module only needs to get the cue name and the
# words right.


class _Writer:
    def __init__(self, title: str) -> None:
        self.out: list[str] = [title, ""]
        self._pending_cue: str | None = None
        self._open = False
        self.speeches = 0

    def cue(self, name: str) -> None:
        if self._open:
            self.out.append("")
            self._open = False
        self._pending_cue = name

    def line(self, text: str) -> None:
        if not text:
            return
        if self._pending_cue is not None:
            self.out.append(f"{self._pending_cue}. {text}")
            self._pending_cue = None
            self._open = True
            self.speeches += 1
        else:
            self.out.append(text)

    def line_joined(self, text: str) -> None:
        """Like `line`, but a continuation of the LAST printed line rather
        than a new one of its own -- for a shouted all-caps refrain ending
        in a full stop (`_ALL_CAPS_SHOUT`), which `_SPEAKER_LINE`'s grammar
        cannot tell apart from a brand new cue when it opens a raw line of
        its own (2026-09-17 regression: two of Rogers's refrains, read as
        wordless new speakers instead of the words they are)."""
        if not text:
            return
        if self._pending_cue is not None or not self._open or not self.out or not self.out[-1]:
            self.line(text)
            return
        self.out[-1] = f"{self.out[-1]} {text}"

    def retain_calls(self, text: str) -> None:
        """Keep resolved calls when their page-foot definition is dropped.

        They are project links, not Rogers's note prose; retaining them on
        the preceding verse line keeps the existing popup contract intact.
        """
        calls = "".join(_OUTPUT_NOTE_CALL.findall(text))
        if calls and self._open and self.out and self.out[-1]:
            self.out[-1] = f"{self.out[-1]}{calls}"

    def direction(self, text: str) -> None:
        if self._pending_cue is not None:
            # A direction between a cue and its own first line of words --
            # print it as its own line; `_parse_as_speeches` reads a
            # `_loeb_direction` line met before any text as the next
            # speech's `directions_before` regardless of where the cue that
            # opened it sits, so the pending cue stays pending across it.
            self.out.append(f"[{text}]")
            return
        if self._open:
            self.out.append(f"[{text}]")
        else:
            self.out.append(f"[{text}]")
            self.out.append("")

    def gap_marker(self) -> int:
        """The index in `out` a Genie-caused gap opens at, for splicing."""
        if self._open:
            self.out.append("")
            self._open = False
        return len(self.out)

    def finish(self, footnotes: list[tuple[int, str]]) -> str:
        if self._open:
            self.out.append("")
        if footnotes:
            self.out.append("Footnotes:")
            for k, text in footnotes:
                self.out.append(f"[{k}] {text}")
        return "\n".join(self.out).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------


def _count_speeches(text: str, title: str) -> int:
    """The number of speeches `stage1_turn_english`'s own loeb-ocr parser
    reads out of ``text`` -- not a running count kept while writing it, so
    it can never drift from what the pipeline actually sees (a cue this
    module's own writer thought was a plain continuation line can still be
    cue-shaped enough for `_SPEAKER_LINE`'s more permissive grammar to open
    a speech under; 2026-09-17 check)."""
    speeches, _notes = parse_play_speeches(text, title, format="loeb-ocr", verse=True)
    return len(speeches)


def _lift_smallcaps_cues(raw: str) -> str:
    """Turn a leading small-caps cue span into an ordinary ``BL.`` line."""
    out: list[str] = []
    for line in raw.splitlines():
        m = _SMALLCAPS_CUE_LINE.match(line)
        if m:
            out.append(f"{m.group('indent')}{m.group('cue').upper()}. {m.group('rest')}")
        else:
            out.append(line)
    if raw.endswith("\n"):
        return "\n".join(out) + "\n"
    return "\n".join(out)


def _is_page_furniture(text: str) -> bool:
    """Page number, volume signature, running head, or the index title."""
    if text in ("INDEX", "***"):
        return True
    return bool(
        _VOL_SIG.match(text)
        or _PAGE_NUM.match(text)
        or _ARISTOPHANES_HEAD.match(text)
        or any(pat.match(text) for pat in _PAGE_HEADINGS)
    )


def _line_stops_note(line: str) -> bool:
    """A wrapped note ends at a blank, the next call, or page furniture.

    ``paragraphs()`` drops blanks, so the boundary has to be applied to the
    raw line. A line that cleans to nothing (a run of ``&nbsp;`` only) is a
    blank. ``---`` is the page marker.
    """
    if not line.strip() or line.strip() == "---":
        return True
    cleaned, _ = gt._clean_line(line)
    if not cleaned:
        return True
    if _split_definitions(cleaned) is not None:
        return True
    return _is_page_furniture(cleaned)


def _note_wraps(lines: list[str]) -> tuple[set[int], set[int]]:
    """``(call lines that wrap, continuation line indexes)``.

    A continuation is every physical line after the call until the next
    blank, note call, page marker, or running head. Indexes are into
    ``lines``, which is ``splitlines()`` of the Genie export.
    """
    calls: set[int] = set()
    cont: set[int] = set()
    i = 0
    while i < len(lines):
        cleaned, _ = gt._clean_line(lines[i])
        if not cleaned or _split_definitions(cleaned) is None:
            i += 1
            continue
        start = i
        i += 1
        wrapped = False
        while i < len(lines) and not _line_stops_note(lines[i]):
            cont.add(i)
            wrapped = True
            i += 1
        if wrapped:
            calls.add(start)
    return calls, cont


def _attach_wrapped_notes(
    paras: list[gt.Paragraph],
    lines: list[str],
    calls: set[int],
    cont: set[int],
) -> list[gt.Paragraph]:
    """Fold wrapped note lines into the call's paragraph.

    Each physical line is cleaned on its own, the way ``paragraphs()``
    already did. Joining the cleaned texts (rather than the raw lines, then
    cleaning once) keeps a split italic marker from changing what the note
    is: an ``Exit`` note whose closing ``*`` sits on the next line stays a
    footnote, which is what a one-line note with that same text already was.
    """
    out: list[gt.Paragraph] = []
    pi = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---" or not line.strip():
            i += 1
            continue
        cleaned, _ = gt._clean_line(line)
        if not cleaned:
            i += 1
            continue
        para = paras[pi]
        pi += 1
        i += 1
        if i - 1 not in calls:
            out.append(para)
            continue
        text = para.text
        while i < len(lines) and i in cont:
            text = f"{text} {paras[pi].text}"
            pi += 1
            i += 1
        out.append(gt.Paragraph(text=text, italic=para.italic, page=para.page))
    if pi != len(paras):
        raise RuntimeError(
            f"note-wrap lockstep consumed {pi} paragraphs of {len(paras)}"
        )
    return out


def _load_genie() -> list[gt.Paragraph]:
    import tempfile

    raw = GENIE_TEXT.read_text(encoding="utf-8")
    orig_lines = raw.splitlines()
    calls, cont = _note_wraps(orig_lines)
    # Lift cues first, then put continuation lines back. A wrap that opens
    # with a small-caps span must not become a ``CHR.`` cue line; once it
    # is part of the note paragraph the span is ordinary note text.
    lifted = _lift_smallcaps_cues(raw)
    lines = lifted.splitlines()
    if len(lines) != len(orig_lines):
        raise RuntimeError("small-caps lift changed the Genie line count")
    for idx in cont:
        lines[idx] = orig_lines[idx]
    # paragraphs() only reads a path, and it strips <span> contents. The
    # Genie export itself is not ours to rewrite.
    path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".txt", delete=False
        ) as handle:
            path = handle.name
            handle.write("\n".join(lines) + ("\n" if raw.endswith("\n") else ""))
        paras = gt.paragraphs(path)
    finally:
        if path is not None:
            Path(path).unlink(missing_ok=True)
    return _attach_wrapped_notes(paras, lines, calls, cont)


def _take_table_row(resolved: str, cfg: _Play, writer: "_Writer") -> bool:
    """A markdown table row that is really a cue. True if the row was ours."""
    m = _TABLE_ROW.match(resolved.strip())
    if not m:
        return False
    cue_cell = m.group(1).strip().strip("*")
    body = m.group(2).strip()
    if (
        (not cue_cell and not body)
        or _TABLE_RULE_CELL.match(cue_cell)
        or _TABLE_RULE_CELL.match(body)
    ):
        return True
    if _GREEK_LETTER.search(cue_cell) or _GREEK_LETTER.search(body):
        return True
    body = body.replace("*", "").strip()
    if cue_cell:
        printed = cue_cell.rstrip(".").strip()
        if not re.fullmatch(r"[A-Z][A-Z .'\-]{0,12}", printed):
            return False
        cue = cfg.abbrev.get(printed, printed)
        writer.cue(cue)
        if body:
            writer.line(body)
        return True
    if body:
        writer.line(body)
    return True


def _real_start(paras: list[gt.Paragraph], title: str) -> int:
    """The play's own title page: the heading immediately followed by a real
    cue+text line (the volume's contents list and running heads print the
    bare title too, but never right before a speech)."""
    for i, p in enumerate(paras):
        t = p.text.strip()
        if t != title and not t.startswith((title + " ", title + "$")):
            continue
        if i + 1 < len(paras) and _CUE_RE.match(paras[i + 1].text.strip()):
            return i
    raise ValueError(f"play title {title!r} never precedes a speech")


def _play_bounds(paras: list[gt.Paragraph], work_id: str) -> tuple[int, int]:
    """(start, end): `start` is the title page the first speech follows;
    `end` is where the NEXT play's own front matter begins (its bare title
    heading, well before its own `_real_start`) -- a play's footnotes and
    endnotes run right up to that boundary, and stopping at the next play's
    `_real_start` instead swallowed the whole of its Introduction, footnotes
    and all, into the current play's Footnotes: block (2026-09-17 regression:
    Lysistrata's tail carried Thesmophoriazusae's "Rogers, Introduction, p.
    x." notes)."""
    i = _PLAY_ORDER.index(work_id)
    start = _real_start(paras, PLAYS[work_id].title)
    if i + 1 < len(_PLAY_ORDER):
        next_head = _heading_re(PLAYS[_PLAY_ORDER[i + 1]].word)
        end = next(j for j, p in enumerate(paras) if j > start and next_head.match(p.text.strip()))
    else:
        end = next(j for j, p in enumerate(paras) if p.text.strip() == "INDEX" and j > start)
    return start, end


def _convert_body(
    paras: list[gt.Paragraph], start: int, end: int, cfg: _Play
) -> tuple[str, int, int, list[str], list[tuple[int, int, int]]]:
    log: list[str] = []

    # --- pass 1: collect footnote/stage-direction definitions, page by page.
    # Checked regardless of the italic flag -- this printing sets some
    # footnote blocks in italic type and some in roman (2026-09-17 check),
    # and regardless of Greek content -- a footnote can quote the Greek it
    # is glossing and still be worth keeping.
    page_notes: dict[int, dict[str, str]] = {}
    page_stage: dict[int, dict[str, str]] = {}
    consumed: set[int] = set()
    for i in range(start, end):
        p = paras[i]
        defs = _split_definitions(p.text)
        if defs is None:
            continue
        consumed.add(i)
        for letter, note in defs:
            if not note:
                continue
            if _STAGE_NOTE.match(note):
                page_stage.setdefault(p.page, {})[letter] = note
            else:
                page_notes.setdefault(p.page, {})[letter] = note

        # A page-foot note occasionally wraps after a hyphen.  Its next
        # physical paragraph has lost the repeated call, but it is still on
        # this page and belongs to the definition just read (Wealth 583).
        # Join only an explicit hyphen wrap: broader guesses risk consuming
        # real verse on the following page.
        if defs and defs[-1][1].rstrip().endswith("-") and i + 1 < end:
            following = paras[i + 1]
            if following.page == p.page and _split_definitions(following.text) is None:
                tail = following.text.strip()
                if tail and not _is_furniture(tail, cfg.word):
                    letter = defs[-1][0]
                    page_notes[p.page][letter] = f"{page_notes[p.page][letter]} {tail}"
                    consumed.add(i + 1)

    def _resolve(page: int, letter: str) -> tuple[str, str] | None:
        """``("note"|"stage", text)`` for a call, checked on its own page
        first, then outward -- Genie's page break sometimes lands a
        page-foot definition a page early or late (2026-09-17 check)."""
        for p in (page, page - 1, page + 1, page - 2, page + 2):
            if p in page_stage and letter in page_stage[p]:
                return "stage", page_stage[p][letter]
            if p in page_notes and letter in page_notes[p]:
                return "note", page_notes[p][letter]
        return None

    footnotes: list[tuple[int, str]] = []
    fn_seq = 0
    fn_seen: dict[tuple[int, str], int] = {}

    def _resolve_calls(text: str, page: int) -> str:
        nonlocal fn_seq

        def repl(m: "re.Match[str]") -> str:
            nonlocal fn_seq
            letter = _call_letter(m)
            found = _resolve(page, letter)
            if found is None:
                log.append(f"uncertain\tfootnote call {letter!r} on page {page} has no definition nearby")
                return ""
            kind, note = found
            if kind == "stage":
                return f" [{note}]"
            key = (page, letter)
            if key not in fn_seen:
                fn_seq += 1
                fn_seen[key] = fn_seq
                footnotes.append((fn_seq, note))
            return f" [{fn_seen[key]}]"

        # A leading space on every substitution (collapsed back to one
        # below) even where the call sat right against the previous letter
        # in print, with no gap of its own: an all-caps line ending right at
        # the call ("...OF WOMEN.$^c$") would otherwise print as
        # "WOMEN.[55]" -- which `_SPEAKER_LINE`'s own grammar (a cue's
        # period may be followed directly by a footnote bracket) reads as a
        # brand new, wordless cue, silently dropping the line it belongs to
        # (2026-09-17 regression, two of Rogers's all-caps refrains).
        resolved = _FN_CALL.sub(repl, text)
        return re.sub(r" {2,}", " ", resolved).strip()

    # --- pass 2: the main stream.
    writer = _Writer(cfg.title)
    prev_hi: int | None = None
    gaps: list[tuple[int, int, int]] = []  # (out index, lo, hi)
    head_re = _heading_range_re(cfg.word)
    # The title's own footnote call (every play in this volume carries one,
    # e.g. "THE LYSISTRATA ^a") always glosses the opening stage direction --
    # printed, in Genie's reading order, at the FOOT of the first page,
    # after a dozen-odd lines of dialogue already spoken. Read literally
    # that direction would interrupt the second speech instead of opening
    # the play, so any whole-italic paragraph on the title's own page is
    # held and printed first, not where Genie's page-foot placed it.
    title_page = paras[start].page
    opening_directions: list[str] = []
    # In this OCR a bare *** is the rule before a page-foot apparatus area,
    # not a textual lacuna.  Keep its scope to one printed page.
    page_footer_notes = False
    footer_page: int | None = None
    apparatus_run = False
    apparatus_page: int | None = None

    for i in range(start, end):
        if i in consumed:
            continue
        p = paras[i]
        if footer_page is not None and p.page != footer_page:
            page_footer_notes = False
            footer_page = None
        if apparatus_page is not None and p.page != apparatus_page:
            apparatus_run = False
            apparatus_page = None
        text = _QUAD_LEFTOVER.sub(" ", p.text).strip()
        if not text:
            continue
        if text == "***":
            page_footer_notes = True
            footer_page = p.page
            log.append("dropped\tseparator furniture (***) before page-foot notes")
            continue
        if gt.is_greek_paragraph(text):
            continue

        m = head_re.match(text)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if prev_hi is not None and lo > prev_hi + 1:
                gaps.append((writer.gap_marker(), prev_hi + 1, lo - 1))
                log.append(f"gap\tGreek {prev_hi + 1}-{lo - 1} has no Genie text (running head jumps {prev_hi}->{lo})")
            prev_hi = hi
            continue
        if _is_furniture(text, cfg.word):
            continue
        if _BARE_HEADING.match(text):
            log.append(f"dropped\tbare scene-heading phrase, not a cue: {text!r}")
            continue
        if _CITATION_FRAGMENT.match(text):
            log.append(f"dropped\tstray citation fragment, not a cue: {text!r}")
            continue

        if any(text.startswith(pre) for pre in cfg.drop_prefixes):
            log.append(f"dropped\tRogers's own Latin aside, not translated: {text[:60]!r}")
            continue
        if text in cfg.fold_into_previous_note:
            if footnotes:
                k, note = footnotes[-1]
                footnotes[-1] = (k, f"{note} {text}")
            log.append(f"folded\tfootnote continuation folded into the previous note: {text[:60]!r}")
            continue

        small_cue = _LATEX_SMALL_CUE.match(text)
        if small_cue:
            text = f"{small_cue.group(1)} {small_cue.group(2)}".strip()

        # Some page-foot prose is wrongly marked italic, including the
        # Ecclesiazusae opening gloss.  Do this before treating italics as a
        # direction, or an editor's note becomes a stage direction.
        if _ROGERS_NOTE_ATTRIBUTION.search(text):
            log.append(f"dropped\tnote-body apparatus (R. attribution), unattached: {text[:60]!r}")
            apparatus_run = True
            apparatus_page = p.page
            continue

        # Calls are resolved BEFORE cue detection, not after: Genie sometimes
        # prints a call flush against the cue's own period with no space
        # ("LAC.<sup>a</sup> Stir...", "JOINT CH.ᵇ Not to..."), which
        # `_CUE_RE`'s own grammar (a real whitespace after the period) does
        # not recognise as a cue at all -- so the line fell through as a
        # continuation, but once written it was STILL cue-shaped enough for
        # `_SPEAKER_LINE`'s more permissive grammar to reopen it as a new,
        # unaliased speaker downstream (2026-09-17 regression: "LAC",
        # "JOINT CH"). Resolving first guarantees the space `_resolve_calls`
        # always inserts is there for `_CUE_RE` to see too.
        if p.italic:
            resolved = _resolve_calls(text, p.page)
            if p.page == title_page:
                opening_directions.append(resolved)
            else:
                writer.direction(resolved)
            continue

        resolved = _resolve_calls(text, p.page)

        # A page-foot note with a lost call is still clearly apparatus when
        # Rogers signs it ": R.".  Drop its wrapped continuation too, until
        # the page changes or a recognised cue proves dialogue has resumed.
        if _ROGERS_NOTE_ATTRIBUTION.search(resolved):
            apparatus_run = True
            apparatus_page = p.page
            writer.retain_calls(resolved)
            log.append(f"dropped\tnote-body apparatus (R. attribution), unattached: {resolved[:60]!r}")
            continue
        if (page_footer_notes or apparatus_run) and not _CUE_RE.match(resolved):
            writer.retain_calls(resolved)
            log.append(f"dropped\tnote-body apparatus continuation, unattached: {resolved[:60]!r}")
            continue

        # A non-cue, non-direction paragraph containing Greek is a gloss in
        # this English stream, not Rogers's translation.  Whole Greek verse
        # was already removed by `is_greek_paragraph`; this catches only the
        # mixed English/Greek apparatus left when Genie lost its note call.
        # Bracketed material remains untouched because it can be a real
        # stage direction.
        if _GREEK_LETTER.search(resolved) and not _CUE_RE.match(resolved) and not resolved.startswith("["):
            writer.retain_calls(resolved)
            log.append(f"dropped\tGreek-bearing note-body apparatus, unattached: {resolved[:60]!r}")
            continue

        if _take_table_row(resolved, cfg, writer):
            continue

        compound = _COMPOUND_RE.match(resolved)
        if compound and (compound.group(1), compound.group(2)) in cfg.compounds:
            cue = cfg.compounds[(compound.group(1), compound.group(2))]
            writer.cue(cue)
            writer.line(compound.group(3))
            continue

        m = _CUE_RE.match(resolved)
        if m:
            printed = m.group(1).strip()
            cue = cfg.abbrev.get(printed, printed)
            writer.cue(cue)
            writer.line(m.group(2))
            continue

        if _LATEX_SPAN.search(resolved):
            # A run of scholarly apparatus (Greek quoted in math mode, a
            # citation) whose call marker sat on an earlier paragraph and so
            # was never picked up as its own footnote definition -- printed
            # nowhere Rogers's own English verse would put a bare `$...$`,
            # so it is dropped from the dialogue stream rather than left to
            # corrupt whichever speech is still open (2026-09-17 check: a
            # 5-line wool-carding gloss otherwise landed inside the
            # Magistrate's own speech).
            log.append(f"dropped\tunattached footnote continuation (math span), not dialogue: {resolved[:60]!r}")
            continue
        if _ALL_CAPS_SHOUT.match(resolved):
            writer.line_joined(resolved)
        else:
            writer.line(resolved)

    if opening_directions:
        insert = []
        for d in opening_directions:
            insert += [f"[{d}]", ""]
        writer.out[2:2] = insert
        gaps = [(idx + len(insert), lo, hi) for idx, lo, hi in gaps]

    text_out = writer.finish(footnotes)
    return text_out, _count_speeches(text_out, cfg.title), len(footnotes), log, gaps


# ---------------------------------------------------------------------------
# Splicing a Genie-caused gap from the current (already-cleaned) bench text.

_NORM = re.compile(r"[^a-z0-9]+")


def _norm(s: str) -> str:
    return _NORM.sub("", s.lower())


def _content_lines(text: str) -> list[str]:
    """Every non-blank, non-title, non-footnote-block line of a loeb-ocr
    bench text, in print order (a blank line only ever separates two
    speeches in this format, so it is skipped, not a stop condition)."""
    lines = text.splitlines()
    out: list[str] = []
    for line in lines[2:]:  # skip the title and its blank line
        s = line.strip()
        if s in ("Footnotes:", "FOOTNOTES:"):
            break
        if s:
            out.append(line)
    return out


def _normalize_splice_cue(line: str, cfg: "_Play") -> str | None:
    """Re-run the same cue grammar this whole module uses over one spliced
    old-bench line -- the old bench was never re-abbreviation-expanded, so a
    short form Genie's own text also uses ("F.W.", "S.H.") still needs
    expanding here too. ``None`` drops the line: a cue this bare (no words
    of its own -- the old bench's own worst OCR, two cues run together like
    "PRAXAGORA. F.W.") produces no speech downstream either way and is
    noise, not content."""
    compound = _COMPOUND_RE.match(line)
    if compound and (compound.group(1), compound.group(2)) in cfg.compounds:
        cue = cfg.compounds[(compound.group(1), compound.group(2))]
        rest = compound.group(3)
        return f"{cue}. {rest}" if any(ch.islower() for ch in rest) else None
    m = _CUE_RE.match(line)
    if m:
        printed = m.group(1).strip()
        rest = m.group(2)
        if not any(ch.islower() for ch in rest):
            return None  # a bare or double-cue collision, no real words
        cue = cfg.abbrev.get(printed, printed)
        return f"{cue}. {rest}"
    if not any(ch.islower() for ch in line) and _BARE_HEADING.match(line):
        return None
    return line


def _splice_gaps(
    new_text: str, old_text: str, gaps: list[tuple[int, int, int]], cfg: "_Play"
) -> tuple[str, list[str]]:
    """Fill each Genie-caused gap from the old bench, located by a plain
    difflib alignment of normalised text against the surviving Genie stream
    (the same technique the sibling Way/Storr genie lane used) -- not by
    Greek line number, which the old bench text does not carry."""
    if not gaps:
        return new_text, []
    log: list[str] = []
    new_lines = new_text.splitlines()
    old_lines = _content_lines(old_text)
    old_norm = [_norm(l) for l in old_lines]
    new_content = _content_lines(new_text)
    new_norm = [_norm(l) for l in new_content]
    matcher = difflib.SequenceMatcher(None, old_norm, new_norm, autojunk=False)
    opcodes = matcher.get_opcodes()

    # `gap_marker` records a RAW line index (into `new_lines`, blank lines
    # and all); the diff runs over `new_content` (blanks stripped) instead,
    # since a blank means nothing to the old bench's own line breaks. Map
    # one to the other by counting the non-blank lines seen up to each gap.
    header_offset = 2  # title + blank line
    content_idx_at: dict[int, int] = {}
    count = 0
    for raw_idx, line in enumerate(new_lines):
        if raw_idx >= header_offset:
            content_idx_at[raw_idx] = count
            if line.strip():
                count += 1

    insertions: list[tuple[int, list[str]]] = []
    for out_idx, lo, hi in gaps:
        content_idx = content_idx_at.get(out_idx, len(new_content))
        old_span: tuple[int, int] | None = None
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal" or i1 == i2:
                continue
            # The gap sits at the point in `new_content` where this
            # old-only (or old-heavier) block's new-side span opens.
            if j1 <= content_idx <= j2:
                old_span = (i1, i2)
                break
        if old_span is None:
            log.append(f"uncertain\tno old-bench span found to splice for Greek {lo}-{hi}")
            continue
        i1, i2 = old_span
        # A leftover running head the earlier cue-repair lane did not clean
        # out of the old bench, whether on its own line or run on right
        # after a cue with no line break of its own ("PRAXAGORA. THE
        # ECCLESIAZUSAE, 488—509"), is not a splice -- stripped out
        # rather than spliced in as if it were dialogue.
        embedded_head = re.compile(
            rf"(?:THE\s+)?{cfg.word}\s*,?\s*\d+\s*[–—\- ]+\s*\d+"
        )
        splice = []
        for raw_line in old_lines[i1:i2]:
            cleaned = embedded_head.sub("", raw_line).strip()
            if not cleaned:
                continue
            normalized = _normalize_splice_cue(cleaned, cfg)
            if normalized is not None:
                splice.append(normalized)
        if not splice:
            log.append(f"uncertain\told-bench span for Greek {lo}-{hi} had no real dialogue either (only furniture/blank)")
            continue
        # This exact stretch is very often the ABBYY bench's OWN worst OCR
        # (why the earlier lane flagged it in the first place): a real
        # printed line always carries a lowercase word, so a span dominated
        # by bare, cue-shaped, all-caps fragments ("PRAXAGORA. F.W.", "PRS",
        # "S.W.") is not usable dialogue either, and splicing it in would
        # trade a Genie-caused hole for a garbled-cue one -- left as an
        # honest gap instead, flagged for a human to look at the Loeb page
        # image directly.
        # A stray Greek letter in what should be an all-English splice is a
        # strong, cheap signal of exactly the OCR breakdown this whole
        # rebuild exists to get away from (Wealth 819-843's old-bench text:
        # "— ολλ 11. LIT ANI RART", scattered one-letter
        # cues, a Greek stage direction run together with the English) --
        # rejected outright rather than measured line by line.
        if any(re.search(r"[Ͱ-Ͽἀ-῿]", l) for l in splice):
            log.append(
                f"uncertain\told-bench span for Greek {lo}-{hi} has Greek-letter garbage mixed into "
                f"the English (its own OCR breakdown) -- left as a gap, needs a human"
            )
            continue
        lowercase_lines = sum(1 for l in splice if any(ch.islower() for ch in l))
        if lowercase_lines / len(splice) < 0.7:
            log.append(
                f"uncertain\told-bench span for Greek {lo}-{hi} is itself mostly bare/garbled cues "
                f"({lowercase_lines}/{len(splice)} lines have real words) -- left as a gap, needs a human"
            )
            continue
        insertions.append((out_idx, splice))
        log.append(f"splice\tGreek {lo}-{hi}: {len(splice)} old-bench lines spliced in ({splice[0][:50]!r} .. {splice[-1][:50]!r})")

    for out_idx, splice in sorted(insertions, key=lambda t: -t[0]):
        new_lines[out_idx:out_idx] = ["", *splice, ""]

    return "\n".join(new_lines).rstrip("\n") + "\n", log


def _pre_rebuild_bench_text(cfg: _Play) -> str | None:
    """The bench text as it stood at HEAD, before this converter ever wrote
    to ``sources/bench/rogers/*.txt`` -- read from git, not the working
    tree, so `convert_play` stays a pure function of the (unwritten-to)
    Genie source: the working-tree file is exactly what this function's own
    caller is about to overwrite, and reading it back would splice the
    previous run's own output into the next one (2026-09-17: two rounds of
    `main()` doubled every splice)."""
    result = subprocess.run(
        ["git", "show", f"HEAD:sources/bench/rogers/{cfg.bench}.txt"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else None


def convert_play(work_id: str) -> Converted:
    cfg = PLAYS[work_id]
    paras = _load_genie()
    start, end = _play_bounds(paras, work_id)
    text, speeches, n_footnotes, log, gaps = _convert_body(paras, start, end, cfg)
    if gaps:
        old_text = _pre_rebuild_bench_text(cfg)
        if old_text is not None:
            text, splice_log = _splice_gaps(text, old_text, gaps, cfg)
            log += splice_log
            speeches = _count_speeches(text, cfg.title)
        else:
            log.append("uncertain\tGenie-caused gap found but no old bench text (at HEAD) to splice from")
    return Converted(text, speeches, n_footnotes, log)


def main() -> int:
    out_dir = SOURCES_DIR / "bench" / "rogers"
    out_dir.mkdir(parents=True, exist_ok=True)
    for work_id in PLAYS:
        result = convert_play(work_id)
        (out_dir / f"{PLAYS[work_id].bench}.txt").write_text(result.text, encoding="utf-8")
        print(f"{work_id}: speeches={result.speeches} footnotes={result.footnotes} log_lines={len(result.log)}")
        for line in result.log:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
