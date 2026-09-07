from pathlib import Path

from drama_pipeline.preflight import (
    WorkManifest,
    _validate_public_domain_allowlist,
)


def _manifest(translation_id: str = "smyth") -> WorkManifest:
    return WorkManifest(
        "play",
        Path("play.yaml"),
        {"english": {"primary": {"id": translation_id}}},
    )


def _messages(manifest: WorkManifest, path: Path) -> list[str]:
    problems = []
    _validate_public_domain_allowlist(manifest, problems, allowlist_path=path)
    return [message for _work, _file, message in problems]


def test_public_domain_allowlist_accepts_known_id(tmp_path: Path):
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "translations:\n"
        "  - {id: smyth, translator: H. W. Smyth, year: 1922, note: Public domain.}\n",
        encoding="utf-8",
    )
    assert _messages(_manifest(), allowlist) == []


def test_public_domain_allowlist_fails_when_file_is_missing(tmp_path: Path):
    messages = _messages(_manifest(), tmp_path / "missing.yaml")
    assert any("allowlist missing" in message for message in messages)


def test_public_domain_allowlist_fails_for_unknown_id(tmp_path: Path):
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "translations:\n"
        "  - {id: jebb, translator: R. C. Jebb, year: 1883, note: Public domain.}\n",
        encoding="utf-8",
    )
    messages = _messages(_manifest(), allowlist)
    assert any("'smyth' (primary) is not on" in message for message in messages)


def test_public_domain_allowlist_fails_for_empty_list(tmp_path: Path):
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text("translations: []\n", encoding="utf-8")
    messages = _messages(_manifest(), allowlist)
    assert any("must be a non-empty list" in message for message in messages)


def test_public_domain_allowlist_walks_column_sources_and_summary_overlay(tmp_path: Path):
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "translations:\n"
        "  - {id: smyth, translator: H. W. Smyth, year: 1922, note: Public domain.}\n",
        encoding="utf-8",
    )
    manifest = WorkManifest(
        "play",
        Path("play.yaml"),
        {
            "english": {
                "primary": {"id": "smyth"},
                "summary_overlay": {"id": "smyth-summary", "columns": ["1"]},
                "column_sources": [
                    {"column": "B11", "file": "gatt-helen.clean.json"}
                ],
            }
        },
    )
    messages = _messages(manifest, allowlist)
    assert any("'smyth-summary' (summary_overlay)" in message for message in messages)
    assert any("'gatt-helen' (column:B11)" in message for message in messages)


def test_oneill_name_is_denied_even_on_an_allowlisted_id(tmp_path: Path):
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "translations:\n"
        "  - {id: smyth, translator: H. W. Smyth, year: 1922, note: Public domain.}\n"
        "denied:\n"
        "  - {pattern: \"o'?neill\", note: \"Eugene O'Neill Jr. 1938, not PD\"}\n",
        encoding="utf-8",
    )
    manifest = WorkManifest(
        "play",
        Path("play.yaml"),
        {
            "english": {
                "primary": {
                    "id": "smyth",
                    "name": "Eugene O'Neill Jr. (1938)",
                    "source": "perseus/tlg0019.tlg001.perseus-eng1.xml",
                }
            }
        },
    )
    messages = _messages(manifest, allowlist)
    assert any("is denied" in message and "O'Neill" in message for message in messages)


def test_oneill_source_is_denied_even_on_an_allowlisted_id(tmp_path: Path):
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "translations:\n"
        "  - {id: athenian-society, translator: The Athenian Society, year: 1912, note: Public domain.}\n"
        "denied:\n"
        "  - {pattern: \"o'?neill\", note: \"Eugene O'Neill Jr. 1938, not PD\"}\n",
        encoding="utf-8",
    )
    manifest = WorkManifest(
        "play",
        Path("play.yaml"),
        {
            "english": {
                "primary": {
                    "id": "athenian-society",
                    "name": "The Athenian Society (1912)",
                    "source": "https://example.org/oneill-frogs.xml",
                }
            }
        },
    )
    messages = _messages(manifest, allowlist)
    assert any("is denied" in message for message in messages)
