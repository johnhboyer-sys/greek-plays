"""Stage 6: build the search index for the Astro frontend.

Emits these files under build/stage6/ (source-language-neutral names, per
docs/wave2-latin-design.md §2/§6 — the index is a "source-language index vs
english.json" axis, not a Greek-only one):

  lemma.json — {fold(key, language): [[seg_idx, token_pos], ...]}
                 keyed by the token's dictionary HEADWORD (lemma), so a query
                 finds every inflected form of a word. fold() strips all
                 accents/marks (Greek: Beta Code diacritics; Latin: unifies
                 u/v and i/j — see fold() below), so wildcard prefix matching
                 works uniformly.

  form.json  — {fold(surface, language): [[seg_idx, token_pos], ...]}
                 keyed by the SURFACE form as written (the inflected token), so
                 a query can match the exact form rather than the whole lemma.

  english.json — {word: [[seg_idx, translation_id], ...]}
                 Every published translation gets its own posting. Phrase
                 checks use that translation's full text in meta.json.

  meta.json    — [{id, book, column, head, tokens, english_head, english_slots}]
                 Ordered list of segment metadata, indexed by seg_idx.
                 head: first line of text (for result preview).
                 tokens: space-joined fold token sequence (phrase search).
                 english_head: the FULL primary chunk (legacy name).
                 english_slots: full non-primary texts by translation id.

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

from .config import BUILD_DIR, Manifest, private_translation_ids
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

    # -- English inverted index -----------------------------------------------
    # word -> [[segment index, translation id], ...]
    eng_posts: dict[str, set] = defaultdict(set)
    for seg in segments:
        si = seg_idx[seg["id"]]
        for slot_id, chunks in slot_chunks.items():
            # The same words the phrase index (stage 8) and the reader count:
            # curly apostrophes made straight, æ as ae, edge quotes dropped.
            for word in english_words(slot_text(chunks.get(seg["id"]))):
                eng_posts[word].add((si, slot_id))
    english_idx = {w: [list(pair) for pair in sorted(pairs)] for w, pairs in eng_posts.items()}

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
    spine_refs: dict[str, list] = {}
    if spine_path.exists():
        for spine_seg in json.loads(spine_path.read_text(encoding="utf-8")).get("segments", []):
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

    chapter_bounds: list[dict] = []

    offsets = {
        # Doubles as a build fingerprint: every artifact indexed by global
        # offset must agree on it, or they were built from different runs.
        "token_count": token_count,
        "seg_base_offset": seg_base_offset,
        "segments": seg_coords,
        "book_bounds": book_bounds,
        "chapter_bounds": chapter_bounds,
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
                    lsj_key = (a.get("lsj") or [None])[0]
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
                    "chapter_bounds": chapter_bounds,
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
    (out_dir / "lemma.json").write_text(
        json.dumps(lemma_idx, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "form.json").write_text(
        json.dumps(form_idx, ensure_ascii=False), encoding="utf-8"
    )
    if not manifest.data["work"].get("edition_id"):
        (out_dir / "english.json").write_text(
            json.dumps(english_idx, ensure_ascii=False), encoding="utf-8"
        )
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    summary = {
        "lemmata": len(lemma_idx),
        "forms": len(form_idx),
        "english_terms": len(english_idx),
        "segments": len(meta),
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
