"""Manifest loading and path resolution.

Repo layout assumed:
    plato-reader/            <- repo root
      manifests/ne.yaml
      sources/               <- committable sources (Perseus TEI)
      build/                 <- pipeline output, gitignored
      pipeline/              <- this package
"""

from __future__ import annotations

import copy
import os
from pathlib import Path

import yaml

from . import scheme as scheme_mod
from .refs import line_key

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_DIR = Path(os.environ.get("DRAMA_BUILD_DIR", REPO_ROOT / "build"))
SOURCES_DIR = REPO_ROOT / "sources"


def private_translation_ids(data: dict) -> set[str]:
    """Ids marked private: true on an english slot or registry.translations.

    Astra lane B, F3: the six hidden comparison slots live on
    registry.translations (and sometimes also on the english overlay).
    """
    ids: set[str] = set()
    registry = data.get("registry") if isinstance(data.get("registry"), dict) else {}
    for item in registry.get("translations") or []:
        if isinstance(item, dict) and item.get("private") and isinstance(item.get("id"), str):
            ids.add(item["id"])
    english = data.get("english") if isinstance(data.get("english"), dict) else {}
    for slot in ("primary", "secondary", "third"):
        entry = english.get(slot)
        if isinstance(entry, dict) and entry.get("private") and isinstance(entry.get("id"), str):
            ids.add(entry["id"])
    for item in english.get("overlays") or []:
        if isinstance(item, dict) and item.get("private") and isinstance(item.get("id"), str):
            ids.add(item["id"])
    return ids


def exclude_private_slots(data: dict) -> tuple[dict, list[tuple[str, str]]]:
    """Copy `data` without private comparison slots (public build only).

    Astra lane B, F3.
    """
    out = copy.deepcopy(data)
    private_ids = private_translation_ids(out)
    excluded: list[tuple[str, str]] = []
    english = out.get("english")
    if isinstance(english, dict):
        for slot in ("secondary", "third"):
            entry = english.get(slot)
            if isinstance(entry, dict) and (
                entry.get("private") or entry.get("id") in private_ids
            ):
                excluded.append((slot, entry.get("id") or ""))
                del english[slot]
        overlays = english.get("overlays")
        if isinstance(overlays, list):
            kept = []
            for item in overlays:
                if isinstance(item, dict) and (
                    item.get("private") or item.get("id") in private_ids
                ):
                    excluded.append(("overlay", item.get("id") or ""))
                else:
                    kept.append(item)
            english["overlays"] = kept
    registry = out.get("registry")
    if isinstance(registry, dict) and isinstance(registry.get("translations"), list):
        registry["translations"] = [
            item
            for item in registry["translations"]
            if not (
                isinstance(item, dict)
                and (item.get("private") or item.get("id") in private_ids)
            )
        ]
    return out, excluded


class Manifest:
    def __init__(self, data: dict, path: Path, public: bool = False):
        self.data = data
        self.path = path
        self.public = public
        self.excluded_private_slots: list[tuple[str, str]] = []

    @classmethod
    def load(cls, path: Path | None = None) -> "Manifest":
        path = path or REPO_ROOT / "manifests" / "EN.yaml"
        with open(path, encoding="utf-8") as f:
            return cls(yaml.safe_load(f), path)

    @classmethod
    def for_work(cls, work: str, public: bool = False) -> "Manifest":
        """Load the manifest for a work slug, e.g. 'EN' or 'DA'.

        Public builds use manifests/<work>-public.yaml when it exists, falling
        back to the normal manifest for works with no private translations.
        Private comparison slots are then stripped (Astra lane B, F3).
        """
        manifests_dir = REPO_ROOT / "manifests"
        if public:
            public_path = manifests_dir / f"{work}-public.yaml"
            loaded = cls.load(public_path if public_path.exists() else manifests_dir / f"{work}.yaml")
            data, excluded = exclude_private_slots(loaded.data)
            loaded.data = data
            loaded.public = True
            loaded.excluded_private_slots = excluded
            return loaded
        return cls.load(manifests_dir / f"{work}.yaml")

    def for_edition(self, edition_id: str) -> "Manifest":
        """Make a one-edition view without changing the reference manifest."""
        matches = [e for e in self.data.get("greek_editions") or [] if e.get("id") == edition_id]
        if len(matches) != 1:
            raise ValueError(f"{self.work_id}: unknown Greek edition {edition_id!r}")
        edition = matches[0]
        data = copy.deepcopy(self.data)
        data["work"]["greek_edition"] = edition["label"]["full"]
        data["work"]["edition_id"] = edition_id
        data["work"]["greek_source"] = copy.deepcopy(edition["source"])
        data["citation"] = {"scheme": "play-line", **copy.deepcopy(edition["citation"])}
        old_speakers = data.get("speakers") or {}
        data["speakers"] = {k: v for k, v in old_speakers.items() if k.startswith("english")}
        data["speakers"].update(copy.deepcopy(edition.get("speakers") or {}))
        pairs = set(edition.get("pairs") or [])
        old_english = data.get("english") or {}
        english = {"gaps": copy.deepcopy(edition.get("gaps") or [])}
        for slot in ("primary", "secondary", "third"):
            entry = old_english.get(slot)
            if entry and entry.get("id") in pairs:
                entry = copy.deepcopy(entry)
                for key in ("line_fixes", "pins", "cuts", "covered", "tick_fixes"):
                    entry.pop(key, None)
                entry.update(copy.deepcopy((edition.get("alignment") or {}).get(entry["id"]) or {}))
                english[slot] = entry
        english["overlays"] = []
        for entry in old_english.get("overlays") or []:
            if entry.get("id") in pairs:
                entry = copy.deepcopy(entry)
                for key in ("line_fixes", "pins", "cuts", "covered", "tick_fixes"):
                    entry.pop(key, None)
                entry.update(copy.deepcopy((edition.get("alignment") or {}).get(entry["id"]) or {}))
                english["overlays"].append(entry)
        data["english"] = english
        if isinstance(data.get("registry"), dict):
            data["registry"]["translations"] = [t for t in data["registry"].get("translations") or [] if t.get("id") in pairs]
        view = Manifest(data, self.path, self.public)
        view.edition = edition
        # alignment.<pair>.anchor_map names another declared edition whose
        # Greek count the pair's English anchors are printed in.
        view.anchor_editions = {}
        for entry in [*(english.get(slot) for slot in ("primary", "secondary", "third")), *english["overlays"]]:
            source_id = (entry or {}).get("anchor_map")
            if source_id is None:
                continue
            if source_id == edition_id or source_id not in {e.get("id") for e in self.data.get("greek_editions") or []}:
                raise ValueError(f"{self.work_id}: edition {edition_id!r} anchor_map {source_id!r} must name another declared Greek edition")
            view.anchor_editions[source_id] = self.for_edition(source_id)
        return view

    @property
    def work_id(self) -> str:
        return self.data["work"]["id"]

    @property
    def author(self) -> str:
        """Author slug (e.g. 'aristotle', 'plato'), required by every manifest."""
        return self.data["work"]["author"]

    @property
    def language(self) -> str:
        """Work's source language: 'grc' (default) or 'lat'. Only 'grc' is
        actually wired up end-to-end today; 'lat' is accepted here so
        stage4/stage5 can parameterize on it, but Latin support itself is
        Wave 2 work (see stage4_morphology / stage5_lsj)."""
        return self.data["work"].get("language", "grc")

    @property
    def lexicon(self) -> bool:
        """Whether this work's tokens are keyed against a lexicon at all
        (Wave 2 §4.2's no-lexicon-first posture: a work may legitimately
        ship with tokens that carry `t` but no `k` — declared
        `work.lexicon: false`, first used by Cicero's De Officiis, Batch
        1a). Defaults to True: every pre-Wave-2 manifest has no `lexicon`
        key at all and must keep keying tokens exactly as before."""
        return bool(self.data["work"].get("lexicon", True))

    @property
    def first_column(self) -> str:
        span = self.data.get("bekker_range")
        if span:
            return span["first_column"]
        return self._boundary_column(self.books[0]["start"])

    @property
    def last_column(self) -> str:
        span = self.data.get("bekker_range")
        if span:
            return span["last_column"]
        return self._boundary_column(self.books[-1]["end"])

    def _boundary_column(self, token: str) -> str:
        """The bare column of a book-boundary token. A letter scheme strips the
        trailing editorial line ('357a1' -> '357a', '1094a2' -> '1094a'); a
        numeric-section scheme's dotted token ('1.1') has no line component and
        already IS the whole column, so stripping trailing digits would corrupt
        it to '1.' — return it unchanged. A flat-numeric scheme's bare-integer
        token ('53') is ALL digits, so the strip would corrupt it to '' —
        likewise return it unchanged. A dk column ('B30', 'B84a') ends in a
        DIGIT (or a letter suffix) that is part of the token itself, never an
        editorial line — stripping trailing digits would corrupt "B30" to "B"
        — likewise return it unchanged. A verse-line dotted token ('1.101',
        '3.47a') is the same shape as a dk column for this purpose (its
        lineref is the whole column, not an editorial line to strip)."""
        sch = scheme_mod.for_manifest(self)
        if (
            sch.numeric_section or sch.flat_numeric or sch.fragment_scheme
            or sch.verse_line_scheme or sch.play_line_scheme
        ):
            return token
        return token.rstrip("0123456789")

    @property
    def books(self) -> list[dict]:
        return self.data["books"]

    def tlg_dir(self) -> Path:
        src = self.data["sources"]
        env = os.environ.get(src["tlg_dir_env"])
        if env:
            return Path(env)
        return (REPO_ROOT / src["tlg_dir_default"]).resolve()

    def phi_dir(self) -> Path:
        """PHI (Latin) corpus location, mirroring `tlg_dir()` exactly: an
        env var override (`sources.phi_dir_env`, e.g. "PHI_DIR") wins, else
        a manifest-declared default path relative to REPO_ROOT
        (`sources.phi_dir_default`) — see docs/tlg-phi-export.md's Wave 2
        PHI section (EMPIRICAL UPDATE 2026-07-17: the `phi_dir`-keyed
        Diogenes prefs line is what's actually load-bearing for the export
        itself, written by stage1_latin.run_export; this accessor is what
        supplies that value from the manifest/env, exactly as `tlg_dir()`
        supplies the TLG line)."""
        src = self.data["sources"]
        env = os.environ.get(src["phi_dir_env"])
        if env:
            return Path(env)
        return (REPO_ROOT / src["phi_dir_default"]).resolve()

    def diogenes_server(self) -> Path:
        return Path(self.data["sources"]["diogenes_server"])

    def diogenes_data(self) -> Path:
        return Path(self.data["sources"]["diogenes_data"])

    def perseus_eng(self) -> Path:
        # Vendored Perseus eng TEI for this work: an explicit work.english_source
        # name, else derived from the TLG work number. Falls back to the legacy
        # sources.perseus_eng path (NE-only download location).
        name = self.data["work"].get("english_source")
        if not name:
            name = f"tlg0086.tlg{self.data['work']['tlg_work']}.perseus-eng2.xml"
        vendored = SOURCES_DIR / name
        if vendored.exists():
            return vendored
        legacy = (self.data.get("sources") or {}).get("perseus_eng")
        return Path(legacy) if legacy else vendored

    def book_for_line(self, column: str, line: int) -> int | None:
        """Book number containing Bekker position (column, line), or None
        if the position falls in an inter-book numbering gap."""
        pos = line_key(column, line)
        for b in self.books:
            m_start = _ref_to_key(b["start"])
            m_end = _ref_to_key(b["end"])
            if m_start <= pos <= m_end:
                return b["n"]
        return None

    def lettered_fragments_for_book(self, book_n: str | int) -> dict | None:
        """Manifest-declared lettered-fragment remap table for one book
        (citation.lettered_fragments — see manifests/lives.yaml and
        stage1_greek._resolve_lettered_fragments), or None if this book has
        no declaration. A list entry looks like:
            {book: 10, found: ["120a", "121b", "120b", "121a"],
             merge: {120: ["120a", "121b", "120b"], 121: ["121a"]}}

        Raises loudly if more than one entry declares the same book — a
        silent first-match would hide a manifest-authoring duplicate behind
        whichever entry happens to come first (Sol round-2 review, Hole 3).
        """
        matches = [
            entry
            for entry in (self.data.get("citation") or {}).get("lettered_fragments", [])
            if str(entry["book"]) == str(book_n)
        ]
        if len(matches) > 1:
            raise ValueError(
                f"{self.work_id}: {len(matches)} duplicate "
                f"citation.lettered_fragments declarations for book "
                f"{book_n!r} — each book may be declared at most once"
            )
        return matches[0] if matches else None

    def lettered_fragment_books(self) -> list[str]:
        """Every book_n declared in citation.lettered_fragments (as a
        string), in manifest order. Used by stage1_greek to check for stale
        declarations — a declared book whose encountered lettered-@n set
        turns out empty once the document is scanned."""
        return [
            str(entry["book"])
            for entry in (self.data.get("citation") or {}).get("lettered_fragments", [])
        ]

    def book_for_column(self, column: str) -> int | None:
        """Book number whose declared range contains a column token, compared
        at (page, letter) granularity, or None if it falls outside every book.

        For section schemes (stephanus): book boundaries fall page-initial on a
        section letter, so a whole section (page+letter column) belongs to one
        book and the editorial per-section line numbers are irrelevant to the
        assignment. Book start/end may be given as bare columns ('357a') or full
        refs ('357a1'); only the (page, letter) prefix is compared."""
        from .refs import column_prefix_key

        sch = scheme_mod.for_manifest(self)
        pos = column_prefix_key(column, sch)
        for b in self.books:
            if column_prefix_key(b["start"], sch) <= pos <= column_prefix_key(b["end"], sch):
                return b["n"]
        return None


def _ref_to_key(ref: str):
    from .refs import ref_key

    return ref_key(ref)
