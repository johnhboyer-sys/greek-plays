"""Counting units for the plays' search: what a search counts under each unit.

Reads the built corpus (build/dist/<play>/book-01.json and search/) directly,
not the site, so its counts are independent of the page under test.

    python3 docs/search-port/units.py build/dist > docs/search-port/units.json

Units, all derived from the built data (the corpus has no scene divisions):
- line: one printed Greek line.
- segment: the pipeline's unit, one speech capped at 40 lines (an antilabe
  can leave two speakers in one); today's search matches "and" by segment.
- speech: from one speaker label to the next. A label part-way through a
  line (antilabe) starts a speech there, so a line can belong to two; a Greek
  hit goes to the speech its word is in.
- ode: a run of chorus lines holding at least one strophe label (στρ./ἀντ./
  Str./Ant./Ep.); a run of named chorus lines with no labels counts as an ode
  at 12 lines or more. Lines with no named speaker (the edition's bare dash)
  join a chorus run. Odes split by 25 actor lines or fewer join into one.
  Chorus = a display name naming the chorus, a half-chorus, a leader, or one
  of its members. This is a rule, not a reading of each play: it misplaces
  some boundaries, and a real scene table would be made by hand.
- scene: the play cut at its odes; each stretch between two odes is a scene,
  each ode a unit of its own (prologue, parodos, episodes, stasima, exodos).

English is stored per segment, never per line or per speech. An English hit
is credited to its segment, to every speech in that segment, and to the
scene or ode of the segment's lines; there is no English count by line. For
the speech unit that is an upper bound where a segment holds more than one
speech: `and_speeches_in_shared_segments` says how many "and" speeches that
touches.
"""
import json, re, statistics, sys
from pathlib import Path

DIST = Path(sys.argv[1])
CHORUS = re.compile(r'chorus|semichorus|half-chorus|leader|coryph|elder \d|old m[ae]n \d|maiden \d|women \d', re.I)
STROPHE = re.compile(r'^(στρ|ἀντ|ἐπῳδ|μεσῳδ|ἐφυμν|Str|Ant|Ep|Mesode)', re.I)
WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")
DASH = ('—', '-', '–')

def play_units(work):
    book = json.loads((DIST / work / 'book-01.json').read_text())
    meta = json.loads((DIST / work / 'search' / 'meta.json').read_text())
    offsets = json.loads((DIST / work / 'search' / 'offsets.json').read_text())
    lines = []          # one dict per Greek line, in order
    toks = []           # per segment: [(line index, char offset)] in index order
    speaker, sp = None, -1
    for si, seg in enumerate(book['segments']):
        events = {}
        for ev in seg.get('speakers', []):
            events.setdefault(ev['line'], []).append(ev)
        seg_toks = []
        for ln in seg['greek']:
            starts = []                     # (char offset, speech id) on this line
            if not lines:                   # text before any label is a speech too
                sp += 1
            if not lines or ln['n'] not in events or min(e['offset'] for e in events[ln['n']]) > 0:
                starts.append((0, sp))      # the line opens in the running speech
            for ev in sorted(events.get(ln['n'], []), key=lambda e: e['offset']):
                sp += 1
                speaker = ev['display'] or ev['label']
                starts.append((ev['offset'], sp))
            if starts[0][0] > 0:
                starts.insert(0, (0, starts[0][1] - 1))
            i = len(lines)
            lines.append({'seg': si, 'n': ln['n'], 'ref': ln.get('ref'), 'speaker': speaker,
                          'speeches': starts, 'label': bool(ln.get('label') and STROPHE.match(ln['label']))})
            seg_toks.extend((i, t['o']) for t in ln['tokens'])
        toks.append(seg_toks)
    for si, seg in enumerate(offsets['segments']):
        expect = sum(count for _n, count in seg['line_runs'])
        if expect != len(toks[si]):
            raise SystemExit(f'{work} segment {si}: offsets.json has {expect} tokens, the book {len(toks[si])}')
    def chorusish(ln):
        return ln['speaker'] is None or ln['speaker'] in DASH or bool(CHORUS.search(ln['speaker']))
    runs, cur = [], None
    for i, ln in enumerate(lines):
        if chorusish(ln):
            if cur is None: cur = [i, i]
            else: cur[1] = i
        elif cur is not None:
            runs.append(cur); cur = None
    if cur is not None: runs.append(cur)
    def is_ode(a, b):
        span = range(a, b + 1)
        if any(lines[k]['label'] for k in span): return True
        named = all(lines[k]['speaker'] and lines[k]['speaker'] not in DASH and CHORUS.search(lines[k]['speaker']) for k in span)
        return named and b - a + 1 >= 12
    odes = []
    for a, b in (r for r in runs if is_ode(*r)):
        if odes and a - odes[-1][1] - 1 <= 25: odes[-1][1] = b
        else: odes.append([a, b])
    in_ode = {}
    for oi, (a, b) in enumerate(odes):
        for k in range(a, b + 1): in_ode[k] = oi
    sc = -1
    for i, ln in enumerate(lines):
        ode = in_ode.get(i)
        if i == 0 or ode != in_ode.get(i - 1):
            sc += 1
        ln['scene'], ln['ode'] = sc, ode
    seg_speeches = {}
    for ln in lines:
        seg_speeches.setdefault(ln['seg'], set()).update(s for _o, s in ln['speeches'])
    return {'lines': lines, 'meta': meta, 'toks': toks, 'seg_speeches': seg_speeches,
            'odes': len(odes), 'scenes': sc + 1, 'speeches': sp + 1, 'segments': len(book['segments'])}

def speech_at(ln, offset):
    owner = ln['speeches'][0][1]
    for o, s in ln['speeches']:
        if o <= offset: owner = s
    return owner

def english_counts(text, words):
    return sum(1 for w in WORD.findall(text) if w.lower().replace('’', "'") in words)

UNITS = ('line', 'segment', 'speech', 'scene', 'ode')

def seg_units(p, si):
    """The units a segment's English is credited to (no lines)."""
    L = p['lines']
    idx = [i for i, ln in enumerate(L) if ln['seg'] == si]
    return {'segment': {si}, 'speech': set(p['seg_speeches'][si]),
            'scene': {L[i]['scene'] for i in idx}, 'ode': {L[i]['ode'] for i in idx if L[i]['ode'] is not None}}

def run(searches, works):
    plays = {w: play_units(w) for w in works}
    for p in plays.values():
        p['seg_units'] = {si: seg_units(p, si) for si in range(p['segments'])}
    lengths = {u: [] for u in UNITS[1:]}
    for p in plays.values():
        sizes = {u: {} for u in UNITS[1:]}
        for ln in p['lines']:
            keys = {'segment': [ln['seg']], 'speech': {s for _o, s in ln['speeches']},
                    'scene': [ln['scene']], 'ode': [] if ln['ode'] is None else [ln['ode']]}
            for u, ks in keys.items():
                for k in ks: sizes[u][k] = sizes[u].get(k, 0) + 1
        for u in UNITS[1:]: lengths[u] += list(sizes[u].values())
    def stats(v):
        v = sorted(v)
        return {'units': len(v), 'median_lines': statistics.median(v), 'mean_lines': round(statistics.mean(v), 1),
                'p90_lines': v[int(len(v) * 0.9)], 'max_lines': v[-1]}
    total_lines = sum(len(p['lines']) for p in plays.values())
    shared = sum(1 for p in plays.values() for s in p['seg_speeches'].values() if len(s) > 1)
    out = {'plays': len(plays), 'lines': total_lines, 'segments_with_several_speeches': shared,
           'unit_lengths': {'line': {'units': total_lines, 'median_lines': 1, 'mean_lines': 1, 'p90_lines': 1, 'max_lines': 1},
                            **{u: stats(v) for u, v in lengths.items()}},
           'searches': []}
    for s in searches:
        rec = {'name': s['name'], 'greek': s.get('greek'), 'english': s.get('english'), 'units': {}}
        g_hits = e_all = e_main = 0
        sets = {u: {'g': set(), 'e': set(), 'e_main': set(), 'e_multi': set()} for u in UNITS}
        shared_and = set()
        for w, p in plays.items():
            L = p['lines']
            if s.get('greek'):
                idx = json.loads((DIST / w / 'search' / 'lemma.json').read_text())
                for si, pos in idx.get(s['greek'], []):
                    i, off = p['toks'][si][pos]
                    ln = L[i]; g_hits += 1
                    sets['line']['g'].add((w, i))
                    sets['segment']['g'].add((w, ln['seg']))
                    sets['speech']['g'].add((w, speech_at(ln, off)))
                    sets['scene']['g'].add((w, ln['scene']))
                    if ln['ode'] is not None: sets['ode']['g'].add((w, ln['ode']))
            if s.get('english'):
                tr_by_unit = {u: {} for u in UNITS[1:]}
                for si, m in enumerate(p['meta']):
                    texts = {'main': m.get('english_head') or '', **(m.get('english_slots') or {})}
                    per = {k: english_counts(t, s['english']) for k, t in texts.items()}
                    hit = {k for k, c in per.items() if c}
                    if not hit: continue
                    e_all += sum(per.values()); e_main += per['main']
                    for u, ks in p['seg_units'][si].items():
                        for k in ks:
                            sets[u]['e'].add((w, k))
                            if per['main']: sets[u]['e_main'].add((w, k))
                            tr_by_unit[u].setdefault(k, set()).update(hit)
                for u in UNITS[1:]:
                    sets[u]['e_multi'] |= {(w, k) for k, v in tr_by_unit[u].items() if len(v) > 1}
                if s.get('greek'):
                    for si, ks in p['seg_speeches'].items():
                        if len(ks) > 1: shared_and |= {(w, k) for k in ks}
        for u, d in sets.items():
            r = {'with_greek': len(d['g'])}
            if s.get('english') and u != 'line':
                r.update({'with_english_any_translation': len(d['e']), 'with_english_main_translation': len(d['e_main']),
                          'with_english_in_more_than_one': len(d['e_multi'])})
                if s.get('greek'):
                    r.update({'both_and': len(d['g'] & d['e']), 'greek_only': len(d['g'] - d['e']),
                              'english_only': len(d['e'] - d['g']), 'either_or': len(d['g'] | d['e'])})
            if s.get('english') and u == 'line':
                r['note'] = 'English is stored per segment, not per line: no English or "and" count by line'
            rec['units'][u] = r
        if s.get('english') and s.get('greek'):
            rec['units']['speech']['and_speeches_in_shared_segments'] = len(sets['speech']['g'] & sets['speech']['e'] & shared_and)
        rec['greek_word_hits'] = g_hits
        if s.get('english'):
            rec['english_word_hits_every_translation'] = e_all
            rec['english_word_hits_main_translation'] = e_main
        out['searches'].append(rec)
    return out

if __name__ == '__main__':
    works = sorted(p.parent.name for p in DIST.glob('*/book-01.json'))
    searches = [
        {'name': 'δίκη (lemma)', 'greek': 'dikh'},
        {'name': 'justice (English, with "justices")', 'english': {'justice', 'justices'}},
        {'name': 'δίκη (lemma) and justice', 'greek': 'dikh', 'english': {'justice', 'justices'}},
        {'name': 'θεός (lemma)', 'greek': 'qeos'},
    ]
    res = run(searches, works)
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1, default=sorted)
    print()
