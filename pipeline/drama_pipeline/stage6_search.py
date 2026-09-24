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

All four files are copied to build/dist/<work>/search/ by stage7. Stage 6 also
merges shipped analyses into build/dist/lemma-map/<letter>.json shards.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from .config import BUILD_DIR, Manifest, private_translation_ids

_FOLD = re.compile(r"[^a-z']")  # keep only base letters and apostrophe
_EN_WORD = re.compile(r"[a-z']+")


def slot_text(chunks: object) -> str:
    """Use the same ordered text for indexing and client-side snippets."""
    if isinstance(chunks, dict):
        return chunks.get("text", "")
    if isinstance(chunks, list):
        return "\n".join(c.get("text", "") for c in chunks if isinstance(c, dict))
    return ""


def build_lemma_map(current: dict, work_id: str, build_dir: Path = BUILD_DIR) -> None:
    """Merge shipped analyses across works into fold(form) -> headword shards."""
    forms: dict[str, set[str]] = defaultdict(set)
    paths = (build_dir / "dist").glob("*/analyses.json")
    for path in paths:
        if path.parent.name == work_id:
            continue
        add_analyses(forms, json.loads(path.read_text(encoding="utf-8")))
    add_analyses(forms, current)
    shards: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for surface, lemmata in forms.items():
        shards[surface[0] if surface[0].isalpha() else "_"][surface] = sorted(lemmata)
    out = build_dir / "dist" / "lemma-map"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.json"):
        old.unlink()
    for letter, values in shards.items():
        (out / f"{letter}.json").write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")


def add_analyses(forms: dict[str, set[str]], analyses: dict) -> None:
    for surface, parses in analyses.items():
        key = fold_lemma(surface)
        if not key:
            continue
        for parse in parses:
            head = parse.get("lemma")
            if head:
                folded = fold_lemma(head)
                if folded:
                    forms[key].add(folded)
                    forms[folded].add(folded)


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
            for word in _EN_WORD.findall(slot_text(chunks.get(seg["id"])).lower()):
                eng_posts[word].add((si, slot_id))
    english_idx = {w: [list(pair) for pair in sorted(pairs)] for w, pairs in eng_posts.items()}

    # -- Segment metadata -----------------------------------------------------
    meta = []
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
        english_head = eng["text"] if eng else ""
        meta.append(
            {
                "id": seg["id"],
                "book": seg["book"],
                "column": seg["column"],
                "head": head,
                "tokens": fold_seq_by_id.get(seg["id"], ""),
                "english_head": english_head,
                "english_slots": {sid: text for sid, chunks in slot_chunks.items()
                                  if sid != primary_id
                                  if (text := slot_text(chunks.get(seg["id"])))},
            }
        )

    out_dir = BUILD_DIR / "stage6"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lemma.json").write_text(
        json.dumps(lemma_idx, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "form.json").write_text(
        json.dumps(form_idx, ensure_ascii=False), encoding="utf-8"
    )
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
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    build_lemma_map(analyses, manifest.work_id, BUILD_DIR)
    return out_dir
