"""A hand-written `speakers.overrides` entry must always outrank a
synthesized numbered-character override (_synthesized_numbered_overrides,
C3), not just at the "scene end" restoration it already guards but at the
scene's START too.

Helen's `Θε.` is `Servant` by default but a manifest override reassigns it
to `Theoclymenus` from line 1165 on. Later (1628 on) a second, genuinely
different character enters as `Θε.β` = `Second Servant`. Because Helen's
default `Θε.` display ("Servant") is the base of "Second Servant", C3's
numbered-override synthesis mistook `Θε.`/`Θε.β` for a shared-abbreviation
pair (like a Chresmologos' `Α'`/`Β'`) and manufactured a SECOND override,
`Θε.` -> "Second Servant" from the Second Servant's first line -- which,
sorted after the declared 1165 override, won every later `Θε.` event and
relabelled Theoclymenus's own half-lines "Second Servant" (Helen
1628-1640). The declared override's own comment says a hand-written
override "always outranks a synthesized one"; that rule was applied to the
scene-end restoration but not to this initial synthesis."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from drama_pipeline.config import Manifest
from drama_pipeline.stage7_emit import _canonicalize_play_line_speakers


def _manifest() -> Manifest:
    data = {
        "work": {"id": "helen", "author": "euripides"},
        "speakers": {
            "sigla": {
                "—": None,
                "Θε.": "Servant",
                "Θε.β": "Second Servant",
            },
            "overrides": [
                {"siglum": "Θε.", "from": "1165", "display": "Theoclymenus"},
            ],
        },
    }
    return Manifest(data, ROOT / "manifests" / "helen.yaml")


def _spine() -> dict:
    return {
        "segments": [
            {
                "id": "1:100",
                "book": 1,
                "lines": [{"n": 1, "ref": "100"}],
                "speakers": [{"line": 1, "offset": 0, "label": "Θε."}],
            },
            {
                "id": "1:1628",
                "book": 1,
                "lines": [{"n": 2, "ref": "1628"}],
                "speakers": [{"line": 2, "offset": 0, "label": "Θε."}],
            },
            {
                "id": "1:1629",
                "book": 1,
                "lines": [{"n": 3, "ref": "1629"}],
                "speakers": [{"line": 3, "offset": 0, "label": "Θε.β"}],
            },
            {
                "id": "1:1630",
                "book": 1,
                "lines": [{"n": 4, "ref": "1630"}],
                "speakers": [{"line": 4, "offset": 0, "label": "Θε."}],
            },
        ],
    }


def test_declared_override_outranks_synthesized_numbered_override():
    spine = _spine()
    _canonicalize_play_line_speakers(spine, _manifest())
    displays = {
        seg["id"]: seg["speakers"][0]["display"] for seg in spine["segments"]
    }
    # Before the 1165 override: the plain roster meaning, "Servant".
    assert displays["1:100"] == "Servant"
    # After 1165, and both before and after the Second Servant's own entry
    # at 1629: still Theoclymenus, per the manifest's own override -- never
    # relabelled "Second Servant" just because a same-prefixed sibling
    # siglum later showed up.
    assert displays["1:1628"] == "Theoclymenus"
    assert displays["1:1630"] == "Theoclymenus"
