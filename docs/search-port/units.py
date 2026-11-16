"""Counting units for the plays' search: what a search counts under each unit.

Reads the built corpus (build/dist/<play>/book-01.json and search/) directly,
not the site, so its counts are independent of the page under test.

    python3 docs/search-port/units.py build/dist > docs/search-port/units.json

Units, all derived from the built data (the corpus has no scene divisions):
- line: one printed Greek line.
- segment: the pipeline's unit, one speech capped at 40 lines; today's search
  matches "and" by segment.
- speech: consecutive lines of one speaker (a speaker label starts a new one).
- ode: a run of chorus lines holding at least one strophe label (στρ./ἀντ./
  Str./Ant./Ep.); a run of named chorus lines with no labels counts as an ode
  at 12 lines or more. Lines with no named speaker (the edition's bare dash)
  join a chorus run. Odes split by 25 actor lines or fewer join into one.
  Chorus = a display name naming the chorus, a half-chorus, a leader, or one
  of its members. This is a rule, not a reading of each play: it misplaces
  some boundaries, and a real scene table would be made by hand.
- scene: the play cut at its odes; each stretch between two odes is a scene,
  each ode a unit of its own (prologue, parodos, episodes, stasima, exodos).
English is attached to segments, never to lines, so an English hit falls in
a segment, a speech, a scene or an ode, but not in a line.
"""
import json, re, statistics, sys
from pathlib import Path

DIST = Path(sys.argv[1])
CHORUS = re.compile(r'chorus|semichorus|half-chorus|leader|coryph|elder \d|old m[ae]n \d|maiden \d|women \d', re.I)
STROPHE = re.compile(r'^(στρ|ἀντ|ἐπῳδ|μεσῳδ|ἐφυμν|Str|Ant|Ep|Mesode)', re.I)
WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")

def play_units(work):
    book = json.loads((DIST / work / 'book-01.json').read_text())
    meta = json.loads((DIST / work / 'search' / 'meta.json').read_text())
    offsets = json.loads((DIST / work / 'search' / 'offsets.json').read_text())
    lines = []          # one dict per Greek line, in order
    speaker = None
    for si, seg in enumerate(book['segments']):
        events = {}
        for ev in seg.get('speakers', []):
            events.setdefault(ev['line'], []).append(ev)
        for ln in seg['greek']:
            new = ln['n'] in events
            if new:
                speaker = events[ln['n']][-1]['display'] or events[ln['n']][-1]['label']
            lines.append({'seg': si, 'n': ln['n'], 'ref': ln.get('ref'), 'speaker': speaker, 'new_speech': new,
                          'label': bool(ln.get('label') and STROPHE.match(ln['label']))})
    # speeches
    sp = -1
    for i, ln in enumerate(lines):
        if i == 0 or ln['new_speech'] or ln['speaker'] != lines[i - 1]['speaker']:
            sp += 1
        ln['speech'] = sp
    # chorus runs -> odes. A line with no named speaker (the edition's bare
    # dash) joins a chorus run, but such a run is an ode only if it holds a
    # strophe label; a run of named chorus lines with no labels is an ode at
    # 12 lines or more. Odes split by an actor passage of 25 lines or fewer
    # join into one lyric stretch (a kommos, an epirrhematic exchange).
    def chorusish(ln):
        return ln['speaker'] is None or ln['speaker'] in ('—', '-', '–') or bool(CHORUS.search(ln['speaker']))
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
        named = all(lines[k]['speaker'] and CHORUS.search(lines[k]['speaker']) for k in span)
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
        prev = in_ode.get(i - 1) if i else 'start'
        if i == 0 or ode != prev:
            sc += 1
        ln['scene'] = sc
        ln['ode'] = ode
    # token position -> line index, per segment
    seg_first = {}
    for i, ln in enumerate(lines):
        seg_first.setdefault(ln['seg'], i)
    tok_line = []
    for si, seg in enumerate(offsets['segments']):
        m, k = [], seg_first.get(si)
        for j, (_n, count) in enumerate(seg['line_runs']):
            m.extend([k + j] * count)
        tok_line.append(m)
    return {'lines': lines, 'meta': meta, 'tok_line': tok_line, 'odes': len(odes),
            'scenes': sc + 1, 'speeches': sp + 1, 'segments': len(book['segments'])}

def english_counts(text, words):
    return sum(1 for w in WORD.findall(text) if w.lower().replace('’', "'") in words)

def run(searches, works):
    plays = {w: play_units(w) for w in works}
    lengths = {u: [] for u in ('segment', 'speech', 'scene', 'ode')}
    for p in plays.values():
        L = p['lines']
        for unit in ('segment', 'speech', 'scene'):
            key = 'seg' if unit == 'segment' else unit
            sizes = {}
            for ln in L: sizes[ln[key]] = sizes.get(ln[key], 0) + 1
            lengths[unit] += list(sizes.values())
        sizes = {}
        for ln in L:
            if ln['ode'] is not None: sizes[ln['ode']] = sizes.get(ln['ode'], 0) + 1
        lengths['ode'] += list(sizes.values())
    def stats(v):
        v = sorted(v)
        return {'units': len(v), 'median_lines': statistics.median(v), 'mean_lines': round(statistics.mean(v), 1),
                'p90_lines': v[int(len(v) * 0.9)], 'max_lines': v[-1]}
    total_lines = sum(len(p['lines']) for p in plays.values())
    out = {'plays': len(plays), 'lines': total_lines,
           'unit_lengths': {'line': {'units': total_lines, 'median_lines': 1, 'mean_lines': 1, 'p90_lines': 1, 'max_lines': 1},
                            **{u: stats(v) for u, v in lengths.items()}},
           'searches': []}
    for s in searches:
        rec = {'name': s['name'], 'greek': s.get('greek'), 'english': s.get('english'), 'units': {}}
        g_hits = 0
        e_hits_all = e_hits_main = 0
        sets = {u: {'g': set(), 'e': set(), 'e_main': set(), 'e_multi': set()} for u in ('line', 'segment', 'speech', 'scene', 'ode')}
        for w, p in plays.items():
            L = p['lines']
            if s.get('greek'):
                idx = json.loads((DIST / w / 'search' / 'lemma.json').read_text())
                for si, pos in idx.get(s['greek'], []):
                    i = p['tok_line'][si][pos]
                    g_hits += 1
                    ln = L[i]
                    for u, key in (('line', None), ('segment', 'seg'), ('speech', 'speech'), ('scene', 'scene')):
                        sets[u]['g'].add((w, i if key is None else ln[key]))
                    if ln['ode'] is not None: sets['ode']['g'].add((w, ln['ode']))
            if s.get('english'):
                first = {}
                for i, ln in enumerate(L): first.setdefault(ln['seg'], i)
                for si, m in enumerate(p['meta']):
                    texts = {'main': m.get('english_head') or '', **(m.get('english_slots') or {})}
                    per = {k: english_counts(t, s['english']) for k, t in texts.items()}
                    hit = [k for k, c in per.items() if c]
                    if not hit: continue
                    e_hits_all += sum(per.values()); e_hits_main += per['main']
                    ln = L[first[si]]
                    for u, key in (('segment', 'seg'), ('speech', 'speech'), ('scene', 'scene')):
                        unit = (w, ln[key])
                        sets[u]['e'].add(unit)
                        if per['main']: sets[u]['e_main'].add(unit)
                    if ln['ode'] is not None:
                        sets['ode']['e'].add((w, ln['ode']))
                        if per['main']: sets['ode']['e_main'].add((w, ln['ode']))
            # more than one translation in a unit
        if s.get('english'):
            for u in ('segment', 'speech', 'scene', 'ode'):
                key = {'segment': 'seg', 'speech': 'speech', 'scene': 'scene', 'ode': 'ode'}[u]
                for w, p in plays.items():
                    L = p['lines']; first = {}
                    for i, ln in enumerate(L): first.setdefault(ln['seg'], i)
                    tr_by_unit = {}
                    for si, m in enumerate(p['meta']):
                        texts = {'main': m.get('english_head') or '', **(m.get('english_slots') or {})}
                        unit = L[first[si]][key]
                        if unit is None: continue
                        for k, t in texts.items():
                            if english_counts(t, s['english']): tr_by_unit.setdefault(unit, set()).add(k)
                    sets[u]['e_multi'] |= {(w, k) for k, v in tr_by_unit.items() if len(v) > 1}
        for u, d in sets.items():
            r = {'with_greek': len(d['g'])}
            if s.get('english'):
                r.update({'with_english_any_translation': len(d['e']), 'with_english_main_translation': len(d['e_main']),
                          'with_english_in_more_than_one': len(d['e_multi'])})
                if s.get('greek'):
                    r.update({'both_and': len(d['g'] & d['e']), 'greek_only': len(d['g'] - d['e']),
                              'english_only': len(d['e'] - d['g']), 'either_or': len(d['g'] | d['e'])})
            rec['units'][u] = r
        if s.get('english'):
            rec['units']['line'] = {'with_greek': len(sets['line']['g']),
                                    'note': 'English is attached to segments, not lines: no English or "and" count by line'}
        rec['greek_word_hits'] = g_hits
        if s.get('english'):
            rec['english_word_hits_every_translation'] = e_hits_all
            rec['english_word_hits_main_translation'] = e_hits_main
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
    for s in res['searches']:
        if isinstance(s.get('english'), set): s['english'] = sorted(s['english'])
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1, default=sorted)
    print()
