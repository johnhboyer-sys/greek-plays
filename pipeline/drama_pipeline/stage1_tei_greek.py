"""Read a numbered drama TEI edition into the play-line Greek spine."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
from pathlib import Path

from lxml import etree

from . import scheme
from .config import BUILD_DIR, SOURCES_DIR, Manifest
from .stage1_greek import (
    _check_repeated_refs, _derive_play_line_transposed_blocks,
    _load_play_ref_fixes, _load_repeated_refs, _normalize_play_lineref,
    _rejoin_play_line_hyphens, _segment_play_lines,
    _transposition_derived_rows, _english_line_marks,
)


def _text(el: etree._Element) -> str:
    def walk(node: etree._Element) -> str:
        if not isinstance(node.tag, str):  # an XML comment or PI: its text is not the line's
            return node.tail or ''
        tag = etree.QName(node).localname
        if tag in {'note', 'milestone', 'pb'}:
            return node.tail or ''
        inner = (node.text or '') + ''.join(walk(child) for child in node)
        if tag == 'del':
            inner = f'[{inner}]'
        elif tag == 'add':
            inner = f'<{inner}>'
        elif tag == 'gap':
            inner = node.get('rend') or '…'
        return inner + (node.tail or '')
    raw = (el.text or '') + ''.join(walk(child) for child in el)
    raw = re.sub(r'(?<=[\u0370-\u03ff\u1f00-\u1fff])\.(?=[\u0370-\u03ff\u1f00-\u1fff])', '. ', raw)
    # Both raised-dot code points (U+00B7, U+0387 ano teleia) are punctuation.
    raw = re.sub(r'([,;\u00b7\u0387])(?=[\u0370-\u03ff\u1f00-\u1fff])', r'\1 ', raw)
    raw = raw.replace('…', ' … ')
    return re.sub(r'\s+', ' ', raw).strip()


def _strophe_label(line: etree._Element) -> str | None:
    names = {'strophe': 'στρ.', 'antistrophe': 'ἀντ.', 'epode': 'ἐπῳδ.',
             'ephymn': 'ἐφύμν.', 'mesode': 'μεσῳδ.'}
    for div in line.iterancestors():
        if etree.QName(div).localname != 'div':
            continue
        subtype = div.get('subtype')
        if subtype not in names:
            continue
        first = next((x for x in div.iter() if isinstance(x.tag, str) and etree.QName(x).localname == 'l' and x.get('n') != '0'), None)
        if first is line:
            n = div.get('n')
            return f"{names[subtype]} {n}." if n else names[subtype]
    return None


def parse_spine(xml_path: Path, manifest: Manifest, *, check_fingerprint: bool = True) -> dict:
    tree = etree.parse(str(xml_path))
    source = manifest.data['work']['greek_source']
    for field, expected in (source.get('expect') or {}).items():
        nodes = tree.xpath(f'//*[local-name()="teiHeader"]//*[local-name()="{field}"]')
        if expected not in [' '.join(''.join(n.itertext()).split()) for n in nodes]:
            raise ValueError(f'{xml_path}: TEI header {field} does not match {expected!r}')
    # A Perseus file is checked against sources/perseus/SHA256SUMS; an OCR'd
    # edition always against the SHA256SUMS of its own directory.
    if xml_path.parent.name == 'perseus' or source.get('kind') == 'ocr-tei':
        sums = xml_path.parent / 'SHA256SUMS'
        rows = sums.read_text().splitlines() if sums.is_file() else []
        expected = next((row.split()[0] for row in rows if row.split() and row.split()[-1] == xml_path.name), None)
        if not expected or hashlib.sha256(xml_path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'{xml_path}: source SHA256SUMS mismatch')
    body = tree.find('.//{*}body')
    if body is None:
        raise ValueError(f'{xml_path}: no TEI body')
    citation = manifest.data['citation']
    fixes = _load_play_ref_fixes(manifest)
    fix_hits = Counter()
    repeats = _load_repeated_refs(manifest)
    counts = Counter()
    flat = []
    marks = _english_line_marks(manifest)
    # Perseus splits one speech into several <sp> (a chorus per strophe, a
    # messenger per paragraph). The TLG text runs it as one speech, and a
    # turn-text pair (Storr's) has one turn for it, so with no line-anchored
    # pair the same speaker straight on opens no new speaker event. A
    # line-anchored pair (Smyth's) anchors its English to each <sp>, so it
    # keeps them apart.
    # An unlabelled <sp> leaves current_label alone: it continues the speech
    # before it, so an A, unlabelled, A run gives the last A no event.
    current_label = None
    merge_same_speaker = marks is None
    margins: list[tuple[int, int, bool, str, bool]] = []   # (index in flat, printed number, may hold several, ref, joined part)
    apart: list[tuple[int, str | None, int]] = []   # (index in flat, page, number printed apart)
    page = None
    for el in body.iter():
        if isinstance(el.tag, str) and etree.QName(el).localname == 'pb':
            page = el.get('n')
            continue
        if not isinstance(el.tag, str) or etree.QName(el).localname != 'l':
            continue
        if el.get('style') == 'hidden' or el.get('n') == '0':
            continue
        raw = el.get('n')
        if not raw:
            raise ValueError(f'{xml_path}: visible play <l> has no @n')
        rend = (el.get('rend') or '').split()
        if raw in fixes:
            fix_hits[raw] += 1
        ref = _normalize_play_lineref(raw, xml_path, fixes)
        scheme.play_line_kind(ref)
        sp = next((a for a in el.iterancestors() if isinstance(a.tag, str) and etree.QName(a).localname == 'sp'), None)
        speaker = sp.find('{*}speaker') if sp is not None else None
        label = ' '.join(''.join(speaker.itertext()).split()) if speaker is not None else None
        text = _text(el)
        # A joined share (part F/M) folds into the line before it, but its
        # printed number is still a checkpoint, against the share's own ref.
        joined = el.get('part') in {'F', 'M'}
        at = len(flat) - 1 if joined else len(flat)
        for token in rend:
            if re.fullmatch(r'margin-apart-\d+', token):
                apart.append((at, page, int(token[13:])))
            elif re.fullmatch(r'margin-\d+', token):
                # A lyric line (a colon number, a strophe) or a line with a
                # turn-over may hold several numbers of the traditional count.
                several = any(t.startswith('colon-') or t == 'turn' for t in rend) or _in_strophe(el)
                margins.append((at, int(token[7:]), several, ref, joined))
        part = el.get('part')
        if part in {'F', 'M'}:
            if not flat:
                raise ValueError(f'{xml_path}: orphan joined part {ref}')
            previous = flat[-1]
            offset = len(previous['text']) + (1 if previous['text'] and text else 0)
            previous['text'] += (' ' if previous['text'] and text else '') + text
            previous['joined'] = True
            previous.setdefault('parts', []).append({'ref': ref, 'offset': offset})
            if label and (not previous.get('_sp') is sp) and (label != current_label or not merge_same_speaker):
                previous.setdefault('speakers', []).append({'offset': offset, 'label': label})
                current_label = label
            continue
        counts[ref] += 1
        if counts[ref] > 1 and ref not in repeats:
            raise ValueError(f'{xml_path}: undeclared repeated ref {ref}')
        entry = {'ref': ref, 'text': text, '_sp': sp, '_page': page}
        if label and (not flat or flat[-1].get('_sp') is not sp) and (label != current_label or not merge_same_speaker):
            entry['speakers'] = [{'offset': 0, 'label': label}]
            current_label = label
        mark = _strophe_label(el)
        if mark:
            entry['label'] = mark
        kids = [c for c in el if isinstance(c.tag, str)]  # comments and PIs are not content
        if len(kids) == 1 and etree.QName(kids[0]).localname == 'gap' and kids[0].get('reason') == 'lost' and not (el.text or '').strip() and not any((c.tail or '').strip() for c in el):
            entry['role'] = 'lacuna'
            entry['text'] = ''
        flat.append(entry)
    if {k: fix_hits[k] for k in fixes if fix_hits[k] != 1}:
        raise ValueError(f'{xml_path}: stale citation.ref_fixes')
    _check_margin_numbers(flat, margins, apart, xml_path)
    _check_repeated_refs(repeats, counts, xml_path)
    lacunae = {e['ref'] for e in flat if e.get('role') == 'lacuna'}
    if lacunae != set((citation.get('lacunae') or {}).get('1') or []):
        raise ValueError(f'{xml_path}: citation.lacunae mismatch: observed {sorted(lacunae)}')
    refs = [e['ref'] for e in flat]
    observed = _derive_play_line_transposed_blocks(refs)
    declared = _transposition_derived_rows((citation.get('transpositions') or {}).get('1'), manifest.work_id)
    if declared != observed:
        raise ValueError(f'{xml_path}: citation.transpositions mismatch: observed {observed!r}')
    if citation.get('title_labels'):
        raise ValueError(f'{xml_path}: citation.title_labels declares unobserved title')
    fingerprint = {'count': len(refs), 'sha256': hashlib.sha256(','.join(refs).encode()).hexdigest()}
    if check_fingerprint and fingerprint != citation.get('fingerprint'):
        raise ValueError(f'{xml_path}: citation.fingerprint mismatch: observed {fingerprint!r}')
    for e in flat:
        e.pop('_sp', None)
        e.pop('_page', None)
    _apply_greek_text_fixes(flat, getattr(manifest, 'edition', None), xml_path)
    _rejoin_play_line_hyphens(flat)
    segments = _segment_play_lines(flat, *(marks or (None, None)))
    # Keep lettered part anchors on the joined line for later alignment.
    part_map = {e['ref']: e['parts'] for e in flat if e.get('parts')}
    for seg in segments:
        for line in seg['lines']:
            if line['ref'] in part_map:
                line['parts'] = part_map[line['ref']]
    return {'work': manifest.work_id, 'edition': manifest.data['work']['greek_edition'],
            'segments': segments, 'headings': [], 'unassigned_lines': []}


def _in_strophe(line: etree._Element) -> bool:
    return any(isinstance(a.tag, str) and etree.QName(a).localname == 'div' and a.get('subtype') in
               {'strophe', 'antistrophe', 'epode', 'ephymn', 'mesode'} for a in line.iterancestors())


def _line_number(ref: str) -> int:
    m = re.match(r'\d+', ref)
    return int(m.group(0)) if m else 0


def _check_margin_numbers(flat: list[dict], margins: list, apart: list, xml_path: Path) -> None:
    """The OCR profile's checkpoint gate: every number the page prints must
    agree with the counted ``n``. A printed number P on a line numbered n
    agrees when P = n; on a line that may hold several numbers of the
    traditional count, also when n < P <= the next line's number (P inside
    the line, or on a turn-over row where the next line begins). A number
    printed apart from its lines must fall within its page's numbers."""
    nums = [_line_number(e['ref']) for e in flat]
    bad = []
    for i, printed, several, n, joined in margins:
        here = _line_number(n)
        nxt = next((v for v in nums[i + 1:] if v > here), None)
        if printed == here and (n.isdigit() or joined):
            continue
        if several and nxt is not None and here < printed <= nxt:
            continue
        bad.append(f'{n} (printed {printed})')
    for i, page, printed in apart:
        on_page = [nums[k] for k in range(len(flat)) if flat[k].get('_page') == page]
        after = next((nums[k] for k in range(i + 1, len(flat)) if flat[k].get('_page') != page), None)
        if not on_page or not (min(on_page) <= printed and (printed <= max(on_page) or (after is not None and printed < after))):
            bad.append(f'page {page} (printed apart {printed})')
    if bad:
        raise ValueError(f'{xml_path}: printed margin numbers disagree with the line numbers: {", ".join(bad[:10])}')


def _apply_greek_text_fixes(flat: list[dict], edition: dict | None, xml_path: Path) -> None:
    """Apply the edition's ``text_fixes`` (``ref`` + find/replace).

    Each fix names its line by ``ref`` and touches only that line, where
    ``find`` must occur exactly once. A missing ref, an absent or repeated
    ref, or a ``find`` that is not there once fails the build; a line that
    carries joined-part or speaker offsets is refused, since an edit there
    would shift them."""
    for fix in (edition or {}).get('text_fixes') or []:
        find, replace, ref = fix['find'], fix['replace'], fix.get('ref')
        if not isinstance(ref, str) or not ref:
            raise ValueError(f'{xml_path}: text_fixes find {find!r} needs a ref')
        lines = [e for e in flat if e['ref'] == ref]
        if len(lines) != 1:
            raise ValueError(f'{xml_path}: text_fixes ref {ref!r} must name exactly one line, found {len(lines)}')
        line = lines[0]
        if line['text'].count(find) != 1:
            raise ValueError(f'{xml_path}: text_fixes find {find!r} must occur exactly once on line {ref}')
        if line.get('parts') or len(line.get('speakers') or []) > 1:
            raise ValueError(f'{xml_path}: text_fixes find {find!r} sits on a joined line')
        line['text'] = line['text'].replace(find, replace)


def run(manifest: Manifest) -> Path:
    source = manifest.data['work']['greek_source']
    path = SOURCES_DIR / source['path']
    spine = parse_spine(path, manifest)
    out = BUILD_DIR / 'stage1' / 'greek_spine.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spine, ensure_ascii=False, indent=1), encoding='utf-8')
    return out
