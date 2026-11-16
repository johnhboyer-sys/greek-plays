"""Sort the hunks of diff(plays, aristotle origin/main) three ways, against the
plays' fork point (classical-philosophy-reader @ 233ec2547a) as the base.

port = only Aristotle's side differs from the base; keep = only the plays' side
does; both = both sides changed lines in the hunk. Prints JSON."""
import difflib, json, subprocess, sys, os
PLAYS = sys.argv[1]
AR = os.path.expanduser('~/Developer/aristotle-reader')
CPR = os.path.expanduser('~/Developer/classical-philosophy-reader')
BASE, AR_OLD, AR_NEW = '233ec2547a', '6941109fb7', 'de57f687c6'
def show(repo, rev, path):
    r = subprocess.run(['git', '-C', repo, 'show', f'{rev}:{path}'], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else None
def base_equal(base, other):
    sm = difflib.SequenceMatcher(None, base, other, autojunk=False)
    eq = set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal': eq.update(range(j1, j2))
    return eq
out = []
for spec in sys.argv[2:]:
    # path[::base[::plays_file]]; base is cpr (the fork) or an aristotle-reader sha
    path, basespec, pfile = (spec.split('::') + ['', ''])[:3]
    pfile = pfile or os.path.join(PLAYS, path)
    plays = open(pfile).read().splitlines() if os.path.exists(pfile) else None
    new = show(AR, 'origin/main', path); old = show(AR, AR_OLD, path)
    base = show(AR, basespec, path) if basespec and basespec != 'cpr' else show(CPR, BASE, path)
    rec = {'file': path, 'base_rev': basespec or 'cpr:' + BASE, 'plays_file': os.path.relpath(pfile, PLAYS), 'plays': len(plays) if plays else None, 'aristotle': len(new) if new else None,
           'base': len(base) if base else None, 'aristotle_before_redesign': len(old) if old else None}
    if plays is None or new is None:
        out.append(rec); continue
    pe = base_equal(base or [], plays); ae = base_equal(base or [], new)
    sm = difflib.SequenceMatcher(None, plays, new, autojunk=False)
    hunks = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal': continue
        pnew = any(i not in pe for i in range(i1, i2)); anew = any(j not in ae for j in range(j1, j2))
        if i1 == i2: cls = 'port' if anew else 'keep'
        elif j1 == j2: cls = 'keep' if pnew else 'port'
        elif pnew and anew: cls = 'both'
        elif anew: cls = 'port'
        elif pnew: cls = 'keep'
        else: cls = 'both'
        first = next((l.strip() for l in (plays[i1:i2] or new[j1:j2]) if l.strip()), '')
        hunks.append({'cls': cls, 'plays': [i1 + 1, i2], 'aristotle': [j1 + 1, j2], 'pl': i2 - i1, 'al': j2 - j1, 'first': first[:90]})
    rec['identical'] = not hunks
    for c in ('port', 'keep', 'both'):
        hs = [h for h in hunks if h['cls'] == c]
        rec[c] = {'hunks': len(hs), 'plays_lines': sum(h['pl'] for h in hs), 'aristotle_lines': sum(h['al'] for h in hs)}
    rec['same_lines'] = sum(t[2] for t in sm.get_matching_blocks())
    rec['hunk_list'] = hunks
    out.append(rec)
json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
