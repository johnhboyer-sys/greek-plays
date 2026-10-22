// Stage 1: proper-name lemmas in the drama corpus vs Grammata T8.
// node scripts/sweeps/proper-names-t8.mjs build/dist <dir with Grammata's grc-analyses, grc-lsj-t8, grc-lsj .idx.json + .pack> <out.json>
// Packs: https://pub-d505f3fd993b4e01b2ab095428d0493e.r2.dev/wordtool/<name>.{idx.json,pack} (the base lookup.js reads).
import fs from 'node:fs';
import zlib from 'node:zlib';
import { betaToGreek } from '../../shared/lib/betacode.ts';

const [DIST, T8, OUT] = process.argv.slice(2);

// --- T8 packs, mirrored from lookup.js (P / Z / Bt / I / ut) ---
const packs = {};
function bucket(name, b) {
  const p = (packs[name] ??= { idx: JSON.parse(fs.readFileSync(`${T8}/${name}.idx.json`)), buf: fs.readFileSync(`${T8}/${name}.pack`), cache: new Map() });
  if (!p.cache.has(b)) {
    const span = p.idx.buckets[b];
    p.cache.set(b, span ? JSON.parse(zlib.gunzipSync(p.buf.subarray(span[0], span[0] + span[1]))) : null);
  }
  return p.cache.get(b);
}
const MAP = { α:'a',β:'b',γ:'g',δ:'d',ε:'e',ζ:'z',η:'h',θ:'q',ι:'i',κ:'k',λ:'l',μ:'m',ν:'n',ξ:'c',ο:'o',π:'p',ρ:'r',σ:'s',ς:'s',τ:'t',υ:'u',φ:'f',χ:'x',ψ:'y',ω:'w',ϝ:'v' };
const strip = (t) => { let e = ''; for (const n of t.normalize('NFD').toLowerCase()) MAP[n] ? (e += MAP[n]) : /[a-z]/.test(n) && (e += n); return e; };
const B = (t) => (t.length >= 2 ? t.slice(0, 2) : t.length === 1 ? t : '_');
// I(): a T8 entry under the key, else the older grc-lsj HTML entry.
function renderKeys(keys) {
  let n = 0;
  for (const k of keys) {
    const u = strip(k), m = B(u);
    const t8 = (bucket('grc-lsj-t8', m)?.[u] ?? []).filter((g) => g.key === k);
    n += t8.length || (bucket('grc-lsj', m)?.[u] ?? []).filter((g) => g.key === k).length;
  }
  return n;
}
// ut() with no key (headwordFirst false): Grammata's form index first; if it
// knows the form, only its dictionary keys count. Else an exact T8 headword.
function lookupWord(word) {
  const s = strip(word);
  if (!s) return { found: false, via: 'empty' };
  const an = bucket('grc-analyses', B(s))?.[s];
  if (an && Object.keys(an).length) {
    const keys = new Set();
    for (const rows of Object.values(an)) for (const [, dk] of rows) for (const k of dk) keys.add(k);
    return renderKeys([...keys]) ? { found: true, via: 'grammata-form-index', keys: [...keys] } : { found: false, via: 'form-index-no-entry' };
  }
  const heads = bucket('grc-lsj-t8', B(s))?.[s] ?? [];
  const exact = /[̀-ͯ]/.test(word.normalize('NFD')) ? heads.filter((h) => h.head.normalize('NFC') === word.normalize('NFC')) : heads;
  if (exact.length) return { found: true, via: 'headword', keys: exact.map((h) => h.key) };
  return { found: false, via: heads.length ? 'headword-differs' : 'not-in-grammata', near: heads.map((h) => h.head) };
}

// --- corpus ---
const surfaceCap = (t) => { const c = t.normalize('NFD').replace(/^[^\p{L}]+/u, '')[0]; return !!c && c !== c.toLowerCase(); };
const cap1 = (g) => { const d = g.normalize('NFD'); return (d[0].toUpperCase() + d.slice(1)).normalize('NFC'); };
const works = fs.readdirSync(DIST).filter((w) => fs.existsSync(`${DIST}/${w}/analyses.json`));
function* tokensOf(dir) {
  const an = JSON.parse(fs.readFileSync(`${dir}/analyses.json`));
  for (const f of fs.readdirSync(dir).filter((f) => /^book-\d+\.json$/.test(f)))
    for (const seg of JSON.parse(fs.readFileSync(`${dir}/${f}`)).segments)
      for (const line of seg.greek ?? []) for (const tok of line.tokens ?? []) if (tok.k) yield { tok, line, as: an[tok.k] ?? [] };
}

// Pass 0. A lowercase lemma is a name when the edition prints it capitalised
// in >= 80% of at least 3 occurrences AND Grammata's form index lists the
// capitalised word itself as a lemma (Ὀρέστης, Φοῖβος). Otherwise a
// capitalised word filed under a common word (Ζεῦ under ζέω) is a wrong lemma.
const lowStats = new Map();
for (const w of works) for (const { tok, as } of tokensOf(`${DIST}/${w}`))
  for (const l of new Set(as.map((a) => a.lemma))) if (!l.startsWith('*')) {
    const st = lowStats.get(l) ?? { n: 0, cap: 0, forms: new Map() };
    st.n++;
    if (surfaceCap(tok.t)) { st.cap++; st.forms.set(tok.t, (st.forms.get(tok.t) ?? 0) + 1); }
    lowStats.set(l, st);
  }
const lowNames = new Set(), wrongLemma = [];
for (const [l, st] of lowStats) if (st.n >= 3 && st.cap / st.n >= 0.8) {
  const g = betaToGreek(l.replace(/\d+$/, '')), s = strip(g);
  const an = bucket('grc-analyses', B(s))?.[s] ?? {};
  if (Object.values(an).some((rows) => rows.some((r) => r[0].normalize('NFC') === cap1(g)))) lowNames.add(l);
  else {
    // What does Grammata make of the commonest printed form?
    const forms = [...st.forms].sort((a, b) => b[1] - a[1]).slice(0, 5);
    const top = forms[0][0].replace(/[^\p{L}\p{M}]/gu, ''), ts = strip(top);
    const gl = [...new Set(Object.entries(bucket('grc-analyses', B(ts))?.[ts] ?? {}).filter(([f]) => f.normalize('NFC') === top.normalize('NFC')).flatMap(([, rows]) => rows.map((r) => r[0])))];
    const same = gl.some((x) => x.normalize('NFD').toLowerCase().normalize('NFC') === g.normalize('NFC'));
    wrongLemma.push({ lemma: l, greek: g, n: st.n, cap: st.cap, forms, grammataLemmas: gl, kind: same ? 'name-filed-lowercase' : 'other-word' });
  }
}
const isName = (l) => l.startsWith('*') || lowNames.has(l);

// Pass 1. Count name tokens in the default Greek text; other Greek editions
// (ed/*) add lemmas and citations but not counts.
const lemmas = new Map();
const rec = (l) => lemmas.get(l) ?? lemmas.set(l, { lemma: l, greek: betaToGreek(l), lowerLemma: !l.startsWith('*'), count: 0, nameOnly: 0, lowerSurface: 0, edOnly: 0, glosses: new Set(), lsj: new Set(), cites: [], edCites: [], plays: new Set() }).get(l);
let tokens = 0, nameTokens = 0;
for (const w of works) {
  const dirs = [[`${DIST}/${w}`, '']];
  if (fs.existsSync(`${DIST}/${w}/ed`)) for (const e of fs.readdirSync(`${DIST}/${w}/ed`)) if (fs.existsSync(`${DIST}/${w}/ed/${e}/analyses.json`)) dirs.push([`${DIST}/${w}/ed/${e}`, e]);
  for (const [dir, ed] of dirs) for (const { tok, line, as } of tokensOf(dir)) {
    if (!ed) tokens++;
    const names = [...new Set(as.filter((a) => isName(a.lemma)).map((a) => a.lemma))];
    if (!names.length) continue;
    if (!ed) nameTokens++;
    const only = as.every((a) => isName(a.lemma));
    for (const l of names) {
      const r = rec(l);
      for (const a of as) if (a.lemma === l) { if (a.gloss) r.glosses.add(a.gloss); for (const k of a.lsj ?? []) r.lsj.add(k); }
      if (ed) { r.edOnly++; r.edCites.push(`${w}/${ed} ${line.ref ?? line.n}`); continue; }
      r.count++; if (only) r.nameOnly++; if (!surfaceCap(tok.t)) r.lowerSurface++;
      r.plays.add(w); r.cites.push(`${w} ${line.ref ?? line.n}`);
    }
  }
}

// Resolve each lemma the way WordPopup does: a card per LSJ key when the
// analysis has keys (lookup('', el, { key })), else lookup(betaToGreek(lemma)).
const heads = JSON.parse(fs.readFileSync(`${DIST}/lsj-heads.json`));
const rows = [];
for (const r of lemmas.values()) {
  let res;
  if (r.lsj.size) {
    const keys = [...r.lsj];
    res = renderKeys(keys) ? { found: true, via: 'site-lsj-key', keys } : { found: false, via: 'site-lsj-key-no-entry', keys };
    res.inHeads = keys.every((k) => heads[k]);
  } else res = lookupWord(r.greek);
  rows.push({ ...r, ...res, glosses: [...r.glosses], lsj: [...r.lsj], plays: [...r.plays] });
}
rows.sort((a, b) => b.count - a.count || b.edOnly - a.edOnly || a.greek.localeCompare(b.greek));
fs.writeFileSync(OUT, JSON.stringify({ tokens, nameTokens, lowNames: [...lowNames], wrongLemma: wrongLemma.sort((a, b) => b.n - a.n), rows }, null, 1));
const f = rows.filter((r) => r.found), m = rows.filter((r) => !r.found);
console.log({ works: works.length, tokens, nameTokens, lemmas: rows.length, found: f.length, missed: m.length,
  foundOcc: f.reduce((s, r) => s + r.count, 0), missedOcc: m.reduce((s, r) => s + r.count, 0),
  lowNames: lowNames.size, wrongLemma: wrongLemma.length, edOnlyLemmas: rows.filter((r) => !r.count).length,
  via: rows.reduce((o, r) => ((o[r.via] = (o[r.via] ?? 0) + 1), o), {}) });
