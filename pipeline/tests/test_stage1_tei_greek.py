import json
from pathlib import Path

import pytest

from drama_pipeline.config import Manifest
from drama_pipeline.stage1_tei_greek import parse_spine
from drama_pipeline.beta import to_beta_key
from drama_pipeline.stage3_tokenize import tokenize


def test_tei_brackets_join_and_speaker(tmp_path):
    xml = tmp_path / 'play.xml'
    xml.write_text('''<TEI><teiHeader><fileDesc><titleStmt><editor>Editor</editor></titleStmt></fileDesc></teiHeader><text><body><sp><speaker>Α</speaker><l n="1"><del>λόγος</del> <add>θεός</add></l></sp><sp><speaker>Β</speaker><l n="1b" part="F">ἄλλος</l><l n="2">τέλος</l></sp></body></text></TEI>''')
    data = {'work': {'id': 'test', 'greek_edition': 'Test', 'greek_source': {'expect': {'editor': 'Editor'}}}, 'citation': {'scheme': 'play-line', 'lacunae': {'1': []}, 'transpositions': {'1': []}, 'repeated_refs': {}, 'ref_fixes': {}, 'title_labels': [], 'fingerprint': {}}, 'english': {}, 'books': [{'n': 1, 'start': '1', 'end': '2'}]}
    spine = parse_spine(xml, Manifest(data, tmp_path / 'test.yaml'), check_fingerprint=False)
    lines = [line for segment in spine['segments'] for line in segment['lines']]
    assert len(lines) == 2
    assert lines[0]['ref'] == '1'
    assert lines[0]['text'] == '[λόγος] <θεός> ἄλλος'
    assert lines[0]['parts'] == [{'ref': '1b', 'offset': len('[λόγος] <θεός> ')}]
    assert spine['segments'][0]['speakers'][1]['offset'] == len('[λόγος] <θεός> ')


def test_unnumbered_line_fails(tmp_path):
    xml = tmp_path / 'play.xml'
    xml.write_text('<TEI><teiHeader><fileDesc><titleStmt><editor>Editor</editor></titleStmt></fileDesc></teiHeader><text><body><l>text</l></body></text></TEI>')
    data = {'work': {'id': 'test', 'greek_edition': 'Test', 'greek_source': {'expect': {'editor': 'Editor'}}}, 'citation': {'scheme': 'play-line', 'lacunae': {'1': []}, 'transpositions': {'1': []}, 'title_labels': []}, 'english': {}, 'books': [{'n': 1, 'start': '1', 'end': '1'}]}
    with pytest.raises(ValueError, match='no @n'):
        parse_spine(xml, Manifest(data, tmp_path / 'test.yaml'), check_fingerprint=False)


def test_strophe_lacuna_and_lettered_line(tmp_path):
    xml = tmp_path / 'play.xml'
    xml.write_text('''<TEI><teiHeader><editor>Editor</editor></teiHeader><text><body>
      <div type="textpart" subtype="strophe" n="1"><sp><speaker>Α</speaker>
      <l n="1">ἀρχή<note>omit</note><pb n="1"/></l><l n="1b">ἔπος</l>
      <l n="2"><gap reason="lost" rend="···"/></l>
      <l n="3">πρὶν <gap reason="ellipsis" rend="..."/> τέλος</l></sp></div>
      <l n="0" style="hidden">cast</l></body></text></TEI>''')
    data = {'work': {'id': 'test', 'greek_edition': 'Test', 'greek_source': {'expect': {'editor': 'Editor'}}},
            'citation': {'scheme': 'play-line', 'lacunae': {'1': ['2']}, 'transpositions': {'1': []},
                         'repeated_refs': {}, 'ref_fixes': {}, 'title_labels': [], 'fingerprint': {}},
            'english': {}, 'books': [{'n': 1, 'start': '1', 'end': '3'}]}
    spine = parse_spine(xml, Manifest(data, tmp_path / 'test.yaml'), check_fingerprint=False)
    lines = [line for segment in spine['segments'] for line in segment['lines']]
    assert [line['ref'] for line in lines] == ['1', '1b', '2', '3']
    assert lines[0]['label'] == 'στρ. 1.'
    assert lines[0]['text'] == 'ἀρχή'
    assert lines[2]['role'] == 'lacuna'
    assert lines[2]['text'] == ''
    assert lines[3]['text'] == 'πρὶν ... τέλος'


def test_perseus_elision_and_iota_subscript_keys():
    assert to_beta_key('αὐτῷ') == to_beta_key('αὐτῷ') == 'au)tw=|'
    assert to_beta_key('ἀπʼ') == to_beta_key('ἀπ’')
    spine = {'work': 'test', 'segments': [{'id': '1:1', 'book': 1, 'column': '1',
                           'lines': [{'n': 1, 'text': 'ἀπʼ αὐτῷ'}]}]}
    tokens, _, failures = tokenize(spine)
    assert not failures
    assert [t['k'] for t in tokens['segments'][0]['lines'][0]['tokens']] == ["a)p'", 'au)tw=|']
