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


def _one_line_manifest(tmp_path, edition=None):
    data = {'work': {'id': 'test', 'greek_edition': 'Test', 'greek_source': {'expect': {'editor': 'Editor'}}},
            'citation': {'scheme': 'play-line', 'lacunae': {'1': []}, 'transpositions': {'1': []},
                         'repeated_refs': {}, 'ref_fixes': {}, 'title_labels': [], 'fingerprint': {}},
            'english': {}, 'books': [{'n': 1, 'start': '1', 'end': '1'}]}
    manifest = Manifest(data, tmp_path / 'test.yaml')
    if edition is not None:
        manifest.edition = edition
    return manifest


def _one_line_xml(tmp_path, line):
    xml = tmp_path / 'play.xml'
    xml.write_text('<TEI><teiHeader><editor>Editor</editor></teiHeader><text><body><sp><speaker>Α</speaker>'
                   + line + '</sp></body></text></TEI>')
    return xml


def test_xml_comment_in_line_is_not_text(tmp_path):
    # Hecuba 387 carries `<!-- very odd crasis mark here -->` inside its <l>.
    xml = _one_line_xml(tmp_path, '<l n="1">ἐγὼ τεκον <!-- editor note --></l>')
    spine = parse_spine(xml, _one_line_manifest(tmp_path), check_fingerprint=False)
    assert spine['segments'][0]['lines'][0]['text'] == 'ἐγὼ τεκον'


def test_lacuna_line_ignores_xml_comment(tmp_path):
    xml = _one_line_xml(tmp_path, '<l n="5"><gap reason="lost"/><!-- note --></l>')
    manifest = _one_line_manifest(tmp_path)
    manifest.data['citation']['lacunae'] = {'1': ['5']}
    manifest.data['books'] = [{'n': 1, 'start': '5', 'end': '5'}]
    spine = parse_spine(xml, manifest, check_fingerprint=False)
    line = spine['segments'][0]['lines'][0]
    assert line['role'] == 'lacuna'
    assert line['text'] == ''


def _two_line_xml(tmp_path):
    xml = tmp_path / 'play.xml'
    xml.write_text('<TEI><teiHeader><editor>Editor</editor></teiHeader><text><body><sp><speaker>Α</speaker>'
                   '<l n="1">ἐγὼ ῎τεκον</l><l n="2">ἄλλος ῎τεκον</l></sp></body></text></TEI>')
    manifest = _one_line_manifest(tmp_path)
    manifest.data['books'] = [{'n': 1, 'start': '1', 'end': '2'}]
    return xml, manifest


def _spine_with_fix(tmp_path, fix):
    xml, manifest = _two_line_xml(tmp_path)
    manifest.edition = {'text_fixes': [fix]}
    return parse_spine(xml, manifest, check_fingerprint=False)


def test_greek_text_fix_hits_its_own_line_once(tmp_path):
    fix = {'ref': '2', 'find': '῎τεκον', 'replace': 'ʼτεκον', 'note': 'test'}
    lines = [l for s in _spine_with_fix(tmp_path, fix)['segments'] for l in s['lines']]
    assert [l['text'] for l in lines] == ['ἐγὼ ῎τεκον', 'ἄλλος ʼτεκον']


def test_greek_text_fix_needs_a_ref(tmp_path):
    with pytest.raises(ValueError, match='text_fixes.*ref'):
        _spine_with_fix(tmp_path, {'find': 'ἄλλος', 'replace': 'ἄλλως', 'note': 'test'})


def test_greek_text_fix_on_a_line_without_the_text_fails(tmp_path):
    # `find` occurs once in the file, but on line 2; naming line 1 must not apply it.
    with pytest.raises(ValueError, match='text_fixes'):
        _spine_with_fix(tmp_path, {'ref': '1', 'find': 'ἄλλος', 'replace': 'ἄλλως', 'note': 'test'})


def test_greek_text_fix_ref_absent_from_the_edition_fails(tmp_path):
    with pytest.raises(ValueError, match='text_fixes'):
        _spine_with_fix(tmp_path, {'ref': '99', 'find': 'ἄλλος', 'replace': 'ἄλλως', 'note': 'test'})


def test_greek_text_fix_find_twice_on_its_line_fails(tmp_path):
    xml = _one_line_xml(tmp_path, '<l n="1">῎τεκον ῎τεκον</l>')
    fix = {'ref': '1', 'find': '῎τεκον', 'replace': 'ʼτεκον', 'note': 'test'}
    with pytest.raises(ValueError, match='text_fixes'):
        parse_spine(xml, _one_line_manifest(tmp_path, {'text_fixes': [fix]}), check_fingerprint=False)


def _speaker_labels(spine):
    """(line ref, speaker label) for every speaker event, in order."""
    out = []
    for segment in spine['segments']:
        for event in segment.get('speakers') or []:
            out.append(event['label'])
    return out


_SPLIT_SPEECH = ('<sp><speaker>Α</speaker><l n="1">ἀρχή</l></sp>'
                 '<sp><speaker>Α</speaker><l n="2">μέσον</l></sp>'
                 '<sp><speaker>Β</speaker><l n="3">τέλος</l></sp>'
                 '<sp><speaker>Α</speaker><l n="4">πάλιν</l></sp>')


def _split_speech_setup(tmp_path):
    xml = tmp_path / 'play.xml'
    xml.write_text('<TEI><teiHeader><editor>Editor</editor></teiHeader><text><body>' + _SPLIT_SPEECH + '</body></text></TEI>')
    data = {'work': {'id': 'test', 'greek_edition': 'Test', 'greek_source': {'expect': {'editor': 'Editor'}}},
            'citation': {'scheme': 'play-line', 'lacunae': {'1': []}, 'transpositions': {'1': []},
                         'repeated_refs': {}, 'ref_fixes': {}, 'title_labels': [], 'fingerprint': {}},
            'english': {}, 'books': [{'n': 1, 'start': '1', 'end': '4'}]}
    return xml, Manifest(data, tmp_path / 'test.yaml')


def test_same_speaker_blocks_are_one_speech_without_a_line_anchored_pair(tmp_path):
    # Perseus splits one speech into several <sp>; with no line-anchored pair
    # the same speaker straight on opens no new speaker event.
    xml, manifest = _split_speech_setup(tmp_path)
    spine = parse_spine(xml, manifest, check_fingerprint=False)
    assert _speaker_labels(spine) == ['Α', 'Β', 'Α']


def test_unlabelled_block_between_same_speaker_blocks_opens_no_event(tmp_path):
    # A, an <sp> with no <speaker>, A: with no line-anchored pair the unlabelled
    # block continues A's speech, so the last A opens no speaker event either.
    xml, manifest = _split_speech_setup(tmp_path)
    xml.write_text('<TEI><teiHeader><editor>Editor</editor></teiHeader><text><body>'
                   '<sp><speaker>Α</speaker><l n="1">ἀρχή</l></sp>'
                   '<sp><l n="2">μέσον</l></sp>'
                   '<sp><speaker>Α</speaker><l n="3">τέλος</l></sp></body></text></TEI>')
    manifest.data['books'] = [{'n': 1, 'start': '1', 'end': '3'}]
    spine = parse_spine(xml, manifest, check_fingerprint=False)
    assert _speaker_labels(spine) == ['Α']


def test_same_speaker_blocks_stay_apart_with_a_line_anchored_pair(tmp_path, monkeypatch):
    # A line-anchored pair (Smyth's) anchors its English to each <sp>: keep them.
    import drama_pipeline.stage1_tei_greek as mod
    monkeypatch.setattr(mod, '_english_line_marks', lambda manifest: (set(), set()))
    xml, manifest = _split_speech_setup(tmp_path)
    spine = parse_spine(xml, manifest, check_fingerprint=False)
    assert _speaker_labels(spine) == ['Α', 'Α', 'Β', 'Α']


def test_modifier_turned_comma_is_edge_punctuation():
    # Perseus opens a quotation with U+02BD (Philoctetes 858); the key must be
    # the word's own. Every other builds' Greek has no U+02BD at a token edge.
    spine = {'work': 'test', 'segments': [{'id': '1:1', 'book': 1, 'column': '1',
                           'lines': [{'n': 1, 'text': 'ʽἄλλος ὕπνος'}]}]}
    tokens, _, failures = tokenize(spine)
    assert not failures
    assert [t['k'] for t in tokens['segments'][0]['lines'][0]['tokens']] == [to_beta_key('ἄλλος'), to_beta_key('ὕπνος')]


# --- OCR'd editions (source.kind: ocr-tei, edition-picker plan §3.1, P4) ---

def _ocr_setup(tmp_path, lines, *, sums=True, books_end='5'):
    """An OCR'd TEI in its own directory, with (or without) its SHA256SUMS."""
    import hashlib
    ocr = tmp_path / 'ocr' / 'ed'
    ocr.mkdir(parents=True)
    xml = ocr / 'play.xml'
    xml.write_text('<TEI><teiHeader><editor>Editor</editor></teiHeader><text><body>' + lines + '</body></text></TEI>',
                   encoding='utf-8')
    if sums:
        (ocr / 'SHA256SUMS').write_text(f'{hashlib.sha256(xml.read_bytes()).hexdigest()}  play.xml\n')
    data = {'work': {'id': 'test', 'greek_edition': 'Test',
                     'greek_source': {'kind': 'ocr-tei', 'expect': {'editor': 'Editor'}}},
            'citation': {'scheme': 'play-line', 'lacunae': {'1': []}, 'transpositions': {'1': []},
                         'repeated_refs': {}, 'ref_fixes': {}, 'title_labels': [], 'fingerprint': {}},
            'english': {}, 'books': [{'n': 1, 'start': '1', 'end': books_end}]}
    return xml, Manifest(data, tmp_path / 'test.yaml')


_OCR_DIALOGUE = ('<sp><speaker>Α</speaker><pb n="10"/><l n="1">ἀρχή</l><l n="2">δεύτερον</l>'
                 '<l n="3">τρίτον</l><l n="4">τέταρτον</l><l n="5" rend="margin-5">πέμπτον</l></sp>')


def test_ocr_edition_needs_its_own_sha256sums(tmp_path):
    xml, manifest = _ocr_setup(tmp_path, _OCR_DIALOGUE)
    lines = [l for s in parse_spine(xml, manifest, check_fingerprint=False)['segments'] for l in s['lines']]
    assert [l['ref'] for l in lines] == ['1', '2', '3', '4', '5']
    xml.write_text(xml.read_text(encoding='utf-8').replace('τρίτον', 'τρίτος'), encoding='utf-8')
    with pytest.raises(ValueError, match='SHA256SUMS'):
        parse_spine(xml, manifest, check_fingerprint=False)


def test_ocr_edition_without_sha256sums_fails(tmp_path):
    xml, manifest = _ocr_setup(tmp_path, _OCR_DIALOGUE, sums=False)
    with pytest.raises(ValueError, match='SHA256SUMS'):
        parse_spine(xml, manifest, check_fingerprint=False)


def test_printed_margin_number_must_equal_a_dialogue_line(tmp_path):
    # A trimeter holds one number: a printed 5 on the line counted 4 fails.
    xml, manifest = _ocr_setup(tmp_path, _OCR_DIALOGUE.replace('<l n="4">', '<l n="4" rend="margin-5">')
                               .replace(' rend="margin-5">πέμπτον', '>πέμπτον'))
    with pytest.raises(ValueError, match='printed margin numbers disagree'):
        parse_spine(xml, manifest, check_fingerprint=False)


def test_printed_margin_number_may_fall_inside_a_lyric_line(tmp_path):
    # Jebb's long lyric lines hold several numbers of the traditional count:
    # colon 12 of OT 1342 prints 1345, the next line being 1346.
    lines = ('<div type="textpart" subtype="strophe" n="2"><sp><speaker>Α</speaker>'
             '<l n="1" rend="colon-1">ἀρχή</l><l n="2" rend="colon-2 margin-4">δεύτερον τρίτον τέταρτον</l>'
             '<l n="5" rend="colon-3">πέμπτον</l></sp></div>')
    xml, manifest = _ocr_setup(tmp_path, lines)
    spine = parse_spine(xml, manifest, check_fingerprint=False)
    got = [l for s in spine['segments'] for l in s['lines']]
    assert [l['ref'] for l in got] == ['1', '2', '5']
    assert got[1]['text'] == 'δεύτερον τρίτον τέταρτον'  # the colon number is not text
    bad = lines.replace('margin-4', 'margin-6')
    xml.parent.joinpath('SHA256SUMS').unlink()
    xml2, manifest2 = _ocr_setup(tmp_path / 'b', bad)
    with pytest.raises(ValueError, match='printed margin numbers disagree'):
        parse_spine(xml2, manifest2, check_fingerprint=False)


def test_turn_over_row_number_may_mark_the_next_line(tmp_path):
    # OT 1194–1195: the turn-over 'βροτῶν' prints 1195 on its own row; 1195
    # (οὐδὲν μακαρίζω) begins there. The joined line carries the 'turn' mark.
    lines = ('<sp><speaker>Α</speaker><l n="1">ἀρχή</l>'
             '<l n="2" rend="margin-3 turn">δεύτερον βροτῶν</l><l n="3">τρίτον</l></sp>')
    xml, manifest = _ocr_setup(tmp_path, lines, books_end='3')
    assert parse_spine(xml, manifest, check_fingerprint=False)


def test_number_printed_apart_checks_against_its_page(tmp_path):
    # OT p. 18 prints '140 145' below its block: each must fall within the page.
    lines = ('<sp><speaker>Α</speaker><pb n="18"/><l n="1">ἀρχή</l><l n="2" rend="margin-apart-2">δεύτερον</l>'
             '<pb n="20"/><l n="3">τρίτον</l></sp>')
    xml, manifest = _ocr_setup(tmp_path, lines, books_end='3')
    assert parse_spine(xml, manifest, check_fingerprint=False)
    xml2, manifest2 = _ocr_setup(tmp_path / 'b', lines.replace('margin-apart-2', 'margin-apart-7'), books_end='3')
    with pytest.raises(ValueError, match='printed apart 7'):
        parse_spine(xml2, manifest2, check_fingerprint=False)


def test_printed_margin_number_on_a_joined_part_is_checked(tmp_path):
    # An antilabe line: <l n="3"> plus its final share <l n="3b" part="F">.
    # The share's printed number was never recorded, so a wrong one passed.
    def lines(part_rend):
        return ('<sp><speaker>Α</speaker><l n="1">ἀρχή</l><l n="2">δεύτερον</l>'
                '<l n="3" part="I">τρίτον</l></sp><sp><speaker>Β</speaker>'
                f'<l n="3b" part="F"{part_rend}>ναί</l><l n="4">τέταρτον</l><l n="5">πέμπτον</l></sp>')
    xml, manifest = _ocr_setup(tmp_path / 'a', lines(' rend="margin-3"'))
    assert parse_spine(xml, manifest, check_fingerprint=False)      # 3b is line 3: agrees
    xml2, manifest2 = _ocr_setup(tmp_path / 'b', lines(' rend="margin-4"'))
    with pytest.raises(ValueError, match='printed margin numbers disagree'):
        parse_spine(xml2, manifest2, check_fingerprint=False)


def test_a_joined_turn_over_line_may_carry_two_printed_numbers(tmp_path):
    # The converter keeps the target's number and the turn-over's: both are checked.
    def lines(second):
        return ('<sp><speaker>Α</speaker><l n="1">ἀρχή</l>'
                f'<l n="2" rend="margin-2 {second} turn">δεύτερον βροτῶν</l><l n="4">τέταρτον</l></sp>')
    xml, manifest = _ocr_setup(tmp_path / 'a', lines('margin-3'), books_end='4')
    assert parse_spine(xml, manifest, check_fingerprint=False)
    xml2, manifest2 = _ocr_setup(tmp_path / 'b', lines('margin-9'), books_end='4')
    with pytest.raises(ValueError, match='printed margin numbers disagree'):
        parse_spine(xml2, manifest2, check_fingerprint=False)
