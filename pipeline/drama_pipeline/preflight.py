"""Preflight validation for emitted Plato Reader corpus data."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import scheme as scheme_mod
from .config import SOURCES_DIR, private_translation_ids
from .refs import column_key, column_prefix_key, line_key, ref_key
from .stage5_lsj import SHARD_DIR


Problem = tuple[str, str, str]

# MAJOR 2 fix (Sol adversarial review, De Fato chapter-concordance round):
# the only `english.primary.model` values any stage1 dispatch actually
# implements -- "archive" (every existing flat/book-section/verse-line
# work's 1:1 direct-map builder, stage1_flat_english/stage1_book_section_
# english/stage1_verse_line_english don't even branch on the model string,
# they just always do their fixed mapping), "chapter_concordance" (De
# Fato's dedicated chapter-span builder, stage1_chapter_concordance_
# english.py, __main__.py's flat_numeric dispatch, and -- generalized to a
# multi-book work for De Finibus phase 3 -- its numeric_section dispatch
# too), and
# "perseus_stephanus" (the has_sections/stephanus scheme's in-pass Perseus
# TEI builder, stage1_stephanus_english.py, __main__.py's has_sections
# dispatch only -- pre-existing, not part of this round's fix). A manifest
# declaring anything else (a typo like "chapter_concordence", or "none" for
# a scheme where it isn't separately permitted) used to pass this generic
# "non-empty string" gate silently and either get treated as a plain
# direct-map translation (skipping every concordance hash/anchor check) or
# fail deep inside a later stage instead of at preflight.
_LEGAL_ENGLISH_MODELS = {
    "archive", "chapter_concordance", "perseus_stephanus", "freeman",
    "perseus-play",
    "turn-text",  # P3: speaker-turn aligned prose/verse without line numbers (stage1_turn_english)
}
PUBLIC_DOMAIN_ALLOWLIST_PATH = Path(__file__).with_name("public_domain_translations.yaml")


def _stephanus_like_dispatch(scheme) -> bool:
    """True for exactly the schemes __main__.py's `_stage1` dispatch falls
    through to its `has_sections` branch for -- the ONLY branch that
    recognizes `perseus_stephanus` at all. Every other has_sections branch
    (`fragment_scheme`/dk, `verse_line_scheme`, `numeric_section`,
    `flat_numeric`) `return`s earlier in that dispatch, so a scheme
    matching any of them never reaches the has_sections branch regardless
    of its own `has_sections` value (see scheme.py's has_sections doc for
    which schemes derive/override it True).

    MAJOR fix (Sol re-verification, 2026-07-21): `perseus_stephanus` used
    to be checked ONLY against `_LEGAL_ENGLISH_MODELS` membership, with no
    scoping to the one scheme whose runtime dispatch actually implements
    it -- a book-section or flat `section` manifest declaring
    `model: perseus_stephanus` passed preflight silently, even though
    `__main__.py` would never reach the perseus_stephanus branch for it at
    all (its own dispatch `return`s earlier, from the numeric_section/
    flat_numeric branch instead, without ever looking at that model
    string)."""
    return (
        scheme.has_sections
        and not scheme.fragment_scheme
        and not scheme.verse_line_scheme
        and not scheme.numeric_section
        and not scheme.flat_numeric
        and not scheme.play_line_scheme
    )


def _no_english_allowed(work: dict, scheme) -> bool:
    """Whether a manifest may legitimately omit `english` entirely (Blocker 2
    fix, Sol): dk (fragment_scheme) keeps its pre-existing STRUCTURAL
    allowance — every DK A-testimonia/B-fragments work ships Greek/Latin-only
    by design, no per-work declaration required, unchanged here. A
    book-section (numeric_section), verse-line, or flat `section`
    (flat_numeric) work instead needs its OWN manifest declaration,
    `work.no_english: true` (mirrors `work.lexicon` exactly) — NOT scheme
    shape alone, which would silently permit any such work (including an
    existing Greek one, e.g. Epictetus' Enchiridion) to omit english
    regardless of whether that absence is actually intentional. verse-line
    joins numeric_section here (Wave 2 Batch 2 — Lucretius' DRN ships
    Latin-only, English is a later task, exactly the De Officiis Batch-1a
    staging precedent) even though `scheme.numeric_section` is itself False
    for verse-line (its lineref grammar is richer than book-section's plain
    integer — see scheme.py's `numeric_section` property doc). flat_numeric
    joins the same relaxation at Wave 2 Batch 3 round 2 (Cicero's Cato
    Maior/Laelius/De Fato/Lucullus/Paradoxa Stoicorum, the first Latin-only
    works on this scheme — Enchiridion, the scheme's only prior work, always
    carried real English). See _validate_manifest_schema's `no_english`
    block for the full rationale."""
    return scheme.fragment_scheme or (
        (
            scheme.numeric_section or scheme.verse_line_scheme or scheme.flat_numeric
            or scheme.play_line_scheme
        )
        and work.get("no_english") is True
    )


@dataclass
class WorkManifest:
    work_id: str
    path: Path
    data: dict[str, Any]
    public_path: Path | None = None
    private_data: dict[str, Any] | None = None


def validate(data_dir: Path, manifests_dir: Path, public: bool = False, editions: bool | None = None) -> list[Problem]:
    """`editions`: whether this build emits the Greek editions (build-public's
    DRAMA_EDITIONS=1; None reads that variable). A build of editions needs
    every declared OCR source, and a public one every declared edition's dir."""
    if editions is None:
        editions = os.environ.get("DRAMA_EDITIONS") == "1"
    problems: list[Problem] = []
    manifests = _load_manifests(manifests_dir, problems)
    for manifest in manifests:
        _validate_manifest_schema(manifest, problems)
        _validate_greek_editions(manifest, data_dir, problems, editions_built=editions, public=public)
        _validate_public_domain_allowlist(manifest, problems)
        _validate_work_data(data_dir, manifest, problems, public_build=public)
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    public = False
    if "--public" in argv:
        public = True
        argv = [a for a in argv if a != "--public"]
    editions = None
    if "--editions" in argv:
        editions = True
        argv = [a for a in argv if a != "--editions"]
    if len(argv) != 2:
        print(
            "usage: python3 -m drama_pipeline.preflight [--public] [--editions] <data-dir> <manifests-dir>",
            file=sys.stderr,
        )
        return 2

    data_dir = Path(argv[0])
    manifests_dir = Path(argv[1])
    problems = validate(data_dir, manifests_dir, public=public, editions=editions)
    if problems:
        for work, file_name, problem in problems:
            print(f"{work}: {file_name}: {problem}")
        return 1

    print(f"preflight ok: validated {data_dir} against {manifests_dir}")
    return 0


def _load_manifests(manifests_dir: Path, problems: list[Problem]) -> list[WorkManifest]:
    if not manifests_dir.exists():
        problems.append(("-", str(manifests_dir), "manifests directory does not exist"))
        return []

    parsed: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(manifests_dir.glob("*.yaml")):
        # authors.yaml is the corpus author roster (P2 registry data), not a
        # per-work manifest.
        if path.name == "authors.yaml":
            continue
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - exact parser text is not stable
            problems.append(("-", path.name, f"invalid YAML: {exc}"))
            continue
        if not isinstance(raw, dict):
            problems.append(("-", path.name, "manifest root must be an object"))
            continue
        parsed.append((path, raw))

    by_work: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for path, data in parsed:
        work_id = ((data.get("work") or {}).get("id") if isinstance(data.get("work"), dict) else None)
        if not isinstance(work_id, str) or not work_id:
            problems.append(("-", path.name, "work.id must be a non-empty string"))
            continue
        by_work.setdefault(work_id, []).append((path, data))

    selected: list[WorkManifest] = []
    for work_id, variants in sorted(by_work.items()):
        public = next(((p, d) for p, d in variants if p.name.endswith("-public.yaml")), None)
        private = next(((p, d) for p, d in variants if not p.name.endswith("-public.yaml")), None)
        path, data = public or private or variants[0]
        selected.append(
            WorkManifest(
                work_id=work_id,
                path=path,
                data=data,
                public_path=public[0] if public else None,
                private_data=private[1] if private and public else None,
            )
        )
    return selected


def _validate_manifest_schema(manifest: WorkManifest, problems: list[Problem]) -> None:
    """Validate a manifest's schema, dispatching on its citation scheme.

    The scheme-agnostic frame (work identity, english/sources objects, the books
    list) is shared. The scheme then decides the rest: a *bekker* manifest names
    its English on ``work.english_translation`` and cites by Bekker column
    (``bekker_range``), an explicit chapter div, and books bounded by full Bekker
    refs; a *section* manifest (stephanus) carries its English in the
    ``english.primary`` block, cites by page+section token with no Bekker range
    or chapter div, pins the observed spine with a ``section_spine`` fingerprint,
    and bounds books by section tokens. stage1/stage2 dispatch the same way."""
    data = manifest.data
    file_name = manifest.path.name

    # Reject an unrecognized or not-yet-implemented citation.scheme up front,
    # before dispatching on it — `scheme_mod.get()` raises KeyError for a
    # genuinely unknown name (which would abort validation of every other
    # manifest too), and a `stub=True` scheme's data shape is undefined by
    # definition, so neither can safely fall through to the schema checks
    # below. An omitted/empty scheme still defaults to bekker as before.
    citation = data.get("citation")
    scheme_name = citation.get("scheme") if isinstance(citation, dict) else None
    if scheme_name and scheme_name not in scheme_mod.SCHEMES:
        problems.append((manifest.work_id, file_name, f"citation.scheme {scheme_name!r} is not a recognized scheme"))
        return
    if scheme_name and scheme_mod.SCHEMES[scheme_name].stub:
        problems.append((manifest.work_id, file_name, f"scheme {scheme_name!r} is registered but not implemented"))
        return

    # Same reasoning as the scheme-name/stub pre-checks above: `citation.
    # div_types` (the section_div_type override — see scheme.py's
    # for_manifest and DIV_TYPE_OVERRIDE_KEYS) is validated HERE, before
    # for_manifest is called, so a bad override lands as a collected Problem
    # rather than an uncaught ValueError that would abort validating every
    # other manifest in this run.
    div_types = citation.get("div_types") if isinstance(citation, dict) else None
    if div_types is not None:
        if not isinstance(div_types, dict):
            problems.append((manifest.work_id, file_name, "citation.div_types must be an object"))
            return
        unknown_div_type_keys = set(div_types) - scheme_mod.DIV_TYPE_OVERRIDE_KEYS
        if unknown_div_type_keys:
            problems.append((
                manifest.work_id, file_name,
                f"citation.div_types has unknown override key(s): {sorted(unknown_div_type_keys)}",
            ))
            return
        # Blocker 3 fix (Sol): a page/section override value itself must be
        # a non-empty string — scheme.py's for_manifest used to accept
        # anything non-None (an empty string, an int, a list) and pass it
        # straight into `replace(sch, page_div_type=...)`/`section_div_type`,
        # producing a div type no export div could ever match (a silent
        # no-div parse: `_parse_book_section` would walk the whole tree and
        # find nothing, instead of failing loudly at the manifest-authoring
        # mistake). Checked for both keys, independently, before either is
        # applied.
        for div_type_key in ("page", "section"):
            if div_type_key not in div_types:
                continue
            value = div_types[div_type_key]
            if not isinstance(value, str) or not value:
                problems.append((
                    manifest.work_id, file_name,
                    f"citation.div_types.{div_type_key} must be a non-empty string",
                ))
                return

    # Same reasoning again: `citation.lines` (dk's verse-work override — see
    # scheme.py's for_manifest) is pre-checked here so a bad value/scheme
    # combination lands as a collected Problem, not an uncaught ValueError
    # that aborts validating every other manifest in this run.
    lines_override = citation.get("lines") if isinstance(citation, dict) else None
    if lines_override is not None:
        if scheme_name != "dk":
            problems.append((
                manifest.work_id, file_name,
                f"citation.lines is only meaningful for scheme 'dk', not {scheme_name!r}",
            ))
            return
        if lines_override not in (True, False):
            problems.append((manifest.work_id, file_name, "citation.lines must be true or false"))
            return

    # Same reasoning again: `citation.no_series` (a DK chapter printed with
    # no series letter at all, e.g. Pythagoras DK 14 — see scheme.py's
    # for_manifest) is pre-checked here so a bad value/scheme combination
    # lands as a collected Problem, not an uncaught ValueError.
    no_series_override = citation.get("no_series") if isinstance(citation, dict) else None
    if no_series_override is not None:
        if scheme_name != "dk":
            problems.append((
                manifest.work_id, file_name,
                f"citation.no_series is only meaningful for scheme 'dk', not {scheme_name!r}",
            ))
            return
        if no_series_override not in (True, False):
            problems.append((manifest.work_id, file_name, "citation.no_series must be true or false"))
            return

    # Same reasoning again: `citation.no_series: true` combined with
    # `citation.lines: true` is a declared-unimplemented combination (see
    # scheme.py's `for_manifest`, which raises ValueError for exactly this
    # pair) -- pre-checked here, once both overrides are known individually
    # valid, so the combination lands as a collected Problem instead of an
    # uncaught exception that would abort validating every other manifest
    # in this run.
    if lines_override is True and no_series_override is True:
        problems.append((
            manifest.work_id, file_name,
            "citation.no_series with citation.lines is not implemented",
        ))
        return

    # MAJOR 3 fix (Sol adversarial review): `citation.exclude_sections`
    # (De Fato's apparatus/fragment-tail exclusion — stage1_latin.py's
    # `_check_exclude_sections`, stage1_chapter_concordance_english.py's
    # `build_spans`) is compared at runtime against STRINGIFIED span/column
    # numbers (`str(n)`, `sec_div.get("n")`), so a YAML author writing an
    # integer token (`exclude_sections: [2]` instead of `["2"]`) would
    # silently never match anything and the "excluded" section would ship
    # as ordinary citable/translated text with no error at all. Constrained
    # here to a list of unique, non-empty strings — checked before
    # `for_manifest` is called, same posture as the overrides just above.
    exclude_sections = citation.get("exclude_sections") if isinstance(citation, dict) else None
    if exclude_sections is not None:
        if not isinstance(exclude_sections, list) or not exclude_sections:
            problems.append((manifest.work_id, file_name, "citation.exclude_sections must be a non-empty list"))
            return
        bad = [tok for tok in exclude_sections if not isinstance(tok, str) or not tok]
        if bad:
            problems.append((manifest.work_id, file_name,
                             f"citation.exclude_sections entries must all be non-empty strings, got {bad!r}"))
            return
        dupes = sorted({tok for tok in exclude_sections if exclude_sections.count(tok) > 1})
        if dupes:
            problems.append((manifest.work_id, file_name,
                             f"citation.exclude_sections has duplicate token(s): {dupes}"))
            return

    scheme = scheme_mod.for_manifest(data)
    _require_object(manifest, data, "work", problems)
    work = data.get("work") if isinstance(data.get("work"), dict) else {}

    # work.language is optional (defaults to 'grc' — see Manifest.language).
    # drama_pipeline supports 'grc' only: Latin/PHI support (stage1_latin,
    # latin.py) was removed in the drama fork, so a 'lat' manifest must fail
    # loudly HERE — before any stage-specific code that no longer exists for
    # it can be reached — rather than surfacing as an ImportError or
    # NotImplementedError deep in some later stage.
    language = work.get("language", "grc")
    if language not in ("grc",):
        problems.append((
            manifest.work_id, file_name,
            f"work.language {language!r} is not supported by drama_pipeline "
            "(Latin/PHI support was removed in the drama fork; only 'grc' "
            "is supported)",
        ))

    # work.lexicon is optional, defaults to True (every pre-Wave-2 manifest
    # is implicitly lexicon-on). `false` declares the no-lexicon-first
    # posture (Wave 2 §4.2): tokens carry `t` but no `k`. Only meaningful as
    # a boolean — anything else is a manifest-authoring mistake.
    #
    # `lexicon: false` is a LATIN-ONLY affordance (Wave 2 Batch 1a memo §4.2:
    # "the exact mirror of the Greek-only translation mode" — it mirrors an
    # omitted `english`, never a Greek work's lexicon itself). A grc work
    # declaring it would silently strip every LSJ click-through from a Greek
    # reader page with no user-visible signal until someone notices the
    # words aren't clickable — reject it here instead (Sol blocker: the
    # lexicon flag used to fail OPEN for this case).
    lexicon = work.get("lexicon", True)
    if not isinstance(lexicon, bool):
        problems.append((manifest.work_id, file_name, "work.lexicon must be a boolean"))
    elif lexicon is False:
        problems.append((
            manifest.work_id, file_name,
            "work.lexicon: false is not permitted — the no-lexicon posture "
            "(Wave 2 §4.2) was a Latin-only affordance and Latin support "
            "was removed in the drama fork; every grc work must ship "
            "clickable (lexicon-keyed) tokens",
        ))

    # work.no_english is optional, defaults to False — the manifest's OWN,
    # explicit declaration that this work legitimately ships with no
    # `english` block at all (mirrors `work.lexicon` above exactly). Only
    # meaningful as a boolean.
    no_english = work.get("no_english", False)
    if not isinstance(no_english, bool):
        problems.append((manifest.work_id, file_name, "work.no_english must be a boolean"))
    elif no_english is True and "english" in data:
        # `work.no_english: true` declares "this work legitimately ships with
        # no english block at all" -- an `english:` block present alongside
        # it is a self-contradictory manifest that schema-passed before this
        # check (stage1's verse-line dispatch, __main__.py's `_stage1`,
        # decides Latin-only vs. +english purely on `"english" in
        # manifest.data`, with no awareness of `no_english` at all -- see
        # that dispatch's defensive assertion for the runtime backstop).
        problems.append((
            manifest.work_id, file_name,
            "work.no_english: true and an english: block are mutually "
            "exclusive -- a manifest declaring no_english must not also "
            "declare english",
        ))

    # A dk (fragment_scheme) work ships Greek/Latin-only by structural
    # design (every A-testimonia work; no per-work declaration needed — this
    # scope is unchanged from before). A book-section (numeric_section) work
    # may ALSO omit `english`, but ONLY when its own manifest explicitly
    # declares `work.no_english: true` — Cicero's De Officiis (Wave 2 Batch
    # 1a) is the first case. Blocker 2 fix (Sol): the old relaxation was
    # `scheme.fragment_scheme or scheme.numeric_section`, a SCHEME-SHAPE
    # test that silently permitted ANY book-section work to omit english —
    # including a Greek book-section work (e.g. Marcus Aurelius' Meditations)
    # missing it due to a genuine extraction bug, since `numeric_section` is
    # true for every book-section work regardless of whether THIS work's own
    # absent english is intentional. Conditioning on the manifest's own
    # declaration instead closes that hole while leaving dk's existing
    # structural allowance untouched. The registry side (does
    # shared/lib/works.ts also declare `translations: []` for this work?) is
    # cross-checked by the existing scripts/check-manifest-translations.mjs
    # seam gate, not re-derived here — preflight has no access to the
    # TypeScript registry.
    if not (_no_english_allowed(work, scheme) and "english" not in data):
        _require_object(manifest, data, "english", problems)
    _require_object(manifest, data, "sources", problems)
    _require_list(manifest, data, "books", problems)

    # Source-corpus identity keys are per-language: TLG for Greek
    # (tlg_author/tlg_work/greek_edition), PHI for Latin (phi_author/
    # phi_work/latin_edition — Wave 2 Batch 1a, Cicero the first real PHI
    # work). An unrecognized `language` (already reported above) falls back
    # to the grc key set here so one bad manifest doesn't also cascade into
    # a confusing wall of "phi_author must be..." errors.
    work_keys = ["id", "title", "author"]
    if language == "lat":
        work_keys += ["phi_author", "phi_work", "latin_edition"]
    else:
        work_keys += ["tlg_author", "tlg_work", "greek_edition"]
    if scheme.bekker_native:
        # Bekker manifests name the translation on work.english_translation;
        # section schemes carry it in english.primary (validated per-scheme below).
        work_keys.append("english_translation")
    for key in work_keys:
        if not isinstance(work.get(key), str) or not work.get(key):
            problems.append((manifest.work_id, file_name, f"work.{key} must be a non-empty string"))

    if scheme.bekker_native:
        _validate_bekker_manifest_schema(manifest, problems)
    else:
        _validate_section_manifest_schema(manifest, problems, scheme)


def _validate_bekker_manifest_schema(manifest: WorkManifest, problems: list[Problem]) -> None:
    """Bekker-scheme manifest rules: a required Bekker column range, an optional
    explicit chapter list, and books bounded by full Bekker refs (with lines)."""
    data = manifest.data
    file_name = manifest.path.name
    _require_object(manifest, data, "bekker_range", problems)
    _require_object(manifest, data, "chapters", problems)

    bekker = data.get("bekker_range") if isinstance(data.get("bekker_range"), dict) else {}
    for key in ["first_column", "last_column"]:
        if not _is_column(bekker.get(key)):
            problems.append((manifest.work_id, file_name, f"bekker_range.{key} must be a Bekker column string"))

    _validate_books_schema(
        manifest, problems,
        token_ok=_is_ref, sort_key=ref_key, token_label="a Bekker ref string",
    )

    chapters = data.get("chapters") if isinstance(data.get("chapters"), dict) else {}
    if chapters.get("source") == "explicit":
        chapter_list = chapters.get("list")
        if not isinstance(chapter_list, list):
            problems.append((manifest.work_id, file_name, "chapters.list must be a list when chapters.source is explicit"))
        else:
            previous: tuple[int, str, int] | None = None
            for i, chapter in enumerate(chapter_list):
                if not isinstance(chapter, dict):
                    problems.append((manifest.work_id, file_name, f"chapters.list[{i}] must be an object"))
                    continue
                if not isinstance(chapter.get("n"), int):
                    problems.append((manifest.work_id, file_name, f"chapters.list[{i}].n must be an integer"))
                bekker_ref = chapter.get("bekker")
                if not _is_ref(bekker_ref):
                    problems.append((manifest.work_id, file_name, f"chapters.list[{i}].bekker must be a Bekker ref string"))
                    continue
                current = ref_key(bekker_ref)
                if previous is not None and current < previous:
                    problems.append((manifest.work_id, file_name, f"chapters.list[{i}].bekker is out of order"))
                previous = current


def _validate_section_manifest_schema(manifest: WorkManifest, problems: list[Problem], scheme) -> None:
    """Section-scheme manifest rules: an english.primary translation block, a
    section_spine fingerprint, and books bounded by section tokens. A Bekker
    range and an explicit chapter div do not apply (the reader cites by section
    and gets outline nav from sections.json); they are validated only if a
    manifest chooses to declare them.

    The book-boundary token grammar dispatches on the scheme: a letter scheme
    (stephanus) bounds books by a page+section token ('357a' or '357a1'); a
    numeric-section scheme (book-section) bounds them by a bare dotted
    book.section token ('1.1')."""
    data = manifest.data
    file_name = manifest.path.name

    # A dk or book-section work may ship Greek/Latin-only (no `english` key
    # at all — see _validate_manifest_schema's matching relaxation): the
    # A-testimonia series ships this way by design (no free translation
    # exists at all); a B-fragments work with no Burnet source YET is the
    # same declared-gap shape; Cicero's De Officiis (Wave 2 Batch 1a) is the
    # book-section case, gated on its OWN `work.no_english: true`
    # declaration — see `_no_english_allowed`'s doc for the Blocker 2 fix
    # rationale). Every other scheme (and a work that DOES declare
    # `english`) still requires a well-formed english.primary block.
    work = data.get("work") if isinstance(data.get("work"), dict) else {}
    primary: Any = None
    if not (_no_english_allowed(work, scheme) and "english" not in data):
        english = data.get("english") if isinstance(data.get("english"), dict) else {}
        primary = english.get("primary")
        if not isinstance(primary, dict):
            problems.append((manifest.work_id, file_name, "english.primary must be an object"))
        else:
            # perseus-play and turn-text (P3, the comedies and the verse
            # benches) name their text with `source` (+ `play`), not `file`.
            source_key = "source" if primary.get("model") in ("perseus-play", "turn-text") else "file"
            for key in ["id", "name", "model", source_key]:
                if not isinstance(primary.get(key), str) or not primary.get(key):
                    problems.append((manifest.work_id, file_name, f"english.primary.{key} must be a non-empty string"))
            # MAJOR 2 fix (Sol adversarial review): a non-empty string was
            # previously ENOUGH for primary.model -- any typo or unimplemented
            # value silently reached __main__.py's stage1 dispatch, which
            # falls back to the plain direct-map builder for anything it
            # doesn't explicitly recognize (see that dispatch's own comment).
            # Constrained here to the explicit set of models a dispatch
            # actually implements (`_LEGAL_ENGLISH_MODELS`); "chapter_
            # concordance" is additionally scoped to the two schemes
            # (flat_numeric -- De Fato; numeric_section/book-section -- De
            # Finibus phase 3, __main__.py's numeric_section branch dispatches
            # it exactly like flat_numeric's own branch does) whose dispatch
            # knows what to do with it.
            model = primary.get("model")
            if isinstance(model, str) and model:
                stephanus_like = _stephanus_like_dispatch(scheme)
                if model not in _LEGAL_ENGLISH_MODELS:
                    problems.append((manifest.work_id, file_name,
                                     f"english.primary.model {model!r} is not a recognized model "
                                     f"-- expected one of {sorted(_LEGAL_ENGLISH_MODELS)}"))
                elif scheme.play_line_scheme and model not in ("perseus-play", "turn-text"):
                    problems.append((manifest.work_id, file_name,
                                     "a play-line work with English must use "
                                     "english.primary.model 'perseus-play' or 'turn-text'"))
                elif model == "chapter_concordance" and not (scheme.flat_numeric or scheme.numeric_section):
                    problems.append((manifest.work_id, file_name,
                                     "english.primary.model 'chapter_concordance' is only "
                                     "supported for the flat 'section' scheme or the "
                                     "numeric-section (book-section) scheme"))
                elif model == "freeman" and not scheme.fragment_scheme:
                    # __main__.py's fragment_scheme dispatch branch is the
                    # only one that ever looks for "freeman" -- every other
                    # branch would silently fall through to its own
                    # 'archive'-only direct-map builder instead (same
                    # failure mode `_stephanus_like_dispatch`'s comment
                    # describes for 'perseus_stephanus').
                    problems.append((manifest.work_id, file_name,
                                     "english.primary.model 'freeman' is only supported "
                                     "for the dk (fragment) scheme"))
                elif model == "perseus_stephanus" and not stephanus_like:
                    # MAJOR fix (Sol re-verification, 2026-07-21): see
                    # `_stephanus_like_dispatch`'s own doc comment -- this
                    # model is only ever recognized by __main__.py's
                    # has_sections dispatch branch.
                    problems.append((manifest.work_id, file_name,
                                     "english.primary.model 'perseus_stephanus' is only "
                                     "supported for a Stephanus-paginated (has_sections, "
                                     "non numeric_section/flat_numeric/verse_line/fragment) "
                                     "scheme"))
                elif model == "perseus-play" and not scheme.play_line_scheme:
                    problems.append((manifest.work_id, file_name,
                                     "english.primary.model 'perseus-play' is only "
                                     "supported for the play-line scheme"))
                elif model == "archive" and stephanus_like:
                    # The has_sections branch's runtime dispatch only ever
                    # recognizes `perseus_stephanus` -- any other model
                    # (including 'archive') falls into its `else` clause,
                    # which silently DROPS the english scratch and ships
                    # the work Greek/Latin-only. Rejecting 'archive' here
                    # for this scheme turns that silent drop into a loud
                    # preflight failure instead.
                    problems.append((manifest.work_id, file_name,
                                     "english.primary.model 'archive' is not supported for "
                                     "this scheme -- __main__.py's has_sections dispatch only "
                                     "recognizes 'perseus_stephanus' and would otherwise "
                                     "silently ship this work with no English at all"))
            if primary.get("model") == "perseus-play":
                if primary.get("anchor_model") != "sp-line":
                    problems.append((manifest.work_id, file_name,
                                     "english.primary.anchor_model must be 'sp-line' "
                                     "for the perseus-play model"))
                if not isinstance(primary.get("footnotes"), bool):
                    problems.append((manifest.work_id, file_name,
                                     "english.primary.footnotes must be a boolean "
                                     "for the perseus-play model"))
            # `chapter_concordance` (De Fato — Yonge's chapter-keyed
            # translation over a flat spine, stage1_chapter_concordance_
            # english.py) needs a second source file the other flat-scheme
            # models don't: the chapter->section concordance itself. Without
            # this gate a manifest that forgets `concordance` would only
            # fail deep inside stage1 with a raw KeyError instead of a
            # clear preflight diagnostic.
            if primary.get("model") == "chapter_concordance":
                if not isinstance(primary.get("concordance"), str) or not primary.get("concordance"):
                    problems.append((manifest.work_id, file_name,
                                     "english.primary.concordance must be a non-empty string "
                                     "when english.primary.model is 'chapter_concordance'"))

    # `section_spine` is this generic gate's DOCUMENT-order fingerprint,
    # consumed only by stage2's "immutable observed section baseline" check
    # (gated on `scheme.has_sections`, which is False for verse-line — see
    # scheme.py's own comment on why a per-line outline nav would be
    # unusable). verse-line has its own CITATION-order fingerprint instead
    # (`citation.fingerprint`, design memo §3.3(b)), required and validated
    # by `_validate_verse_line_work`'s dist-level gate — requiring an
    # UNCONSUMED `section_spine` here too would be a declaration nothing
    # ever checks.
    if not scheme.verse_line_scheme and not scheme.play_line_scheme:
        spine = data.get("section_spine")
        if not isinstance(spine, dict):
            problems.append((manifest.work_id, file_name, "section_spine must be an object"))
        else:
            if not isinstance(spine.get("count"), int):
                problems.append((manifest.work_id, file_name, "section_spine.count must be an integer"))
            sha256 = spine.get("sha256")
            if not isinstance(sha256, str) or len(sha256) != 64:
                problems.append((manifest.work_id, file_name, "section_spine.sha256 must be a 64-character hex string"))

    if scheme.flat_numeric:
        # Flat bookless scheme (Epictetus' Enchiridion; also, from Wave 2
        # Batch 3 round 2, Cicero's Cato Maior/Laelius/De Fato/Lucullus/
        # Paradoxa Stoicorum): the single declared book is bounded by bare
        # chapter/section-integer tokens ("1".."53"), which neither the
        # dotted nor the Stephanus token grammar accepts.
        #
        # CONSTRAIN LOUDLY (Sol re-review round 2, 2026-07-16; still applies
        # to a work that DOES declare `english` — a work.no_english: true
        # work has `primary is None` here, per `_no_english_allowed` above,
        # so the model-"none" check below is a no-op for it): the
        # configurations the pipeline cannot actually run are rejected here
        # with a clear message instead of breaking silently downstream:
        #  * primary.model "none" — stage1 deletes the english scratch for
        #    every has_sections work not on the perseus_stephanus in-pass
        #    builder, and stage6/stage7 load english_chunks.json
        #    unconditionally (pre-existing platform behavior), so a flat
        #    model:none work cannot complete `drama_pipeline all`.
        #  * books != exactly 1 — stage1 assigns every flat column to the
        #    single book 1, so a multi-book flat manifest would silently
        #    collapse its books into one.
        if isinstance(primary, dict) and primary.get("model") == "none":
            problems.append((manifest.work_id, file_name,
                             "english.primary.model 'none' is unsupported for the flat "
                             "'section' scheme — the all-stages pipeline requires a real "
                             "English model for this scheme"))
        books_list = data.get("books") if isinstance(data.get("books"), list) else []
        if len(books_list) != 1:
            problems.append((manifest.work_id, file_name,
                             "a flat 'section'-scheme work is bookless and must declare "
                             f"exactly one book entry, got {len(books_list)}"))
        elif isinstance(books_list[0], dict) and books_list[0].get("n") != 1:
            # non-dict entries fall through to _validate_books_schema's own
            # "books[0] must be an object" diagnostic
            # stage1 hardcodes flat segments to book 1; any other declared
            # number would silently disagree with the emitted book-01 files.
            problems.append((manifest.work_id, file_name,
                             "a flat 'section'-scheme work's single book entry must be "
                             f"n: 1, got n: {books_list[0].get('n')!r}"))
        _validate_books_schema(
            manifest, problems,
            token_ok=lambda v: _is_column(v, scheme),
            sort_key=lambda t: column_prefix_key(t, scheme),
            token_label="a chapter number token",
        )
    elif scheme.numeric_section:
        _validate_books_schema(
            manifest, problems,
            token_ok=lambda v: _is_column(v, scheme),
            sort_key=lambda t: column_prefix_key(t, scheme),
            token_label="a book.section token",
        )
    elif scheme.verse_line_scheme:
        # verse-line (Lucretius' DRN, Wave 2 Batch 2): real multi-book
        # boundaries (unlike flat_numeric/fragment_scheme's bookless single
        # declared book) bounded by dotted book.lineref tokens ('1.1',
        # '3.47a') — the same shape as numeric_section's book-token
        # validation just above, dispatched separately because
        # `scheme.numeric_section` is False for verse-line (its lineref
        # grammar is richer than book-section's plain integer — see
        # scheme.py's `numeric_section` doc).
        _validate_books_schema(
            manifest, problems,
            token_ok=lambda v: _is_column(v, scheme),
            sort_key=lambda t: column_prefix_key(t, scheme),
            token_label="a book.lineref token",
        )
    elif scheme.fragment_scheme:
        # dk (Diels-Kranz) is bookless like `section` — a single declared
        # book covers the whole fragment/testimonium spine (§3 of the Wave
        # 1b memo). citation.series is also required here (not just at
        # parse time — a manifest missing it should fail preflight, not
        # only stage1) and must match the letter every column in the
        # (already-validated-elsewhere) grammar carries.
        dk_citation = data.get("citation") or {}
        no_series = dk_citation.get("no_series")
        series = dk_citation.get("series")
        if no_series:
            # An explicit `citation.series: ""` is NOT "series omitted" --
            # only a genuinely absent (None) series satisfies this
            # contract; an empty string used to slip through here (mirrored
            # in stage1_greek.py's own pre-check of the same hole).
            if series is not None:
                problems.append((manifest.work_id, file_name,
                                 "citation.series must be omitted when citation.no_series is true"))
        elif series not in ("A", "B"):
            problems.append((manifest.work_id, file_name, "citation.series must be 'A' or 'B' for a dk work"))
        books_list = data.get("books") if isinstance(data.get("books"), list) else []
        if len(books_list) != 1:
            problems.append((manifest.work_id, file_name,
                             "a dk-scheme work is bookless and must declare "
                             f"exactly one book entry, got {len(books_list)}"))
        elif isinstance(books_list[0], dict) and books_list[0].get("n") != 1:
            problems.append((manifest.work_id, file_name,
                             "a dk-scheme work's single book entry must be "
                             f"n: 1, got n: {books_list[0].get('n')!r}"))
        _validate_books_schema(
            manifest, problems,
            token_ok=lambda v: _is_column(v, scheme),
            sort_key=lambda t: column_prefix_key(t, scheme),
            token_label="a dk (Diels-Kranz) column token",
        )
    elif scheme.play_line_scheme:
        # play-line (the Greek drama corpus, P1) is bookless like `section`/
        # dk -- a single declared book covers the whole play's printed
        # lineref spine (a play running 1000+ lines gets no multi-book
        # split; "books: 1" is the manifest's own declared shape).
        speakers = data.get("speakers")
        if not isinstance(speakers, dict):
            problems.append((
                manifest.work_id, file_name,
                "speakers must be an object for a play-line work",
            ))
        else:
            sigla = speakers.get("sigla")
            if not isinstance(sigla, dict):
                problems.append((
                    manifest.work_id, file_name,
                    "speakers.sigla must be an object for a play-line work",
                ))
            else:
                for label, display in sigla.items():
                    if not isinstance(label, str) or not label:
                        problems.append((
                            manifest.work_id, file_name,
                            "speakers.sigla keys must be non-empty strings",
                        ))
                    elif label == "—":
                        if display is not None:
                            problems.append((
                                manifest.work_id, file_name,
                                "speakers.sigla['—'] must be null",
                            ))
                    elif not isinstance(display, str) or not display:
                        problems.append((
                            manifest.work_id, file_name,
                            f"speakers.sigla[{label!r}] must be a non-empty "
                            "canonical display string",
                        ))
                if "—" not in sigla:
                    problems.append((
                        manifest.work_id, file_name,
                        "speakers.sigla must declare the unattributed dash '—': null",
                    ))
        books_list = data.get("books") if isinstance(data.get("books"), list) else []
        if len(books_list) != 1:
            problems.append((manifest.work_id, file_name,
                             "a play-line-scheme work is bookless and must declare "
                             f"exactly one book entry, got {len(books_list)}"))
        elif isinstance(books_list[0], dict) and books_list[0].get("n") != 1:
            problems.append((manifest.work_id, file_name,
                             "a play-line-scheme work's single book entry must be "
                             f"n: 1, got n: {books_list[0].get('n')!r}"))
        _validate_books_schema(
            manifest, problems,
            token_ok=lambda v: _is_column(v, scheme),
            sort_key=lambda t: column_prefix_key(t, scheme),
            token_label="a play-line lineref token",
        )
    else:
        _validate_books_schema(
            manifest, problems,
            token_ok=_is_section_token, sort_key=column_prefix_key,
            token_label="a Stephanus section token",
        )

    # A section manifest normally omits bekker_range/chapters; validate them only
    # if present so a future variant can still declare them meaningfully.
    bekker = data.get("bekker_range")
    if bekker is not None:
        if not isinstance(bekker, dict):
            problems.append((manifest.work_id, file_name, "bekker_range must be an object"))
        else:
            for key in ["first_column", "last_column"]:
                if not _is_column(bekker.get(key)):
                    problems.append((manifest.work_id, file_name, f"bekker_range.{key} must be a section token"))


def _validate_books_schema(
    manifest: WorkManifest,
    problems: list[Problem],
    *,
    token_ok,
    sort_key,
    token_label: str,
) -> None:
    """Shared books-list schema: unique integer numbers and ordered, in-range,
    non-overlapping boundaries. The boundary token grammar (full Bekker ref vs.
    section token) and its sort key vary by scheme, passed in by the caller."""
    file_name = manifest.path.name
    books = manifest.data.get("books") if isinstance(manifest.data.get("books"), list) else []
    previous_end = None
    seen_books: set[int] = set()
    for i, book in enumerate(books):
        if not isinstance(book, dict):
            problems.append((manifest.work_id, file_name, f"books[{i}] must be an object"))
            continue
        n = book.get("n")
        if not isinstance(n, int):
            problems.append((manifest.work_id, file_name, f"books[{i}].n must be an integer"))
        elif n in seen_books:
            problems.append((manifest.work_id, file_name, f"duplicate book number {n}"))
        else:
            seen_books.add(n)
        start = book.get("start")
        end = book.get("end")
        if not token_ok(start):
            problems.append((manifest.work_id, file_name, f"books[{i}].start must be {token_label}"))
            continue
        if not token_ok(end):
            problems.append((manifest.work_id, file_name, f"books[{i}].end must be {token_label}"))
            continue
        start_key = sort_key(start)
        end_key = sort_key(end)
        if start_key > end_key:
            problems.append((manifest.work_id, file_name, f"books[{i}] start must not be after end"))
        if previous_end is not None and start_key < previous_end:
            problems.append((manifest.work_id, file_name, f"books[{i}] start is before previous book end"))
        previous_end = end_key


def _validate_work_data(
    data_dir: Path,
    manifest: WorkManifest,
    problems: list[Problem],
    public_build: bool = False,
) -> None:
    work_dir = data_dir / manifest.work_id
    if not work_dir.exists():
        problems.append((manifest.work_id, str(work_dir), "emitted work directory does not exist"))
        return
    if not work_dir.is_dir():
        problems.append((manifest.work_id, str(work_dir), "emitted work path is not a directory"))
        return

    loaded: dict[str, Any] = {}
    required = ["manifest.json", "chapters.json", "columns.json", "analyses.json"]
    primary_model = (((manifest.data.get("english") or {}).get("primary") or {})
                     .get("model"))
    if primary_model == "freeman":
        # paratext.json is ALWAYS written for a freeman-model work (even a
        # work with zero group headers writes an empty list, per
        # stage1_freeman_english.py's group_headers_file requirement) --
        # absence here is a stage7 emission regression, fatal (finding 4,
        # phase-1 adversarial fix round).
        required.append("paratext.json")
    for book in manifest.data.get("books", []):
        if isinstance(book, dict) and isinstance(book.get("n"), int):
            required.append(f"book-{book['n']:02d}.json")
    for name in required:
        path = work_dir / name
        if not path.exists():
            problems.append((manifest.work_id, name, "emitted JSON file is missing"))
            continue
        try:
            loaded[name] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            problems.append((manifest.work_id, name, f"invalid JSON: {exc}"))

    # Non-Bekker works (e.g. Porphyry's Isagoge, citation.scheme: busse) carry
    # synthetic column/line numbers that do not obey Bekker ordering/anchoring
    # semantics, so the Bekker-specific structural checks are skipped for them
    # (schema, file existence, JSON validity, columns, analyses, and public
    # gating still run).
    scheme = scheme_mod.for_manifest(manifest.data)
    bekker_native = scheme.bekker_native

    # Manifests declare known, verified irregularities in the TLG line numbering
    # (`expected_line_gaps`: within `column`, after line `after` the sequence
    # legitimately continues at `next` — including backwards jumps and repeats,
    # where the Greek text itself is continuous). These are intentional, so the
    # Greek-line-order and duplicate-anchor checks must not flag the declared
    # transitions.
    expected_gaps = {
        (g["column"], g["after"], g["next"])
        for g in (manifest.data.get("expected_line_gaps") or [])
        if isinstance(g, dict) and {"column", "after", "next"} <= g.keys()
    }

    # dk (Diels-Kranz) fragment/testimonia validation (_validate_dk_work and
    # its Freeman/section-paragraph companions) was corpus-specific with no
    # drama use and was removed in the drama fork (docs/plan.md §1); the
    # 'dk' scheme itself stays registered (scheme.py), so this expected set
    # is simply empty here rather than re-derived per manifest.
    dk_all_context_columns: set[str] = set()

    _validate_emitted_manifest(manifest, loaded.get("manifest.json"), problems)
    segments, anchors, token_keys = _validate_books(
        manifest, loaded, problems, bekker_native, expected_gaps, scheme, dk_all_context_columns,
    )
    _validate_chapters(manifest, loaded.get("chapters.json"), segments, anchors, problems, bekker_native, scheme)
    _validate_columns(manifest, loaded.get("columns.json"), segments, problems, scheme, dk_all_context_columns)
    _validate_analyses(manifest, data_dir, loaded.get("analyses.json"), token_keys, problems)
    _validate_public_gating(manifest, loaded, problems, public_build=public_build)
    if scheme.fragment_scheme:
        problems.append((
            manifest.work_id, "<scheme>",
            "scheme 'dk' has no corpus-specific preflight validation in "
            "drama_pipeline (its walker and validators were removed in the "
            "drama fork; only 'grc' schemes drama_pipeline actually builds "
            "are supported)",
        ))
    if scheme.verse_line_scheme:
        _validate_verse_line_work(manifest, loaded, problems, scheme)
    if scheme.play_line_scheme:
        _validate_play_line_work(manifest, loaded, problems, scheme)


def _validate_verse_line_work(
    manifest: WorkManifest,
    loaded: dict[str, Any],
    problems: list[Problem],
    scheme,
) -> None:
    """verse-line (Lucretius' DRN, Wave 2 Batch 2)-specific dist-level gates
    the generic checks above don't cover — mirrors `_validate_dk_work`'s own
    "preflight never simply trusts an upstream stage already checked
    something" posture, re-derived from the DIST output independently of
    stage1_latin's own parse-time gates (`_derive_transposed_blocks` and the
    lacuna-declaration check there catch drift against the SOURCE export;
    these catch drift in the EMIT/sort step that runs after that):

      * bidirectional lacuna declaration (design memo §3.2, orchestrator
        design delta): the set of role='lacuna' columns actually emitted,
        per book, must equal the manifest's declared `citation.lacunae`
        exactly.
      * a lacuna segment carries zero Latin tokens (§3.2: "have NO Latin
        tokens").
      * post-sort citation-order monotonicity (§3.3(a)): after stage7's
        citation-order sort, each book's column sequence must be strictly
        increasing — a stale/broken sort would otherwise ship silently.
      * observed-spine token-SET fingerprint (§3.3(b)): count + sha256 over
        every emitted book.lineref column, in emission order (already
        citation order, book-major after the sort above), compared against
        the manifest's declared `citation.fingerprint`.
    """
    citation = manifest.data.get("citation") or {}
    declared_lacunae: dict[str, set[str]] = {
        str(k): set(v) for k, v in (citation.get("lacunae") or {}).items()
    }
    all_columns: list[str] = []
    for book in manifest.data.get("books", []):
        if not isinstance(book, dict) or not isinstance(book.get("n"), int):
            continue
        name = f"book-{book['n']:02d}.json"
        doc = loaded.get(name)
        if not isinstance(doc, dict) or not isinstance(doc.get("segments"), list):
            continue
        book_n = str(book["n"])
        found_lacunae: set[str] = set()
        previous_key: tuple | None = None
        for segment in doc["segments"]:
            if not isinstance(segment, dict):
                continue
            column = segment.get("column")
            if not isinstance(column, str) or not _is_column(column, scheme):
                # Already reported as a structural problem by _validate_books
                # (segments[i].column must be a Bekker column string) — not
                # re-reported here.
                continue
            all_columns.append(column)
            key = column_key(column, scheme)
            if previous_key is not None and key <= previous_key:
                problems.append((
                    manifest.work_id, name,
                    f"column {column} is not strictly greater than the "
                    f"preceding column in citation order (post-sort "
                    f"monotonicity gate)",
                ))
            previous_key = key
            lineref = column.split(".", 1)[1]
            greek = segment.get("greek")
            line0 = greek[0] if isinstance(greek, list) and greek else None
            role = line0.get("role") if isinstance(line0, dict) else None
            if role == "lacuna":
                found_lacunae.add(lineref)
                tokens = line0.get("tokens") if isinstance(line0, dict) else None
                if tokens:
                    problems.append((
                        manifest.work_id, name,
                        f"{column}: a lacuna segment carries {len(tokens)} "
                        f"token(s) — a lacuna must have zero Latin tokens",
                    ))
        declared = declared_lacunae.get(book_n, set())
        undeclared = found_lacunae - declared
        stale = declared - found_lacunae
        if undeclared or stale:
            problems.append((
                manifest.work_id, name,
                f"book {book_n} lacuna declaration mismatch against dist "
                f"output — undeclared (emitted but not in citation."
                f"lacunae): {sorted(undeclared) or 'none'}; stale (declared "
                f"but not emitted): {sorted(stale) or 'none'}",
            ))

    fp = citation.get("fingerprint")
    if not isinstance(fp, dict):
        problems.append((manifest.work_id, "<verse-line fingerprint>", "citation.fingerprint must be an object"))
    else:
        got_count = len(all_columns)
        got_sha256 = hashlib.sha256(",".join(all_columns).encode("utf-8")).hexdigest()
        if fp.get("count") != got_count or fp.get("sha256") != got_sha256:
            problems.append((
                manifest.work_id, "<verse-line fingerprint>",
                f"citation.fingerprint mismatch — declared count="
                f"{fp.get('count')!r} sha256={fp.get('sha256')!r}, got "
                f"count={got_count!r} sha256={got_sha256!r}",
            ))


def _validate_play_line_work(
    manifest: WorkManifest,
    loaded: dict[str, Any],
    problems: list[Problem],
    scheme,
) -> None:
    """play-line (the Greek drama corpus, P1 — docs/p1-probe.md)-specific
    dist-level gates, mirroring `_validate_verse_line_work`'s posture
    (re-derived from the DIST output independently of stage1_greek's own
    parse-time gates) but at LINE granularity rather than per-segment-
    column: unlike verse-line, a play-line segment holds many printed
    lines (one per speech, capped at 40 — see stage1_greek._segment_play_
    lines), so `citation.fingerprint` is a hash over every emitted line's
    own `ref`, in document (never re-sorted) order, not over segment
    column tokens:

      * every emitted line's `ref` matches the play-line grammar.
      * a lacuna ('post N') line carries zero tokens (mirrors verse-line's
        own "zero tokens" lacuna gate).
      * observed-spine ref-list fingerprint: count + sha256 over every
        emitted book-1.json line's `ref`, in emission order (document
        order -- play-line is never re-sorted, docs/p1-probe.md), compared
        against the manifest's declared `citation.fingerprint`.

    No post-sort monotonicity gate (contrast verse-line's own): play-line
    never resorts into citation order at emit time (the manuscript's real
    transpositions are declared and displayed exactly as printed), so there
    is no "after the sort" invariant to assert here."""
    all_refs: list[str] = []
    seen_refs: set[str] = set()
    # Mirror of stage1's `citation.repeated_refs` allowlist (REVIEW-CHECKLIST 3).
    _rep = (manifest.data.get("citation") or {}).get("repeated_refs") or {}
    allowed_repeats = {
        e["ref"]: e["count"] for e in (_rep.get("1", []) if isinstance(_rep, dict) else [])
        if isinstance(e, dict) and isinstance(e.get("ref"), str) and isinstance(e.get("count"), int)
    }
    ref_counts: dict[str, int] = {}
    for book in manifest.data.get("books", []):
        if not isinstance(book, dict) or not isinstance(book.get("n"), int):
            continue
        name = f"book-{book['n']:02d}.json"
        doc = loaded.get(name)
        if not isinstance(doc, dict) or not isinstance(doc.get("segments"), list):
            continue
        for segment in doc["segments"]:
            if not isinstance(segment, dict):
                continue
            greek = segment.get("greek")
            if not isinstance(greek, list):
                continue
            for line in greek:
                if not isinstance(line, dict):
                    continue
                ref = line.get("ref")
                if not isinstance(ref, str) or not scheme.column_re.match(ref):
                    problems.append((
                        manifest.work_id, name,
                        f"{segment.get('id')}: line n={line.get('n')} has "
                        f"missing/malformed ref {ref!r}",
                    ))
                    continue
                ref_counts[ref] = ref_counts.get(ref, 0) + 1
                if ref in seen_refs and ref not in allowed_repeats:
                    problems.append((
                        manifest.work_id, name,
                        f"{segment.get('id')}: repeated play-line ref {ref!r}",
                    ))
                seen_refs.add(ref)
                all_refs.append(ref)
                if line.get("role") == "lacuna":
                    tokens = line.get("tokens")
                    if tokens:
                        problems.append((
                            manifest.work_id, name,
                            f"{segment.get('id')}: ref {ref} is a lacuna line "
                            f"but carries {len(tokens)} token(s) — a lacuna "
                            f"must have zero tokens",
                        ))

    for _ref, _exp in allowed_repeats.items():
        if ref_counts.get(_ref, 0) != _exp:
            problems.append((manifest.work_id, 'book-01.json', f"citation.repeated_refs declares {_ref!r} x{_exp} but dist has x{ref_counts.get(_ref, 0)}"))
    fp = (manifest.data.get("citation") or {}).get("fingerprint")
    if not isinstance(fp, dict):
        problems.append((manifest.work_id, "<play-line fingerprint>", "citation.fingerprint must be an object"))
    else:
        got_count = len(all_refs)
        got_sha256 = hashlib.sha256(",".join(all_refs).encode("utf-8")).hexdigest()
        if fp.get("count") != got_count or fp.get("sha256") != got_sha256:
            problems.append((
                manifest.work_id, "<play-line fingerprint>",
                f"citation.fingerprint mismatch — declared count="
                f"{fp.get('count')!r} sha256={fp.get('sha256')!r}, got "
                f"count={got_count!r} sha256={got_sha256!r}",
            ))


# German stopwords that must never survive into emitted dk work data (memo
# §4.3(c), the belt-and-braces scan). Six bare bibliographic-apparatus
# particles -- "vgl." "compare", "nach" "after/following", "bei" "in/as
# quoted by" (Parmenides finding, Wave 1b: "EUDEM. bei Simpl. Phys. 143, 4"
# — "Eudemus, as quoted by/in Simplicius", the German-scholarship analogue
# of Latin "apud"); "aus" "from"/"des" "of the" (Xenophanes finding, Sol
# review blocker S3: "THEODORET. IV 5 aus Aëtios" -- "Theodoret ... from
# Aëtios", and "[Berthelot Collect. des Alchim. gr. I 2]" -- Berthelot's
# FRENCH-titled "Collection des Alchimistes grecs", "des" there is French,
# not German, but the bare-word scan can't tell the two languages apart and
# doesn't need to); and "richtig" "correct(ly)" (Xenophanes finding, Grok
# review defect G3, A9: EUSEB. Chron. "b) Ol. 59—61 [richtig Arm. 60,1 =
# 540]" -- a Eusebius-chronicle date correction functioning exactly like
# Latin "recte", not narrative commentary) -- are legitimate even under a
# CORRECT decision (DK's own bracketed cross-reference notation, "[vgl. B
# 13]"), the same way "cf."/"see"/"recte" would be in an English apparatus:
# all six are citation-internal connectors, not commentary. They used to be
# excluded from this set GLOBALLY -- any number of occurrences, anywhere,
# forever, uncounted (Sol review nit: that let a genuinely NEW leak of any
# of them hide behind the same blanket pass). Scoped instead: they stay IN
# the scan (`_DK_BOUNDED_STOPWORDS`, checked separately in
# `_validate_dk_work`'s loop), and each OCCURRENCE is exempt only when the
# specific non-Greek run it lives in has a REVIEWED, KEPT decision in this
# work's own dk-context-lang.json -- `citation` OR `keep-latin` (verified
# against the real Heraclitus corpus: several genuine `keep-latin` runs are
# a Latin bibliographic citation with "vgl."/"Vgl." embedded as the
# connector between two references, e.g. "—aqu. et ign. comp. 7 p. 957 A;
# vgl. de fort. 3. p. 98 C" -- Plutarch title abbreviations joined by the
# German shorthand, not German prose). Both decisions represent the same
# thing for this purpose: a human reviewed the run and chose to KEEP it
# verbatim, as opposed to `strip-german` (removed before this gate ever
# runs) or no decision at all. `_DK_GERMAN_STOPWORDS` above stays
# unconditional regardless of decision -- a genuine German stopword like
# "und"/"der" surviving in ANY kept run (citation or keep-latin) is still
# exactly the undecided/mis-decided leak this whole scan exists to catch;
# only vgl/nach/bei/aus/des/richtig get this scoped, decision-traced pass.
# (An earlier version of this gate bounded the total occurrence COUNT
# against the decision file's own reviewed count instead; that undercounted
# for real data, since one decided run recurs verbatim across many divs —
# DK's own citation apparatus repeats.)
_DK_GERMAN_STOPWORDS = {
    "der", "die", "das", "und", "oder", "über", "auch", "ist",
    "sind", "nämlich", "näml", "vielmehr", "mit", "für", "zum", "zur",
    "vom", "dem", "den", "eine", "einer", "wie", "wird", "werden",
    "sein", "seine", "ihre", "noch", "schon", "nur", "hier", "dort",
    "diese", "dieser", "dieses", "man",
}
_DK_BOUNDED_STOPWORDS = {"vgl", "nach", "bei", "aus", "des", "richtig"}

# A NARROWER exemption than `_DK_BOUNDED_STOPWORDS`' word-level pass: this
# one is bound to the EXACT normalized run text, per work, not to a word in
# isolation (Sol blocker S1, Empedocles B142/B101). Über/das/zur (and every
# other member of `_DK_GERMAN_STOPWORDS`) are ordinary German function
# words, not apparatus shorthand like "vgl."/"nach." -- a genuine German-
# commentary leak using any of them must stay unconditionally fatal, so
# these can never join `_DK_BOUNDED_STOPWORDS` wholesale (that would quietly
# widen the exemption to cover every future occurrence of "über" anywhere in
# the corpus, undecided or not). Two real Empedocles citations were being
# sacrificed to `strip-german` purely because their German glue words
# happened to be unconditional stopwords -- a Callimachus cross-reference
# and an Alexander *Problemata* citation, both now decided `citation` in
# dk-context-lang.json instead, with their German glue exempted HERE.
#
# Keyed by `dk_lang.decision_key(dk_lang.normalize_run(run))` -- the SAME
# hash the work's own dk-context-lang.json uses -- never the run's literal
# text: this dict is committed CODE, and the repo's hard rule (corpus
# source text is never committed) applies to it exactly as it does to the
# decision files themselves. Each entry's comment names the work/citation
# and WHY in non-verbatim terms; the run text itself is never quoted here.
# An occurrence is exempt only when ALL of: (1) the run's decision-file
# hash exactly matches a key below for this work; (2) the specific
# stopword hit(s) are a subset of that key's declared word set; (3) the
# run itself is decided `citation` or `keep-latin` (never `strip-german`
# -- deleting the run cannot "satisfy" this gate by making the exemption's
# hash match something that was never actually kept).
_DK_UNCONDITIONAL_STOPWORD_EXEMPTIONS: dict[str, dict[str, frozenset[str]]] = {
    "empedocles-fragments": {
        # A17 run: a Callimachus *Epigr.* 7.3-4 cross-reference (a grammatical-
        # construction parallel) introduced by two words of German glue.
        "ed853047fca51312": frozenset({"über", "das"}),
        # B101 run: an Alexander *Problemata* III 102 citation (the dog-
        # scent aporia) closed by one word of German glue.
        "7f6ae40ec6fc6c05": frozenset({"zur"}),
    },
    # Wave 1b Zeno/Melissus/Anaxagoras batch: "Hier." is the standard
    # abbreviation for Hieronymus (Jerome) in a Eusebius-chronicle citation
    # ("Eus. [Hier.] a. Abr. ..." -- Eusebius' chronicle as continued/
    # transmitted by Jerome's Latin version), not the German adverb "hier"
    # ("here") -- the bare-word stopword scan is case-folded and cannot
    # distinguish the two. Both occurrences in this work are this exact
    # abbreviation, verified against the surrounding citation apparatus
    # (a Marmor Parium-style chronological entry in each case).
    "anaxagoras-testimonia": {
        # A short Eusebius/Jerome (Marmor Parium-style) death-date entry.
        "1bb5fbaea2070580": frozenset({"hier"}),
        # A long Pliny N.H. II 149f. passage (the falling-stone prediction)
        # continuing into the same Eusebius/Jerome chronicle entry.
        "3164c7c8cef23034": frozenset({"hier"}),
    },
    # Wave 1b Milesian batch (Thales/Anaximander/Anaximenes): two distinct
    # false-positive shapes, both keyed exactly per the mechanism above.
    "thales-testimonia": {
        # A1 run: Pliny N.H. XVIII 213 (the equinox-timing passage) --
        # Latin ablative "die" ("[on the 25th] day"), not the German
        # article -- the bare-word scan cannot tell Latin "die" from German
        # "die" apart, same posture as "des"/"aus" already scoped.
        "d44906ea51f85339": frozenset({"die"}),
        # A3 run (Clem. Strom. I 65 / Euseb. Chron.): a genuine DK
        # Olympiad-year citation bracket is glued with no intervening Greek
        # to a short German parenthetical aside -- the run cannot be split
        # at decision-file granularity without either losing the citation
        # number (stripping the whole run) or leaving the German word
        # behind (keeping it); kept whole as `citation` in dk-context-
        # lang.json to preserve the Olympiad number, glue word exempted here.
        "18934192ea178718": frozenset({"das"}),
    },
    "anaximander-testimonia": {
        # Same Pliny N.H. XVIII 213 passage as thales-testimonia above,
        # continuing on to name Anaximander's own equinox-timing figure --
        # same Latin "die", same exemption.
        "73854d5919d6549b": frozenset({"die"}),
    },
    # Wave-atomist (Democritus B300, the Bolos-Democritean dubia collection,
    # div_concat part 300,10): a Celsus prooemium citation (Dar. CML I 18,
    # naming Democritus among the sages skilled in medicine) whose German
    # gloss explains a pronoun's antecedent ("[namely] medicine"). As with
    # the Thales/Anaximander "die" and Empedocles cases above, the run
    # cannot be split at decision-file granularity without either losing
    # the whole citation (stripping the run) or leaving the gloss behind
    # (keeping it); kept whole as `keep-latin` in dk-context-lang.json to
    # preserve the citation, glue word exempted here instead.
    "democritus-fragments": {
        "78a9a34ebb443776": frozenset({"nämlich"}),
    },
    # Wave-sophists (Protagoras/Gorgias/Prodicus, DK vol. 2): two exemptions,
    # both keyed exactly per the mechanism above.
    "protagoras-testimonia": {
        # A4: the same Hieronymus (Jerome) Eusebius-chronicle abbreviation
        # already exempted for anaxagoras-testimonia above -- not the
        # German adverb it is homographic with. Verified against the
        # surrounding citation apparatus: a Eusebius/Jerome chronicle entry
        # dating Protagoras' book-burning to Ol. 84, continuing into an
        # Apuleius Florida quotation, the whole run a kept Latin
        # testimonium (decision `keep-latin`).
        "e4c383dc783d06f0": frozenset({"hier"}),
        # A1: a Favorinus FHG fragment-number bracket glued (no intervening
        # Greek) through the closing parenthesis to Diogenes Laertius' own
        # section-number marker, with two words of German glue in the
        # middle -- the Thales-A3 shape exactly: the run cannot be split at
        # decision-file granularity without either losing the FHG citation
        # and the section number (stripping) or leaving the glue behind
        # (keeping). Kept whole as `citation`, glue word exempted here (a
        # second glue word in the same run is bounded, auto-exempt on any
        # kept decision).
        "a621111cebcdf11f": frozenset({"näml"}),
    },
    # Wave 1c Sophists batch 2 (Hippias/Antiphon-Sophist/Critias): a Sol/Grok
    # content-verification finding -- four `strip-german` decisions had
    # over-reached, truncating a DK citation down to a single word (the
    # Thales-A3/Protagoras-A1 shape above: a citation run can't be split at
    # decision-file granularity, so it is kept whole as `citation` instead,
    # with its German glue word(s) exempted here). Three of the four carry
    # only BOUNDED stopwords (vgl./des), already auto-exempt on a kept
    # decision with no entry needed here; this one carries an UNCONDITIONAL
    # stopword too.
    "antiphon-sophist-testimonia": {
        # A6: a Plutarch Vitae X oratorum citation closed by a short German
        # identification phrase naming Antiphon by his demotic.
        "6b26820e50c4a059": frozenset({"der"}),
    },
}
_DK_WORD_RE = re.compile(r"[A-Za-zÀ-ſ]+")

# Quote-mark polarity gate (owner ruling 2026-08-05, "we fix it and make
# damn sure every instance is correct") -- duplicated from stage1_greek.py's
# identically-named constants rather than imported (same posture as
# `_is_greek_letter`'s own duplication across stage1/stage3, see stage1_
# greek.py's doc comment: this file is the independent DIST-level check
# and deliberately never trusts stage1_greek's own in-process state, only
# the emitted JSON). U+0027 APOSTROPHE (Greek elision -- δ', ἀλλ', καθ',
# etc.) is a different code point from either and is never touched or
# scanned for here.
_DK_QUOTE_OPEN = "‘"   # LEFT SINGLE QUOTATION MARK (U+2018)
_DK_QUOTE_CLOSE = "’"  # RIGHT SINGLE QUOTATION MARK (U+2019)
_DK_QUOTE_CHARS = _DK_QUOTE_OPEN + _DK_QUOTE_CLOSE


def _div_map_label_strip_re(manifest: WorkManifest) -> re.Pattern[str] | None:
    """A div_map merge block's own synthetic label prefix (stage1_greek.
    _parse_fragments: `f"[{label}] {text}"`, Parmenides B7/B8) -- stripped
    before re-deriving non-Greek runs for the bounded-stopword check below;
    see that check's own comment for why.

    Built EXACTLY from this work's own manifest-declared citation.div_map
    labels (Sol review nit (b)), never a generic "any leading [...]" regex:
    the old blanket pattern would strip ANY bracketed lead-in a source
    happened to carry -- including a genuine DK apparatus bracket that is
    NOT a div_map label (e.g. a bracketed cross-reference like "[vgl. B
    13]") -- silently widening what this gate exempts from the bounded-
    stopword scan. `None` when the work declares no div_map at all (no
    merge block, nothing to strip)."""
    labels = sorted({
        e.get("label") for e in (manifest.data.get("citation") or {}).get("div_map", [])
        if isinstance(e, dict) and isinstance(e.get("label"), str)
    })
    if not labels:
        return None
    alternation = "|".join(re.escape(label) for label in labels)
    return re.compile(rf"^\[(?:{alternation})\]\s*")


def _is_greek_letter_pf(ch: str) -> bool:
    """True when ch is a Greek LETTER of any accentuation (mirrors the
    identically-named helpers elsewhere in this pipeline -- duplicated
    rather than imported, same reasoning as those modules' docstrings)."""
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return False
    return name.startswith("GREEK") and unicodedata.category(ch).startswith("L")


def _is_latin_letter_pf(ch: str) -> bool:
    """True when ch is a Latin-script LETTER of any accentuation (mirrors
    stage3_tokenize._is_latin_letter -- duplicated rather than imported,
    same reasoning as `_is_greek_letter_pf` above)."""
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return False
    return name.startswith("LATIN") and unicodedata.category(ch).startswith("L")


def _is_letter_pf(ch: str) -> bool:
    """True when ch is a Greek or Latin LETTER -- used by `_validate_greek_
    lined`'s I3 wrap-tail check to tell a bare punctuation/space tail
    (valid: the absorbed continuation fragment's attached punctuation, e.g.
    the `.` in `ἀποδοκιμαστικήν.`) apart from a tail that still hides a
    word (invalid)."""
    return _is_greek_letter_pf(ch) or _is_latin_letter_pf(ch)


def _validate_emitted_manifest(manifest: WorkManifest, emitted: Any, problems: list[Problem]) -> None:
    if emitted is None:
        return
    if not isinstance(emitted, dict):
        problems.append((manifest.work_id, "manifest.json", "root must be an object"))
        return
    work = emitted.get("work")
    if not isinstance(work, dict):
        problems.append((manifest.work_id, "manifest.json", "work must be an object"))
        return
    if work.get("id") != manifest.work_id:
        problems.append((manifest.work_id, "manifest.json", f"work.id {work.get('id')!r} does not match manifest"))


def _validate_books(
    manifest: WorkManifest,
    loaded: dict[str, Any],
    problems: list[Problem],
    bekker_native: bool = True,
    expected_gaps: set[tuple[str, int, int]] | None = None,
    scheme=None,
    dk_all_context_columns: set[str] | None = None,
) -> tuple[dict[tuple[int, str], dict[str, Any]], set[tuple[int, str, int]], set[str]]:
    expected_gaps = expected_gaps or set()
    # The all-context cross-check below is meaningful ONLY for a VERSE dk
    # work (citation.lines: true): only there does `n >= 0` (this function's
    # `line_numbers`) correspond to "carries a role='text' line" -- a verse
    # context block is deliberately given a NEGATIVE synthetic n precisely so
    # it never counts (stage1_greek._parse_fragments). A LINELESS (prose)
    # dk work has no such split: `out_n = i` there is a plain position index
    # assigned to EVERY block regardless of role (context included), so a
    # prose column's `line_numbers` is non-empty whenever it has ANY content
    # at all -- unmarked or not -- and can never legitimately go empty (an
    # empty `greek` list is already rejected above as its own problem). Using
    # `line_numbers` as an "all-context" proxy for prose would therefore be
    # wrong on its face (verified against the live Heraclitus/Parmenides-
    # testimonia corpus: gating this on `fragment_scheme` alone produced 174
    # false "stale unmarked_columns declaration" reports against columns that
    # are correctly declared unmarked) -- prose's role-coverage/emission-loss
    # exposure is real but is a DIFFERENT signal (the segment's own `role`
    # fields, already partly examined by `_validate_dk_work`'s zero-Greek-
    # token gate) and is out of scope for this columns.json/line-range gate.
    is_dk_verse = scheme is not None and scheme.fragment_scheme and scheme.lines_user_facing
    dk_all_context_columns = dk_all_context_columns or set()
    segments_by_book_col: dict[tuple[int, str], dict[str, Any]] = {}
    anchors: set[tuple[int, str, int]] = set()
    token_keys: set[str] = set()
    seen_segment_ids: set[str] = set()
    previous_segment_key: tuple[int, str, int] | None = None
    walk_failures: list[str] = []
    walk_failure_total = 0
    offset_mismatches: list[str] = []
    offset_mismatch_total = 0
    lined_indent_observations: list[tuple[int, str, str]] = []
    lined_segments: list[tuple[str, str]] = []

    for book in manifest.data.get("books", []):
        if not isinstance(book, dict) or not isinstance(book.get("n"), int):
            continue
        name = f"book-{book['n']:02d}.json"
        doc = loaded.get(name)
        if doc is None:
            continue
        if not isinstance(doc, dict):
            problems.append((manifest.work_id, name, "root must be an object"))
            continue
        if doc.get("book") != book["n"]:
            problems.append((manifest.work_id, name, f"book field must be {book['n']}"))
        segments = doc.get("segments")
        if not isinstance(segments, list):
            problems.append((manifest.work_id, name, "segments must be a list"))
            continue
        previous_in_book: tuple[int, str, int] | None = None
        for i, segment in enumerate(segments):
            if not isinstance(segment, dict):
                problems.append((manifest.work_id, name, f"segments[{i}] must be an object"))
                continue
            seg_id = segment.get("id")
            column = segment.get("column")
            if not isinstance(seg_id, str) or not seg_id:
                problems.append((manifest.work_id, name, f"segments[{i}].id must be a non-empty string"))
            elif seg_id in seen_segment_ids:
                problems.append((manifest.work_id, name, f"duplicate segment id {seg_id}"))
            else:
                seen_segment_ids.add(seg_id)
            if not _is_column(column, scheme):
                problems.append((manifest.work_id, name, f"segments[{i}].column must be a Bekker column string"))
                continue
            greek = segment.get("greek")
            if not isinstance(greek, list) or not greek:
                problems.append((manifest.work_id, name, f"segments[{i}].greek must be a non-empty list"))
                continue
            _validate_lined_source(
                manifest,
                name,
                seg_id or f"segments[{i}]",
                greek,
                problems,
                lined_indent_observations,
            )
            citation = manifest.data.get("citation")
            if isinstance(citation, dict) and citation.get("lined_source") is True:
                lined_segments.append((name, seg_id or f"segments[{i}]"))
            # Line numbers carrying a speaker-turn event (Segment.speakers,
            # see SpeakerTurn in shared/lib/data.ts) in THIS segment -- feeds
            # _validate_greek_sections' sections/speakers co-occurrence gate
            # below, computed once per segment rather than per line.
            speaker_lines: set[int] = set()
            speakers_field = segment.get("speakers")
            if isinstance(speakers_field, list):
                for ev in speakers_field:
                    if isinstance(ev, dict):
                        ev_line = ev.get("line")
                        if isinstance(ev_line, int) and not isinstance(ev_line, bool):
                            speaker_lines.add(ev_line)
            line_numbers: set[int] = set()
            previous_line: int | None = None
            for j, line in enumerate(greek):
                if not isinstance(line, dict):
                    problems.append((manifest.work_id, name, f"{seg_id}: greek[{j}] must be an object"))
                    continue
                n = line.get("n")
                if not isinstance(n, int):
                    problems.append((manifest.work_id, name, f"{seg_id}: greek[{j}].n must be an integer"))
                    continue
                prior_line = previous_line
                declared_gap = (column, prior_line, n) in expected_gaps
                if bekker_native and prior_line is not None and n < prior_line and not declared_gap:
                    problems.append((manifest.work_id, name, f"{seg_id}: Greek Bekker lines are out of order at {column}{n}"))
                previous_line = n
                anchor = (book["n"], column, n)
                if bekker_native and anchor in anchors and not declared_gap:
                    problems.append((manifest.work_id, name, f"duplicate Bekker anchor {column}{n}"))
                anchors.add(anchor)
                # A dk verse fragment's role='context' line carries a
                # non-citable NEGATIVE synthetic n (stage1_greek.
                # _parse_fragments) -- excluded from `line_numbers` here so
                # it never widens the citable range this segment reports to
                # `_validate_columns` (columns.json) / `_validate_english_
                # bekker` / `_validate_chapter_starts` below, mirroring
                # stage7_emit.column_line_ranges' own exclusion for the same
                # value it's cross-checked against.
                if n >= 0:
                    line_numbers.add(n)
                _collect_token_keys(manifest, name, seg_id or f"segments[{i}]", line, token_keys, problems)
                wf, om = _check_token_walk(column, n, line)
                walk_failure_total += len(wf)
                offset_mismatch_total += len(om)
                if len(walk_failures) < 10:
                    walk_failures.extend(wf[: 10 - len(walk_failures)])
                if len(offset_mismatches) < 10:
                    offset_mismatches.extend(om[: 10 - len(offset_mismatches)])
                _validate_greek_sections(manifest, name, seg_id or f"segments[{i}]", line, problems, speaker_lines)

            # An all-context dk verse fragment (citation.unmarked_columns,
            # e.g. Parmenides B22-B24 -- no role='text' block at all) has NO
            # citable line at all once negative synthetic n's are excluded
            # above: skip the Bekker-order/columns.json-range bookkeeping
            # below, which assumes at least one citable anchor exists (this
            # segment legitimately gets no columns.json entry either -- see
            # `_validate_columns`' matching skip for the same case). But an
            # empty `line_numbers` is no longer trusted on its own as proof
            # of that: for a dk work it is cross-checked against the
            # manifest-derived `dk_all_context_columns` (see
            # `_dk_expected_all_context_columns`'s doc comment) in BOTH
            # directions, so an emission-stage bug that silently loses a
            # column's citable lines cannot pass as "legitimately
            # all-context", and a stale `unmarked_columns` declaration
            # (the column actually carries citable lines) is caught too.
            if is_dk_verse and not line_numbers and column not in dk_all_context_columns:
                problems.append((
                    manifest.work_id, name,
                    f"{seg_id}: column {column} has zero citable (role='text') "
                    f"line(s) in the emitted data but is not declared in "
                    f"citation.unmarked_columns -- preflight independently "
                    f"derives the expected all-context column set from the "
                    f"manifest and will not treat an empty emitted line set "
                    f"as legitimately all-context without a matching "
                    f"declaration (an emission-stage bug that lost every "
                    f"citable line of this column would look identical)",
                ))
            if is_dk_verse and line_numbers and column in dk_all_context_columns:
                problems.append((
                    manifest.work_id, name,
                    f"{seg_id}: column {column} is declared in "
                    f"citation.unmarked_columns (expected zero citable lines) "
                    f"but the emitted data carries citable line(s) "
                    f"{sorted(line_numbers)} -- a stale unmarked_columns "
                    f"declaration must be removed, not left to silently no-op",
                ))
            if line_numbers:
                first_line = min(line_numbers)
                current_key = line_key(column, first_line, scheme)
                if bekker_native and previous_in_book is not None and current_key < previous_in_book:
                    problems.append((manifest.work_id, name, f"{seg_id}: segment Bekker order moved backwards at {column}{first_line}"))
                if bekker_native and previous_segment_key is not None and current_key < previous_segment_key:
                    problems.append((manifest.work_id, name, f"{seg_id}: work Bekker order moved backwards at {column}{first_line}"))
                previous_in_book = current_key
                previous_segment_key = current_key
            segments_by_book_col[(book["n"], column)] = {"segment": segment, "lines": line_numbers, "file": name}
            _validate_english_bekker(manifest, name, seg_id or f"segments[{i}]", segment, line_numbers, problems)
            _validate_chapter_starts(manifest, name, seg_id or f"segments[{i}]", segment, line_numbers, anchors, book["n"], column, problems, bekker_native)
    if walk_failure_total:
        problems.append((
            manifest.work_id,
            "<token-walk>",
            f"{walk_failure_total} Greek token(s) fail the sequential "
            f"text.find(t, ptr) walk that shared/lib/speakers.ts's "
            f"lineRenderParts performs at render time (a token's `t` is not "
            f"a literal, in-order-findable substring of its line's `text`) "
            f"-- samples: " + "; ".join(walk_failures)
            + (" ..." if walk_failure_total > len(walk_failures) else "")
        ))
    if offset_mismatch_total:
        problems.append((
            manifest.work_id,
            "<token-walk>",
            f"{offset_mismatch_total} Greek token(s) have an `o` that does "
            f"not point at their own `t` (text[o:o+len(t)] != t) -- "
            f"samples: " + "; ".join(offset_mismatches)
            + (" ..." if offset_mismatch_total > len(offset_mismatches) else "")
        ))
    _validate_lined_indent_max(
        manifest,
        lined_indent_observations,
        lined_segments,
        problems,
    )
    return segments_by_book_col, anchors, token_keys


def _check_token_walk(column: str, n: int, line: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Mirror shared/lib/speakers.ts's lineRenderParts render-time walk: step
    through `line["tokens"]` in order against `line["text"]` with a moving
    pointer via `text.find(t, ptr)`, exactly like the reader's
    `text.indexOf(tok.t, ptr)`. On success `ptr` advances past the match;
    on failure `ptr` is deliberately left UNCHANGED before moving to the
    next token -- matching the renderer's own behavior (it does not advance
    `ptr` on a miss either) -- so a single stripped-mark token reproduces the
    same cascading leapfrog the reader hits, rather than a preflight walk
    that quietly resyncs on the next token.

    Returns `(walk_failure_descriptions, offset_mismatch_descriptions)`,
    both empty for a clean line. Structurally invalid lines/tokens (missing
    or wrong-typed `text`/`tokens`/`t`/`o`) are skipped here without error --
    `_collect_token_keys` already reports those as their own problems, and
    this check would either double-report or crash on them."""
    text = line.get("text")
    tokens = line.get("tokens")
    if not isinstance(text, str) or not isinstance(tokens, list):
        return [], []
    walk_failures: list[str] = []
    offset_mismatches: list[str] = []
    ptr = 0
    for tok in tokens:
        if not isinstance(tok, dict):
            continue
        t = tok.get("t")
        if not isinstance(t, str) or not t:
            continue
        idx = text.find(t, ptr)
        if idx < 0:
            walk_failures.append(f"{column}{n} {t!r} (ptr={ptr})")
            continue
        ptr = idx + len(t)
        o = tok.get("o")
        if isinstance(o, int) and not isinstance(o, bool) and text[o : o + len(t)] != t:
            offset_mismatches.append(f"{column}{n} {t!r} o={o}")
    return walk_failures, offset_mismatches


def _validate_lined_source(
    manifest: WorkManifest,
    file_name: str,
    seg_id: str,
    greek: list[Any],
    problems: list[Problem],
    indent_observations: list[tuple[int, str, str]] | None = None,
) -> None:
    """Validate the segment-wide shape used by lined source works.

    ``citation.lined_source: true`` is the source-of-truth scope guard. The
    emitted ``sec`` key is also accepted as a shape-based guard so preflight
    still checks lined data when a caller has not yet passed through the new
    manifest flag.
    """
    citation = manifest.data.get("citation")
    manifest_lined = isinstance(citation, dict) and citation.get("lined_source") is True
    shape_lined = any(
        isinstance(line, dict) and ("sec" in line or "wrap" in line)
        for line in greek
    )
    if not manifest_lined and not shape_lined:
        return

    got_n = [line.get("n") if isinstance(line, dict) else None for line in greek]
    expected_n = list(range(1, len(greek) + 1))
    if any(type(n) is not int for n in got_n) or got_n != expected_n:
        problems.append((
            manifest.work_id,
            file_name,
            f"{seg_id}: lined source `n` values must be exactly 1..{len(greek)} "
            f"in order (got {got_n!r})",
        ))

    bad_secs: list[str] = []
    has_secs = [isinstance(line, dict) and "sec" in line for line in greek]
    if any(has_secs) and not all(has_secs):
        bad_secs.append("`sec` is present on some lines but not others")
    previous_sec: int | None = None
    for i, line in enumerate(greek):
        if not isinstance(line, dict) or "sec" not in line:
            continue
        sec = line.get("sec")
        if type(sec) is not int or sec < 1:
            bad_secs.append(f"greek[{i}].sec={sec!r} is not a positive integer")
            continue
        if previous_sec is not None and sec < previous_sec:
            bad_secs.append(f"greek[{i}].sec={sec} follows {previous_sec}")
        previous_sec = sec
    if bad_secs:
        problems.append((
            manifest.work_id,
            file_name,
            f"{seg_id}: lined source `sec` must be present on every line or on "
            f"none; when present, it must be a positive integer and must not "
            f"decrease ({'; '.join(bad_secs)})",
        ))

    bad_wraps: list[str] = []
    for i, line in enumerate(greek):
        if not isinstance(line, dict):
            continue
        has_wrap = "wrap" in line
        has_joined = "joined" in line
        has_wrap_o = "wrapO" in line
        if not has_wrap and not has_joined and not has_wrap_o:
            continue

        reasons: list[str] = []
        if has_wrap != has_wrap_o:
            reasons.append("`wrap` and `wrapO` must be present together")
        if (has_wrap or has_wrap_o) and not has_joined:
            reasons.append("`wrap` or `wrapO` requires `joined`")
        if has_joined and not has_wrap and not has_wrap_o and i != len(greek) - 1:
            reasons.append("`joined` without `wrap`/`wrapO` is allowed only on the segment's last line")

        if has_wrap and has_wrap_o:
            wrap = line.get("wrap")
            wrap_o = line.get("wrapO")
            tokens = line.get("tokens")
            text = line.get("text")
            if type(wrap_o) is not int:
                reasons.append("`wrapO` must be an integer")
            elif not isinstance(tokens, list):
                reasons.append("`wrapO` requires `tokens` to be a list")
            else:
                # The wrapped token is the one AT offset `wrapO` -- named
                # explicitly (2026-08-29 deviation, docs/lined-source-
                # plan.md §3) because whole-whitespace-token absorption
                # (I4) can glue more than the wrapped word onto this line
                # (an em-dash glob with no space before the next word), so
                # the wrapped token is not always the LAST token.
                wrapped_idx = None
                wrapped_token = None
                for ti, tok in enumerate(tokens):
                    if isinstance(tok, dict) and tok.get("o") == wrap_o:
                        wrapped_idx = ti
                        wrapped_token = tok
                        break
                if wrapped_token is None:
                    reasons.append(f"`wrapO`={wrap_o!r} does not match any token's `o`")
                else:
                    token_text = wrapped_token.get("t")
                    if not isinstance(token_text, str) or not token_text:
                        reasons.append("the token at `wrapO` must carry a non-empty `t`")
                    else:
                        if type(wrap) is not int or not 0 < wrap < len(token_text):
                            reasons.append(
                                f"`wrap` must be an integer with 0 < wrap < "
                                f"len(token at wrapO `t`)={len(token_text)} (got {wrap!r})"
                            )
                        if not isinstance(text, str):
                            reasons.append("line `text` must be a string")
                        elif text[wrap_o : wrap_o + len(token_text)] != token_text:
                            reasons.append(
                                "line `text` must contain the token at `wrapO`'s `t` "
                                "at its own offset"
                            )
                        elif wrapped_idx == len(tokens) - 1:
                            # Only when no token follows the wrapped one does
                            # the letterless-tail rule apply: the absorbed
                            # continuation fragment may carry attached
                            # punctuation (a sentence-final period, most
                            # commonly -- see I3's 2026-08-29 amendment), and
                            # text after the wrapped token's `t` is a valid
                            # TAIL as long as it hides no further letters.
                            # When tokens follow (the em-dash glob case), no
                            # such requirement applies -- the glob
                            # legitimately contains a following word.
                            tail = text[wrap_o + len(token_text) :]
                            if any(_is_letter_pf(ch) for ch in tail):
                                reasons.append(
                                    "text after the wrapped token's `t` must contain "
                                    "no letter characters (only a punctuation/space "
                                    "tail is allowed)"
                                )

        if reasons:
            bad_wraps.append(f"greek[{i}]: {', '.join(reasons)}")
    if bad_wraps:
        problems.append((
            manifest.work_id,
            file_name,
            f"{seg_id}: invalid lined source wrap metadata ({'; '.join(bad_wraps)})",
        ))

    declared_indent_max = citation.get("lined_indent_max") if isinstance(citation, dict) else None
    bad_indents: list[str] = []
    for i, line in enumerate(greek):
        if not isinstance(line, dict) or "indent" not in line:
            continue
        indent = line.get("indent")
        if type(indent) is not int or not 1 <= indent <= 20:
            bad_indents.append(
                f"greek[{i}].indent={indent!r} is not an integer 1..20"
            )
            continue
        if indent_observations is not None:
            indent_observations.append((indent, file_name, seg_id))
        if type(declared_indent_max) is int and indent > declared_indent_max:
            bad_indents.append(
                f"greek[{i}].indent={indent} exceeds citation.lined_indent_max="
                f"{declared_indent_max}"
            )
    if bad_indents:
        problems.append((
            manifest.work_id,
            file_name,
            f"{seg_id}: invalid lined source `indent` ({'; '.join(bad_indents)})",
        ))

    sec_and_sections = [
        i
        for i, line in enumerate(greek)
        if isinstance(line, dict) and "sec" in line and "sections" in line
    ]
    if sec_and_sections:
        problems.append((
            manifest.work_id,
            file_name,
            f"{seg_id}: lined source line(s) {sec_and_sections} carry both `sec` "
            f"and a `sections` key",
        ))


def _validate_lined_indent_max(
    manifest: WorkManifest,
    observations: list[tuple[int, str, str]],
    lined_segments: list[tuple[str, str]],
    problems: list[Problem],
) -> None:
    """Reject a stale-high declared indent maximum once per lined work."""
    citation = manifest.data.get("citation")
    if not isinstance(citation, dict) or citation.get("lined_source") is not True:
        return
    declared = citation.get("lined_indent_max")
    if type(declared) is not int:
        return
    observed = max((level for level, _, _ in observations), default=0)
    if observed >= declared:
        return
    if observations:
        _, file_name, seg_id = max(observations, key=lambda item: item[0])
    elif lined_segments:
        file_name, seg_id = lined_segments[0]
    else:
        file_name, seg_id = "<lined-source>", "<work>"
    problems.append((
        manifest.work_id,
        file_name,
        f"{seg_id}: lined source citation.lined_indent_max={declared} is stale-high; "
        f"the greatest emitted `indent` in the work is {observed}",
    ))


def _validate_greek_sections(
    manifest: WorkManifest,
    file_name: str,
    seg_id: str,
    line: dict[str, Any],
    problems: list[Problem],
    speaker_lines: set[int] | None = None,
) -> None:
    """Validate a Greek line's `sections` channel (Discourses/Enchiridion's
    TLG-section paragraphing standoff -- see stage1_greek._chapter_sections
    and GreekLine.sections in shared/lib/data.ts): every entry's `n`/`o` a
    positive int / int, offsets strictly ascending (so the first is
    implicitly >= 0), all in-bounds (< len(text)), and the RENDER-SAFETY
    contract Reader.svelte's splitGreekSections depends on -- no offset
    falls strictly INSIDE any token's [o, o+len(t)) span (an inter-token
    gap, or a token's own start, are both fine; the fixed renderer slices
    `text` directly by these offsets, so a mid-token offset would silently
    split a clickable word). FATAL, matching the sibling token-walk gate
    above. Token spans are located the same way `_check_token_walk` locates
    them (a sequential text.find(t, ptr) walk), so this reports against
    what the renderer will actually see, not a naive trust of a token's own
    declared `o` (already checked separately).

    Two further FATAL rules, both from a GPT-5.6-Sol-High confirm review
    (2026-07-16) of the render-safety gate above:

    1. `sections[0].o` must be exactly 0. `splitGreekSections` (shared/lib/
       speakers.ts) slices `line.text` starting at `secs[0].o`, not from 0 --
       stage1_greek._chapter_sections always anchors the first section at the
       chapter's start (o=0), but nothing enforced that here, so any future
       producer emitting a nonzero first offset would silently drop the text
       before it at render time with no build-time signal.

    2. A Greek line may not carry BOTH a `sections` channel and a
       speaker-turn event (Segment.speakers, see SpeakerTurn in
       shared/lib/data.ts; caller passes the segment's speaker-carrying line
       numbers as `speaker_lines`). `splitGreekSections` does not re-bucket
       `Segment.speakers` across the pieces it produces -- a continuation
       piece (`cont: true`) silently loses any speaker event that belonged to
       it. This combination has never shipped (Discourses/Enchiridion, the
       only `sections` users, carry no dialogue turns), so this FATAL simply
       documents that renderer support must be built before it does, rather
       than let it ship silently broken.
    """
    # Lined-source works use the per-line `sec` channel instead. Even a bad
    # lined line that still carries the old `sections` key belongs solely to
    # `_validate_lined_source`, which reports that I5 clash once per segment.
    if "sec" in line:
        return
    secs = line.get("sections")
    if secs is None:
        return
    n_field = line.get("n")
    if speaker_lines and isinstance(n_field, int) and not isinstance(n_field, bool) and n_field in speaker_lines:
        problems.append((
            manifest.work_id,
            file_name,
            f"{seg_id}: greek line {n_field} carries both a `sections` channel and a "
            f"speaker-turn event -- splitGreekSections does not re-bucket speaker events "
            f"across section pieces, so a continuation piece would silently drop it",
        ))
    if not isinstance(secs, list):
        problems.append((manifest.work_id, file_name, f"{seg_id}: greek line {n_field}.sections must be a list"))
        return
    text = line.get("text")
    text_len = len(text) if isinstance(text, str) else None
    spans: list[tuple[int, int]] = []
    if isinstance(text, str) and isinstance(line.get("tokens"), list):
        ptr = 0
        for tok in line["tokens"]:
            if not isinstance(tok, dict):
                continue
            t = tok.get("t")
            if not isinstance(t, str) or not t:
                continue
            idx = text.find(t, ptr)
            if idx < 0:
                continue
            spans.append((idx, idx + len(t)))
            ptr = idx + len(t)
    prev_o: int | None = None
    for k, entry in enumerate(secs):
        if not isinstance(entry, dict):
            problems.append((manifest.work_id, file_name, f"{seg_id}: greek line {n_field}.sections[{k}] must be an object"))
            continue
        n = entry.get("n")
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            problems.append((manifest.work_id, file_name, f"{seg_id}: greek line {n_field}.sections[{k}].n must be a positive integer"))
        o = entry.get("o")
        if not isinstance(o, int) or isinstance(o, bool):
            problems.append((manifest.work_id, file_name, f"{seg_id}: greek line {n_field}.sections[{k}].o must be an integer"))
            continue
        if o < 0 or (text_len is not None and o >= text_len):
            problems.append((manifest.work_id, file_name, f"{seg_id}: greek line {n_field}.sections[{k}].o={o} out of bounds (text length {text_len})"))
        elif prev_o is not None and o <= prev_o:
            problems.append((manifest.work_id, file_name, f"{seg_id}: greek line {n_field}.sections offsets not strictly ascending (o={o} after {prev_o})"))
        elif k == 0 and o != 0:
            problems.append((manifest.work_id, file_name, f"{seg_id}: greek line {n_field}.sections[0].o must be 0 (got {o}) -- splitGreekSections slices line.text starting at sections[0].o, so text before a nonzero first offset would be silently dropped"))
        for start, end in spans:
            if start < o < end:
                problems.append((manifest.work_id, file_name, f"{seg_id}: greek line {n_field}.sections[{k}].o={o} falls inside token span [{start},{end}) -- would split a clickable word"))
                break
        prev_o = o


def _validate_english_paras(
    manifest: WorkManifest,
    file_name: str,
    seg_id: str,
    english: dict[str, Any],
    problems: list[Problem],
) -> None:
    """Validate an English chunk's `paras` channel (Discourses' Oldfather
    every-5th-TLG-section Loeb-reference paragraph markers -- see
    stage1_book_section_english.py's paras sidecar and EnglishChunk.paras):
    entries' `n`/`o` both ints, offsets strictly ascending and in-bounds
    (< len(text)). FATAL, matching the sibling Greek `sections` gate."""
    paras = english.get("paras")
    if paras is None:
        return
    if not isinstance(paras, list):
        problems.append((manifest.work_id, file_name, f"{seg_id}: english.paras must be a list"))
        return
    text = english.get("text")
    text_len = len(text) if isinstance(text, str) else None
    prev_o: int | None = None
    for k, entry in enumerate(paras):
        if not isinstance(entry, dict):
            problems.append((manifest.work_id, file_name, f"{seg_id}: english.paras[{k}] must be an object"))
            continue
        n = entry.get("n")
        if not isinstance(n, int) or isinstance(n, bool):
            problems.append((manifest.work_id, file_name, f"{seg_id}: english.paras[{k}].n must be an integer"))
        o = entry.get("o")
        if not isinstance(o, int) or isinstance(o, bool):
            problems.append((manifest.work_id, file_name, f"{seg_id}: english.paras[{k}].o must be an integer"))
            continue
        if o < 0 or (text_len is not None and o >= text_len):
            problems.append((manifest.work_id, file_name, f"{seg_id}: english.paras[{k}].o={o} out of bounds (text length {text_len})"))
        elif prev_o is not None and o <= prev_o:
            problems.append((manifest.work_id, file_name, f"{seg_id}: english.paras offsets not strictly ascending (o={o} after {prev_o})"))
        prev_o = o


def _collect_token_keys(
    manifest: WorkManifest,
    file_name: str,
    seg_id: str,
    line: dict[str, Any],
    token_keys: set[str],
    problems: list[Problem],
) -> None:
    tokens = line.get("tokens")
    if not isinstance(tokens, list):
        problems.append((manifest.work_id, file_name, f"{seg_id}: greek line tokens must be a list"))
        return
    for token in tokens:
        if not isinstance(token, dict):
            problems.append((manifest.work_id, file_name, f"{seg_id}: token must be an object"))
            continue
        # Explicit schema, checked independently of the (optional) `k` field
        # below: a structurally invalid token — missing `t`, missing `o`, or
        # either of the wrong type — must be rejected on its own terms, not
        # rely on the `k` check to incidentally catch it (a non-lexical
        # token legitimately carries no `k` at all, so that check alone lets
        # {}, {"t": "..."} , and {"o": 0} all slip through). A whitespace-only
        # `t` (e.g. " ") is likewise rejected, with its own distinct message
        # rather than folding into the empty-string case — a real emitted
        # token is never pure whitespace (stage3_tokenize's regex splits on
        # whitespace, so a token's `t` can only be whitespace-only if
        # something upstream of stage3 is broken).
        t = token.get("t")
        if not isinstance(t, str) or not t:
            problems.append((manifest.work_id, file_name, f"{seg_id}: token.t must be a non-empty string"))
        elif not t.strip():
            problems.append((manifest.work_id, file_name, f"{seg_id}: token.t must not be whitespace-only"))
        o = token.get("o")
        if not isinstance(o, int) or isinstance(o, bool) or o < 0:
            problems.append((manifest.work_id, file_name, f"{seg_id}: token.o must be a non-negative integer"))
        # A token with no `k` field at all is NON-LEXICAL (no Greek letters —
        # inline Latin-script apparatus, editor names, bare numerals) and is
        # valid as-is: stage3_tokenize omits `k` for those rather than
        # emitting an empty string. A token that DOES carry `k` must still
        # have a non-empty string — an empty string is never valid, and
        # stage3 fails loudly before emission if a Greek token would key
        # empty, so a present-but-empty `k` here is an emission-side bug.
        if "k" in token:
            key = token.get("k")
            if not isinstance(key, str) or not key:
                problems.append((manifest.work_id, file_name, f"{seg_id}: token.k must be a non-empty string"))
            else:
                token_keys.add(key)
    for cell in line.get("cells", []) or []:
        if not isinstance(cell, dict):
            problems.append((manifest.work_id, file_name, f"{seg_id}: cell must be an object"))
            continue
        if not isinstance(cell.get("tokens"), list):
            problems.append((manifest.work_id, file_name, f"{seg_id}: cell tokens must be a list"))


def _validate_english_bekker(
    manifest: WorkManifest,
    file_name: str,
    seg_id: str,
    segment: dict[str, Any],
    line_numbers: set[int],
    problems: list[Problem],
) -> None:
    english = segment.get("english")
    if english is None:
        return
    if not isinstance(english, dict):
        problems.append((manifest.work_id, file_name, f"{seg_id}: english must be an object or null"))
        return
    for marker in english.get("bekker", []) or []:
        if not isinstance(marker, dict):
            problems.append((manifest.work_id, file_name, f"{seg_id}: english.bekker marker must be an object"))
            continue
        n = marker.get("n")
        if not isinstance(n, int):
            problems.append((manifest.work_id, file_name, f"{seg_id}: english.bekker.n must be an integer"))
            continue
        # NOTE: english.bekker markers carry only a line number `n`, not the
        # column. A segment's English prose routinely runs past its own column
        # into the next one, so the marker list legitimately contains e.g.
        # ...,30,35,1 (column X line 35 then column X+1 line 1). Without a column
        # tag we cannot tell that valid reset apart from real disorder, nor
        # verify a marker's Greek anchor (line 1 belongs to the next column's
        # Greek, absent from this segment's line set). Both checks produced only
        # false positives on the live corpus, so marker *shape* is validated but
        # ordering/anchoring is not.
    _validate_english_paras(manifest, file_name, seg_id, english, problems)


def _validate_chapter_starts(
    manifest: WorkManifest,
    file_name: str,
    seg_id: str,
    segment: dict[str, Any],
    line_numbers: set[int],
    anchors: set[tuple[int, str, int]],
    book: int,
    column: str,
    problems: list[Problem],
    bekker_native: bool = True,
) -> None:
    starts = segment.get("chapterStarts", []) or []
    if not isinstance(starts, list):
        problems.append((manifest.work_id, file_name, f"{seg_id}: chapterStarts must be a list"))
        return
    previous_line: int | None = None
    for start in starts:
        if not isinstance(start, dict):
            problems.append((manifest.work_id, file_name, f"{seg_id}: chapterStart must be an object"))
            continue
        before_line = start.get("beforeLine")
        if not isinstance(before_line, int):
            problems.append((manifest.work_id, file_name, f"{seg_id}: chapterStarts.beforeLine must be an integer"))
            continue
        if bekker_native and previous_line is not None and before_line < previous_line:
            problems.append((manifest.work_id, file_name, f"{seg_id}: chapterStarts are out of order at line {before_line}"))
        if bekker_native and before_line not in line_numbers:
            problems.append((manifest.work_id, file_name, f"{seg_id}: chapterStart beforeLine {before_line} has no Greek line"))
        if bekker_native and (book, column, before_line) not in anchors:
            problems.append((manifest.work_id, file_name, f"{seg_id}: chapterStart beforeLine {before_line} has no Bekker anchor"))
        previous_line = before_line


def _validate_chapters(
    manifest: WorkManifest,
    chapters: Any,
    segments: dict[tuple[int, str], dict[str, Any]],
    anchors: set[tuple[int, str, int]],
    problems: list[Problem],
    bekker_native: bool = True,
    scheme=None,
) -> None:
    if chapters is None:
        return
    if not isinstance(chapters, dict):
        problems.append((manifest.work_id, "chapters.json", "root must be an object"))
        return
    for book_key, refs in chapters.items():
        try:
            book = int(book_key)
        except (TypeError, ValueError):
            problems.append((manifest.work_id, "chapters.json", f"book key {book_key!r} is not an integer string"))
            continue
        if not isinstance(refs, list):
            problems.append((manifest.work_id, "chapters.json", f"book {book_key} value must be a list"))
            continue
        previous: tuple[int, str, int] | None = None
        for i, ref in enumerate(refs):
            if not isinstance(ref, dict):
                problems.append((manifest.work_id, "chapters.json", f"{book_key}[{i}] must be an object"))
                continue
            column = ref.get("column")
            line_raw = ref.get("line")
            if not _is_column(column, scheme):
                problems.append((manifest.work_id, "chapters.json", f"{book_key}[{i}].column must be a Bekker column string"))
                continue
            try:
                line = int(line_raw)
            except (TypeError, ValueError):
                problems.append((manifest.work_id, "chapters.json", f"{book_key}[{i}].line must be an integer string"))
                continue
            current = line_key(column, line, scheme)
            if bekker_native and previous is not None and current < previous:
                problems.append((manifest.work_id, "chapters.json", f"chapter refs are out of order at {column}{line}"))
            previous = current
            # Book divisions do not always align with Bekker column boundaries:
            # a book's opening chapter can begin mid-column in a column that is
            # emitted under the PREVIOUS book (e.g. Rhetoric, where Freese marks
            # the I/II and II/III divisions one column before the Greek). When
            # the same column exists under book-1, treat the anchor as a
            # legitimate book-boundary offset rather than a dangling reference.
            missing_segment = (book, column) not in segments
            boundary_offset = missing_segment and (book - 1, column) in segments
            if missing_segment and not boundary_offset:
                problems.append((manifest.work_id, "chapters.json", f"chapter {ref.get('chapter')!r} points to missing segment {book}:{column}"))
            elif not missing_segment and bekker_native and line not in segments[(book, column)]["lines"]:
                problems.append((manifest.work_id, "chapters.json", f"chapter {ref.get('chapter')!r} points to missing Bekker anchor {column}{line}"))
            if bekker_native and not boundary_offset and (book, column, line) not in anchors:
                problems.append((manifest.work_id, "chapters.json", f"chapter {ref.get('chapter')!r} has dangling Bekker anchor {column}{line}"))
            if bekker_native and not boundary_offset:
                _validate_bekker_span(manifest, "chapters.json", ref.get("bekker"), anchors, book, problems)


def _validate_columns(
    manifest: WorkManifest,
    columns: Any,
    segments: dict[tuple[int, str], dict[str, Any]],
    problems: list[Problem],
    scheme=None,
    dk_all_context_columns: set[str] | None = None,
) -> None:
    if columns is None:
        return
    if not isinstance(columns, dict):
        problems.append((manifest.work_id, "columns.json", "root must be an object"))
        return
    # See _validate_books' matching comment: this cross-check only applies to
    # a VERSE dk work (citation.lines: true) -- a lineless (prose) dk work's
    # position-index `n` is assigned to every block regardless of role, so
    # its `lines` set can never legitimately be empty and unmarked_columns
    # has no correspondence to columns.json presence there at all.
    is_dk_verse = scheme is not None and scheme.fragment_scheme and scheme.lines_user_facing
    dk_all_context_columns = dk_all_context_columns or set()
    for column, entries in columns.items():
        if not _is_column(column, scheme):
            problems.append((manifest.work_id, "columns.json", f"column key {column!r} is not a Bekker column"))
            continue
        if not isinstance(entries, list):
            problems.append((manifest.work_id, "columns.json", f"{column} entries must be a list"))
            continue
        previous_book: int | None = None
        for entry in entries:
            if not isinstance(entry, dict):
                problems.append((manifest.work_id, "columns.json", f"{column} entry must be an object"))
                continue
            book = entry.get("book")
            lo = entry.get("lo")
            hi = entry.get("hi")
            if not isinstance(book, int) or not isinstance(lo, int) or not isinstance(hi, int):
                problems.append((manifest.work_id, "columns.json", f"{column} entry book/lo/hi must be integers"))
                continue
            if lo > hi:
                problems.append((manifest.work_id, "columns.json", f"{column} book {book} lo must not exceed hi"))
            if previous_book is not None and book < previous_book:
                problems.append((manifest.work_id, "columns.json", f"{column} book entries are out of order"))
            previous_book = book
            segment = segments.get((book, column))
            if segment is None:
                problems.append((manifest.work_id, "columns.json", f"{column} book {book} has no emitted segment"))
            else:
                lines = segment["lines"]
                if lines and (min(lines) != lo or max(lines) != hi):
                    problems.append((manifest.work_id, "columns.json", f"{column} book {book} range {lo}-{hi} does not match Greek lines"))
    for book, column in segments:
        lines = segments[(book, column)]["lines"]
        if column not in columns:
            if lines:
                # A segment with NO citable line at all (a dk verse fragment
                # whose only content is role='context' -- citation.
                # unmarked_columns, e.g. Parmenides B22-B24) legitimately has
                # no columns.json entry (stage7_emit.column_line_ranges emits
                # none for it either) -- not a missing declaration.
                problems.append((manifest.work_id, "columns.json", f"missing column entry for {book}:{column}"))
            elif is_dk_verse and column not in dk_all_context_columns:
                # Same independent cross-check as _validate_books' fatal
                # above, wired here too (Sol confirm review: neither path
                # may mask the defect on its own) -- an empty line set with
                # no columns.json entry is only legitimate when the manifest
                # itself declares this column all-context.
                problems.append((
                    manifest.work_id, "columns.json",
                    f"{book}:{column} has zero citable lines and no "
                    f"columns.json entry, but is not declared in "
                    f"citation.unmarked_columns -- an emission-stage bug "
                    f"that lost every citable line of this column would "
                    f"look identical to a legitimate all-context column",
                ))
        elif is_dk_verse and column in dk_all_context_columns and lines:
            problems.append((
                manifest.work_id, "columns.json",
                f"column {column} is declared in citation.unmarked_columns "
                f"(expected zero citable lines) but carries a columns.json "
                f"entry with citable line(s) -- a stale unmarked_columns "
                f"declaration must be removed, not left to silently no-op",
            ))


def _validate_analyses(
    manifest: WorkManifest,
    data_dir: Path,
    analyses: Any,
    token_keys: set[str],
    problems: list[Problem],
) -> None:
    if analyses is None:
        return
    if not isinstance(analyses, dict):
        problems.append((manifest.work_id, "analyses.json", "root must be an object"))
        return
    # A referenced Greek token having no entry in analyses is EXPECTED, not a
    # defect: Morpheus fails to parse some rare/inflected forms and the
    # spurious-parse filter deliberately drops others, so the reader simply
    # shows no word popup for them. Flagging every such token produced ~1300
    # false positives against the live corpus, so token-key *presence* is not
    # validated. (token_keys is still passed in for possible future coverage
    # reporting.) The structural validation of the entries that DO exist, and
    # LSJ-key resolution, remain below.
    lsj_keys: set[str] = set()
    for key, entries in analyses.items():
        if not isinstance(entries, list):
            problems.append((manifest.work_id, "analyses.json", f"{key}: analyses value must be a list"))
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                problems.append((manifest.work_id, "analyses.json", f"{key}: analysis entry must be an object"))
                continue
            for required in ["lemma", "gloss", "parse"]:
                if not isinstance(entry.get(required), str):
                    problems.append((manifest.work_id, "analyses.json", f"{key}: {required} must be a string"))
            lsj = entry.get("lsj")
            if not isinstance(lsj, list):
                problems.append((manifest.work_id, "analyses.json", f"{key}: lsj must be a list"))
                continue
            for lsj_key in lsj:
                if not isinstance(lsj_key, str) or not lsj_key:
                    problems.append((manifest.work_id, "analyses.json", f"{key}: lsj key must be a non-empty string"))
                else:
                    lsj_keys.add(lsj_key)
    _validate_lsj_keys(manifest, data_dir, lsj_keys, problems)


def _validate_lsj_keys(
    manifest: WorkManifest,
    data_dir: Path,
    lsj_keys: set[str],
    problems: list[Problem],
) -> None:
    # Dictionary shard directory is per-language: 'lsj' (Greek/LSJ, default)
    # or 'ls' (Latin/Lewis & Short, Wave 2 Batch 1b) — see
    # stage5_lsj.SHARD_DIR, which stage5/stage7 also key off of. The two
    # dictionaries are separate key spaces, so a Latin work's keys must
    # never be looked up in the Greek 'lsj' shards or vice versa.
    language = manifest.data.get("work", {}).get("language", "grc")
    # FAIL-OPEN fix (Wave 2 Batch 1b review, item 4): an unrecognized
    # language used to fall back to "lsj" (Greek's shard dir) via
    # `.get(language, "lsj")` — a manifest with a typo'd/unknown
    # work.language would have its dictionary keys silently checked against
    # the WRONG language's shards instead of failing preflight. Reject
    # instead of guessing.
    if language not in SHARD_DIR:
        problems.append((
            manifest.work_id, "work.language",
            f"unrecognized language {language!r} — not in {sorted(SHARD_DIR)} "
            f"(stage5_lsj.SHARD_DIR); cannot determine which dictionary "
            f"shard dir its keys belong to",
        ))
        return
    shard_dir_name = SHARD_DIR[language]
    shards: dict[str, dict[str, Any]] = {}
    for key in sorted(lsj_keys):
        shard_name = _lsj_shard(key)
        shard_path = data_dir / shard_dir_name / f"{shard_name}.json"
        if not shard_path.exists():
            problems.append((manifest.work_id, f"{shard_dir_name}/{shard_name}.json", f"dictionary key {key!r} references missing shard"))
            continue
        if shard_name not in shards:
            try:
                shard = json.loads(shard_path.read_text(encoding="utf-8"))
            except Exception as exc:
                problems.append((manifest.work_id, f"{shard_dir_name}/{shard_name}.json", f"invalid JSON: {exc}"))
                continue
            if not isinstance(shard, dict):
                problems.append((manifest.work_id, f"{shard_dir_name}/{shard_name}.json", "shard root must be an object"))
                continue
            shards[shard_name] = shard
        if key not in shards.get(shard_name, {}):
            problems.append((manifest.work_id, f"{shard_dir_name}/{shard_name}.json", f"dictionary key {key!r} is not present in shard"))


def _private_flag_slots(data: dict[str, Any]) -> set[str]:
    """Slots whose id is marked private: true (Astra lane B, F3)."""
    ids = private_translation_ids(data)
    omitted: set[str] = set()
    english = data.get("english") if isinstance(data.get("english"), dict) else {}
    for slot in ("secondary", "third"):
        entry = english.get(slot)
        if isinstance(entry, dict) and entry.get("id") in ids:
            omitted.add(slot)
    for item in english.get("overlays") or []:
        if isinstance(item, dict) and item.get("id") in ids:
            omitted.add(f"overlay:{item['id']}")
    return omitted


def _validate_public_gating(
    manifest: WorkManifest,
    loaded: dict[str, Any],
    problems: list[Problem],
    public_build: bool = False,
) -> None:
    omitted: set[str] = set()
    if manifest.public_path is not None and manifest.private_data is not None:
        omitted |= _omitted_translation_slots(manifest.private_data, manifest.data)
    if public_build:
        omitted |= _private_flag_slots(manifest.data)
    if not omitted:
        return
    for file_name, doc in loaded.items():
        if not file_name.startswith("book-") or not isinstance(doc, dict):
            continue
        for segment in doc.get("segments", []) or []:
            if not isinstance(segment, dict):
                continue
            for slot in omitted:
                if slot == "secondary" and "ross" in segment:
                    problems.append((manifest.work_id, file_name, "private secondary translation appears in public data"))
                elif slot == "third" and "third" in segment:
                    problems.append((manifest.work_id, file_name, "private third translation appears in public data"))
                elif slot.startswith("overlay:"):
                    overlay_id = slot.split(":", 1)[1]
                    overlays = segment.get("overlays")
                    if isinstance(overlays, dict) and overlay_id in overlays:
                        problems.append((manifest.work_id, file_name, f"private overlay {overlay_id!r} appears in public data"))


def load_public_domain_allowlist(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load the positive translation allowlist, or fail closed."""
    if path is None:
        override = os.environ.get("DRAMA_PUBLIC_DOMAIN_ALLOWLIST")
        path = Path(override) if override else PUBLIC_DOMAIN_ALLOWLIST_PATH
    if not path.is_file():
        raise ValueError(f"public-domain allowlist missing: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("public-domain allowlist root must be an object")
    entries = raw.get("translations")
    if not isinstance(entries, list) or not entries:
        raise ValueError("public-domain allowlist translations must be a non-empty list")

    allowed: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            raise ValueError(
                f"public-domain allowlist translations[{index}] must be an object"
            )
        translation_id = item.get("id")
        if not isinstance(translation_id, str) or not translation_id:
            raise ValueError(
                f"public-domain allowlist translations[{index}].id must be a non-empty string"
            )
        if translation_id in allowed:
            raise ValueError(
                f"public-domain allowlist has duplicate id {translation_id!r}"
            )
        translator = item.get("translator")
        year = item.get("year")
        note = item.get("note")
        if not isinstance(translator, str) or not translator:
            raise ValueError(
                f"public-domain allowlist {translation_id!r}: translator must be a non-empty string"
            )
        if not isinstance(year, int):
            raise ValueError(
                f"public-domain allowlist {translation_id!r}: year must be an integer"
            )
        if not isinstance(note, str) or not note:
            raise ValueError(
                f"public-domain allowlist {translation_id!r}: note must be a non-empty string"
            )
        sources = item.get("sources")
        if sources is None:
            sources = []
        if not isinstance(sources, list) or any(
            not isinstance(pattern, str) or not pattern for pattern in sources
        ):
            raise ValueError(
                f"public-domain allowlist {translation_id!r}: sources must be a "
                "list of non-empty path globs"
            )
        item = dict(item)
        item["sources"] = sources
        allowed[translation_id] = item
    return allowed


def load_public_domain_denylist(
    path: Path | None = None,
) -> list[tuple[re.Pattern[str], str]]:
    """Load fail-closed denial patterns (O'Neill, etc.) from the allowlist file."""
    if path is None:
        override = os.environ.get("DRAMA_PUBLIC_DOMAIN_ALLOWLIST")
        path = Path(override) if override else PUBLIC_DOMAIN_ALLOWLIST_PATH
    if not path.is_file():
        raise ValueError(f"public-domain allowlist missing: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("public-domain allowlist root must be an object")
    denied = raw.get("denied")
    if denied is None:
        return []
    if not isinstance(denied, list):
        raise ValueError("public-domain allowlist denied must be a list")
    compiled: list[tuple[re.Pattern[str], str]] = []
    for index, item in enumerate(denied):
        if not isinstance(item, dict):
            raise ValueError(
                f"public-domain allowlist denied[{index}] must be an object"
            )
        pattern = item.get("pattern")
        note = item.get("note")
        if not isinstance(pattern, str) or not pattern:
            raise ValueError(
                f"public-domain allowlist denied[{index}].pattern must be a "
                "non-empty string"
            )
        if not isinstance(note, str) or not note:
            raise ValueError(
                f"public-domain allowlist denied[{index}].note must be a "
                "non-empty string"
            )
        compiled.append((re.compile(pattern, re.IGNORECASE), note))
    return compiled


def manifest_translation_ids(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return every declared ``english`` slot and its translation id."""
    return [(slot, entry["id"]) for slot, entry in manifest_emitted_translations(data)]


def manifest_emitted_translations(data: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Every translation stage7 can emit, with the fields the denylist scans."""
    english = data.get("english") if isinstance(data.get("english"), dict) else {}
    found: list[tuple[str, dict[str, Any]]] = []
    for slot in ("primary", "secondary", "third"):
        entry = english.get(slot)
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"]:
            found.append((slot, entry))
    for entry in english.get("overlays") or []:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"]:
            found.append((f"overlay:{entry['id']}", entry))
    summary = english.get("summary_overlay")
    if isinstance(summary, dict) and isinstance(summary.get("id"), str) and summary["id"]:
        found.append(("summary_overlay", summary))
    for entry in english.get("column_sources") or []:
        if not isinstance(entry, dict) or not entry.get("file"):
            continue
        source_id = Path(str(entry["file"])).name.split(".")[0]
        credit = entry.get("credit") if isinstance(entry.get("credit"), dict) else {}
        synthesized = {
            "id": source_id,
            "name": credit.get("translator") or source_id,
            "translator": credit.get("translator"),
            "source": credit.get("source") or entry.get("file"),
        }
        found.append((f"column:{entry.get('column') or source_id}", synthesized))
    return found


_PD_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})
_COMPARISON_ONLY_IDS = frozenset({"rogers", "hickie"})


def _norm_pd_text(value: str) -> str:
    """Fold curly apostrophes and case for PD name/source scans (Astra lane C, F2)."""
    return value.translate(_PD_APOSTROPHES).casefold()


def _translator_matches(entry: dict[str, Any], allowed_translator: str) -> bool:
    needle = _norm_pd_text(allowed_translator)
    if not needle:
        return False
    for field in (entry.get("name"), entry.get("translator")):
        if isinstance(field, str) and needle in _norm_pd_text(field):
            return True
    return False


def _source_matches(source: str, patterns: list[str]) -> bool:
    path = source.replace("\\", "/")
    return any(fnmatch.fnmatch(path, pattern.replace("\\", "/")) for pattern in patterns)


def _is_comparison_slot(slot: str) -> bool:
    return slot in ("secondary", "third") or slot.startswith("overlay:")


def _validate_public_domain_allowlist(
    manifest: WorkManifest,
    problems: list[Problem],
    *,
    allowlist_path: Path | None = None,
) -> None:
    """Require a positive allowlist entry for every English translation."""
    label = (allowlist_path or PUBLIC_DOMAIN_ALLOWLIST_PATH).name
    try:
        allowed = load_public_domain_allowlist(allowlist_path)
        denied = load_public_domain_denylist(allowlist_path)
    except Exception as exc:
        problems.append((manifest.work_id, label, str(exc)))
        return
    work = manifest.data.get("work") if isinstance(manifest.data.get("work"), dict) else {}
    author = str(work.get("author") or "")
    for slot, entry in manifest_emitted_translations(manifest.data):
        translation_id = entry.get("id")
        if translation_id not in allowed:
            problems.append(
                (
                    manifest.work_id,
                    manifest.path.name,
                    f"translation id {translation_id!r} ({slot}) is not on the "
                    "public-domain allowlist",
                )
            )
        allowed_entry = allowed.get(translation_id) if isinstance(translation_id, str) else None
        if isinstance(allowed_entry, dict):
            allowed_translator = allowed_entry.get("translator")
            if not isinstance(allowed_translator, str) or not _translator_matches(
                entry, allowed_translator
            ):
                problems.append(
                    (
                        manifest.work_id,
                        manifest.path.name,
                        f"translation {translation_id!r} ({slot}) name/translator "
                        f"does not match allowlist translator {allowed_translator!r}",
                    )
                )
            source = entry.get("source") or entry.get("file") or entry.get("dir")
            patterns = allowed_entry.get("sources") or []
            if isinstance(source, str) and source:
                if not patterns or not _source_matches(source, patterns):
                    problems.append(
                        (
                            manifest.work_id,
                            manifest.path.name,
                            f"translation {translation_id!r} ({slot}) source {source!r} "
                            "is not an allowlisted source for that id",
                        )
                    )
            elif patterns:
                # No source to bind is a failure, not a skip (Sonnet review of C1).
                problems.append(
                    (
                        manifest.work_id,
                        manifest.path.name,
                        f"translation {translation_id!r} ({slot}) has no source/file "
                        "to bind against the allowlist",
                    )
                )
        if translation_id in _COMPARISON_ONLY_IDS and not _is_comparison_slot(slot):
            problems.append(
                (
                    manifest.work_id,
                    manifest.path.name,
                    f"translation {translation_id!r} ({slot}) is comparison-only "
                    "(Rogers/Hickie may not occupy english.primary)",
                )
            )
        if (
            author.casefold() == "aristophanes"
            and slot == "primary"
            and translation_id != "athenian-society"
        ):
            problems.append(
                (
                    manifest.work_id,
                    manifest.path.name,
                    "Aristophanes english.primary must be the Athenian Society "
                    f"translation, not {translation_id!r}",
                )
            )
        fields = [
            entry.get("id"),
            entry.get("name"),
            entry.get("translator"),
            entry.get("source"),
            entry.get("file"),
        ]
        if isinstance(allowed_entry, dict):
            fields.extend(
                [
                    allowed_entry.get("id"),
                    allowed_entry.get("translator"),
                ]
            )
        scanned = [
            (value, _norm_pd_text(value))
            for value in fields
            if isinstance(value, str) and value
        ]
        for pattern, note in denied:
            hit = next(
                (original for original, folded in scanned if pattern.search(folded)),
                None,
            )
            if hit is not None:
                problems.append(
                    (
                        manifest.work_id,
                        manifest.path.name,
                        f"translation {translation_id!r} ({slot}) is denied "
                        f"({note}); matched {hit!r}",
                    )
                )
                break


def _omitted_translation_slots(private: dict[str, Any], public: dict[str, Any]) -> set[str]:
    private_english = private.get("english") if isinstance(private.get("english"), dict) else {}
    public_english = public.get("english") if isinstance(public.get("english"), dict) else {}
    omitted: set[str] = set()
    for slot in ["secondary", "third"]:
        if slot in private_english and slot not in public_english:
            omitted.add(slot)
    private_overlays = {
        item.get("id")
        for item in private_english.get("overlays", []) or []
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    public_overlays = {
        item.get("id")
        for item in public_english.get("overlays", []) or []
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for overlay_id in private_overlays - public_overlays:
        omitted.add(f"overlay:{overlay_id}")
    return omitted


def _validate_bekker_span(
    manifest: WorkManifest,
    file_name: str,
    span: Any,
    anchors: set[tuple[int, str, int]],
    book: int,
    problems: list[Problem],
) -> None:
    if not isinstance(span, str) or not span:
        problems.append((manifest.work_id, file_name, "chapter bekker span must be a non-empty string"))
        return
    parts = span.split("–")
    if len(parts) == 1:
        refs = [_span_ref(parts[0], None)]
    elif len(parts) == 2:
        refs = [_span_ref(parts[0], None), _span_ref(parts[1], parts[0])]
    else:
        problems.append((manifest.work_id, file_name, f"invalid Bekker span {span!r}"))
        return
    parsed: list[tuple[str, int]] = []
    for ref in refs:
        if ref is None:
            problems.append((manifest.work_id, file_name, f"invalid Bekker span {span!r}"))
            return
        column, line = ref
        parsed.append(ref)
        if (book, column, line) not in anchors:
            problems.append((manifest.work_id, file_name, f"chapter span {span!r} references missing Bekker anchor {column}{line}"))
    if len(parsed) == 2 and line_key(*parsed[0]) > line_key(*parsed[1]):
        problems.append((manifest.work_id, file_name, f"chapter span {span!r} is out of order"))


def _span_ref(raw: str, first_part: str | None) -> tuple[str, int] | None:
    raw = raw.strip()
    if _is_ref(raw):
        page, side, line = ref_key(raw)
        return f"{page}{side}", line
    if first_part and raw.isdigit() and _is_ref(first_part.strip()):
        page, side, _line = ref_key(first_part.strip())
        return f"{page}{side}", int(raw)
    return None


def _require_object(manifest: WorkManifest, data: dict[str, Any], key: str, problems: list[Problem]) -> None:
    if not isinstance(data.get(key), dict):
        problems.append((manifest.work_id, manifest.path.name, f"{key} must be an object"))


def _require_list(manifest: WorkManifest, data: dict[str, Any], key: str, problems: list[Problem]) -> None:
    if not isinstance(data.get(key), list):
        problems.append((manifest.work_id, manifest.path.name, f"{key} must be a list"))


def _is_column(value: Any, scheme=None) -> bool:
    if not isinstance(value, str):
        return False
    try:
        column_key(value, scheme)
    except ValueError:
        return False
    return True


def _is_ref(value: Any, scheme=None) -> bool:
    if not isinstance(value, str):
        return False
    try:
        ref_key(value, scheme)
    except ValueError:
        return False
    return True


def _is_section_token(value: Any) -> bool:
    """A section-scheme book boundary is a page+section token, given either as a
    bare column ('357a') or a full ref ('2a1') — the book table may use either
    interchangeably (only the page+letter prefix decides book membership)."""
    return _is_column(value) or _is_ref(value)


def _lsj_shard(key: str) -> str:
    for ch in key:
        if ch == "*":
            continue
        if "a" <= ch <= "z":
            return ch
    return "_"


def _ocr_source_problem(path: str, sources_dir: Path | None = None, required: bool = False) -> str | None:
    """An OCR'd edition's TEI lives under sources/ocr/, and its own
    directory's SHA256SUMS names it. The file itself may be absent in local
    dev (whether OCR'd TEI is committed is the owner's call); `required`, a
    build of editions, makes that a problem. Present, it must match the
    listed hash."""
    if not path.startswith("ocr/") or ".." in Path(path).parts:
        return "OCR source must lie under sources/ocr/"
    src = (sources_dir or SOURCES_DIR) / path
    if not src.is_file():
        return f"OCR source {path} is absent" if required else None
    sums = src.parent / "SHA256SUMS"
    rows = sums.read_text(encoding="utf-8").splitlines() if sums.is_file() else []
    listed = next((row.split()[0] for row in rows if row.split() and row.split()[-1] == src.name), None)
    if listed is None:
        return f"OCR source {path} is not listed in its SHA256SUMS"
    if hashlib.sha256(src.read_bytes()).hexdigest() != listed:
        return f"OCR source {path} does not match its SHA256SUMS"
    return None


def _validate_greek_editions(manifest: WorkManifest, data_dir: Path, problems: list[Problem],
                             editions_built: bool = False, public: bool = False) -> None:
    editions = manifest.data.get("greek_editions") or []
    if not isinstance(editions, list):
        problems.append((manifest.work_id, manifest.path.name, "greek_editions must be a list"))
        return
    try:
        raw = yaml.safe_load(PUBLIC_DOMAIN_ALLOWLIST_PATH.read_text(encoding="utf-8"))
        allowed: dict[str, list[dict]] = {}
        for entry in raw.get("greek_editions") or []:
            allowed.setdefault(entry["id"], []).append(entry)
    except (OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        allowed = {}
        if editions:
            problems.append((manifest.work_id, manifest.path.name, f"Greek edition allowlist unreadable: {exc}"))
    english_ids = {tid for _, tid in manifest_translation_ids(manifest.data)}
    seen_ids: set[str] = set()
    seen_pairs: set[str] = set()
    for edition in editions:
        if not isinstance(edition, dict):
            problems.append((manifest.work_id, manifest.path.name, "Greek edition entry must be an object"))
            continue
        eid = edition.get("id")
        if not isinstance(eid, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", eid) or eid == "tlg" or eid in seen_ids:
            problems.append((manifest.work_id, manifest.path.name, f"invalid or duplicate Greek edition id {eid!r}"))
            continue
        seen_ids.add(eid)
        source = edition.get("source") or {}
        if not isinstance(source, dict):
            problems.append((manifest.work_id, manifest.path.name, f"Greek edition {eid!r} source must be an object"))
            continue
        licence = edition.get("licence") or {}
        if not isinstance(licence, dict):
            problems.append((manifest.work_id, manifest.path.name, f"Greek edition {eid!r} licence must be an object"))
            continue
        # One entry must own this id and source; it must then match the manifest's
        # editor, year, and status whole. Two entries naming one source are ambiguous.
        owners = [entry for entry in allowed.get(eid, [])
                  if _source_matches(source.get("path") or "", entry.get("sources") or [])]
        if not (
            len(owners) == 1
            and edition.get("editor") == owners[0].get("editor")
            and edition.get("year") == owners[0].get("year")
            and licence.get("text") == owners[0].get("status")
        ):
            problems.append((manifest.work_id, manifest.path.name, f"Greek edition {eid!r} is absent from or differs from the allowlist"))
        if source.get("kind") not in {"perseus-tei", "ocr-tei"} or not source.get("expect"):
            problems.append((manifest.work_id, manifest.path.name, f"Greek edition {eid!r} needs a TEI source and header gate"))
        if source.get("kind") == "ocr-tei":
            problem = _ocr_source_problem(source.get("path") or "", required=editions_built)
            if problem:
                problems.append((manifest.work_id, manifest.path.name, f"Greek edition {eid!r} {problem}"))
        if not isinstance(edition.get("citation"), dict) or not isinstance((edition.get("citation") or {}).get("fingerprint"), dict):
            problems.append((manifest.work_id, manifest.path.name, f"Greek edition {eid!r} needs citation fingerprint"))
        pairs = edition.get("pairs") or []
        if not isinstance(pairs, list):
            problems.append((manifest.work_id, manifest.path.name, f"Greek edition {eid!r} pairs must be a list"))
            continue
        alignment = edition.get("alignment") or {}
        if not isinstance(alignment, dict) or set(alignment) - set(pairs):
            problems.append((manifest.work_id, manifest.path.name, f"Greek edition {eid!r} alignment names an unpaired translation"))
        for pair in pairs:
            if pair not in english_ids or pair in seen_pairs:
                problems.append((manifest.work_id, manifest.path.name, f"Greek edition {eid!r} has undeclared or duplicate pair {pair!r}"))
            seen_pairs.add(pair)
    ed_dir = data_dir / manifest.work_id / "ed"
    if editions_built and public:
        for eid in sorted(seen_ids):
            if not (ed_dir / eid).is_dir():
                problems.append((manifest.work_id, manifest.path.name, f"Greek edition {eid!r} not built: {ed_dir / eid} is missing"))
    if ed_dir.is_dir():
        for child in ed_dir.iterdir():
            if child.is_dir() and child.name not in seen_ids:
                problems.append((manifest.work_id, manifest.path.name, f"undeclared emitted Greek edition {child.name!r}"))
            if child.is_dir() and child.name in seen_ids:
                concordance_path = child / "concordance.json"
                if not concordance_path.is_file():
                    problems.append((manifest.work_id, str(concordance_path), "missing edition concordance"))
                    continue
                try:
                    mapping = json.loads(concordance_path.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    problems.append((manifest.work_id, str(concordance_path), f"invalid edition concordance: {exc}"))
                    continue
                if not isinstance(mapping, dict) or any(
                    not isinstance(key, str) or not re.fullmatch(r"[0-9]+[a-z]?(?:\.[0-9]+)?", key)
                    or not isinstance(value, str) or not re.fullmatch(r"[0-9]+[a-z]?(?:\.[0-9]+)?(?:-[0-9]+[a-z]?(?:\.[0-9]+)?)?", value)
                    for key, value in mapping.items()
                ):
                    problems.append((manifest.work_id, str(concordance_path), "concordance must map printed refs to printed refs"))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
