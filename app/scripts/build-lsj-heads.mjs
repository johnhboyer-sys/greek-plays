// Build-time manifest: LSJ key → { head, hom }.
//
// Ported from aristotle-reader/app/scripts/build-lsj-heads.mjs (2026-09-05).
// The word popup shows one card per dictionary entry, and each card needs two
// things about that entry before the reader taps anything: the Unicode headword
// (so key `ei)mi/` displays as εἰμί) and LSJ's own homograph letter (the (A) in
// "δέω (A)"). Nothing else — the entry TEXT is served by grammata's T8 lookup
// (John, 2026-09-05: Grammata T8 for ALL LSJ on the site), keyed, at roughly
// 8 KB a tap. The website fetches no LSJ shards; this manifest is the only
// LSJ-derived file it reads.
//
// Emits public/data/lsj-heads.json.
// Run: node scripts/build-lsj-heads.mjs   (from app/)
//
// Zero-works rule (this repo): with no analyses.json under public/data the
// script writes an EMPTY manifest and exits 0, so the zero-works build gate
// (CLAUDE.md) stays green. With works present it keeps aristotle's fail-closed
// posture: a key any analysis names that has no shard entry refuses the write.

import { readFileSync, writeFileSync, readdirSync, existsSync, statSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const DATA = 'public/data';
const OUT = join(DATA, 'lsj-heads.json');

// ── every LSJ key any analysis names ────────────────────────────────────────
// Keyed on what the reader can actually ask for, not on what the dictionary
// holds: an entry no analysis points at can never surface in a card.
const wanted = new Set();
let works = 0;
if (existsSync(DATA)) {
  for (const d of readdirSync(DATA, { withFileTypes: true })) {
    if (!d.isDirectory()) continue;
    const f = join(DATA, d.name, 'analyses.json');
    if (!existsSync(f)) continue;
    works++;
    const analyses = JSON.parse(readFileSync(f, 'utf8'));
    for (const token of Object.values(analyses)) {
      for (const a of token) for (const k of a.lsj ?? []) wanted.add(k);
    }
  }
}

if (works === 0) {
  mkdirSync(DATA, { recursive: true });
  writeFileSync(OUT, '{}');
  console.log('lsj-heads: no analyses.json under ' + DATA + ' (zero works) — wrote an empty manifest.');
  process.exit(0);
}

// ── read the head and the homograph letter out of the shards ────────────────
// LSJ marks its own homographs in the entry text — "νέω (A)", "νέω (B)". Read
// that letter; never derive one from the key's trailing digit. ka/r2 is LSJ's
// (A) and li^to/s2 likewise, so the digit disagrees on six entries, and 32% of
// numbered keys carry no letter at all — those get none rather than an
// invention.
const HOM = /^\s*\S+\s*\(([A-Z])\)/;

const out = {};
let missing = 0;
const shardDir = join(DATA, 'lsj');
if (!existsSync(shardDir)) {
  console.error('lsj-heads: ' + shardDir + ' is missing — run the pipeline (stage5) first.');
  process.exit(1);
}
for (const f of readdirSync(shardDir)) {
  if (!f.endsWith('.json')) continue;
  const shard = JSON.parse(readFileSync(join(shardDir, f), 'utf8'));
  for (const [key, entry] of Object.entries(shard)) {
    if (!wanted.has(key)) continue;
    const rec = { head: entry.head };
    const m = HOM.exec(String(entry.html ?? '').replace(/<[^>]+>/g, ''));
    if (m) rec.hom = m[1];
    out[key] = rec;
  }
}
for (const k of wanted) if (!out[k]) missing++;

// Refuse to write a manifest with holes: a key with no shard entry means the
// popup falls back to transliterating the lemma for that word, which looks
// like a headword bug somewhere else entirely.
if (missing > 0) {
  console.error(
    `lsj-heads: ${missing} of ${wanted.size} keys had no shard entry — refusing to ` +
    'write an incomplete manifest. Rebuild the LSJ shards first.',
  );
  process.exit(1);
}

writeFileSync(OUT, JSON.stringify(out));
const kb = (statSync(OUT).size / 1024).toFixed(0);
const withHom = Object.values(out).filter(r => r.hom).length;
console.log(
  `lsj-heads: ${Object.keys(out).length} entries from ${works} works ` +
  `(${withHom} with a homograph letter) — ${kb} KB`,
);
