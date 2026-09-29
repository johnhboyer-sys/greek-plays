import json
from pathlib import Path

import pytest

from drama_pipeline.config import Manifest
from drama_pipeline.stage1_tei_greek import parse_spine


def test_tei_brackets_join_and_speaker(tmp_path):
    xml = tmp_path / 'play.xml'
    xml.write_text('''<TEI><teiHeader><fileDesc><titleStmt><editor>Editor</editor></titleStmt></fileDesc></teiHeader><text><body><sp><speaker>Α</speaker><l n="1"><del>λόγος</del> <add>θεός</add></l></sp><sp><speaker>Β</speaker><l n="1b" part="F">ἄλλος</l><l n="2">τέλος</l></sp></body></text></TEI>''')
    data = {'work': {'id': 'test', 'greek_edition': 'Test', 'greek_source': {'expect': {'editor': 'Editor'}}}, 'citation': {'scheme': 'play-line', 'lacunae': {'1': []}, 'transpositions': {'1': []}, 'repeated_refs': {}, 'ref_fixes': {}, 'title_labels': [], 'fingerprint': {}}, 'english': {}, 'books': [{'n': 1, 'start': '1', 'end': '2'}]}
    spine = parse_spine(xml, Manifest(data, tmp_path / 'test.yaml'), check_fingerprint=False)
    lines = [line for segment in spine['segments'] for line in segment['lines']]
    assert len(lines) == 2
    assert lines[0]['ref'] == '1'
    assert lines[0]['text'] == '[λόγος] ⟨θεός⟩ ἄλλος'
    assert lines[0]['parts'] == [{'ref': '1b', 'offset': len('[λόγος] ⟨θεός⟩ ')}]
    assert spine['segments'][0]['speakers'][1]['offset'] == len('[λόγος] ⟨θεός⟩ ')


def test_unnumbered_line_fails(tmp_path):
    xml = tmp_path / 'play.xml'
    xml.write_text('<TEI><teiHeader><fileDesc><titleStmt><editor>Editor</editor></titleStmt></fileDesc></teiHeader><text><body><l>text</l></body></text></TEI>')
    data = {'work': {'id': 'test', 'greek_edition': 'Test', 'greek_source': {'expect': {'editor': 'Editor'}}}, 'citation': {'scheme': 'play-line', 'lacunae': {'1': []}, 'transpositions': {'1': []}, 'title_labels': []}, 'english': {}, 'books': [{'n': 1, 'start': '1', 'end': '1'}]}
    with pytest.raises(ValueError, match='no @n'):
        parse_spine(xml, Manifest(data, tmp_path / 'test.yaml'), check_fingerprint=False)
