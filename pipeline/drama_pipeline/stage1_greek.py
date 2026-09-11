"""Stage 1a: TLG Greek spine via Diogenes verse-mode export.

Parses the verse-mode TEI (Bekker-page divs containing <l n="..."> lines),
rejoins words hyphenated across lines onto the first line, assigns each line
to a book from the manifest table, and emits spine segments keyed
(book, column) so book-straddling columns split into per-book segments.
"""

from __future__ import annotations

import copy
from functools import partial
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from lxml import etree

from . import scheme as scheme_mod
from .config import BUILD_DIR, SOURCES_DIR, Manifest
from .lined import (
    LinedAlphabet,
    _LINE_INDENT_RE,
    _SECTION_N_RE,
    _apply_lined_cross_column_wraps as _apply_lined_cross_column_wraps_impl,
    _apply_lined_wraps as _apply_lined_wraps_impl,
    _fold_hyphen_final_sigma,
    _lined_chapter_lines as _lined_chapter_lines_impl,
    _warn_if_lined_source_has_no_wraps as _warn_if_lined_source_has_no_wraps_impl,
    _word_start as _word_start_impl,
)

EXPORT_DIR = BUILD_DIR / "export"


def exported_xml_path(manifest: Manifest) -> Path:
    """The drama corpus's one-invocation-per-author export convention
    (docs/plan.md's P1 phase; CLAUDE.md's "one invocation per author"
    rule): `build/export/tlg<author>/Diogenes-Resources/xml/tlg/
    tlg<author><work>.xml` — the per-author subdirectory (`tlg0085`, ...)
    is what lets one Diogenes export cover every work of that author
    without collision, unlike a single shared `build/export/` root."""
    w = manifest.data["work"]
    return (
        EXPORT_DIR
        / f"tlg{w['tlg_author']}"
        / "Diogenes-Resources"
        / "xml"
        / "tlg"
        / f"tlg{w['tlg_author']}{w['tlg_work']}.xml"
    )


def run_export(manifest: Manifest) -> Path:
    """The pre-existing Diogenes export for this work — NEVER invoked here
    (P1 ruling, docs/plan.md: the drama corpus's TLG export is a manual,
    one-invocation-per-author step run ahead of time per docs/tlg-phi-
    export.md, not something a pipeline run triggers). If the expected
    export file already exists (the common case — every author's export was
    run once, up front), this just returns its path; if it is missing, this
    fails loudly with a pointer to the recipe rather than guessing at a
    `perl`/Diogenes invocation that may target the wrong scratch prefs dir
    or a corpus location this process has no business assuming."""
    out = exported_xml_path(manifest)
    if out.exists():
        return out
    w = manifest.data["work"]
    raise FileNotFoundError(
        f"{manifest.work_id}: expected TLG export at {out} but it does not "
        f"exist. Run the Diogenes export recipe in docs/tlg-phi-export.md "
        f"for author {w.get('tlg_author')!r} (one invocation per author) "
        f"before building this work — drama_pipeline never runs Diogenes "
        f"itself."
    )


def _line_text(el: etree._Element, strip_bars: bool = False, extra_strip_chars: str = "") -> str:
    """Flatten an <l>, dropping heading labels, collapsing whitespace.

    `strip_bars` removes literal "|" edition line-break markers, which some
    exports (e.g. De Mundo's) print inside a plain <l> — mid-word (καλοῦν|ται)
    or between words (μέσον | μὲν); the bar is never part of a Greek word.
    It must stay FALSE on compound-numbered lines (n="8,9"), where "|" is the
    delimiter _expand_compound splits on to map the physical line onto its two
    Bekker numbers — stripping it there would destroy the split.

    `extra_strip_chars` (Sol blocker S3, replacing an earlier unconditional
    module-level constant that used to fire for every scheme/work in the
    whole pipeline): every character in this string is dropped outright,
    same as a bar. Defaults to "" (no-op) for every ordinary call site —
    only `_dk_clean_line_text` passes a manifest-declared value (this
    work's own `citation.export_artifact_chars`), so a confirmed export
    artifact verified against exactly one work's exactly one character
    (e.g. Empedocles' U+1017C GREEK OBOL SIGN glued onto "ὁρῶντα" in
    B109a, div n="109a" line 3, "ἐπὶ τὸν ὁρῶντα𐅼.") is scoped to that
    work + character, not silently applied corpus-wide to every other
    work's every line on the strength of one div's evidence."""
    text = "".join(el.itertext())
    if strip_bars:
        text = text.replace("|", "")
    for ch in extra_strip_chars:
        text = text.replace(ch, "")
    return re.sub(r"\s+", " ", text).strip()


def _is_greek_letter(ch: str) -> bool:
    """True when `ch` is a Greek LETTER of any accentuation. Mirrors
    stage3_tokenize.py's identically-named helper (duplicated rather than
    imported: the two stages have no other coupling, and this is a ~5-line
    pure function)."""
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return False
    return name.startswith("GREEK") and unicodedata.category(ch).startswith("L")


# `_fold_hyphen_final_sigma` itself now lives in lined.py (2026-08-30
# cross-script wrap fix -- see that module's own comment): the wrap
# machinery applies it universally to both alphabets, not just Greek's own.
# Re-imported above (not redefined here) for this module's OTHER, non-lined-
# machinery call sites below (~line 190, ~1550, ~2875 -- the DK-block-merge
# and flat-hyphen-join paths, which are not part of the lined machinery and
# stay Greek-only by their own explicit `_is_greek_letter` guards).

GREEK_LINED = LinedAlphabet(
    is_letter=_is_greek_letter,
    fold_wrap_final=_fold_hyphen_final_sigma,
    name="greek",
    # Empty: Greek's own glued line-start punctuation (a curly opening
    # quote, U+2018) IS stripped by stage3_tokenize._surface()'s _PUNCT
    # edge-trim, so lined.py's fragment-start advance keeps skipping past
    # it, unchanged (the 17-locus Discourses quote fix this depends on).
    frag_start_glued_chars="",
)

# Keep the old Greek-module names for test and caller compatibility. Stage-1
# production call sites below still pass the policy explicitly.
_lined_chapter_lines = partial(_lined_chapter_lines_impl, alphabet=GREEK_LINED)
_apply_lined_wraps = partial(_apply_lined_wraps_impl, alphabet=GREEK_LINED)
_apply_lined_cross_column_wraps = partial(
    _apply_lined_cross_column_wraps_impl, alphabet=GREEK_LINED
)
_warn_if_lined_source_has_no_wraps = partial(
    _warn_if_lined_source_has_no_wraps_impl, alphabet=GREEK_LINED
)
_word_start = partial(_word_start_impl, alphabet=GREEK_LINED)


def _rejoin_wrapped_hyphens_mapped(text: str) -> tuple[str, list[int]]:
    """Same rejoin rule as `_rejoin_wrapped_hyphens` (see its docstring for
    the exact match shape), but also returns `old_to_new`: a length
    len(text)+1 list where old_to_new[i] is the char index in the returned
    text that source index i maps onto. A character consumed by the rejoin
    (the hyphen itself, or an absorbed run of spaces) maps to the join
    point — the index immediately following the word fragment it used to
    separate. old_to_new[len(text)] is always len(new_text), so an offset
    sitting at the very end of `text` maps cleanly too.

    Used by `_chapter_sections` to remap pre-rejoin TLG-section-start
    offsets onto the chapter's final (post-rejoin) text -- see that
    function's docstring for why some remapped offsets land mid-word (a
    print-line hyphen wrap straddling a section boundary) and must be
    dropped rather than rendered as a paragraph break."""
    out: list[str] = []
    old_to_new: list[int] = [0] * (len(text) + 1)
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "-" and i > 0 and _is_greek_letter(text[i - 1]):
            j = i + 1
            while j < n and text[j] == " ":
                j += 1
            if j > i + 1 and j < n and _is_greek_letter(text[j]) and text[j].islower():
                # Fold the whole pre-hyphen fragment in place. The fold is
                # length-preserving, so `old_to_new` needs no adjustment.
                if out:
                    out = list(_fold_hyphen_final_sigma("".join(out)))
                for k in range(i, j):
                    old_to_new[k] = len(out)
                i = j
                continue
        old_to_new[i] = len(out)
        out.append(ch)
        i += 1
    old_to_new[n] = len(out)
    return "".join(out), old_to_new


def _rejoin_wrapped_hyphens(text: str) -> str:
    """Rejoin TLG print-line hyphenation that survives as a literal
    "- " inside a chapter-flattened text (numeric_section / flat_numeric
    schemes flatten a whole chapter's <l> lines in one `_line_text()` shot,
    so the per-line cross-line hyphen rejoin below in parse_spine() never
    sees these lines to stitch — CLAUDE.md defect A). `text` is assumed
    already whitespace-collapsed by `_line_text` (every run of whitespace is
    exactly one U+0020 space), so only that single-space shape needs
    handling here.

    Only the ASCII hyphen-minus U+002D is a wrap candidate (verified against
    the actual corpus data) — U+2014 EM DASH, which glues Discourses'
    dialogue turns together (" — "), is a different codepoint and is never
    touched. A candidate hyphen must be directly preceded by a Greek letter
    and, after the run of spaces, directly followed by a LOWERCASE Greek
    letter — the unambiguous shape of a word broken across a print line. A
    hyphen followed by an uppercase letter or by punctuation does not match
    that shape (it could be a deliberate morpheme-boundary citation, as
    stage3_tokenize.py's _PUNCT comment documents for a different corpus) and
    is left untouched, not silently joined."""
    return _rejoin_wrapped_hyphens_mapped(text)[0]


def _chapter_sections(stripped_chap_div, final_text: str) -> tuple[list[dict], list[dict]]:
    """Per-TLG-section standoff offsets `[{n, o}]` into a chapter's flattened,
    hyphen-rejoined `final_text` (the exact string emitted as the chapter's
    one synthetic Greek line) — John's ruling 2026-07-16: Schenkl's Greek
    sub-chapter section divisions are the default paragraphing wherever TLG
    carries them. Shared by Discourses (book-section scheme, title div
    already excluded by `_strip_title_section` before this is called) and
    Enchiridion (flat `section` scheme, no title div at all — see
    `_parse_flat_chapter`).

    Walks `stripped_chap_div`'s direct <div type="section" n="N"> children in
    document order.
    Each section's own `_line_text` output, joined with a single space, is
    verified — corpus-wide, all 95 chapters — to reproduce
    `_line_text(stripped_chap_div)` byte-for-byte, so the pre-rejoin offset
    of each section's start is well-defined. Those offsets are then remapped
    through `_rejoin_wrapped_hyphens_mapped`'s old_to_new table onto
    `final_text` (the SAME rejoin already applied to produce it).

    Schenkl's print-line wraps do not respect TLG's section numbering: a
    hyphenated word can straddle a section boundary. Ground-truth adjudication
    against the real Discourses TLG XML (2026-07-16, all 618 corpus-wide
    occurrences, spread across all 4 books, individually inspected) found
    EVERY one is a genuine print-line straddle -- the preceding section's
    last physical <l> ends in Schenkl's wrap hyphen and the next section's
    first physical <l> opens with the bare continuation -- never an
    offset-remap bug (independently confirmed: the remap's old_to_new table
    was also verified correct for all 2015 non-straddling boundaries in the
    same run, via an offset-independent check that the mapped position's
    following characters equal the section's own first source word). The
    ~23.5% corpus-wide rate is fully explained by the base rate: ~25.8% of
    ALL physical lines in Schenkl's narrow Teubner column end in a wrap
    hyphen, and a section boundary's position is uncorrelated with line-wrap
    position, so roughly one boundary in four coincidentally lands on one.

    The whole-text rejoin fuses such a boundary's start directly onto the end
    of the PRECEDING section's last word, so the remapped offset lands
    mid-word. Rendering a paragraph break there would split a Greek token
    (forbidden — see Reader.svelte's splitGreekSections), so any offset that
    remaps mid-word is SNAPPED BACK (via `_word_start`) to the start of the
    straddling word rather than dropped: that word becomes the opening word
    of the NEW section's paragraph — matching how a Loeb marginal number
    sits at the wrapped line. No boundary is ever dropped. Returns
    `(kept, snapped)`: `kept` carries every section's boundary, in order;
    `snapped` is the subset of `kept` whose offset was adjusted this way (a
    strict subset also present, already snapped, in `kept`) — for the
    pipeline run's report only.

    One further anomaly, resolved here rather than reported: Discourses
    2.13 has Schenkl's single merged section n="25,26" (one printed section
    covering two Loeb-numbered sections) — the only non-integer section @n
    in the whole work. Recorded under its first number (25); English's
    every-5th-section marker scheme (see stage1_book_section_english.py's
    paras sidecar) happens to anchor at 25 too, so this does not break the
    English/Greek subset validation."""
    pre_entries: list[tuple[int, int]] = []
    cum = ""
    for child in stripped_chap_div:
        if etree.QName(child).localname != "div" or child.get("type") != "section":
            continue
        n_raw = child.get("n")
        if n_raw == "t":
            continue
        m = _SECTION_N_RE.match(n_raw or "")
        if not m:
            raise ValueError(f"unrecognized TLG section @n={n_raw!r}")
        n = int(m.group(1))
        t = _line_text(child)
        if not t:
            continue
        o = len(cum) + (1 if cum else 0)
        cum = f"{cum} {t}" if cum else t
        pre_entries.append((n, o))
    if len(pre_entries) < 2:
        return [], []
    rejoined, old_to_new = _rejoin_wrapped_hyphens_mapped(cum)
    if rejoined != final_text:
        raise ValueError(
            "TLG section-offset flatten does not match the chapter's own "
            "hyphen-rejoined text -- per-section concatenation drifted "
            "from _line_text(stripped_chap_div)"
        )
    kept: list[dict] = []
    snapped: list[dict] = []
    prev_o, prev_n = -1, -1
    for n, o in pre_entries:
        no = old_to_new[o]
        midword = (
            0 < no < len(final_text)
            and final_text[no - 1].isalpha() and final_text[no].isalpha()
        )
        if midword:
            no = _word_start(final_text, no, alphabet=GREEK_LINED)
        if no <= prev_o or n <= prev_n:
            raise ValueError(
                f"non-ascending TLG section offsets: n={n} o={no} "
                f"after prior n={prev_n} o={prev_o}"
            )
        entry = {"n": n, "o": no}
        kept.append(entry)
        if midword:
            snapped.append(entry)
        prev_o, prev_n = no, n
    return kept, snapped


def _lined_source_declared(manifest) -> bool:
    """Whether this work's manifest opts into per-print-line Greek emission
    (`citation.lined_source`, Discourses only — docs/lined-source-plan.md)
    instead of `_parse_flat_book_section`'s default one-flat-entry-per-
    chapter flatten. Mutually exclusive in practice with `section_paragraphs`
    (the `sections` standoff channel `lined_source` replaces for the one work
    that ever carried it, per that plan's Q4) — a lined chapter never calls
    `_chapter_sections` and never emits a `sections` key (I5)."""
    return bool(manifest is not None and manifest.data.get("citation", {}).get("lined_source"))


def _lined_section_div(manifest) -> str | None:
    """`citation.lined_section_div` is the R1a tri-state switch from
    docs/lined-wave2-plan.md: absent (`None`) means the column div is the leaf,
    while Discourses declares `"section"` so `_lined_chapter_lines` walks the
    nested section divs and stamps their @n onto each line as `sec`. A dedicated
    key rather than a reuse of `citation.div_types.section`
    on purpose — the latter mutates the shared `Scheme` dataclass, read by
    several other call sites, whereas this key's blast radius is one
    function."""
    return (
        manifest.data.get("citation", {}).get("lined_section_div")
        if manifest is not None else None
    )


def _lined_cross_column_wraps_declared(manifest) -> int | None:
    """The declared cross-column rejoin count, or ``None`` when absent."""
    if manifest is None:
        return None
    citation = manifest.data.get("citation", {})
    if "lined_cross_column_wraps" not in citation:
        return None
    return citation["lined_cross_column_wraps"]


def _apply_declared_lined_cross_column_wraps(
    flat: list[dict], manifest, declared: int | None
) -> None:
    if declared is None:
        return
    actual = _apply_lined_cross_column_wraps(flat, alphabet=GREEK_LINED)
    work_id = manifest.work_id if manifest is not None else "<unknown>"
    if actual != declared:
        raise ValueError(
            f"{work_id}: citation.lined_cross_column_wraps mismatch: "
            f"declared {declared}, actual {actual}"
        )



_COMPOUND_N = re.compile(r"^\d+(?:\s*,\s*\d+)+$")


def _line_no(n: str | None) -> int | None:
    """The Bekker line number of a plain-numeral <l n="…">, or None otherwise
    (a heading label or a compound range, both handled by the caller)."""
    if n and n.isdigit():
        return int(n)
    return None


def _expand_compound(items: list[tuple[str, str]]) -> list[tuple[int, str]]:
    """Reconstruct true Bekker lines from a run of compound-numbered physical
    lines. In a few places Ross's OCT prints one physical line that straddles
    two Bekker lines, tagging it with both numbers (n="8,9") and an in-line `|`
    at the internal break (seen only at APo 99b8-14). For each physical line we
    rejoin a word the break splits (καθόλου πρῶ|τον → πρῶτον, kept whole on the
    earlier line, as with hyphenation), then split the remainder at word-boundary
    `|`s and map the pieces onto the line's Bekker numbers. Pieces that share a
    Bekker number across adjacent physical lines are concatenated, so every
    Bekker line is recovered exactly once and in order."""
    by_line: dict[int, list[str]] = {}
    order: list[int] = []
    for n_str, raw in items:
        nums = [int(x) for x in n_str.split(",")]
        text = re.sub(r"(?<=\S)\|(?=\S)", "", raw)      # rejoin mid-word break
        pieces = re.split(r"\s*\|\s*", text)            # split word-boundary breaks
        for i, piece in enumerate(pieces):
            piece = piece.strip()
            if not piece:
                continue
            num = nums[i] if i < len(nums) else nums[-1]
            if num not in by_line:
                by_line[num] = []
                order.append(num)
            by_line[num].append(piece)
    return [(num, re.sub(r"\s+", " ", " ".join(by_line[num])).strip())
            for num in order]




_SPEAKER_SENTINEL = "\x00"


def _line_with_speakers(el: etree._Element) -> tuple[str, list[dict]]:
    """Flatten an <l> for a section (Stephanus) work, EXCLUDING inline speaker
    labels from the token stream and returning where each turn begins.

    A `<label type="speaker">` marks the start of a speech; its text (e.g. "ΕΥΘ."
    or the Parmenides dialectic dash "—") must never enter the Greek token stream.
    We drop each such label but record a marker `{offset, label}` whose offset is
    the char position in the returned (whitespace-collapsed) line text where the
    following speech begins. A single physical line may carry several turns
    (Parmenides), so markers is a list in document order."""
    parts: list[str] = [el.text or ""]
    labels: list[str] = []
    for child in el:
        tag = etree.QName(child).localname if isinstance(child.tag, str) else ""
        if tag == "label" and child.get("type") == "speaker":
            labels.append((child.text or "").strip())
            parts.append(_SPEAKER_SENTINEL)
        else:
            # Non-speaker inline content (a <pb/> carries none; a head label on a
            # title line contributes its text) stays in the stream.
            parts.append("".join(child.itertext()))
        parts.append(child.tail or "")
    collapsed = re.sub(r"\s+", " ", "".join(parts)).strip()
    out: list[str] = []
    markers: list[dict] = []
    li = 0
    i = 0
    while i < len(collapsed):
        ch = collapsed[i]
        if ch == _SPEAKER_SENTINEL:
            i += 1
            if i < len(collapsed) and collapsed[i] == " ":
                i += 1  # absorb the single space after the label
            if out and out[-1] != " ":
                out.append(" ")
            markers.append({"offset": len("".join(out)), "label": labels[li]})
            li += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out), markers


def _parse_flat_bekker(tree, sch) -> tuple[list[dict], list[dict]]:
    """Flat (column, line_no, text) list for a flat page-div scheme (bekker,
    busse): the page div carries the whole column and holds <l> lines directly,
    with the Aristotle compound-line (<l n="8,9">) handling. Byte-identical to
    the original single-scheme parser."""
    flat: list[dict] = []
    headings: list[dict] = []
    for div in tree.iter("{*}div"):
        if div.get("type") != sch.page_div_type:
            continue
        column = sch.compose_column(div.get("n"))
        compound: list[tuple[str, str]] = []  # run of compound-numbered lines

        def flush():
            for line_no, text in _expand_compound(compound):
                flat.append({"column": column, "n": line_no, "text": text})
            compound.clear()

        for l in div.iter("{*}l"):
            n = l.get("n")
            if n and not n.isdigit() and _COMPOUND_N.match(n):
                compound.append((n, _line_text(l)))
                continue
            if compound:
                flush()
            line_no = _line_no(n)
            if line_no is None:
                headings.append({"column": column, "text": _line_text(l, strip_bars=True)})
                continue
            flat.append({"column": column, "n": line_no, "text": _line_text(l, strip_bars=True)})
        if compound:
            flush()
    return flat, headings


def _parse_flat_stephanus(tree, sch) -> tuple[list[dict], list[dict]]:
    """Flat (column, line_no, text, speakers) list for a section scheme
    (stephanus): each Stephanus-page div nests section divs; the column token is
    page+section and line numbers restart per section. Inline speaker labels are
    lifted out as per-line markers; title/heading lines (n="t") route to
    headings; stray <pb/> milestones are ignored (they carry no text)."""
    flat: list[dict] = []
    headings: list[dict] = []
    for page_div in tree.iter("{*}div"):
        if page_div.get("type") != sch.page_div_type:
            continue
        page_n = page_div.get("n")
        for sec_div in page_div.iter("{*}div"):
            if sec_div.get("type") != sch.section_div_type:
                continue
            column = sch.compose_column(page_n, sec_div.get("n"))
            for l in sec_div.iter("{*}l"):
                line_no = _line_no(l.get("n"))
                if line_no is None:
                    headings.append(
                        {"column": column, "text": _line_text(l, strip_bars=True)}
                    )
                    continue
                text, speakers = _line_with_speakers(l)
                entry = {"column": column, "n": line_no, "text": text}
                if speakers:
                    entry["speakers"] = speakers
                flat.append(entry)
    return flat, headings


# Diogenes Laertius' book-section export (section_div_type overridden to
# "section" per-manifest — see scheme.py's citation.div_types) intersperses
# philosopher-heading stub divs among its ordinary numbered section divs:
# @n="t18-47" marks the Greek display-name heading for the philosopher whose
# life spans sections 18-47 of that book. A bare numbered section (@n="85")
# is the ordinary citable case; this pattern only ever matches the stub form.
#
# A second stub shape, @n="t105" (no dash), marks a life confined to a
# single section — start == end == 105. Confirmed against the export itself
# (not guessed): every one of the 10 corpus-wide occurrences sits directly
# between two ordinary numbered-section runs whose boundary is exactly that
# one number, and one instance (book 2's "t125" immediately followed by
# "t125-144") lines up exactly with the already-documented doubled Bekker
# section 2.125 (Cebes's one-section life at t125, then Menedemus's life
# starting at the same shared column) — i.e. the abbreviated single-number
# form is how the export spells "start == end", not a different marker.
#
# This stub syntax is DL-specific, not a property of the book-section scheme
# itself — any other book-section work (Meditations, Discourses, Enchiridion)
# has no reason to carry a "t"-prefixed section @n at all. Collecting it into
# the headers channel is therefore gated on the work's manifest opting in
# (declaring a `philosophers` block, the same key emit_philosophers already
# reads — see _philosophers_declared below); for a work that has NOT opted
# in, a t-prefixed @n is a loud parse error rather than silently vanishing
# into an unused headers list (Sol Major 2 review round, 2026-07-16).
_TSTUB_N_RE = re.compile(r"^t(\d+)(?:-(\d+))?$")


def _philosophers_declared(manifest) -> bool:
    """Whether this work's manifest opts into philosopher-heading stub
    collection — presence of a `philosophers:` block (lives.yaml's
    `philosophers.names_file` is the concrete case emit_philosophers reads),
    regardless of its contents. `manifest` may be None (most direct-call
    test fixtures don't need one), which counts as not opted in."""
    return manifest is not None and manifest.data.get("philosophers") is not None


# Diogenes Laertius Book 10 (Epicurus) carries a well-known manuscript leaf
# transposition in the doxographical epitome just before the Letter to
# Menoeceus: the TLG export's own <div type="section"> run for what every
# translation reads as plain sections 120-121 is actually FOUR lettered
# fragments in manuscript document order — n="120a", "121b", "120b", "121a"
# — not two plain-numbered divs (confirmed: this is the ONLY place in the
# whole corpus these letter-suffixed section @n values appear). See
# manifests/lives.yaml's `citation.lettered_fragments` for the full
# philological rationale (Hicks's 1925 Loeb, following Bignone's
# transposition) and the declared found/merge table.
#
# The remap below is deliberately NOT hardcoded to book 10 in code: it is
# manifest-declared (any book-section work can, in principle, carry a
# similar seam) and validated before use. `_LETTERED_FRAGMENT_N_RE` detects
# the general SHAPE of a lettered fragment (digits + one lowercase letter);
# `_resolve_lettered_fragments` pre-scans the whole document, groups
# encountered lettered @n by book, and for each book that has any:
#   * requires a `citation.lettered_fragments` entry for that exact book —
#     an undeclared lettered @n is a loud ValueError, never a silent
#     misparse or a phantom column like "10.120a";
#   * requires the encountered set to match the declared `found` list
#     EXACTLY — same members, same document order — so a missing, extra, or
#     reordered fragment is also a loud ValueError naming the work, book,
#     and found-vs-declared mismatch, rather than being silently accepted.
# Only once both checks pass does the declared `merge` table become the
# (book, lettered-n) -> plain-section-n map the second pass composes columns
# from.
_LETTERED_FRAGMENT_N_RE = re.compile(r"^(\d+)([a-z])$")


def _validate_lettered_fragments_declaration(work_id: str, book_n: str, decl: dict) -> None:
    """Manifest-authoring validation for one citation.lettered_fragments
    entry, run BEFORE any comparison against the document's encountered
    lettered-@n set: a duplicate value inside `found`, or inside any single
    `merge` component list, can never be satisfied by any document — it is
    an error in the declaration itself, so it must fail loudly here rather
    than surfacing later as a confusing found-vs-declared mismatch, or
    silently overwriting the same (book, n) -> resolved_n mapping twice
    (Sol round-2 review, Hole 4)."""
    found = [str(x) for x in decl["found"]]
    if len(found) != len(set(found)):
        dupes = sorted({x for x in found if found.count(x) > 1})
        raise ValueError(
            f"{work_id}: book {book_n!r} citation.lettered_fragments "
            f"`found` list has duplicate entries {dupes!r} — each lettered "
            f"fragment may be declared at most once"
        )
    for resolved_n, components in decl["merge"].items():
        comps = [str(x) for x in components]
        if len(comps) != len(set(comps)):
            dupes = sorted({x for x in comps if comps.count(x) > 1})
            raise ValueError(
                f"{work_id}: book {book_n!r} citation.lettered_fragments "
                f"`merge` entry {resolved_n!r} has duplicate components "
                f"{dupes!r} — each lettered fragment may map to its "
                f"resolved section only once"
            )


def _resolve_lettered_fragments(tree, sch, manifest) -> dict[tuple[str, str], str]:
    encountered: dict[str, list[str]] = {}
    for book_div in tree.iter("{*}div"):
        if book_div.get("type") != sch.page_div_type:
            continue
        book_n = book_div.get("n")
        for chap_div in book_div.iter("{*}div"):
            if chap_div.get("type") != sch.section_div_type:
                continue
            n = chap_div.get("n")
            if _TSTUB_N_RE.match(n or ""):
                continue
            if _LETTERED_FRAGMENT_N_RE.match(n or ""):
                encountered.setdefault(book_n, []).append(n)

    work_id = manifest.work_id if manifest is not None else "<unknown>"

    # Validate every DECLARED book's table (not just encountered ones) up
    # front: a manifest-authoring duplicate inside `found`/`merge` fails
    # regardless of the document's contents (Hole 4), and a declared book
    # with NO encountered lettered @n at all — the document only ever
    # carries the plain form, e.g. n="120" instead of "120a" — is a stale
    # declaration that must fail loudly rather than silently no-opping,
    # which is what happened before when the loop below only ever visited
    # books that WERE encountered (Sol round-2 review, Hole 1).
    if manifest is not None:
        for book_n in manifest.lettered_fragment_books():
            decl = manifest.lettered_fragments_for_book(book_n)
            _validate_lettered_fragments_declaration(work_id, book_n, decl)
            if not encountered.get(book_n):
                raise ValueError(
                    f"{work_id}: stale lettered_fragments declaration: "
                    f"book {book_n!r} declares {decl['found']!r} but the "
                    f"document carries none"
                )

    resolved: dict[tuple[str, str], str] = {}
    for book_n, found in encountered.items():
        decl = manifest.lettered_fragments_for_book(book_n) if manifest is not None else None
        if decl is None:
            raise ValueError(
                f"{work_id}: lettered-fragment section n(s) {found!r} found "
                f"in book {book_n!r} but this work's manifest has no "
                f"citation.lettered_fragments entry for that book — a "
                f"lettered @n can only be remapped onto a plain section "
                f"number when the manifest declares the exact expected "
                f"fragment table for that book"
            )
        declared_found = [str(x) for x in decl["found"]]
        if found != declared_found:
            raise ValueError(
                f"{work_id}: book {book_n!r} lettered-fragment set does not "
                f"match the manifest's citation.lettered_fragments "
                f"declaration — found {found!r} (in document order), "
                f"declared {declared_found!r}"
            )
        merge = {str(k): [str(x) for x in v] for k, v in decl["merge"].items()}
        merge_components = [n for components in merge.values() for n in components]
        if sorted(merge_components) != sorted(declared_found):
            raise ValueError(
                f"{work_id}: book {book_n!r} citation.lettered_fragments "
                f"declaration is inconsistent — `merge` components "
                f"{sorted(merge_components)!r} do not match `found` "
                f"{sorted(declared_found)!r}"
            )
        for resolved_n, components in merge.items():
            for n in components:
                resolved[(book_n, n)] = resolved_n

    return resolved


def _parse_flat_book_section(tree, sch, manifest=None) -> tuple[list[dict], list[dict], list[dict]]:
    """Flat (column, line_no, text) list for a book-section prose scheme
    (Marcus Aurelius): <div type="Book" n="4"> nests <div type="chapter"
    n="23"> -> column "4.23" — the citable unit. A chapter usually nests a
    single <div type="section"> (up to 10, e.g. 1.16), which is NOT a
    separate citable column; its <p> paragraphs are flattened straight into
    the chapter as one synthetic line (n=1; this scheme has no user-facing
    line component — lines_user_facing is False).

    Flattening the whole chapter div's itertext() in one shot (via the same
    `_line_text` used elsewhere) also handles every documented anomaly for
    free, since none of them carries text of its own that would need special
    stripping: bare <pb/> milestones and <space quantity="N"/> indent markers
    contribute nothing (no .text, only a tail that already flows through);
    editorial [square] brackets and the `&lt;angle&gt;`-entity brackets and
    crux marks (†) are ordinary character data. The 2.1/3.1 manuscript
    colophons (<p><label type="head">Τὰ ἐν Κουάδοις...</label></p>, "Τὰ ἐν
    Καρνούντῳ") have no dedicated heading precedent in this scheme (unlike
    the <l n="t"> title-line -> `headings` convention the line-bearing
    parsers below use), so they fall out of this same flatten as the chapter
    text's leading text unit, preserved verbatim — the fallback the brief
    calls for when no heading precedent applies.

    One further exception: Epictetus' Discourses (also book-section) tags a
    chapter's Greek title as <div type="section" n="t">, mirroring the
    <l n="t"> title-line convention — it must not leak into the chapter body,
    so it is excluded from the flatten (see _strip_title_section) rather than
    being folded in like an ordinary sub-section.

    A third case (Diogenes Laertius, section_div_type overridden to
    "section"): a section div whose @n is a "tSTART-END" stub is a
    philosopher-heading marker, not a citable column at all — composing a
    column from it would flatten into a phantom column like "2.t18-47".
    Instead of joining `flat`, it is collected into the returned `headers`
    list as {book, start_section, end_section, greek_name}, where
    `greek_name` is the stub div's own flattened text (the philosopher's
    Greek display name). Collection is gated on `manifest` opting in (see
    `_philosophers_declared`) and the stub's bounds are validated (start >=
    1, end >= start) — both loud ValueError on failure, never a silent drop
    or a bogus header (Sol Major 2 review round, 2026-07-16).

    `manifest` also supplies the citation.lettered_fragments declaration
    (see `_resolve_lettered_fragments`) needed to remap DL book 10's
    manuscript-order lettered fragments onto plain section numbers; it may
    be None when the document carries no lettered fragments at all (most
    direct-call test fixtures).

    `manifest.data["citation"]["section_paragraphs"]` (opt-in, Discourses
    only) additionally attaches each chapter's `_chapter_sections` standoff
    channel as a `sections` key on its `flat` entry. Gated explicitly rather
    than by shape: Meditations' chapter divs nest the SAME kind of numbered
    section divs (up to ~10 per chapter) but John's ruling scopes the new
    paragraphing channel to Discourses only — see CANON.md / the Wave
    report for the rationale (Meditations' sub-chapter sections are not a
    meaningful citation granularity the way Discourses' Loeb-numbered
    sections are).

    `manifest.data["citation"]["lined_source"]` (opt-in, Discourses only —
    docs/lined-source-plan.md) replaces the single-flattened-line emission
    with one `flat` entry per Schenkl print `<l>` (`_lined_chapter_lines` +
    `_apply_lined_wraps`), and skips `_chapter_sections`/`section_paragraphs`
    entirely for that chapter — see those two helpers' own docstrings."""
    flat: list[dict] = []
    headings: list[dict] = []
    headers: list[dict] = []
    lettered = _resolve_lettered_fragments(tree, sch, manifest)
    emit_sections = bool(
        manifest is not None and manifest.data.get("citation", {}).get("section_paragraphs")
    )
    lined = _lined_source_declared(manifest)
    lined_section_div = _lined_section_div(manifest)
    declared_cross_column_wraps = _lined_cross_column_wraps_declared(manifest)
    # Lined emission collects per-column line lists BEFORE wrap application,
    # because one citable column can arrive as multiple leaf divs: a section
    # interrupted by a philosopher-heading stub (Lives 2.125, 7.160, 7.166,
    # 8.83, 8.84), or the declared lettered_fragments remap (Lives 10.120 =
    # 120a+121b+120b). Fragments renumber `n` continuously on merge (I1) and
    # the wrap pass runs ONCE over the assembled column, so a hypothetical
    # wrap at an interruption point is an ordinary in-column wrap, not a
    # spurious column-final one.
    lined_pending: dict[str, list[dict]] = {}
    for book_div in tree.iter("{*}div"):
        if book_div.get("type") != sch.page_div_type:
            continue
        book_n = book_div.get("n")
        for chap_div in book_div.iter("{*}div"):
            if chap_div.get("type") != sch.section_div_type:
                continue
            n = chap_div.get("n")
            m = _TSTUB_N_RE.match(n or "")
            if n and n.startswith("t") and not m:
                # Any @n beginning with "t" that is NOT a well-formed
                # tSTART(-END) stub is unrecognized, regardless of whether
                # this work's manifest opts into philosophers — malformed-
                # ness is what makes it an error, not opt-in status. Without
                # this guard a value like "t5-" or "tbad" falls through to
                # ordinary column composition below and is silently emitted
                # as a phantom column (Sol round-2 review, Hole 2).
                work_id = manifest.work_id if manifest is not None else "<unknown>"
                raise ValueError(
                    f"{work_id}: unrecognized t-prefixed section n={n!r} in "
                    f"book {book_n!r} — a well-formed philosopher-heading "
                    f"stub matches tSTART or tSTART-END; this value matches "
                    f"neither, so it cannot be a stub and must not fall "
                    f"through to ordinary column composition"
                )
            if m:
                if not _philosophers_declared(manifest):
                    work_id = manifest.work_id if manifest is not None else "<unknown>"
                    raise ValueError(
                        f"{work_id}: philosopher-heading stub section "
                        f"n={n!r} found in book {book_n!r}, but this work's "
                        f"manifest does not declare a `philosophers` block "
                        f"— a t-prefixed @n is only ever a header stub for "
                        f"a work that opts in; otherwise it is an "
                        f"unrecognized section n, which must fail loudly "
                        f"rather than silently dropping out of the "
                        f"citable spine"
                    )
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else start
                if start < 1 or end < start:
                    work_id = manifest.work_id if manifest is not None else "<unknown>"
                    raise ValueError(
                        f"{work_id}: malformed philosopher-heading stub "
                        f"n={n!r} in book {book_n!r} — start={start}, "
                        f"end={end} (start must be >= 1 and end >= start)"
                    )
                headers.append({
                    "book": int(book_n),
                    "start_section": start,
                    "end_section": end,
                    "greek_name": _line_text(chap_div),
                })
                continue
            resolved_n = lettered.get((book_n, n), n)
            column = sch.compose_column(book_n, resolved_n)
            stripped = _strip_title_section(chap_div)
            if lined:
                chap_lines = _lined_chapter_lines(
                    stripped,
                    lined_section_div,
                    alphabet=GREEK_LINED,
                    column=column,
                )
                if column in lined_pending:
                    base = len(lined_pending[column])
                    for i, cl in enumerate(chap_lines):
                        cl["n"] = base + i + 1
                    lined_pending[column].extend(chap_lines)
                else:
                    lined_pending[column] = chap_lines
                continue
            text = _rejoin_wrapped_hyphens(_line_text(stripped))
            if text:
                entry = {"column": column, "n": 1, "text": text}
                if emit_sections:
                    kept, _snapped = _chapter_sections(stripped, text)
                    if len(kept) >= 2:
                        entry["sections"] = kept
                flat.append(entry)
            else:
                headings.append({"column": column, "text": ""})
    if lined:
        for column, chap_lines in lined_pending.items():
            if chap_lines:
                _apply_lined_wraps(
                    column,
                    chap_lines,
                    alphabet=GREEK_LINED,
                    defer_column_final=declared_cross_column_wraps is not None,
                )
                flat.extend({"column": column, **cl} for cl in chap_lines)
            else:
                headings.append({"column": column, "text": ""})
        _apply_declared_lined_cross_column_wraps(
            flat, manifest, declared_cross_column_wraps
        )
    return flat, headings, headers


def _strip_title_section(chap_div: etree._Element) -> etree._Element:
    """`chap_div`, or (only if it nests one) a deep copy with any
    <div type="section" n="t"> removed — the chapter's Greek title (Discourses
    n="t" fix), which must not leak into the body text `_line_text`'s
    itertext() would otherwise flatten it into.

    Removal preserves the title div's .tail (the standard lxml removal dance:
    reattach it to the previous sibling's tail, or the parent's text when the
    div is the first child) — that tail is real body text sitting between the
    title's close tag and the next sibling, not part of the title."""
    titles = [
        d for d in chap_div.iter("{*}div")
        if d is not chap_div and d.get("type") == "section" and d.get("n") == "t"
    ]
    if not titles:
        return chap_div
    clone = copy.deepcopy(chap_div)
    for d in list(clone.iter("{*}div")):
        if d.get("type") == "section" and d.get("n") == "t":
            parent = d.getparent()
            tail = d.tail or ""
            if tail:
                prev = d.getprevious()
                if prev is not None:
                    prev.tail = (prev.tail or "") + tail
                else:
                    parent.text = (parent.text or "") + tail
            parent.remove(d)
    return clone


def _flat_title_content_hash(text: str) -> str:
    """Mirrors stage1_latin.py's `_title_content_hash` (same hash, same
    truncation) — kept as its own copy rather than a cross-module import
    since the two stages have no other coupling and the drop/merge
    declarations below are Greek-flat-scheme-specific (see
    `_load_flat_title_declarations`)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load_flat_title_declarations(manifest) -> dict[str, str]:
    """A flat-scheme manifest's declared top-level `n="t"` divs (Epicurus'
    Letters/Vatican Sayings, Wave 3), keyed by `_flat_title_content_hash`
    (never a positional/shape heuristic — Sol re-review round 2's whole
    point for this parser): `citation.title_labels` ({sha256_16, note}[]).

    TLG's export carries an `n="t"` div for two different reasons, both
    dropped outright here (mirroring stage1_latin.py's PHI title-drop
    convention — same field name/shape, independently loaded since Latin's
    loader enforces a stricter 2-key-only shape this module does not need
    to share):

      * a bare work/collection title (Kuriai Doxai's "ΚΥΡΙΑΙ ΔΟΞΑΙ",
        Vatican Sayings' "ΕΠΙΚΟΥΡΟΥ ΠΡΟΣΦΩΝΗΣΙΣ") — carries no citable
        content of its own;
      * a letter's own opening salutation (Ep. Herodotum's "Ἐπίκουρος
        Ἡροδότῳ χαίρειν.", Ep. Menoeceum's "Ἐπίκουρος Μενοικεῖ χαίρειν."),
        exported as its own div immediately before the first numbered
        section rather than inline within it (contrast Ep. Pythoclem,
        where the identical greeting formula is an `<l n="t">` INSIDE
        section 84's own div and needs no special handling at all —
        confirmed against the export). Every scholarly edition (Bailey,
        Hicks) prints this salutation as an unnumbered rubric ABOVE the
        first numbered section, never as part of its text — dropping it
        here matches that convention, so section 35/122 read exactly as
        every printed edition cites them, opening with their own first
        substantive sentence rather than the salutation.

    An undeclared `n="t"` div is a LOUD error (raised at the call site),
    never a silent drop — a future re-export's differently-shaped title
    div must be reviewed and classified, not guessed at."""
    citation = (manifest.data.get("citation") or {}) if manifest is not None else {}
    out: dict[str, str] = {}
    for entry in citation.get("title_labels") or []:
        out[entry["sha256_16"]] = entry.get("note", "")
    return out


def _parse_flat_chapter(tree, sch, manifest=None, xml_path=None) -> tuple[list[dict], list[dict]]:
    """Flat (column, line_no, text) list for a flat, bookless prose scheme
    (Epictetus' Enchiridion, citation.scheme: "section"): <div type="Chapter"
    n="5"> sits at the TOP LEVEL — no Book wrapper — and IS the citable
    column (compose_column("5") -> "5"). A nested <div type="section"> (the
    chapter's un-cited sub-paragraph breaks) is not a separate citable
    column; it flattens straight into the chapter as one synthetic line
    (n=1; this scheme has no user-facing line component), exactly like
    _parse_flat_book_section's chapter flatten.

    Two guards against a mis-declared export — both LOUD errors, never a
    silent skip or misparse (Sol re-review round 2):
      * any <div type="Book"> in the document: this scheme is bookless by
        definition (the caller assigns every column to the single declared
        book), so a Book wrapper means the work is NOT flat and silently
        parsing it would misassign every chapter to book 1;
      * a Chapter div with ANY div ancestor (another Chapter, a front-matter
        wrapper, anything): the flat scheme describes chapters at the top
        level only, so a wrapped Chapter is a topology this scheme does not
        describe — treating it as a real column would emit a phantom
        chapter, and skipping it would silently drop text.

    `manifest.data["citation"]["section_paragraphs"]` (opt-in; per John's
    ruling 2026-07-16 that Greek sub-chapter divisions are the default
    paragraphing wherever TLG carries them — mirrors Discourses'
    book-section opt-in, see `_parse_flat_book_section`'s docstring)
    additionally attaches each chapter's `_chapter_sections` standoff channel
    as a `sections` key on its `flat` entry. A chapter with no chapter-title
    stub (confirmed against the export: zero occurrences in this scheme) so
    `_chapter_sections` runs directly against `chap_div` — no
    `_strip_title_section` pre-pass needed.

    `manifest.data["citation"]["lined_source"]` (opt-in, wave 1 —
    docs/lined-rollout-plan.md Ruling 1) replaces the single-flattened-line
    emission with one `flat` entry per Schenkl print `<l>`
    (`_lined_chapter_lines` + `_apply_lined_wraps`), mutually exclusive with
    `section_paragraphs` by construction (the lined branch `continue`s before
    the `section_paragraphs` code below can run). `citation.lined_section_div`
    (Enchiridion only) selects `_lined_chapter_lines`' string-walk mode,
    stamping `sec` from the chapter's own nested `<div type=…>` sub-division;
    absent, the five Epicurus works walk `<l>` directly under the column div
    and stamp no `sec` at all — see `_lined_section_div`'s and
    `_lined_chapter_lines`' own docstrings.

    A top-level `n="t"` div (Epicurus, Wave 3 — see
    `_load_flat_title_declarations`) is not itself a citable chapter and is
    dropped outright (a bare collection title, or a letter's own opening
    greeting — see that function's doc comment for why both drop). Which
    divs may be dropped is a manifest-declared hash gate, never inferred
    from position alone. Contrast Ep. Pythocles, whose IDENTICAL greeting
    formula is exported as an `<l n="t">` INSIDE its numbered section's own
    div rather than as a dedicated top-level div — that line needs no
    declaration and no dropping; it flattens into (or, lined, becomes a line
    of) that section automatically (Ruling 3)."""
    for el in tree.iter("{*}div"):
        if el.get("type") == "Book":
            raise ValueError(
                f"{xml_path or '<xml>'}: found div[@type=\"Book\"] under flat "
                f"scheme {sch.name!r} — this scheme is bookless; a Book "
                f"wrapper means the export does not match the declared "
                f"citation scheme"
            )

    flat: list[dict] = []
    headings: list[dict] = []
    emit_sections = bool(
        manifest is not None and manifest.data.get("citation", {}).get("section_paragraphs")
    )
    lined = _lined_source_declared(manifest)
    lined_section_div = _lined_section_div(manifest)
    declared_cross_column_wraps = _lined_cross_column_wraps_declared(manifest)
    declared_titles = _load_flat_title_declarations(manifest)
    for chap_div in tree.iter("{*}div"):
        if chap_div.get("type") != sch.page_div_type:
            continue
        wrapper = next(iter(chap_div.iterancestors("{*}div")), None)
        if wrapper is not None:
            raise ValueError(
                f"{xml_path or '<xml>'}: div[@type=\"{sch.page_div_type}\"]"
                f"[@n=\"{chap_div.get('n')}\"] is nested inside "
                f"div[@type=\"{wrapper.get('type')}\"] under flat scheme "
                f"{sch.name!r} — chapters must be top-level; a wrapped "
                f"export does not match the declared citation scheme"
            )
        if chap_div.get("n") == "t":
            title_text = _rejoin_wrapped_hyphens(_line_text(chap_div))
            h = _flat_title_content_hash(title_text)
            if h in declared_titles:
                continue
            raise ValueError(
                f"{xml_path or '<xml>'}: undeclared top-level n=\"t\" div "
                f"(sha256_16={h!r}, text={title_text!r}) under flat scheme "
                f"{sch.name!r} — declare it in citation.title_labels before "
                f"this can build"
            )
        column = sch.compose_column(chap_div.get("n"))
        if lined:
            chap_lines = _lined_chapter_lines(
                chap_div,
                lined_section_div,
                alphabet=GREEK_LINED,
                column=column,
            )
            if chap_lines:
                _apply_lined_wraps(
                    column,
                    chap_lines,
                    alphabet=GREEK_LINED,
                    defer_column_final=declared_cross_column_wraps is not None,
                )
                flat.extend({"column": column, **cl} for cl in chap_lines)
            else:
                headings.append({"column": column, "text": ""})
            continue
        text = _rejoin_wrapped_hyphens(_line_text(chap_div))
        if text:
            entry = {"column": column, "n": 1, "text": text}
            if emit_sections:
                kept, _snapped = _chapter_sections(chap_div, text)
                if len(kept) >= 2:
                    entry["sections"] = kept
            flat.append(entry)
        else:
            headings.append({"column": column, "text": ""})
    if lined:
        _apply_declared_lined_cross_column_wraps(
            flat, manifest, declared_cross_column_wraps
        )
        _warn_if_lined_source_has_no_wraps(
            manifest.work_id if manifest is not None else "<unknown>",
            flat,
            alphabet=GREEK_LINED,
        )
    return flat, headings




# --------------------------------------------------------------------------
# Play-line (P1 — docs/p1-probe.md): the Greek drama corpus's own scheme.
# The export carries NO wrapping div at all — <body> holds a flat sequence
# of <l n="…"> lines directly (model: `_parse_flat_stephanus` above, minus
# its page/section div walk; `_line_with_speakers` above is NOT reused
# as-is because a play line's <label type="speaker"> carries BOTH true
# speakers AND strophe/antistrophe markers that must be classified apart —
# see `_line_with_play_labels` below).
#
# Segment cut (documented here, the play-line walker's one home): a segment
# breaks whenever a NEW line opens with a fresh speaker cue (its first
# speaker marker sits at char offset 0 — an antilabe's SECOND, mid-line
# speaker never splits a segment, since a segment can never split a single
# physical line), or after 40 lines without one — whichever comes first, cut
# only ever at a line boundary. The cap keeps a long uninterrupted rhesis or
# choral ode from becoming one giant segment the reader's virtual scroll
# would have to render whole.

# Case-SENSITIVE on purpose (Sol review 2026-09-05, item 9): the Greek
# marker forms are printed lowercase by every edition in the corpus
# ("[στρ. α.", "ἀντ.", "ἐπῳδ."), and a case-fold would swallow a genuine
# speaker siglum that happens to share the letters — "Στρ." (Strophius, or
# any editor's capitalised abbreviation) must stay a speaker. The Latin forms
# are the exact capitalised abbreviations Dain–Mazon and Coulon print.
# "ἐπῳδός" (Persians 673, 899, 1066) is Murray's bracketed epode marker
# spelled out as the full inflected nominative rather than abbreviated
# "ἐπῳδ." — the bare "ἐπῳδ" alternative's \b fails right after "δ" because
# "ός" continues the word, so the literal inflected form is listed first
# (P2-Greek, docs/p2-greek-report.md).
_PLAY_LINE_STROPHE_RE = re.compile(
    r"^\[?(στρ|ἀντ|ἐπῳδός|ἐπῳδ|μεσῳδ|ἐφυμν|ἐφ|Str|Ant|Epod|Ep|Epode)\b"
)
# The one malformed shape observed corpus-wide (docs/p1-probe.md): a strophe
# mark glued to a speaker siglum inside ONE <label> element ("[ἀντ. α. Αν."
# — a strophe/antistrophe mark, its own single-character stanza-number token
# (a lowercase Greek letter or digit — "α.", "1." — never itself a speaker),
# immediately followed by a speaker's own abbreviation). Split into its two
# halves rather than either misclassifying the whole label as a speaker
# (losing the strophe marker) or as a strophe marker (losing the speaker
# cue). Deliberately narrow — NOT case-insensitive, and the trailing
# "speaker" group must start with an UPPERCASE letter (Greek or Latin): an
# ordinary "[στρ. α." is two whitespace-separated tokens too (the marker,
# then its own lowercase stanza letter "α."), and a looser match here would
# misparse every ordinary strophe label's own numbering letter as a phantom
# speaker (verified against the real Agamemnon export, which carries no
# genuine occurrence of this malformed shape at all — every "[στρ. α."-style
# label in it is the ordinary two-token form).
_GREEK_UPPER = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
_PLAY_LINE_MALFORMED_RE = re.compile(
    r"^(?P<strophe>\[?(?:στρ|ἀντ|ἐπῳδ|μεσῳδ|ἐφυμν|ἐφ|Str|Ant|Ep|Epode)[^\sΑ-Ω]*\.?"
    r"(?:\s+[a-zα-ω0-9]+ʹ?\.)?)"
    rf"\s+(?P<speaker>[{_GREEK_UPPER}A-Z][^\s]*\.)\s*$"
)


def _normalize_strophe_label(text: str) -> str:
    """A classified strophe/antistrophe/epode label, stripped of its
    leading "[" only (Murray prints "[στρ. α.", Dain/Coulon prints bare
    "Str. 1." with no bracket at all — stripping is a no-op for those).
    Nothing else about the printed text is altered."""
    return text[1:] if text.startswith("[") else text


def _line_with_play_labels(el: etree._Element) -> tuple[str, list[dict], str | None]:
    """Flatten a play <l>: classify each `<label type="speaker">` as a real
    speaker cue or a strophe/antistrophe/epode marker (see the module-doc
    block above), returning (text, speaker_markers, strophe_label).

    A speaker cue is excluded from the text stream and recorded as an
    `{offset, label}` marker, exactly like `_line_with_speakers` above — the
    offset is the char position in the FINAL text (after every label is
    removed and whitespace is collapsed), so it stays correct for a strophe
    marker printed BEFORE a speaker cue on the same physical line (not
    observed in the corpus, but the algorithm does not assume position). A
    strophe label is dropped from the stream entirely and returned as
    `strophe_label` (see `_normalize_strophe_label`) — never a speaker
    marker, never citable text.

    Unlike `_line_with_speakers`, a label's text is taken via `itertext()`
    (not `.text`), because a full-caps first-appearance speaker name is
    wrapped in its own `<hi rend="small">` child ("<label type=\"speaker\">
    <hi rend=\"small\">ΦΥΛΑΞ</hi></label>") — `.text` alone would see only
    the label's own (empty) direct text and silently lose the name."""
    parts: list[str] = [el.text or ""]
    speaker_texts: list[str] = []
    strophe_label: str | None = None
    for child in el:
        tag = etree.QName(child).localname if isinstance(child.tag, str) else ""
        if tag == "label" and child.get("type") == "speaker":
            text = re.sub(r"\s+", " ", "".join(child.itertext())).strip()
            m = _PLAY_LINE_MALFORMED_RE.match(text)
            if m:
                if strophe_label is not None:
                    raise ValueError(f"more than one strophe label on one play line: {text!r}")
                strophe_label = _normalize_strophe_label(m.group("strophe"))
                speaker_texts.append(m.group("speaker"))
                parts.append(_SPEAKER_SENTINEL)
            elif _PLAY_LINE_STROPHE_RE.match(text):
                if strophe_label is not None:
                    raise ValueError(f"more than one strophe label on one play line: {text!r}")
                strophe_label = _normalize_strophe_label(text)
                # Dropped outright: no sentinel, no token-stream content, no
                # speaker marker.
            else:
                speaker_texts.append(text)
                parts.append(_SPEAKER_SENTINEL)
        else:
            parts.append("".join(child.itertext()))
        parts.append(child.tail or "")
    collapsed = re.sub(r"\s+", " ", "".join(parts)).strip()
    out: list[str] = []
    markers: list[dict] = []
    li = 0
    i = 0
    while i < len(collapsed):
        ch = collapsed[i]
        if ch == _SPEAKER_SENTINEL:
            i += 1
            if i < len(collapsed) and collapsed[i] == " ":
                i += 1  # absorb the single space after the label
            if out and out[-1] != " ":
                out.append(" ")
            markers.append({"offset": len("".join(out)), "label": speaker_texts[li]})
            li += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out), markers, strophe_label


def _normalize_play_lineref(n: str | None, xml_path=None) -> str:
    """Normalize a play `<l n>` token to the play-line grammar (scheme.py's
    `PLAY_LINE_REF_SOURCE`) — the ONLY two normalizations the P1 probe
    found necessary, both applied here so every later consumer (the
    grammar check, the order key, the manifest's declared lacunae/
    transpositions) sees the canonical form:

      * Diggle's unspaced lacuna placeholder ("post1226") -> "post 1226".
      * Ecclesiazusae's slash-joined double number ("289/290") -> the
        ordinary range form "289-290" (the SAME editorial phenomenon as an
        int-int range token, just spelled with a different separator)."""
    if not isinstance(n, str) or not n:
        raise ValueError(f"{xml_path or '<xml>'}: play <l> has no @n")
    m = re.match(r"^post\s*([0-9]+)$", n)
    if m:
        return f"post {m.group(1)}"
    m = re.match(r"^([0-9]+)/([0-9]+)$", n)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return n


def _play_line_start_key(ref: str) -> tuple[int, int, str]:
    """Sort key for a document-order transposition scan: an ordinary ref
    via `scheme_mod.play_line_order_key`; a range token has no single
    citable position, so it sorts at its START (mirrors stage1_latin.py's
    identically-reasoned `_verse_lineref_order_key` in CPR)."""
    if scheme_mod.play_line_kind(ref) == "range":
        ref = ref.split("-", 1)[0]
    return scheme_mod.play_line_order_key(ref)


def _derive_play_line_transposed_blocks(doc_refs: list[str]) -> list[dict]:
    """Mechanically derive the transposed blocks from a play's DOCUMENT-order
    lineref sequence — byte-for-byte the same algorithm as CPR's
    `_derive_transposed_blocks` (stage1_latin.py, Lucretius' DRN), reused
    here under the play-line grammar's own order key. A maximal run of
    consecutive document-order refs whose order key is LESS than the
    running maximum already seen is a block transmitted out of numeric
    sequence — printed here, in the edition's own transmitted position,
    immediately after the higher-numbered ref that is its "before" anchor.
    See docs/p1-probe.md's Agamemnon example (1290 printed one position
    early): the block this derives for it is `{start: "1284", end: "1289",
    before: "1290"}` — 1284-1289 are the ascending run sitting below the
    running max 1290 set one ref earlier, not "1290" itself (which, at the
    moment it is read, is simply a new maximum) — the same convention this
    algorithm already uses for DRN's own worked examples."""
    blocks: list[dict] = []
    running_max_key: tuple | None = None
    running_max_ref: str | None = None
    i, n = 0, len(doc_refs)
    while i < n:
        ref = doc_refs[i]
        key = _play_line_start_key(ref)
        if running_max_key is not None and key < running_max_key:
            start = ref
            before = running_max_ref
            j = i
            cur_key = key
            while j + 1 < n:
                nxt = doc_refs[j + 1]
                nkey = _play_line_start_key(nxt)
                if nkey < running_max_key and nkey > cur_key:
                    j += 1
                    cur_key = nkey
                    continue
                break
            blocks.append({"start": start, "end": doc_refs[j], "before": before})
            i = j + 1
            continue
        running_max_key = key
        running_max_ref = ref
        i += 1
    return blocks



def _load_repeated_refs(manifest) -> dict[str, int]:
    """`citation.repeated_refs` -> {ref: expected count} (book "1" only:
    play-line is bookless). Shape: {"1": [{ref: "803", count: 2, note: ...}]}."""
    if manifest is None:
        return {}
    decl = (manifest.data.get("citation") or {}).get("repeated_refs") or {}
    out: dict[str, int] = {}
    for entry in decl.get("1", []) if isinstance(decl, dict) else []:
        ref = entry.get("ref") if isinstance(entry, dict) else None
        count = entry.get("count") if isinstance(entry, dict) else None
        if not isinstance(ref, str) or not isinstance(count, int) or count < 2:
            raise ValueError(f"citation.repeated_refs entry malformed: {entry!r}")
        out[ref] = count
    return out


def _check_repeated_refs(allowed: dict[str, int], counts: dict[str, int], xml_path=None) -> None:
    """Bidirectional gate: every declared repeat must be observed with exactly
    its declared count (an undeclared repeat already failed in the walk)."""
    for ref, expected in allowed.items():
        seen = counts.get(ref, 0)
        if seen != expected:
            raise ValueError(
                f"{xml_path or '<xml>'}: citation.repeated_refs declares {ref!r} x{expected} "
                f"but the export prints it x{seen}"
            )


def _parse_play(tree, sch, manifest, xml_path=None) -> list[dict]:
    """Flat (ref, text, speakers, role?, label?) list for play-line's flat
    export, in DOCUMENT (printed) order — never re-sorted (docs/p1-probe.md:
    "display document order, never re-sort"; a jump to a transposed number
    lands on its printed position, no seam note needed).

    The first `<l n="t">` is the play's title-drop (Murray's all-caps title
    inside a `<label type="head">`), gated on the manifest's declared
    `citation.title_labels` exactly like `_load_flat_title_declarations`'s
    other callers (an undeclared title is a loud ValueError, never a silent
    drop).

    Every other `<l>`'s `@n` is normalized (`_normalize_play_lineref`) and
    checked against the play-line grammar (`scheme_mod.play_line_kind`,
    which raises loudly on a malformed token); a "post N" line's role is
    `"lacuna"` and its text is forced empty (mirrors verse-line's own
    lacuna convention) while its speaker marker (Diggle's convention prints
    the anonymous character's name inside the empty brackets) is kept, so
    the reader can still show who the lost line belonged to."""
    declared_titles = _load_flat_title_declarations(manifest)
    observed_titles: set[str] = set()
    title_seen = False
    flat: list[dict] = []
    seen_refs: set[str] = set()
    # John's ruling (2026-09-06, REVIEW-CHECKLIST 3): a ref the edition prints
    # twice (Septem's 803/810 doublet, Helen's two lacunae at 1226, Troades'
    # split 170) stays as printed. `citation.repeated_refs` is a bidirectional
    # allowlist: {ref: expected count}; any other repeat, or a declared repeat
    # not observed with exactly that count, fails loudly.
    allowed_repeats = _load_repeated_refs(manifest)
    ref_counts: dict[str, int] = {}
    body = tree.find(".//{*}body")
    if body is None:
        raise ValueError(f"{xml_path or '<xml>'}: no <body> element in play-line export")
    for l_el in body.iterfind("{*}l"):
        n = l_el.get("n")
        if n == "t":
            if title_seen:
                raise ValueError(f"{xml_path or '<xml>'}: more than one <l n=\"t\"> title line")
            title_seen = True
            title_text = _line_text(l_el)
            h = _flat_title_content_hash(title_text)
            observed_titles.add(h)
            if h not in declared_titles:
                raise ValueError(
                    f"{xml_path or '<xml>'}: undeclared play title line "
                    f"(sha256_16={h!r}, text={title_text!r}) — declare it in "
                    f"citation.title_labels before this can build"
                )
            continue
        ref = _normalize_play_lineref(n, xml_path)
        kind = scheme_mod.play_line_kind(ref)  # raises loudly on a bad token
        ref_counts[ref] = ref_counts.get(ref, 0) + 1
        if ref in seen_refs and ref not in allowed_repeats:
            raise ValueError(
                f"{xml_path or '<xml>'}: repeated play-line ref {ref!r} "
                f"(declare it in citation.repeated_refs if the edition prints it twice)"
            )
        seen_refs.add(ref)
        text, markers, label = _line_with_play_labels(l_el)
        entry: dict = {"ref": ref, "text": text}
        if markers:
            entry["speakers"] = markers
        if label:
            entry["label"] = label
        if kind == "post":
            entry["role"] = "lacuna"
            entry["text"] = ""
            # Diggle's placeholder names the lost line's speaker inside the
            # empty brackets; the marker's offset is meaningless once the
            # text is forced empty, so it is pinned to 0 rather than left
            # pointing past the end of an empty string.
            if "speakers" in entry:
                entry["speakers"] = [{**m, "offset": 0} for m in entry["speakers"]]
        flat.append(entry)
    if not title_seen and declared_titles:
        # The tragedians' exports open with a title line; Dover/Coulon/
        # MacDowell/Ussher print none (all eleven comedies, P3 2026-09-07).
        # A title line is required only when the manifest declares one.
        raise ValueError(f"{xml_path or '<xml>'}: play-line export has no <l n=\"t\"> title line")
    _check_repeated_refs(allowed_repeats, ref_counts, xml_path)
    stale_titles = set(declared_titles) - observed_titles
    if stale_titles:
        stale = ", ".join(sorted(stale_titles))
        raise ValueError(
            f"{xml_path or '<xml>'}: citation.title_labels declares unobserved "
            f"sha256_16 hash(es): {stale}"
        )
    return flat


def _rejoin_play_line_hyphens(flat: list[dict]) -> None:
    """Rejoin a word hyphenated across two ADJACENT play `<l>` divs (the
    edition's own metrical line-break, not a print-column wrap) — measured
    against the real Agamemnon export: choral odes hyphenate mid-word
    across `<l n>` boundaries often (`τρια-` / `κτῆρος`), sometimes
    chained across three lines in a row. Mutates `flat` in place; byte-for-
    byte the same algorithm as `parse_spine`'s own generic rejoin loop
    (this scheme bypasses that loop entirely — see `_parse_spine_play` —
    because it needs its own segment-grouping, so the rejoin is duplicated
    here rather than threading a "used by 1288-line parse_spine's tail
    literally" special case through it)."""
    for i, line in enumerate(flat):
        if not line["text"].endswith("-"):
            continue
        if i + 1 >= len(flat) or not flat[i + 1]["text"]:
            raise ValueError(f"hyphenated play line with no continuation: {line['ref']}")
        nxt = flat[i + 1]
        head, _, rest = nxt["text"].partition(" ")
        fragment = line["text"][:-1]
        if fragment and head and _is_greek_letter(head[0]):
            fragment = _fold_hyphen_final_sigma(fragment)
        line["text"] = fragment + head
        line["joined"] = True
        removed = len(nxt["text"]) - len(rest)
        nxt["text"] = rest
        for m in nxt.get("speakers", []):
            m["offset"] = max(0, m["offset"] - removed)


def _speech_start_lines_from_tei(text: str) -> set[str]:
    """The printed Greek line each top-level `<sp>` of a Perseus play
    translation opens on: the `n` of its first `<l n>` that is not inside a
    speech quoted within it. Those are the places the translator starts a
    speech block, and so a sentence. (Grok review of fa76916: parsed, not
    regex-matched, so a quoted or unclosed `<sp>` cannot misplace a start.)"""
    root = etree.fromstring(text.encode("utf-8"), parser=etree.XMLParser(recover=True, huge_tree=True))
    if root is None:
        return set()
    out: set[str] = set()
    for sp in root.iter("{*}sp", "sp"):
        if next(sp.iterancestors("{*}sp", "sp"), None) is not None:
            continue
        first = next(
            (l for l in sp.iter("{*}l", "l")
             if l.get("n") and next(l.iterancestors("{*}sp", "sp"), None) is sp),
            None,
        )
        if first is not None:
            out.add(first.get("n"))
    return out


def _marked_lines_from_tei(text: str) -> set[str]:
    """Every printed Greek line a Perseus play translation marks with `<l n>`."""
    return set(re.findall(r'<l\b[^>]*\bn="([^"]+)"', text))


def _english_line_marks(manifest: Manifest) -> tuple[set[str], set[str]] | None:
    """(speech-block starts, every marked line) of the work's primary
    line-keyed English (Smyth, Jebb, Coleridge as Perseus encodes them), or
    None for a turn-text primary (the comedies), which has no line markers."""
    cfg = (manifest.data.get("english") or {}).get("primary") or {}
    if cfg.get("model") != "perseus-play" or not cfg.get("source"):
        return None
    path = SOURCES_DIR / cfg["source"]
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    return _speech_start_lines_from_tei(text), _marked_lines_from_tei(text)


def _segment_play_lines(
    flat: list[dict],
    cut_lines: set[str] | None = None,
    marked_lines: set[str] | None = None,
) -> list[dict]:
    """Group play-line's dense-numbered flat list into per-speech segments
    (see the module-doc block above this section for the cut rule). Each
    segment's `column` is its OWN first line's printed ref — unique per
    segment by construction (two segments can never open on the same
    printed line) — so the generic dist-level validators (preflight's
    per-(book,column) segment/columns.json bookkeeping) see an ordinary
    one-segment-per-column shape, even though play-line's citation grammar
    itself has no page/column axis at all (a reader jump resolves by
    printed lineref, client-side — shared/lib/citation.ts's play-line
    scheme and Reader.svelte, never by this internal column string)."""
    seg_ids_seen: dict[str, int] = {}
    _SEGMENT_LINE_CAP = 40
    # John, 2026-09-11 (Persians 83): a long speech cut at an arbitrary 40th
    # line opened a segment whose English only began at the translator's
    # next marker, a gap in both columns and a sentence broken across rows.
    # With the primary English's speech-block starts known (`cut_lines`), a
    # speech past the cap is cut only where the English opens a block; past
    # the ceiling (a long messenger speech the translator never breaks), at
    # the next line the English marks at all (`marked_lines`), so the new
    # segment still opens where its English does; at the hard stop regardless.
    _SEGMENT_LINE_CEILING = 80
    _SEGMENT_LINE_STOP = 100
    segments: list[dict] = []
    cur: dict | None = None
    for i, entry in enumerate(flat, start=1):
        starts_new_speaker = bool(entry.get("speakers")) and entry["speakers"][0]["offset"] == 0
        over = cur is not None and len(cur["lines"]) >= _SEGMENT_LINE_CAP
        if over and cut_lines is not None:
            # Printed refs compared whole ("85a" is not "85"); a joined
            # ("173-174") or lacuna ("post 1241") ref never opens a segment,
            # not even at the hard stop (Grok review of fa76916).
            ref = str(entry.get("ref", ""))
            numbered = re.fullmatch(r"\d+[a-z]?", ref) is not None
            if len(cur["lines"]) >= _SEGMENT_LINE_STOP:
                over = numbered
            else:
                over = ref in cut_lines or (
                    len(cur["lines"]) >= _SEGMENT_LINE_CEILING
                    and numbered and (marked_lines is None or ref in marked_lines)
                )
        if cur is not None and (starts_new_speaker or over):
            segments.append(cur)
            cur = None
        if cur is None:
            # A repeated printed ref (citation.repeated_refs) may open two
            # segments; ids must stay unique, so the second gets ".2" etc.
            seg_id = f"1:{entry['ref']}"
            seg_ids_seen[seg_id] = seg_ids_seen.get(seg_id, 0) + 1
            if seg_ids_seen[seg_id] > 1:
                seg_id = f"{seg_id}.{seg_ids_seen[seg_id]}"
            cur = {"id": seg_id, "book": 1, "column": entry["ref"], "lines": []}
        line_entry: dict = {"n": i, "text": entry["text"], "ref": entry["ref"]}
        if entry.get("joined"):
            line_entry["joined"] = True
        if entry.get("role"):
            line_entry["role"] = entry["role"]
        if entry.get("label"):
            line_entry["label"] = entry["label"]
        cur["lines"].append(line_entry)
        for m in entry.get("speakers", []):
            cur.setdefault("speakers", []).append({"line": i, "offset": m["offset"], "label": m["label"]})
    if cur is not None:
        segments.append(cur)
    return segments


def _parse_spine_play(xml_path: Path, manifest: Manifest, sch) -> dict:
    """`parse_spine`'s play-line counterpart (mirrors CPR's
    `_parse_spine_verse`): parses the flat export, rejoins hyphenated
    words, checks the manifest's declared `citation.lacunae`/
    `citation.transpositions` against what was actually observed
    (bidirectional — an undeclared OR a stale declaration both fail
    loudly), and groups the result into per-speech segments."""
    tree = etree.parse(str(xml_path))
    _check_sourcedesc(tree, manifest, xml_path)
    flat = _parse_play(tree, sch, manifest, xml_path)
    _rejoin_play_line_hyphens(flat)

    doc_refs = [e["ref"] for e in flat]
    found_lacunae = {e["ref"] for e in flat if e.get("role") == "lacuna"}
    citation = manifest.data.get("citation") or {}
    declared_lacunae = set((citation.get("lacunae") or {}).get("1") or [])
    undeclared = found_lacunae - declared_lacunae
    stale = declared_lacunae - found_lacunae
    if undeclared or stale:
        raise ValueError(
            f"{manifest.work_id}: lacuna declaration mismatch against "
            f"citation.lacunae['1'] — undeclared (observed but not "
            f"declared): {sorted(undeclared) or 'none'}; stale (declared "
            f"but not observed): {sorted(stale) or 'none'}"
        )

    declared_transpositions = citation.get("transpositions")
    if not isinstance(declared_transpositions, dict) or "1" not in declared_transpositions:
        raise ValueError(
            f"{manifest.work_id}: citation.transpositions['1'] is required "
            f"for a play-line work — declare the derived block list (an "
            f"explicit empty list is fine once verified to have none); "
            f"omission is a fail-open hazard, not a supported bootstrapping "
            f"state"
        )
    observed_blocks = _derive_play_line_transposed_blocks(doc_refs)
    declared_blocks = declared_transpositions["1"]
    if declared_blocks != observed_blocks:
        raise ValueError(
            f"{manifest.work_id}: transposition mismatch against "
            f"citation.transpositions['1'] — observed {observed_blocks!r} "
            f"but manifest declares {declared_blocks!r}"
        )

    marks = _english_line_marks(manifest)
    segments = _segment_play_lines(flat, *(marks or (None, None)))
    return {
        "work": manifest.work_id,
        "edition": manifest.data["work"]["greek_edition"],
        "segments": segments,
        "headings": [],
        "unassigned_lines": [],
    }


def _check_sourcedesc(tree, manifest: Manifest, xml_path) -> None:
    """FATAL gate (Wave 1c Sol nit): the export XML's own <teiHeader>
    <sourceDesc> text must CONTAIN this work's manifest-declared
    `work.expected_sourcedesc` substring -- an author-name + edition
    fragment in the exact wording Diogenes' own export prints (e.g.
    "Anaxagoras Phil." + "Die Fragmente der Vorsokratiker, vol. 2",
    verified against the export at manifest-authoring time). Catches a
    wrong-author or wrong-edition re-export at the earliest possible
    point: a stale TLG_DIR pointing at a DIFFERENT author's numbered file
    (e.g. TLG0635 Stoic Zeno re-exported in place of TLG0595 Zeno of
    Elea -- both plausibly named "Zeno" in a casual export run) would
    otherwise silently parse as if it were the declared philosopher's own
    corpus; every div/column mechanism downstream has no way to know the
    text is simply the wrong work. Declared per-work (not hardcoded here)
    so a differently-shaped sourceDesc (a different scheme, a PHI Latin
    work, ...) needs no special-casing.

    Optional: a work with no `work.expected_sourcedesc` declared skips
    this check entirely -- not every work has been backfilled with it."""
    expected = manifest.data.get("work", {}).get("expected_sourcedesc")
    if not expected:
        return
    nodes = tree.findall(".//{*}sourceDesc")
    actual = " ".join(
        re.sub(r"\s+", " ", "".join(node.itertext())).strip() for node in nodes
    )
    if expected not in actual:
        raise ValueError(
            f"{xml_path or manifest.work_id}: export XML's <sourceDesc> "
            f"does not contain the manifest-declared work.expected_sourcedesc "
            f"{expected!r} -- got {actual!r}. A wrong-author or wrong-edition "
            f"re-export (e.g. a stale TLG_DIR pointing at a different "
            f"numbered file) must fail loudly here, not silently parse as if "
            f"it were the declared work's own corpus."
        )


def parse_spine(xml_path: Path, manifest: Manifest) -> dict:
    sch = scheme_mod.for_manifest(manifest)
    if sch.play_line_scheme:
        # play-line (P1 — docs/p1-probe.md): a wholly separate flow, like
        # CPR's verse-line/_parse_spine_verse — its flat, wrapping-div-less
        # export and per-speech (not per-column) segment grouping share
        # nothing with the generic page/section walk + book/column grouping
        # below, so it never enters that shared tail at all.
        return _parse_spine_play(xml_path, manifest, sch)
    tree = etree.parse(str(xml_path))
    _check_sourcedesc(tree, manifest, xml_path)
    # The citation scheme selects the export shape and column-token grammar:
    #   - bekker       : <div type="Bekker-page" n="16a"> holds <l> directly.
    #   - busse        : <div type="page" n="1"> -> synthetic a-side column
    #                    "1a" (Porphyry's Isagoge; reader relabels the gutter).
    #   - stephanus    : <div type="Stephanus-page" n="2"> nests
    #                    <div type="section" n="a"> -> column "2a"; lines
    #                    restart per section; inline
    #                    <label type="speaker"> turn markers.
    #   - book-section : <div type="Book" n="4"> nests <div type="chapter"
    #                    n="23"> -> column "4.23"; no <l> lines at all (plain
    #                    <p> prose), so the whole chapter flattens to one
    #                    synthetic line (see _parse_flat_book_section).
    #   - section      : <div type="Chapter" n="5"> at the TOP LEVEL (no Book
    #                    wrapper) -> column "5"; a nested <div type="section">
    #                    flattens into the chapter the same way (see
    #                    _parse_flat_chapter). Bookless — every column is
    #                    assigned to the work's single declared book below.
    # philosopher_headers is only ever populated by the book-section branch
    # (Diogenes Laertius' "t18-47" philosopher-heading stubs — see
    # _parse_flat_book_section); every other scheme leaves it empty, and the
    # returned spine dict omits the key entirely in that case (see below).
    philosopher_headers: list[dict] = []
    if sch.flat_numeric:
        flat, headings = _parse_flat_chapter(tree, sch, manifest, xml_path)
    elif sch.numeric_section:
        flat, headings, philosopher_headers = _parse_flat_book_section(tree, sch, manifest)
    elif sch.fragment_scheme:
        # dk (Diels-Kranz): the scheme stays registered (scheme.py), but its
        # walker (_parse_fragments) was corpus-specific with no drama use and
        # was removed in the drama fork (docs/plan.md §1).
        raise NotImplementedError(
            f"scheme {sch.name!r} has no stage1_greek walker in drama_pipeline"
        )
    elif sch.has_sections:
        flat, headings = _parse_flat_stephanus(tree, sch)
    else:
        flat, headings = _parse_flat_bekker(tree, sch)

    # Rejoin hyphenated words: a line ending in "-" takes the first
    # whitespace-delimited token of the next line (which may sit in the next
    # section or page). Consuming that token off the FRONT of the next line
    # shifts any speaker markers on it left by the removed prefix length.
    # Book-section's synthetic per-chapter line is not a physical print-line
    # wrap artifact (no editions hyphenate across chapters), so this rejoin
    # would only ever misfire by splicing one chapter's trailing "-" onto the
    # next chapter's opening word; skip it for that scheme entirely. `section`
    # (Epictetus' Enchiridion) is the same synthetic-per-chapter-line shape.
    # dk's role-tagged blocks are likewise not physical print-line wraps —
    # excluded for the same reason, PLUS adjacent flat[] entries can belong
    # to two DIFFERENT fragments (no book/column boundary check here), so
    # splicing across that boundary would corrupt an unrelated fragment.
    for i, line in enumerate([] if (sch.numeric_section or sch.flat_numeric or sch.fragment_scheme) else flat):
        if not line["text"].endswith("-"):
            continue
        if i + 1 >= len(flat) or not flat[i + 1]["text"]:
            raise ValueError(
                f"hyphenated line with no continuation: {line['column']}{line['n']}"
            )
        nxt = flat[i + 1]
        head, _, rest = nxt["text"].partition(" ")
        # No Greek-letter guard on this loop's JOIN (see the comment above),
        # but the sigma FOLD keeps the same guard the other three sites have
        # (Sol review WARN, 2026-08-29): fold a line-end ς only when the
        # absorbed continuation begins with a Greek letter — a ς before an
        # apostrophe/bracket continuation is genuinely word-final and must
        # stay ς. Zero corpus occurrences today; this is a tripwire-grade
        # guard, not a behavior change.
        fragment = line["text"][:-1]
        if fragment and head and _is_greek_letter(head[0]):
            fragment = _fold_hyphen_final_sigma(fragment)
        line["text"] = fragment + head
        line["joined"] = True
        removed = len(nxt["text"]) - len(rest)
        nxt["text"] = rest
        for m in nxt.get("speakers", []):
            m["offset"] = max(0, m["offset"] - removed)

    # Group into per-(book, column) segments, preserving document order.
    segments: list[dict] = []
    seg_by_key: dict[tuple, dict] = {}
    unassigned: list[dict] = []
    for line in flat:
        # Section schemes (stephanus) assign a whole section to one book by its
        # (page, letter) column — boundaries are page-initial and the per-section
        # line numbers are editorial. Line-bearing schemes (bekker) split a
        # book-straddling column by line number. `section` is bookless — every
        # column belongs to the work's single declared book (1), with no
        # manifest book-table lookup at all (its column token, a bare integer,
        # carries no book-boundary grammar for book_for_column to parse).
        if sch.flat_numeric or sch.fragment_scheme:
            # Bookless (dk mirrors `section`'s single-declared-book shape —
            # see scheme.py's dk module doc): no manifest book-table lookup
            # at all, since a dk column ("B30") carries no book-boundary
            # grammar for book_for_column to parse.
            book = 1
        elif sch.has_sections:
            book = manifest.book_for_column(line["column"])
        else:
            book = manifest.book_for_line(line["column"], line["n"])
        if book is None:
            unassigned.append(line)
            continue
        key = (book, line["column"])
        seg = seg_by_key.get(key)
        if seg is None:
            seg = {
                "id": f"{book}:{line['column']}",
                "book": book,
                "column": line["column"],
                "lines": [],
            }
            seg_by_key[key] = seg
            segments.append(seg)
        entry = {"n": line["n"], "text": line["text"]}
        if line.get("joined"):
            entry["joined"] = True
        if "sec" in line:
            entry["sec"] = line["sec"]
        if "wrap" in line:
            entry["wrap"] = line["wrap"]
        if "wrapO" in line:
            entry["wrapO"] = line["wrapO"]
        if "indent" in line:
            entry["indent"] = line["indent"]
        if line.get("sections"):
            entry["sections"] = line["sections"]
        if line.get("role"):
            entry["role"] = line["role"]
        seg["lines"].append(entry)
        # Speaker turn events for this line, keyed by line number within the
        # segment (column). Emitted per-segment so the reader can render the
        # speaker at the char offset where the turn's speech begins.
        for m in line.get("speakers", []):
            seg.setdefault("speakers", []).append(
                {"line": line["n"], "offset": m["offset"], "label": m["label"]}
            )

    return {
        "work": manifest.work_id,
        "edition": manifest.data["work"]["greek_edition"],
        "segments": segments,
        "headings": headings,
        "unassigned_lines": unassigned,
        # Present only for a work whose Greek TEI carries philosopher-heading
        # stubs (Diogenes Laertius); every other work omits the key entirely
        # (stage7_emit's emit_philosophers treats absence/emptiness as "emit
        # nothing" — zero-diff for every work that isn't Diogenes Laertius).
        **({"philosopher_headers": philosopher_headers} if philosopher_headers else {}),
    }


def run(manifest: Manifest) -> Path:
    xml_path = run_export(manifest)
    spine = parse_spine(xml_path, manifest)
    out = BUILD_DIR / "stage1" / "greek_spine.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spine, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
