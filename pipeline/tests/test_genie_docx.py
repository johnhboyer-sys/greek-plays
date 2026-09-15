"""genie_docx.paragraphs on a small docx fixture built with zipfile."""

import zipfile
from pathlib import Path

import pytest

from drama_pipeline.genie_docx import paragraphs

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_DOCUMENT = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{_W}">
<w:body>
<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>DIONYSUS</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Of Sisyphus</w:t></w:r>
<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>1</w:t></w:r>
<w:r><w:t xml:space="preserve">, let not this ill fame cling</w:t></w:r></w:p>
<w:p><w:r><w:rPr><w:i/></w:rPr><w:t>Enter ODYSSEUS, scanning the sand.</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Before the break</w:t></w:r></w:p>
<w:p><w:r><w:br w:type="page"/><w:t xml:space="preserve">After the break</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">   </w:t></w:r></w:p>
</w:body>
</w:document>"""


def _write_fixture(path: Path) -> Path:
    docx_path = path / "fixture.docx"
    with zipfile.ZipFile(docx_path, "w") as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _RELS)
        archive.writestr("word/document.xml", _DOCUMENT)
    return docx_path


@pytest.fixture()
def fixture_paragraphs(tmp_path: Path):
    return paragraphs(_write_fixture(tmp_path))


def test_bold_cue_run_becomes_plain_text(fixture_paragraphs):
    assert fixture_paragraphs[0].text == "DIONYSUS"
    assert fixture_paragraphs[0].italic is False


def test_superscript_run_becomes_bracket_footnote_marker(fixture_paragraphs):
    line = next(p for p in fixture_paragraphs if p.text.startswith("Of Sisyphus"))
    assert line.text == "Of Sisyphus[1], let not this ill fame cling"


def test_whole_paragraph_italic_run_is_a_direction(fixture_paragraphs):
    direction = next(p for p in fixture_paragraphs if "Enter" in p.text)
    assert direction.italic is True
    assert direction.text == "Enter ODYSSEUS, scanning the sand."


def test_page_break_run_increments_page_index(fixture_paragraphs):
    before = next(p for p in fixture_paragraphs if p.text == "Before the break")
    after = next(p for p in fixture_paragraphs if p.text == "After the break")
    assert before.page == 0
    assert after.page == 1


def test_blank_paragraph_dropped(fixture_paragraphs):
    assert all(p.text.strip() for p in fixture_paragraphs)
