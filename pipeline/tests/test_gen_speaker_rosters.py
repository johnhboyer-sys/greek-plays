"""gen_speaker_rosters.py: safe --write and Perseus first-appearance alignment."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

import gen_speaker_rosters as gsr


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


SUPPORTED = """\
work:
  id: demo
  title: Demo Play
citation:
  scheme: play-line
  note: keep me
speakers:
  sigla:
    "—": null
books:
  - {n: 1, start: "1", end: "10"}
extra:
  untouched: true
  nested:
    flag: 1
"""

COMMENT_FORM = """\
work:
  id: demo
citation:
  scheme: play-line
speakers:  # trailing comment on the key
  sigla:
    "—": null
books:
  - {n: 1, start: "1", end: "10"}
"""

INLINE_FORM = """\
work:
  id: demo
citation:
  scheme: play-line
speakers: {sigla: {"—": null}}
books:
  - {n: 1, start: "1", end: "10"}
"""

PERSEUS_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text>
    <body>
      <sp><speaker>Watchman</speaker><p>night.</p></sp>
      <sp><speaker>Chorus</speaker><p>years.</p></sp>
      <sp><speaker>Watchman</speaker><p>again.</p></sp>
      <sp><speaker>Clytaemestra</speaker><p>beacon.</p></sp>
      <sp><speaker>Herald</speaker><p>dust.</p></sp>
      <sp><speaker>Chorus</speaker><p>again.</p></sp>
    </body>
  </text>
</TEI>
"""


@pytest.mark.parametrize(
    "body,form",
    [(COMMENT_FORM, "comment"), (INLINE_FORM, "inline")],
    ids=["comment", "inline"],
)
def test_write_refuses_unsupported_forms_that_would_duplicate(tmp_path, body, form):
    path = _write(tmp_path / f"{form}.yaml", body)
    before = path.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported speakers form"):
        gsr.write_block(path, {"ΦΥΛΑΞ": "Watchman", "—": None})
    after = path.read_text(encoding="utf-8")
    assert after == before
    assert after.count("speakers:") == 1


def test_write_round_trips_other_top_level_keys(tmp_path):
    path = _write(tmp_path / "demo.yaml", SUPPORTED)
    original = yaml.safe_load(path.read_text(encoding="utf-8"))
    gsr.write_block(path, {"ΦΥΛΑΞ": "Watchman", "ΧΟΡΟΣ": "Chorus", "—": None})
    text = path.read_text(encoding="utf-8")
    proposed = yaml.safe_load(text)
    headings = [
        line for line in text.splitlines()
        if not line.startswith((" ", "\t")) and line.startswith("speakers")
    ]
    assert headings == ["speakers:"]
    assert "speakers" in proposed
    for key, value in original.items():
        if key == "speakers":
            continue
        assert proposed[key] == value
    for key in proposed:
        if key != "speakers":
            assert key in original
    assert proposed["speakers"]["sigla"]["ΦΥΛΑΞ"] == "Watchman"
    assert proposed["speakers"]["sigla"]["ΧΟΡΟΣ"] == "Chorus"
    assert proposed["speakers"]["sigla"]["—"] is None
    assert not list(tmp_path.glob("*.tmp"))


def test_perseus_four_align_one_residue(tmp_path):
    perseus = _write(tmp_path / "perseus.xml", PERSEUS_XML)
    book = _write(
        tmp_path / "book-01.json",
        json.dumps(
            {
                "segments": [
                    {"speakers": [{"label": "ΦΥΛΑΞ"}, {"label": "ΧΟΡΟΣ"}]},
                    {"speakers": [{"label": "ΦΥΛΑΞ"}]},
                    {"speakers": [{"label": "ΚΛΥΤΑΙΜΗΣΤΡΑ"}]},
                    {"speakers": [{"label": "ΚΗΡΥΞ"}]},
                    {"speakers": [{"label": "ΞΕΝΟΣ"}]},
                    {"speakers": [{"label": "—"}]},
                ]
            },
            ensure_ascii=False,
        ),
    )
    greek, _ = gsr.labels_from_book_json(book)
    names = gsr.speakers_from_perseus(perseus)
    mapping, leftover_greek, leftover_perseus = gsr.align_perseus(greek, names)
    assert mapping == {
        "ΦΥΛΑΞ": "Watchman",
        "ΧΟΡΟΣ": "Chorus",
        "ΚΛΥΤΑΙΜΗΣΤΡΑ": "Clytaemestra",
        "ΚΗΡΥΞ": "Herald",
    }
    assert leftover_greek == ["ΞΕΝΟΣ"]
    assert leftover_perseus == []
    roster, unresolved = gsr.propose(Counter(greek), {}, {}, mapping)
    assert roster["ΦΥΛΑΞ"] == "Watchman"
    assert roster["—"] is None
    assert unresolved == ["ΞΕΝΟΣ"]


def test_caps_form_rule(tmp_path):
    perseus = _write(
        tmp_path / "perseus.xml",
        """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text><body>
    <sp><speaker>Clytaemestra</speaker><p>a</p></sp>
    <sp><speaker>Herald</speaker><p>b</p></sp>
    <sp><speaker>Clytaemestra</speaker><p>c</p></sp>
  </body></text>
</TEI>
""",
    )
    book = _write(
        tmp_path / "book-01.json",
        json.dumps(
            {
                "segments": [
                    {"speakers": [{"label": "ΚΛΥΤΑΙΜΗΣΤΡΑ"}]},
                    {"speakers": [{"label": "Κλ."}]},
                    {"speakers": [{"label": "ΚΗΡΥΞ"}]},
                    {"speakers": [{"label": "Κλ."}]},
                ]
            },
            ensure_ascii=False,
        ),
    )
    greek, _ = gsr.labels_from_book_json(book)
    names = gsr.speakers_from_perseus(perseus)
    mapping, leftover_greek, leftover_perseus = gsr.align_perseus(greek, names)
    assert mapping["ΚΛΥΤΑΙΜΗΣΤΡΑ"] == "Clytaemestra"
    assert mapping["Κλ."] == "Clytaemestra"
    assert mapping["ΚΗΡΥΞ"] == "Herald"
    assert leftover_greek == []
    assert leftover_perseus == []
