"""Public-build exclusion of private comparison slots (Astra lane B, F3)."""

from pathlib import Path

from drama_pipeline.config import Manifest, exclude_private_slots, private_translation_ids
from drama_pipeline.preflight import WorkManifest, _validate_public_gating
from drama_pipeline.stage7_emit import _manifest_v1_fields, public_private_slot_leaks


def _manifest_data(**overrides):
    data = {
        "work": {
            "id": "ecclesiazusae",
            "title": "Assemblywomen",
            "author": "aristophanes",
            "language": "grc",
            "tlg_author": "0019",
            "tlg_work": "010",
            "greek_edition": "Ussher",
        },
        "citation": {"scheme": "play-line"},
        "books": [{"n": 1, "start": "1", "end": "1183"}],
        "english": {
            "primary": {
                "id": "athenian-society",
                "name": "The Eleven Comedies (The Athenian Society, 1912)",
                "model": "turn-text",
            },
            "secondary": {
                "id": "hickie",
                "name": "W. J. Hickie (Bohn, 1853)",
                "model": "turn-text",
            },
            "third": {
                "id": "rogers",
                "name": "B. B. Rogers (Loeb, 1924)",
                "model": "turn-text",
            },
        },
        "registry": {
            "translations": [
                {"id": "athenian-society", "slot": "english"},
                {"id": "hickie", "private": True, "slot": "secondary"},
                {"id": "rogers", "private": True, "slot": "third"},
            ]
        },
    }
    data.update(overrides)
    return data


def test_private_ids_come_from_registry_even_when_english_slot_has_no_flag():
    ids = private_translation_ids(_manifest_data())
    assert ids == {"hickie", "rogers"}


def test_exclude_private_slots_drops_registry_private_secondary_and_third():
    stripped, excluded = exclude_private_slots(_manifest_data())
    english = stripped["english"]
    assert "secondary" not in english
    assert "third" not in english
    assert english["primary"]["id"] == "athenian-society"
    assert ("secondary", "hickie") in excluded
    assert ("third", "rogers") in excluded
    remaining = {t["id"] for t in stripped["registry"]["translations"]}
    assert remaining == {"athenian-society"}


def test_exclude_private_slots_drops_english_overlay_flagged_private():
    data = _manifest_data()
    del data["english"]["secondary"]
    del data["english"]["third"]
    data["english"]["overlays"] = [
        {"id": "rogers", "name": "Rogers", "model": "turn-text", "private": True},
        {"id": "lindsay", "name": "Lindsay", "model": "turn-text"},
    ]
    data["registry"]["translations"] = [
        {"id": "athenian-society"},
        {"id": "rogers", "private": True},
        {"id": "lindsay"},
    ]
    stripped, excluded = exclude_private_slots(data)
    overlay_ids = [item["id"] for item in stripped["english"]["overlays"]]
    assert overlay_ids == ["lindsay"]
    assert ("overlay", "rogers") in excluded


def test_public_manifest_v1_fields_omit_private_translations(tmp_path):
    data, excluded = exclude_private_slots(_manifest_data())
    manifest = Manifest(data, Path("ecclesiazusae.yaml"), public=True)
    manifest.excluded_private_slots = excluded
    (tmp_path / "sections.json").write_text("{}", encoding="utf-8")
    fields = _manifest_v1_fields(manifest, tmp_path)
    assert [t["id"] for t in fields["translations"]] == ["athenian-society"]


def test_local_manifest_v1_fields_keep_private_translations(tmp_path):
    manifest = Manifest(_manifest_data(), Path("ecclesiazusae.yaml"), public=False)
    (tmp_path / "sections.json").write_text("{}", encoding="utf-8")
    fields = _manifest_v1_fields(manifest, tmp_path)
    assert [t["id"] for t in fields["translations"]] == [
        "athenian-society",
        "hickie",
        "rogers",
    ]


def test_public_private_slot_leaks_finds_hidden_ross_text():
    excluded = [("secondary", "hickie"), ("third", "rogers")]
    doc = {
        "book": 1,
        "segments": [
            {"id": "1:1", "ross": [{"text": "hidden Hickie"}]},
        ],
    }
    leaks = public_private_slot_leaks(doc, excluded, "book-01.json")
    assert leaks
    assert any("private secondary" in message for message in leaks)


def test_preflight_public_gating_flags_private_true_slots():
    manifest = WorkManifest(
        work_id="ecclesiazusae",
        path=Path("ecclesiazusae.yaml"),
        data=_manifest_data(),
    )
    loaded = {
        "book-01.json": {
            "segments": [{"ross": [{"text": "hidden Hickie"}]}],
        }
    }
    problems = []
    _validate_public_gating(manifest, loaded, problems, public_build=True)
    assert any("private secondary" in message for _w, _f, message in problems)


def test_preflight_local_gating_keeps_private_true_slots():
    manifest = WorkManifest(
        work_id="ecclesiazusae",
        path=Path("ecclesiazusae.yaml"),
        data=_manifest_data(),
    )
    loaded = {
        "book-01.json": {
            "segments": [{"ross": [{"text": "hidden Hickie"}]}],
        }
    }
    problems = []
    _validate_public_gating(manifest, loaded, problems, public_build=False)
    assert problems == []
