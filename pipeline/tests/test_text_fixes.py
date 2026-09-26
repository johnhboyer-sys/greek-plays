import pytest
import yaml
from pathlib import Path

from drama_pipeline.text_fixes import apply_text_fixes
from drama_pipeline.preflight import WorkManifest, _validate_manifest_schema


def test_applies_once_to_final_text():
    english = {"chunks": [{"text": "before typo after"}]}
    apply_text_fixes(english, {}, [{"find": "typo", "replace": "word"}],
                     "play.yaml", "primary")
    assert english["chunks"][0]["text"] == "before word after"


@pytest.mark.parametrize("text,count", [("plain", 0), ("typo typo", 2)])
def test_wrong_hit_count_raises(text, count):
    with pytest.raises(ValueError, match=f"play.yaml.*primary.*{count} times"):
        apply_text_fixes({"chunks": [{"text": text}]}, {},
                         [{"find": "typo", "replace": "word"}],
                         "play.yaml", "primary")


def test_empty_replace_deletes_footnote_text():
    notes = {"1": "extra word"}
    apply_text_fixes({}, notes, [{"find": "extra ", "replace": ""}],
                     "play.yaml", "secondary")
    assert notes["1"] == "word"


def test_same_find_and_replace_raises():
    with pytest.raises(ValueError, match="invalid find"):
        apply_text_fixes({"chunks": [{"text": "word"}]}, {},
                         [{"find": "word", "replace": "word"}],
                         "play.yaml", "primary")


def test_stage_direction_is_a_target():
    english = {"chunks": [{"directions": [{"directions": ["[Enter}"]}]}]}
    apply_text_fixes(english, {}, [{"find": "[Enter}", "replace": "[Enter]"}],
                     "play.yaml", "third")
    assert english["chunks"][0]["directions"][0]["directions"] == ["[Enter]"]


def test_turn_offset_moves_with_shortened_text():
    chunk = {"text": "bad bad. Next", "turns": [{"offset": 9}]}
    apply_text_fixes({"chunks": [chunk]}, {},
                     [{"find": "bad bad", "replace": "bad"}],
                     "play.yaml", "secondary")
    assert chunk == {"text": "bad. Next", "turns": [{"offset": 5}]}


def test_display_cue_fix_is_reachable_and_exact_match_not_substring():
    # A turn's `display` (its printed cue) is fixable the same way `text`
    # is -- but a truncated cue can be a literal PREFIX of the correctly
    # spelled one printed everywhere else (Johnston's Agamemnon,
    # "CLYTAEMNESTR" vs "CLYTAEMNESTRA"), so this must match the WHOLE
    # display value, not count it as a substring hit inside every correct
    # one too.
    chunk = {"text": "x", "turns": [
        {"offset": 0, "display": "CLYTAEMNESTR"},
        {"offset": 1, "display": "CLYTAEMNESTRA"},
    ]}
    apply_text_fixes({"chunks": [chunk]}, {},
                     [{"find": "CLYTAEMNESTR", "replace": "CLYTAEMNESTRA"}],
                     "play.yaml", "overlay")
    assert chunk["turns"][0]["display"] == "CLYTAEMNESTRA"
    assert chunk["turns"][1]["display"] == "CLYTAEMNESTRA"
    # The offsets are untouched -- a display fix carries no text-offset math.
    assert [t["offset"] for t in chunk["turns"]] == [0, 1]


def test_text_fixes_key_passes_manifest_validation():
    path = Path(__file__).resolve().parents[2] / "manifests" / "frogs.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    problems = []
    _validate_manifest_schema(WorkManifest("frogs", path, data), problems)
    assert problems == []
