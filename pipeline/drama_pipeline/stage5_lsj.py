"""Stage 5: dictionary entries for corpus-occurring lemmata only.

Greek: streams grc.lsj.xml (110MB, 116,728 <div2 key="..."> entries), keeping
just the entries whose key matches a lemma in the Stage 4 analyses (exact
match first, then digit/macron-stripped base match, which also picks up all
homonyms a)1, a)2, ...). Latin (Wave 2 Batch 1b): streams
lat.ls.perseus-eng1.xml (Lewis & Short, ~78MB, 51,669 <div1 key="..."> entries)
the same way -- the TEI shape is the same family (div/head/orth/gen/sense/
cit/bibl/author), just a different enclosing div name and a handful of
Latin-only tags (itype/pos/usg/case/mood/number/lbl); see _DIV_TAG/_TAG_MAP.
Entry bodies are converted from Perseus TEI to compact HTML and sharded by
initial letter, into a per-language shard directory (SHARD_DIR).
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from html import escape
from pathlib import Path

from lxml import etree

from .config import BUILD_DIR, Manifest

# Master dictionary source file per work.language, resolved under
# manifest.diogenes_data(). 'grc' is LSJ; 'lat' is Lewis & Short (Wave 2
# Batch 1b). The 'lat' filename is the REAL Diogenes filename
# (lat.ls.perseus-eng1.xml, confirmed against docs/wave2-latin-design.md §6 —
# an earlier placeholder "lat.ls.xml" here was a silent-wrong-file landmine
# that would have passed a naive build once stage5 grows Latin support).
_DICTIONARY_FILENAMES = {"grc": "grc.lsj.xml"}

# Both dictionaries are a flat stream of per-lemma div fragments (no root
# element), but Perseus TEI names the element differently per dictionary:
# LSJ uses <div2 key="...">, Lewis & Short uses <div1 key="...">. Everything
# else about the streaming/shard/match approach is shared (see run() below).
_DIV_TAG = {"grc": "div2"}

# Shard directory name under build/stage5/ and build/dist/, per language —
# kept SEPARATE (not merged into one 'lsj' dir) because the two dictionaries
# are keyed in different, potentially-colliding key spaces (LSJ's Beta Code
# vs L&S's plain-Latin-plus-macron-marks) — app/src/components/LemmaPage.astro
# already made this call for the /lemma/<lang> route (`dictShardDir`), so
# stage5/stage7 mirror it rather than introducing a second convention.
SHARD_DIR = {"grc": "lsj"}


def _dictionary_path(manifest: Manifest) -> Path:
    language = manifest.language
    if language not in _DICTIONARY_FILENAMES:
        raise ValueError(f"unsupported work.language: {language!r}")
    return manifest.diogenes_data() / _DICTIONARY_FILENAMES[language]


# Letter-class spans keep the CSS in charge of presentation. Shared across
# both dictionaries -- LSJ (div2) and Lewis & Short (div1) use an overlapping
# TEI tag family (head/orth/gen/i/foreign/quote/cit/bibl/author/sense are
# identical in shape between the two, verified against real L&S entries
# below); the L&S-only rows (itype, pos, usg, case, mood, number, lbl) cover
# tags LSJ's entries don't use. Any tag not in this map (L&S's rare cb/pb/
# ref/figure/sup/hi) falls through to _to_html's generic `else` branch
# (a plain `lsj-<tag>` span) rather than raising -- new/rare TEI tags degrade
# to unstyled text, they don't break the build.
_TAG_MAP = {
    "head": ("b", "lsj-head"),
    "orth": ("b", "lsj-orth"),
    "gen": ("span", "lsj-gen"),
    "etym": ("span", "lsj-etym"),
    "i": ("i", None),
    "tr": ("span", "lsj-tr"),
    "foreign": ("span", "lsj-greek"),
    "quote": ("span", "lsj-quote"),
    "cit": ("span", "lsj-cit"),
    "bibl": ("span", "lsj-bibl"),
    "author": ("span", "lsj-author"),
    "title": ("i", "lsj-title"),
    "sense": ("div", "lsj-sense"),
    # Lewis & Short only (Wave 2 Batch 1b) -- morphology/usage labels that
    # LSJ's entries don't carry.
    "itype": ("i", "lsj-itype"),
    "pos": ("span", "lsj-pos"),
    "usg": ("span", "lsj-usg"),
    "case": ("span", "lsj-case"),
    "mood": ("span", "lsj-mood"),
    "number": ("span", "lsj-number"),
    "lbl": ("span", "lsj-lbl"),
}

# '#' (added Wave 2 Batch 1b): stage4's Latin lemma field carries Diogenes'
# OWN homonym marker as "qui#1", "edo#1" (confirmed: 10.79% of all
# latin-analyses.txt lemma groups, not a rare corner -- e.g. "qui", "edo",
# "is#1"/"is#2" are common words) -- a DIFFERENT convention from Lewis &
# Short's own trailing-digit homonym key ("qui1", "e^do1", "e^do2"). Without
# stripping '#' here, base_key("qui#1") left a dangling "qui#" that could
# never match L&S's base_index (keyed off base_key("qui1") == "qui"), so
# ~11% of Latin lemma lookups would silently fail the base-match fallback.
# '#' never appears in Greek data (grc.lsj.xml, greek-analyses.txt both
# confirmed clean), so this is safe to add to the shared strip sets.
_BASE_STRIP = re.compile(r"[0-9_^\-#]")
_FOLD_STRIP = re.compile(r"[0-9_^\-/=\\|+#]")
_CONNECTIVE = re.compile(r"^[\s,;]*(?:(?:or|and)[\s,;]*)?$", re.IGNORECASE)
_DANGLING_CONNECTIVE = re.compile(r"(?:\s*[,;]\s*)?\b(?:or|and)\s*$", re.IGNORECASE)
_DANGLING_ARTICLE = re.compile(r"\b(?:an?|the)$", re.IGNORECASE)


def base_key(key: str) -> str:
    return _BASE_STRIP.sub("", key)


def fold_key(key: str) -> str:
    """Accent/diaeresis/macron/hyphen-insensitive form; breathings kept."""
    return _FOLD_STRIP.sub("", key)


def lemma_candidates(lemma: str) -> list[tuple[str, str]]:
    """Ranked (index, value) lookups for a lemma against LSJ keys.

    Fallbacks cover Morpheus lemmatizations LSJ heads differently:
    adverbs in -ws live under the adjective (a)kribw=s -> a)kribh/s),
    verbal adjectives in -teos are headed as -teon, and synthetic
    compounds carry hyphens and extra accents (a)nti/-bla/ptw).
    """
    cands = [("exact", lemma), ("base", base_key(lemma))]
    fold = fold_key(lemma)
    cands.append(("fold", fold))
    if fold.endswith("ws"):
        cands.append(("fold", fold[:-2] + "hs"))
    if fold.endswith("teos"):
        cands.append(("fold", fold[:-4] + "teon"))
    return cands


def shard_letter(key: str) -> str:
    """Mirrors the THREE consumer-side implementations exactly (skip '*',
    first ASCII a-z, else '_'): preflight.py's `_lsj_shard`,
    shared/lib/data.ts's `lsjShard`, and LemmaPage.astro's
    `lsjShardLetter`. Bug this replaces (surfaced by the Wave 2 Batch 1b
    case-fold fix, item 2 -- the FIRST thing that made a capitalized L&S
    proper-name key like "Py_tha^go^ras" actually get matched/sharded):
    the old `ch.isalpha()` accepted an UPPERCASE first letter too, sharding
    "Py_tha^go^ras" under 'P' while every reader (the three consumers
    above) looks for it under 'y' (skipping the capital, matching only
    a-z) -- every capitalized L&S key was written to a shard file no
    reader would ever check, silently failing preflight's shared-shard
    coverage gate. Harmless for Greek (Beta Code's capital marker is '*',
    never a literal uppercase ASCII letter, so isalpha() and this were
    always equivalent there)."""
    for ch in key:
        if ch == "*":
            continue
        if "a" <= ch <= "z":
            return ch
    return "_"


def _to_html(el) -> str:
    tag = el.tag if isinstance(el.tag, str) else None
    parts = []
    if tag == "sense":
        level = el.get("level") or "1"
        n = el.get("n") or ""
        parts.append(f'<div class="lsj-sense" data-level="{escape(level)}">')
        if n:
            parts.append(f'<b class="lsj-sense-n">{escape(n)}.</b> ')
        body_open = True
    elif tag in _TAG_MAP:
        html_tag, cls = _TAG_MAP[tag]
        cls_attr = f' class="{cls}"' if cls else ""
        parts.append(f"<{html_tag}{cls_attr}>")
        body_open = True
    elif tag is None:
        body_open = False
    else:
        parts.append(f'<span class="lsj-{escape(tag)}">')
        body_open = True
    if tag is not None and el.text:
        parts.append(escape(el.text))
    for child in el:
        parts.append(_to_html(child))
    if body_open:
        if tag == "sense":
            parts.append("</div>")
        else:
            html_tag = _TAG_MAP.get(tag, ("span", None))[0]
            parts.append(f"</{html_tag}>")
    if el.tail:
        parts.append(escape(el.tail))
    return "".join(parts)


def entry_html(entry_el) -> str:
    parts = []
    if entry_el.text:
        parts.append(escape(entry_el.text))
    for child in entry_el:
        parts.append(_to_html(child))
    return "".join(parts).strip()


def _strip_edge_punctuation(value: str) -> str:
    while value and (
        value[0].isspace() or unicodedata.category(value[0]).startswith("P")
    ):
        value = value[1:]
    while value and (
        value[-1].isspace() or unicodedata.category(value[-1]).startswith("P")
    ):
        value = value[:-1]
    return value


def derive_short_def(entry_el) -> str:
    """Derive a compact definition from an LSJ entry's leading italic run."""
    sense = next((el for el in entry_el.iter() if el.tag == "sense"), None)
    body = sense if sense is not None else entry_el
    children = list(body)
    first_i = next((i for i, child in enumerate(children) if child.tag == "i"), None)
    if first_i is None:
        return ""

    parts = ["".join(children[first_i].itertext())]
    previous = children[first_i]
    for child in children[first_i + 1 :]:
        if child.tag != "i" or not _CONNECTIVE.fullmatch(previous.tail or ""):
            break
        parts.extend((previous.tail or "", "".join(child.itertext())))
        previous = child

    short_def = " ".join("".join(parts).split())
    short_def = _strip_edge_punctuation(short_def)
    short_def = _DANGLING_CONNECTIVE.sub("", short_def)
    short_def = _strip_edge_punctuation(short_def)
    # Adjectives in -ikos/-ios are glossed "of or belonging to a <Greek noun>",
    # and the noun is untranslated Greek outside the italic run: the derivation
    # would end on a stranded article. Give up rather than ship broken English.
    if _DANGLING_ARTICLE.search(short_def):
        return ""
    # A definition this long is one continuous italic clause (technical terms
    # like kefalaiwth/s), never a joined run — cutting it would reintroduce the
    # truncation this function exists to repair, so keep the shipped gloss.
    if len(short_def) > 100:
        return ""
    return short_def


def needed_lemmata(analyses: dict) -> set[str]:
    lemmata = set()
    for groups in analyses.values():
        for g in groups:
            if g["lemma"]:
                lemmata.add(g["lemma"])
    return lemmata


def run(manifest: Manifest) -> Path:
    language = manifest.language
    shard_dir_name = SHARD_DIR[language]
    analyses = json.loads(
        (BUILD_DIR / "stage4" / "analyses.json").read_text(encoding="utf-8")
    )
    lemmata = needed_lemmata(analyses)
    if language == "grc":
        # '#' is Diogenes' Latin-only homonym marker (edo#1, qui#2, ...) --
        # never present in Greek's own lemma vocabulary (confirmed against
        # greek-analyses.txt; see _BASE_STRIP's docstring). A loud gate, not
        # a comment: if this ever fires, `_BASE_STRIP`/`_FOLD_STRIP` would
        # silently mis-strip a real Greek character and the base/fold
        # fallback match would be corrupted for that lemma.
        hashed = sorted(l for l in lemmata if "#" in l)
        if hashed:
            raise ValueError(
                f"{manifest.work_id}: {len(hashed)} Greek lemma(s) contain "
                f"'#' (e.g. {hashed[:5]}) -- '#' is Diogenes' Latin-only "
                f"homonym marker; Greek data was assumed clean of it and "
                f"no longer is (see stage5_lsj._BASE_STRIP's docstring)"
            )

    out_dir = BUILD_DIR / "stage5"
    (out_dir / shard_dir_name).mkdir(parents=True, exist_ok=True)
    # This dir is a PER-WORK artifact, but nothing used to empty it: letters
    # this work doesn't touch kept whatever the previously built work left
    # behind, and stage7's _merge_shared_lsj globs *.json — so stale shards
    # from before a build leaked into build/dist in whatever order history
    # happened to leave them (byte-nondeterminism across otherwise identical
    # builds). The dir's contents must be exactly this work's output.
    for stale in (out_dir / shard_dir_name).glob("*.json"):
        stale.unlink()
    if not lemmata:
        # Blocker 1 fix (Sol): a LEXICON-ON work (`manifest.lexicon` — the
        # default) with zero resolved lemmata is NOT the same shape as a
        # declared no-lexicon work — stage4 now guarantees (see its own
        # Blocker 1 fix) that a lexicon-on work with real keyed tokens never
        # silently produces an empty analyses.json for THAT reason, but
        # stage4's own lookup can still legitimately resolve zero of them
        # (e.g. a wrong/missing analyses filename — the exact
        # `_DICTIONARY_FILENAMES` landmine this module's own history already
        # hit once). Failing loudly here, rather than falling through to the
        # same trivial empty-artifact shape, is what actually catches that:
        # a genuine no-lexicon work must declare `work.lexicon: false`.
        if manifest.lexicon:
            raise ValueError(
                f"{manifest.work_id}: work.lexicon is true but stage4 "
                f"resolved zero lemmata — either stage4's analyses lookup "
                f"failed for every keyed token (e.g. a wrong/missing "
                f"analyses file) or something upstream silently dropped "
                f"every key; a genuine no-lexicon work must declare "
                f"work.lexicon: false instead of producing this empty "
                f"artifact shape"
            )
        # A no-lexicon work (`work.lexicon: false`, Wave 2 §4.2) has no token
        # carrying `k`, so stage4's analyses.json is legitimately `{}` and
        # there is nothing to look up here. Skip the dictionary scan entirely
        # and emit the same trivial-but-valid shard-less output stage7
        # already expects from a work with genuinely zero dictionary hits.
        (out_dir / "lemma_map.json").write_text("{}", encoding="utf-8")
        (out_dir / "short_defs.json").write_text("{}", encoding="utf-8")
        (out_dir / "missing_lemmata.json").write_text("[]", encoding="utf-8")
        summary = {
            "lemmata_needed": 0, "lsj_entries_kept": 0,
            "shards": 0, "lemmata_without_entry": 0,
        }
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
        return out_dir

    # The master dictionary file is not one XML document (no root element); it
    # is a stream of <div1>/<div2> fragments (per-language element name, see
    # _DIV_TAG), so it is scanned line-wise.
    lsj_path = _dictionary_path(manifest)
    div_tag = _DIV_TAG[language]
    div_open = f"<{div_tag} "
    div_close = f"</{div_tag}>"
    key_re = re.compile(rf'<{div_tag} [^>]*key="([^"]*)"')

    # Pass 1: every dictionary key, plus base/fold indexes for fallback matching.
    all_keys: set[str] = set()
    base_index: dict[str, list[str]] = defaultdict(list)
    fold_index: dict[str, list[str]] = defaultdict(list)
    with open(lsj_path, encoding="utf-8") as f:
        for line in f:
            if div_open not in line:
                continue
            m = key_re.search(line)
            if not m:
                continue
            key = m.group(1)
            all_keys.add(key)
            base_index[base_key(key)].append(key)
            fold_index[fold_key(key)].append(key)

    if language == "grc":
        # See the lemmata-side gate above -- same invariant, the dictionary
        # side. Both must hold for the base/fold strip to be trustworthy.
        hashed_keys = sorted(k for k in all_keys if "#" in k)
        if hashed_keys:
            raise ValueError(
                f"{manifest.work_id}: {len(hashed_keys)} Greek LSJ key(s) "
                f"contain '#' (e.g. {hashed_keys[:5]}) -- '#' is Diogenes' "
                f"Latin-only homonym marker; grc.lsj.xml was assumed clean "
                f"of it and no longer is (see stage5_lsj._BASE_STRIP's "
                f"docstring)"
            )

    # Match lemmata to LSJ keys by the ranked candidate list.
    lemma_map: dict[str, list[str]] = {}
    missing: list[str] = []
    for lemma in sorted(lemmata):
        matched: list[str] | None = None
        for kind, value in lemma_candidates(lemma):
            if kind == "exact" and value in all_keys:
                matched = [value]
            elif kind == "base" and base_index.get(value):
                matched = sorted(base_index[value])
            elif kind == "fold" and fold_index.get(value):
                matched = sorted(fold_index[value])
            if matched:
                break
        if matched:
            lemma_map[lemma] = matched
        else:
            missing.append(lemma)
    wanted = {k for keys in lemma_map.values() for k in keys}

    # Pass 2: extract and convert just the wanted entries.
    shards: dict[str, dict] = defaultdict(dict)
    short_defs: dict[str, str] = {}
    n_kept = 0
    buf: list[str] = []
    want = False
    key = ""
    with open(lsj_path, encoding="utf-8") as f:
        for line in f:
            if div_open in line:
                m = key_re.search(line)
                key = m.group(1) if m else ""
                want = key in wanted
                buf = []
            if want:
                buf.append(line)
                if div_close in line:
                    fragment = "".join(buf)
                    start = fragment.index(div_open)
                    end = fragment.rindex(div_close) + len(div_close)
                    entry_el = etree.fromstring(fragment[start:end])
                    head = entry_el.findtext("head") or key
                    shards[shard_letter(key)][key] = {
                        "key": key,
                        "head": head,
                        "html": entry_html(entry_el),
                    }
                    if language == "grc":
                        # Greek only, and not merely out of caution: every
                        # Latin parse entry ships with an EMPTY gloss (0 of
                        # 231,938 across the 14 Latin works, measured
                        # 2026-07-26), so there is no truncated gloss to
                        # extend there — stage7 would skip them all anyway.
                        # Deriving them would cost a full Lewis & Short scan
                        # per work for nothing, on a heuristic calibrated to
                        # LSJ's italic convention (L&S also opens senses with
                        # grammatical labels in <i>, "<i>gen. sing.</i>").
                        short_def = derive_short_def(entry_el)
                        if short_def:
                            short_defs[key] = short_def
                    n_kept += 1
                    want = False

    # out_dir/shard_dir_name already created above, before the zero-lemmata
    # early return. Shard dir is 'lsj' for Greek (unchanged dist layout),
    # 'ls' for Latin (see SHARD_DIR).
    # sort_keys on every shard writer (here, stage7's _merge_shared_lsj,
    # lsj_topup, lsj-merge.mjs): shard bytes are then a pure function of
    # shard CONTENT, never of work build order or leftover state, so
    # byte-identity across builds is a usable regression contract.
    for letter, entries in sorted(shards.items()):
        (out_dir / shard_dir_name / f"{letter}.json").write_text(
            json.dumps(entries, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
    (out_dir / "lemma_map.json").write_text(
        json.dumps(lemma_map, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "short_defs.json").write_text(
        json.dumps(short_defs, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "missing_lemmata.json").write_text(
        json.dumps(missing, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    summary = {
        "lemmata_needed": len(lemmata),
        "lsj_entries_kept": n_kept,
        "short_defs": len(short_defs),
        "shards": len(shards),
        "lemmata_without_entry": len(missing),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    return out_dir
