"""Stage 6: build the search index for the Astro frontend.

Emits these files under build/stage6/, in the shapes the Aristotle reader's
search reads (its pipeline/aristotle_pipeline/stage6_search.py):

  greek_lemma.json — {fold(key, language): [[seg_idx, token_pos], ...]}
                 keyed by the token's dictionary HEADWORD (lemma), so a query
                 finds every inflected form of a word. fold() strips all
                 accents/marks, so wildcard prefix matching works uniformly.

  greek_form.json  — {fold(surface, language): [[seg_idx, token_pos], ...]}
                 keyed by the SURFACE form as written (the inflected token), so
                 a query can match the exact form rather than the whole lemma.

  meta.json    — [{id, book, column, head, tokens, english_head, english_slots}]
                 Ordered list of segment metadata, indexed by seg_idx.
                 head: first line of text (for result preview).
                 tokens: space-joined fold token sequence (phrase search).
                 english_head: the FULL primary chunk (legacy name).
                 english_slots: full non-primary texts by translation id.

  offsets.json — the global token offset primitive, with one `chapter_bounds`
                 entry per SPEECH and `turn_bounds` for the same speeches
                 (speeches.py: the plays count by speech, John 2026-11-16).
  speeches.json — every speech with its cue, name, title and line span, for
                 stage 7's chapters.json, chapter-titles.json and
                 eng-chapters.json.
  running.json — the Greek as one running text (running_text.py).

The English indexes (english.json, english-<slot>.json, eng-chapters.json)
are written by stage 7 through emit_translation_indexes below, from the
emitted books: the text the reader shows.

Stage 7 also copies offsets.json, grammar-dict.json, and grammar-col.bin to
build/dist/<work>/search/. They share one global token offset space.
Reference builds write form/lemma streams to build/ngrams/<work>.json and
merge shipped analyses into build/dist/lemma-map/<letter>.json shards.
"""

from __future__ import annotations

import json
import re
import struct
import unicodedata
from collections import defaultdict
from pathlib import Path

from . import scheme as scheme_mod
from . import speeches as speeches_mod
from .config import BUILD_DIR, Manifest, private_translation_ids
from .running_text import build_running_text, check_alignment, spells_a_letter
from .stage2_validate import check_grammar, check_ngram_streams, check_offsets

_FOLD = re.compile(r"[^a-z']")  # keep only base letters and apostrophe
_EN_WORD = re.compile(r"[a-z']+")

# The archive translations print possessives and contractions with U+2019
# (Aristotle’s, isn’t); U+02BC is the modifier-letter apostrophe. The reader
# folds a typed straight apostrophe to itself (englishFold) and the text's
# curly one to straight (englishWords) — so the index must key "aristotle's"
# as one word or neither path can find it.
_EN_APOSTROPHE = re.compile("[\u2019\u02bc]")
# Apparatus a translation's prose carries inline, which the reader renders as
# controls and not as words: a footnote marker [^1.9] is glued to the word
# before it and is simply dropped; a sidenote or figure marker [[s3]] / [[fig1]]
# stands between words and leaves a space. Indexed as text, [[s3]] was the word
# "s" and broke every phrase that ran across it. (Ported from the Aristotle
# reader, whose translations carry these markers.)
_EN_FOOTNOTE = re.compile(r"\[\^[0-9A-Za-z_.*\u2020]+\]")
_EN_SIDENOTE = re.compile(r"\[\[(?:s|fig)[0-9]+\]\]")
# One pass, so a marker counts only as written: "[[s[^1]12]]" loses its
# footnote and keeps "[[s12]]" as text, never a sidenote, as the reader shows
# it: the footnote becomes a button and the rest stays prose. englishWords
# scans the same.
_EN_MARKER = re.compile(f"(?P<fn>{_EN_FOOTNOTE.pattern})|{_EN_SIDENOTE.pattern}")
# Older translations print Latin letters the fold would otherwise split on:
# "Lacedæmonians" was indexed as "laced" + "monians", "versâ" as "vers". The
# ligatures become two letters and accents drop off, so the word is the one a
# reader types, as latinFold in shared/lib/search.ts folds it.
_EN_COMBINING = re.compile("[\u0300-\u036f]")


def _latin_fold(text: str) -> str:
    text = _EN_COMBINING.sub("", unicodedata.normalize("NFD", text))
    return text.replace("\u00e6", "ae").replace("\u0153", "oe")


def english_words(text: str) -> list[str]:
    """The English word stream as the reader's fold sees it: lowercase, curly
    apostrophes made straight, split on anything outside [a-z']. An apostrophe
    at a word's edge is a quotation mark (‘change’ closes with the same U+2019
    that Aristotle’s elides with) and is not part of the word. Used by
    stage8 for phrase counts and english-segments.json. The existing English
    search index keeps its own word split and translation-id postings.
    Inline footnote, sidenote and figure markers are not words (see
    _EN_FOOTNOTE). Ligatures and accented letters fold to plain ones (see
    _latin_fold)."""
    text = _EN_MARKER.sub(lambda m: "" if m.group("fn") else " ", text)
    words = _EN_WORD.findall(_latin_fold(_EN_APOSTROPHE.sub("'", text).lower()))
    return [w for w in (raw.strip("'") for raw in words) if w]


# -- Morphology feature vocabulary -------------------------------------------
# Derived from what stage4 actually emits. `parse` is a raw Morpheus string
# ("pres ind act 2nd sg (doric aeolic)") with parentheses glued to the first and
# last word of a qualifier run, so strip the parens and classify word by word.
#
# There is deliberately NO part-of-speech category. Morpheus emits no
# noun/verb/adjective field, and inferring one from feature presence would
# overstate the data: participles carry both nominal and verbal morphology, and
# nouns and adjectives are indistinguishable here. Only Morpheus's own explicit
# markers are indexed, under "marker". Note that `part` is the PARTICIPLE mood,
# not `particle` — they are different tags and must not be conflated.
#
# Dialect words (attic, epic, doric, …) and clitic/format markers (enclitic,
# nu_movable, indeclform, …) are not queryable features and are skipped. Two
# analyses differing only by dialect collapse to one reading, which is right:
# they are the same morphological reading.
_FEATURES: dict[str, str] = {
    value: category
    for category, values in {
        "gender": "masc fem neut masc/fem masc/neut masc/fem/neut",
        "case": "nom gen dat acc voc nom/acc nom/voc nom/voc/acc gen/dat",
        "number": "sg pl dual",
        "person": "1st 2nd 3rd",
        "tense": "pres imperf fut aor perf plup futperf",
        "mood": "ind subj opt imperat inf part",
        "voice": "act mid pass mp",
        "degree": "comp superl irreg_comp",
        "marker": "adverb adverbial particle prep conj interrog exclam indecl numeral letter",
    }.items()
    for value in values.split()
}

# Reserved signature ids, so the column stays aligned with the offset space
# even where there is nothing to say about a token.
SIG_UNKEYED = 0     # token had no Beta Code key (stage3 key failure)
SIG_UNANALYSED = 1  # key resolved, but Morpheus returned no analysis


def parse_reading(parse: str) -> dict[str, list[str]]:
    """One Morpheus parse string -> {category: [values]}.

    Syncretic values expand INSIDE the reading (nom/voc/acc -> nom, voc, acc).
    A single analysis spanning three cases is genuinely three-way ambiguous and
    must never be reported as one certain parse — that expansion is what makes
    the ambiguity count honest rather than a count of analysis records.
    """
    reading: dict[str, list[str]] = {}
    for word in parse.replace("(", " ").replace(")", " ").split():
        category = _FEATURES.get(word)
        if category is None:
            continue
        values = reading.setdefault(category, [])
        for value in word.split("/"):
            if value not in values:
                values.append(value)
    return {c: sorted(v) for c, v in reading.items()}


def signature(entries: list[dict]) -> tuple:
    """The distinct readings a token's analyses license, canonically ordered.

    Whole readings are kept rather than a per-category union, so correlations
    survive: analyses {masc nom sg, fem acc pl} must not satisfy a query for
    masc + acc + sg, which a flattened union would wrongly allow.
    """
    readings = []
    for entry in entries:
        reading = parse_reading(entry.get("parse") or "")
        if not reading:
            continue
        key = tuple((c, tuple(v)) for c, v in sorted(reading.items()))
        if key not in readings:
            readings.append(key)
    return tuple(sorted(readings))




def slot_text(chunks: object) -> str:
    """Use the same ordered text for indexing and client-side snippets."""
    if isinstance(chunks, dict):
        return chunks.get("text", "")
    if isinstance(chunks, list):
        return "\n".join(c.get("text", "") for c in chunks if isinstance(c, dict))
    return ""


# -- English indexes, in the Aristotle reader's shapes -------------------------
#
# One index per translation, so a query asking for every word to be present
# asks it of one translator's prose: english.json for the primary,
# english-<slot>.json beyond it ('secondary', 'third', 'overlay-<id>'), each
# {word: [[seg_idx, word_pos], ...]} with word_pos counted as english_words
# counts the segment's text for that slot (pieces run on, no reset), as the
# reader's englishWords counts translationTexts(). Stage 7 calls
# emit_translation_indexes after writing the books, so the words are the ones
# the reader shows.

# An overlay id names a file and a shard source; the plays' ids carry hyphens
# (murray-verse), which Aristotle's [a-z0-9_]+ refused.
_OVERLAY_ID = re.compile(r"[a-z0-9_-]+")

# A speaker cue as the reader finds it in a comparison translation's text
# (extractPrefixedEnglishTurns, shared/lib/speakers.ts): a name of up to 80
# characters at the start of the text or after a blank line, then a full stop.
_CUE = re.compile(r"(^|\n{2,})([^.\n]{1,80})\.\s+")


def _cue_norm(value: str) -> str:
    return re.sub(r"[\W_]+", " ", (value or "").lower()).strip()


def segment_pieces(seg: dict) -> dict[str, list[dict]]:
    """The non-primary translation pieces of one emitted segment, by slot:
    'secondary' (emitted as `ross`; both are read), 'third', 'overlay-<id>'."""
    out: dict[str, list[dict]] = {}
    secondary = seg.get("secondary") or seg.get("ross")
    if secondary:
        out["secondary"] = secondary
    if seg.get("third"):
        out["third"] = seg["third"]
    for tid, pieces in (seg.get("overlays") or {}).items():
        if not _OVERLAY_ID.fullmatch(tid):
            raise ValueError(f"overlay id {tid!r} cannot name an index file")
        if pieces:
            out[f"overlay-{tid}"] = pieces
    return out


def translation_index_name(slot: str) -> str:
    return "english.json" if slot == "english" else f"english-{slot}.json"


def segment_texts(seg: dict) -> dict[str, list[str]]:
    """Every translation's text of one emitted segment, by slot, primary
    ('english') included, as the reader's translationTexts() returns it."""
    out = {slot: [p.get("text") or "" for p in pieces] for slot, pieces in segment_pieces(seg).items()}
    text = (seg.get("english") or {}).get("text")
    if text:
        out["english"] = [text]
    return out


def segment_cue_words(seg: dict, roster: list[str]) -> dict[str, list[int] | None]:
    """Where each speaker cue of each translation begins in one segment, as
    a word position of that slot's index. The primary's cues are its
    `english.turns` (character offsets into its text); a comparison
    translation's are found in its pieces' text the way the reader finds
    them. None for a slot where a cue falls inside a word."""
    out: dict[str, list[int] | None] = {}
    eng = seg.get("english") or {}
    if eng.get("text"):
        text = eng["text"]
        whole = english_words(text)
        at: list[int] | None = []
        for turn in eng.get("turns") or []:
            off = turn["offset"]
            before = english_words(text[:off])
            if before + english_words(text[off:]) != whole:
                at = None
                break
            at.append(len(before))
        out["english"] = at
    for slot, pieces in segment_pieces(seg).items():
        pos, at = 0, []
        for piece in pieces:
            text = piece.get("text") or ""
            known = {_cue_norm(n) for n in [*roster, *(piece.get("cueSpeakers") or [])]}
            for m in _CUE.finditer(text):
                label = m.group(2).strip()
                if _cue_norm(label) in known or (
                    sum(c.isalpha() for c in label) >= 2 and label == label.upper()
                ):
                    at.append(pos + len(english_words(text[:m.start(2)])))
            pos += len(english_words(text))
        out[slot] = at
    return out


def speech_starts(
    seg: dict, si: int, opening: dict, cued: list[dict], roster: list[str]
) -> tuple[dict[str, list[list]], dict[str, str]]:
    """eng-chapters entries for one emitted segment: per slot, where each
    speech that starts in the segment begins in that translation's words,
    [[word_pos, speech name], ...].

    `opening` is the speech in force at the segment's first Greek token (the
    client's fallback for words before the first listed start), `cued` the
    speeches whose cues stand in the segment, in order. A segment holding one
    speech needs no entry. Where it holds more, a translation is split only
    when it carries exactly as many speaker cues in the segment as the Greek
    has: cue i then opens speech i. The names may differ (a translator gives
    a line to another speaker; John 2026-09-29 keeps the translation's own
    colour there), the order still pairs them. Otherwise the segment is left
    out and every word of it counts in `opening`.

    Returns (entries, outcome by slot: 'split' or 'fallback'; slots of a
    one-speech segment are not reported).
    """
    names = {opening["name"], *(sp["name"] for sp in cued)}
    entries: dict[str, list[list]] = {}
    outcome: dict[str, str] = {}
    if len(names) < 2:
        return entries, outcome
    for slot, at in segment_cue_words(seg, roster).items():
        if at is not None and cued and len(at) == len(cued):
            entries[slot] = [[pos, sp["name"]] for pos, sp in zip(at, cued)]
            outcome[slot] = "split"
        else:
            outcome[slot] = "fallback"
    return entries, outcome


def emit_translation_indexes(
    work_dir: Path, speeches: list[dict], excluded: set[str] = frozenset()
) -> dict[str, dict[str, int]]:
    """Write search/english.json, english-<slot>.json and eng-chapters.json.

    Reads the work's emitted book-NN.json and search/meta.json, which must
    already be in place; seg_idx is a segment's position in meta.json.
    `speeches` is stage 6's speeches.json. `excluded` names slots never to
    index (a private translation). Any english*.json or eng-chapters.json
    left from an earlier build is removed first, so an index can never
    outlive its translation. Returns, per slot, the words and segments
    indexed and how many multi-speech segments were split or left to the
    client's fallback.
    """
    search_dir = work_dir / "search"
    meta = json.loads((search_dir / "meta.json").read_text(encoding="utf-8"))
    seg_idx = {m["id"]: i for i, m in enumerate(meta)}
    # The speech in force at each segment's first token, and the cued
    # speeches standing in each segment.
    by_seg: dict[int, list[dict]] = defaultdict(list)
    for sp in speeches:
        if sp["cued"]:
            by_seg[sp["seg"]].append(sp)
    offsets = json.loads((search_dir / "offsets.json").read_text(encoding="utf-8"))
    base = offsets["seg_base_offset"]
    if speeches and [(sp["name"], sp["start"]) for sp in speeches] != [
        (c["chapter"], c["start"]) for c in offsets["chapter_bounds"]
    ]:
        raise ValueError(f"{work_dir.name}: speeches.json disagrees with search/offsets.json — stale stage 6")

    posts: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    segments: dict[str, set[int]] = defaultdict(set)
    chapters: dict[str, dict[str, list]] = defaultdict(dict)
    outcomes: dict[str, dict[str, int]] = defaultdict(lambda: {"split": 0, "fallback": 0})
    k = 0
    for book_path in sorted(work_dir.glob("book-*.json")):
        doc = json.loads(book_path.read_text(encoding="utf-8"))
        roster = doc.get("speakerRoster") or []
        for seg in doc["segments"]:
            si = seg_idx.get(seg["id"])
            if si is None:
                raise ValueError(f"{book_path.name}: segment {seg['id']} is not in search/meta.json")
            while k + 1 < len(speeches) and speeches[k + 1]["start"] <= base[si]:
                k += 1
            texts = {slot: t for slot, t in segment_texts(seg).items() if slot not in excluded}
            for slot, chunks in texts.items():
                pos = 0
                for text in chunks:
                    for word in english_words(text):
                        posts[slot][word].append([si, pos])
                        pos += 1
                if pos:
                    segments[slot].add(si)
            if speeches:
                entries, outcome = speech_starts(seg, si, speeches[k], by_seg.get(si, []), roster)
                for slot, at in entries.items():
                    if slot in texts:
                        chapters[slot][str(si)] = at
                for slot, how in outcome.items():
                    if slot in texts:
                        outcomes[slot][how] += 1

    for stale in [*search_dir.glob("english*.json"), search_dir / "eng-chapters.json"]:
        stale.unlink(missing_ok=True)
    (search_dir / "eng-chapters.json").write_text(
        json.dumps(chapters, ensure_ascii=False), encoding="utf-8"
    )
    summary: dict[str, dict[str, int]] = {}
    for slot in sorted(posts):
        # In document order, as Aristotle's english.json is.
        index = {word: sorted(plist) for word, plist in posts[slot].items()}
        (search_dir / translation_index_name(slot)).write_text(
            json.dumps(index, ensure_ascii=False), encoding="utf-8"
        )
        summary[slot] = {"words": len(posts[slot]), "segments": len(segments[slot]),
                         **outcomes[slot]}
    return summary


def build_lemma_map(current: dict, work_id: str, build_dir: Path = BUILD_DIR) -> None:
    """Merge shipped analyses into fold(form) -> [fold, printed headword] shards."""
    forms: dict[str, dict[str, str]] = defaultdict(dict)
    paths = (build_dir / "dist").glob("*/analyses.json")
    for path in paths:
        if path.parent.name == work_id:
            continue
        add_analyses(forms, json.loads(path.read_text(encoding="utf-8")))
    add_analyses(forms, current)
    shards: dict[str, dict[str, list[list[str]]]] = defaultdict(dict)
    for surface, lemmata in forms.items():
        shards[surface[0] if surface[0].isalpha() else "_"][surface] = sorted(
            [folded, display] for folded, display in lemmata.items()
        )
    out = build_dir / "dist" / "lemma-map"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.json"):
        old.unlink()
    for letter, values in shards.items():
        (out / f"{letter}.json").write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")


def add_analyses(forms: dict[str, dict[str, str]], analyses: dict) -> None:
    for surface, parses in analyses.items():
        key = fold_lemma(surface)
        if not key:
            continue
        for parse in parses:
            head = parse.get("lemma")
            if head:
                folded = fold_lemma(head)
                if folded:
                    for surface in (key, folded):
                        old = forms[surface].get(folded)
                        # Prefer an accented spelling and make the choice stable
                        # when works supply more than one spelling of a fold.
                        forms[surface][folded] = min(
                            (old, head) if old is not None else (head,),
                            key=lambda value: (not any(c in value for c in "/\\=()|+"), value),
                        )


def fold_lemma(beta_key: str) -> str:
    """Strip all Beta Code diacritics; keep only base letters + apostrophe.
    Greek-specific — dispatched to via fold() below; Latin has its own fold
    (latin.fold) with different rules (u/v and i/j unification, memo §4.1)."""
    return _FOLD.sub("", beta_key.lower())


def fold(key: str, language: str) -> str:
    """Per-language search-fold dispatch (memo §2: generic index filenames
    and segment fields, but per-language fold functions). drama_pipeline
    supports 'grc' only — Latin support (latin.fold) was removed in the
    drama fork. An unrecognized language raises rather than silently
    defaulting to the Greek fold (the same fail-loud posture as stage3's
    tokenize() and stage4's _analyses_path for an unsupported
    work.language)."""
    if language == "grc":
        return fold_lemma(key)
    raise ValueError(f"unsupported language: {language!r}")


def run(manifest: Manifest) -> Path:
    language = manifest.language
    tokens_doc = json.loads(
        (BUILD_DIR / "stage3" / "tokens.json").read_text(encoding="utf-8")
    )
    key_map = json.loads(
        (BUILD_DIR / "stage4" / "key_map.json").read_text(encoding="utf-8")
    )
    analyses = json.loads(
        (BUILD_DIR / "stage4" / "analyses.json").read_text(encoding="utf-8")
    )
    # A genuinely Greek-only work (see stage7_emit.run's matching fallback)
    # has no english_chunks.json at all.
    english_path = BUILD_DIR / "stage1" / "english_chunks.json"
    english = (json.loads(english_path.read_text(encoding="utf-8"))
               if english_path.exists() else {"chunks": []})

    # Ordered segment list for index keys
    segments = tokens_doc["segments"]
    seg_idx = {s["id"]: i for i, s in enumerate(segments)}

    eng_by_id = {c["id"]: c for c in english["chunks"]}
    english_block = manifest.data.get("english") or {}
    private = private_translation_ids(manifest.data)
    slot_chunks: dict[str, dict] = {}
    primary_id = (english_block.get("primary") or {}).get("id")
    for slot, filename in (("primary", "english_chunks.json"),
                           ("secondary", "ross_chunks.json"),
                           ("third", "third_chunks.json")):
        entry = english_block.get(slot)
        path = BUILD_DIR / "stage1" / filename
        if not entry or entry.get("private") or entry.get("id") in private or not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        slot_chunks[entry["id"]] = ({c["id"]: c for c in doc["chunks"]}
                                     if slot == "primary" else doc)
    overlays_path = BUILD_DIR / "stage1" / "overlays.json"
    overlays = json.loads(overlays_path.read_text(encoding="utf-8")) if overlays_path.exists() else {}
    for entry in english_block.get("overlays") or []:
        if not entry.get("private") and entry.get("id") not in private:
            slot_chunks[entry["id"]] = overlays.get(entry["id"], {})

    # Token fold sequences per segment — needed by the client for phrase search.
    # One space-separated string of fold lemma keys in document order.
    fold_seq_by_id: dict[str, str] = {}
    for seg in segments:
        folds = []
        for line in seg["lines"]:
            for tok in line["tokens"]:
                key = tok.get("k")
                stored = key_map.get(key) if key else None
                if stored:
                    lemmata = [a["lemma"] for a in analyses.get(stored, []) if a["lemma"]]
                    if lemmata:
                        folds.append(fold(lemmata[0], language))
                    else:
                        folds.append(fold(stored, language))
                elif key:
                    folds.append(fold(key, language))
        fold_seq_by_id[seg["id"]] = " ".join(folds)

    # -- Source-language inverted indexes -------------------------------------
    # Two parallel indexes, both fold(key, language) -> [(seg_idx, token_pos), ...]:
    #   lemma_posts: keyed by each token's dictionary headword(s) — "all forms".
    #   form_posts:  keyed by the token's surface form as written — "exact form".
    lemma_posts: dict[str, list] = defaultdict(list)
    form_posts: dict[str, list] = defaultdict(list)
    for seg in segments:
        si = seg_idx[seg["id"]]
        pos = 0
        for line in seg["lines"]:
            for tok in line["tokens"]:
                key = tok.get("k")
                if key:
                    sf = fold(key, language)  # surface form as written
                    if sf:
                        form_posts[sf].append([si, pos])
                stored = key_map.get(key) if key else None
                if stored:
                    for a in analyses.get(stored, []):
                        fl = fold(a["lemma"], language) if a["lemma"] else fold(stored, language)
                        if fl:
                            lemma_posts[fl].append([si, pos])
                pos += 1

    # Deduplicate each index (a lemma may repeat from homonym analyses; a
    # surface key is added once per token but dedupe defensively).
    def _dedupe(posts: dict[str, list]) -> dict[str, list]:
        out: dict[str, list] = {}
        for fl, plist in posts.items():
            seen: set[tuple] = set()
            deduped = []
            for pair in plist:
                t = tuple(pair)
                if t not in seen:
                    seen.add(t)
                    deduped.append(pair)
            out[fl] = deduped
        return out

    lemma_idx = _dedupe(lemma_posts)
    form_idx = _dedupe(form_posts)

    # -- Segment metadata -----------------------------------------------------
    meta = []
    greek_only = bool(manifest.data["work"].get("edition_id"))
    for seg in segments:
        # head: join first two lines of surface text
        lines = seg["lines"]
        head = " ".join(
            " ".join(t["t"] for t in l["tokens"])
            for l in lines[:2]
        )
        eng = eng_by_id.get(seg["id"])
        # Full English chunk (NOT truncated). Query-time exact-phrase
        # verification and English occurrence counting run against this, so a
        # cap (formerly [:500]) silently dropped matches and undercounted
        # repeats past the cut. It equals the emitted segment's english.text, so
        # char offsets found here map straight onto the rendered passage.
        english_head = eng["text"] if eng and not greek_only else ""
        meta.append(
            {
                "id": seg["id"],
                "book": seg["book"],
                "column": seg["column"],
                "head": head,
                "tokens": fold_seq_by_id.get(seg["id"], ""),
                "english_head": english_head,
                "english_slots": {sid: text for sid, chunks in slot_chunks.items()
                                  if sid != primary_id and not greek_only
                                  if (text := slot_text(chunks.get(seg["id"])))},
            }
        )

    # -- Offset primitive ------------------------------------------------------
    # One running word number per work, assigned in the same document order the
    # index loop above walks. The global offset of any existing posting is
    # seg_base_offset[seg_idx] + token_pos, so no posting has to change and no
    # reverse map is needed. Counts EVERY stage3 token, keyless ones included,
    # so it stays in step with token_pos.
    # The printed citation of each line (the spine's `ref`: "106-107" for a
    # lyric pair, "1290" for a line the editor transposed). `n` is the
    # running line number, which is what nearness is measured on, but a hit is
    # cited and linked by its ref, as the reader prints it.
    spine_path = BUILD_DIR / "stage1" / "greek_spine.json"
    spine = json.loads(spine_path.read_text(encoding="utf-8")) if spine_path.exists() else None
    spine_refs: dict[str, list] = {}
    for spine_seg in (spine or {}).get("segments", []):
        spine_refs[spine_seg.get("id")] = [ln.get("ref") for ln in spine_seg.get("lines", [])]
    seg_base_offset: list[int] = []
    seg_coords: list[dict] = []
    running = 0
    for seg in segments:
        seg_base_offset.append(running)
        # line_runs lets the client turn an offset back into a play line
        # without fetching the whole book-NN.json: [n, count], or [n, count,
        # sub] where a line carries a sub-letter. n is the line as printed
        # (transposed and repeated lines included); fixtures may omit it.
        line_runs = [
            [l.get("n"), len(l["tokens"]), l["sub"]] if l.get("sub") else [l.get("n"), len(l["tokens"])]
            for l in seg["lines"]
        ]
        running += sum(r[1] for r in line_runs)
        coords = {"book": seg["book"], "column": seg["column"], "line_runs": line_runs}
        # The spine and the tokens document are parallel line for line (stage 7
        # checks it), so a line's ref is looked up by position: a number is not
        # a key (a column can print the same number twice).
        refs = spine_refs.get(seg["id"], [])
        if len(refs) != len(seg["lines"]):
            refs = [None] * len(seg["lines"])
        if any(r is not None and r != str(l.get("n")) for r, l in zip(refs, seg["lines"])):
            # Only where some line's printed ref differs from its number.
            coords["refs"] = [r if r is not None else str(l.get("n")) for r, l in zip(refs, seg["lines"])]
        seg_coords.append(coords)
    token_count = running

    # A segment is keyed (book, column) and so never straddles a book: each
    # book begins at its first segment's base.
    book_bounds: list[dict] = []
    for i, seg in enumerate(segments):
        if not book_bounds or book_bounds[-1]["book"] != seg["book"]:
            book_bounds.append({"book": seg["book"], "start": seg_base_offset[i]})

    # The plays count by speech (speeches.py), so each speech is a chapter.
    # A speech's title is its speaker's display name, which stage 7 gives the
    # spine's events (_canonicalize_play_line_speakers); it runs here too, on
    # this stage's own copy of the spine, so the names agree with the books.
    if spine is not None and scheme_mod.for_manifest(manifest).play_line_scheme:
        from .stage7_emit import _canonicalize_play_line_speakers
        _canonicalize_play_line_speakers(spine, manifest)
    speeches = speeches_mod.build_speeches(
        segments, spine["segments"] if spine is not None else None, seg_base_offset
    )
    chapter_bounds = speeches_mod.chapter_bounds(speeches)

    offsets = {
        # Doubles as a build fingerprint: every artifact indexed by global
        # offset must agree on it, or they were built from different runs.
        "token_count": token_count,
        "seg_base_offset": seg_base_offset,
        "segments": seg_coords,
        "book_bounds": book_bounds,
        "chapter_bounds": chapter_bounds,
        "turn_bounds": speeches_mod.turn_bounds(speeches),
    }

    # -- Grammatical index -----------------------------------------------------
    # A signature dictionary plus a packed column, not an inverted index:
    # grammatical predicates are anti-selective (case=gen matches ~10% of every
    # token in the corpus), so postings would go near-dense and dwarf the lexical
    # indexes. Interning readings instead gives a table of a few thousand
    # signatures and one small int per token, indexed by GLOBAL OFFSET — so the
    # column joins directly onto the offset primitive above.
    sig_ids: dict[tuple, int] = {}
    sig_list: list[tuple] = [(), ()]  # slots 0 and 1 are the reserved kinds
    column: list[int] = []
    # The n-gram source, gathered in the same walk. Two fold streams indexed by
    # global offset, keyed exactly as form.json and lemma.json are —
    # so a phrase found here is a phrase the search can find. null marks a token
    # no index can key, which breaks the stream: an n-gram may not span it.
    form_stream: list[str | None] = []
    lemma_stream: list[list[str] | None] = []
    # For the phrase index's display (stage 8): each token as printed, accents
    # and all, and the dictionary key each headword fold is most often read as,
    # whose accented headword the LSJ shards hold.
    surface_stream: list[str | None] = []
    head_keys: dict[str, defaultdict] = defaultdict(lambda: defaultdict(int))
    # Stage 4's analyses carry no LSJ keys yet; stage 5 left lemma -> keys.
    lemma_map_path = BUILD_DIR / "stage5" / "lemma_map.json"
    lsj_by_lemma = (json.loads(lemma_map_path.read_text(encoding="utf-8"))
                    if lemma_map_path.exists() else {})
    for seg in segments:
        for line in seg["lines"]:
            for tok in line["tokens"]:
                key = tok.get("k")
                form_stream.append(fold_lemma(key) or None if key else None)
                surface_stream.append(tok.get("t") if key else None)
                if not key:
                    column.append(SIG_UNKEYED)
                    lemma_stream.append(None)
                    continue
                stored = key_map.get(key)
                entries = analyses.get(stored, []) if stored else []
                # Every lemma this token licenses, not a chosen one: which lemma
                # an ambiguous position contributes is a policy the corpus pass
                # settles, and deciding it here would hide the choice.
                lemmas = sorted({
                    fold_lemma(a["lemma"]) if a["lemma"] else fold_lemma(stored)
                    for a in entries
                } - {""})
                lemma_stream.append(lemmas or None)
                for a in entries:
                    folded = fold_lemma(a["lemma"]) if a["lemma"] else fold_lemma(stored)
                    lsj_key = (a.get("lsj") or lsj_by_lemma.get(a["lemma"] or "") or [None])[0]
                    if folded and lsj_key:
                        head_keys[folded][lsj_key] += 1
                sig = signature(entries)
                if not sig:
                    column.append(SIG_UNANALYSED)
                    continue
                sid = sig_ids.get(sig)
                if sid is None:
                    sid = len(sig_list)
                    sig_ids[sig] = sid
                    sig_list.append(sig)
                column.append(sid)

    # Uint16 covers a few thousand signatures with room to spare; widen rather
    # than silently truncate if a work ever exceeds it.
    width = 4 if len(sig_list) > 0xFFFF else 2
    grammar_dict = {
        "token_count": token_count,  # must match offsets.json — same build
        "width": width,
        "categories": sorted(set(_FEATURES.values())),
        "reserved": {"unkeyed": SIG_UNKEYED, "unanalysed": SIG_UNANALYSED},
        "sigs": [
            [{category: list(values) for category, values in reading} for reading in sig]
            for sig in sig_list
        ],
    }

    streams_check = check_ngram_streams(
        form_stream, lemma_stream, form_idx, lemma_idx, seg_base_offset, token_count
    )
    offsets_check = check_offsets(offsets, segments)
    grammar_check = check_grammar(
        grammar_dict, column, offsets, segments, key_map, analyses, signature
    )
    for name, check in (("offset", offsets_check), ("grammar", grammar_check),
                        ("n-gram stream", streams_check)):
        if not check["ok"]:
            raise ValueError(
                f"stage6: {name} validation failed —\n  "
                + "\n  ".join(check["problems"][:20])
            )

    out_dir = BUILD_DIR / "stage6"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Every stage 3 token as Beta Code with the punctuation between, the n-th
    # run being global token n; built only where the spine (the printed
    # text) is at hand, which every real build has. A token with no letter
    # (an OCR edition's "…" or metrical signs, ¯˘) has no run to be, so a
    # Greek edition that keeps one goes without running-text search; in a
    # reference work it is an error, raised by build_running_text.
    (out_dir / "running.json").unlink(missing_ok=True)
    letterless = [t["t"] for seg in segments for line in seg["lines"] for t in line["tokens"]
                  if not spells_a_letter(t["t"])]
    if letterless and manifest.data["work"].get("edition_id"):
        print(f"stage6: no running.json: {len(letterless)} tokens with no letter, "
              f"e.g. {letterless[:3]}")
    elif spine is not None:
        running_text = build_running_text(segments, spine)
        check_alignment(manifest.work_id, running_text, segments, token_count)
        (out_dir / "running.json").write_text(
            json.dumps({"v": 1, "token_count": token_count, "text": running_text}, ensure_ascii=False),
            encoding="utf-8",
        )
    (out_dir / "speeches.json").write_text(
        json.dumps(speeches, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "offsets.json").write_text(
        json.dumps(offsets, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "grammar-dict.json").write_text(
        json.dumps(grammar_dict, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "grammar-col.bin").write_bytes(
        struct.pack(f"<{len(column)}{'I' if width == 4 else 'H'}", *column)
    )

    # The n-gram source goes OUTSIDE build/stage6, which is per-work scratch and
    # is overwritten by the next work. The corpus n-gram pass is the pipeline's
    # first cross-work stage and needs every work's stream present at once.
    if not manifest.data["work"].get("edition_id"):
        ngram_dir = BUILD_DIR / "ngrams"
        ngram_dir.mkdir(parents=True, exist_ok=True)
        (ngram_dir / f"{manifest.work_id}.json").write_text(
            json.dumps(
                {
                    "work": manifest.work_id,
                    # Fingerprint: the corpus pass refuses to merge streams that
                    # disagree with the offsets they are supposed to index.
                    "token_count": token_count,
                    "book_bounds": book_bounds,
                    # Phrases are counted across speeches as before: stage 8
                    # reads these bounds only to flag a phrase that straddles
                    # a chapter, and a speech is not a chapter in that sense.
                    "chapter_bounds": [],
                    "form": form_stream,
                    "lemma": lemma_stream,
                    "surface": surface_stream,
                    "heads": {
                        folded: sorted(keys.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
                        for folded, keys in head_keys.items()
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    for stale in ("lemma.json", "form.json", "english.json"):
        (out_dir / stale).unlink(missing_ok=True)
    (out_dir / "greek_lemma.json").write_text(
        json.dumps(lemma_idx, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "greek_form.json").write_text(
        json.dumps(form_idx, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    summary = {
        "lemmata": len(lemma_idx),
        "forms": len(form_idx),
        "segments": len(meta),
        "speeches": len(speeches),
        "tokens": token_count,
        "signatures": grammar_check["signatures"],
        "tokens_unanalysed": grammar_check["tokens_unanalysed"],
        "ngram_form_tokens": streams_check["form_tokens"],
        "ngram_multi_lemma": streams_check["multi_lemma_tokens"],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    (out_dir / "grammar_report.json").write_text(
        json.dumps({"offsets": offsets_check, "grammar": grammar_check}, indent=1)
    )
    if not manifest.data["work"].get("edition_id"):
        build_lemma_map(analyses, manifest.work_id, BUILD_DIR)
    return out_dir
