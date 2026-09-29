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
        tag = etree.QName(node).localname if isinstance(node.tag, str) else ''
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
    raw = re.sub(r'([,;])(?=[\u0370-\u03ff\u1f00-\u1fff])', r'\1 ', raw)
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
    if xml_path.parent.name == 'perseus':
        sums = xml_path.parent / 'SHA256SUMS'
        expected = next((row.split()[0] for row in sums.read_text().splitlines() if row.split()[-1] == xml_path.name), None)
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
    for el in body.iter():
        if not isinstance(el.tag, str) or etree.QName(el).localname != 'l':
            continue
        if el.get('style') == 'hidden' or el.get('n') == '0':
            continue
        raw = el.get('n')
        if not raw:
            raise ValueError(f'{xml_path}: visible play <l> has no @n')
        margin = el.get('rend') or ''
        if margin.startswith('margin-') and margin[7:] != raw:
            raise ValueError(f'{xml_path}: margin number {margin[7:]!r} differs from line {raw!r}')
        if raw in fixes:
            fix_hits[raw] += 1
        ref = _normalize_play_lineref(raw, xml_path, fixes)
        scheme.play_line_kind(ref)
        sp = next((a for a in el.iterancestors() if isinstance(a.tag, str) and etree.QName(a).localname == 'sp'), None)
        speaker = sp.find('{*}speaker') if sp is not None else None
        label = ' '.join(''.join(speaker.itertext()).split()) if speaker is not None else None
        text = _text(el)
        part = el.get('part')
        if part in {'F', 'M'}:
            if not flat:
                raise ValueError(f'{xml_path}: orphan joined part {ref}')
            previous = flat[-1]
            offset = len(previous['text']) + (1 if previous['text'] and text else 0)
            previous['text'] += (' ' if previous['text'] and text else '') + text
            previous['joined'] = True
            previous.setdefault('parts', []).append({'ref': ref, 'offset': offset})
            if label and (not previous.get('_sp') is sp):
                previous.setdefault('speakers', []).append({'offset': offset, 'label': label})
            continue
        counts[ref] += 1
        if counts[ref] > 1 and ref not in repeats:
            raise ValueError(f'{xml_path}: undeclared repeated ref {ref}')
        entry = {'ref': ref, 'text': text, '_sp': sp}
        if label and (not flat or flat[-1].get('_sp') is not sp):
            entry['speakers'] = [{'offset': 0, 'label': label}]
        mark = _strophe_label(el)
        if mark:
            entry['label'] = mark
        if len(el) == 1 and etree.QName(el[0]).localname == 'gap' and el[0].get('reason') == 'lost' and not (el.text or '').strip() and not (el[0].tail or '').strip():
            entry['role'] = 'lacuna'
            entry['text'] = ''
        flat.append(entry)
    if {k: fix_hits[k] for k in fixes if fix_hits[k] != 1}:
        raise ValueError(f'{xml_path}: stale citation.ref_fixes')
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
    _rejoin_play_line_hyphens(flat)
    marks = _english_line_marks(manifest)
    segments = _segment_play_lines(flat, *(marks or (None, None)))
    # Keep lettered part anchors on the joined line for later alignment.
    part_map = {e['ref']: e['parts'] for e in flat if e.get('parts')}
    for seg in segments:
        for line in seg['lines']:
            if line['ref'] in part_map:
                line['parts'] = part_map[line['ref']]
    return {'work': manifest.work_id, 'edition': manifest.data['work']['greek_edition'],
            'segments': segments, 'headings': [], 'unassigned_lines': []}


def run(manifest: Manifest) -> Path:
    source = manifest.data['work']['greek_source']
    path = SOURCES_DIR / source['path']
    spine = parse_spine(path, manifest)
    out = BUILD_DIR / 'stage1' / 'greek_spine.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spine, ensure_ascii=False, indent=1), encoding='utf-8')
    return out
