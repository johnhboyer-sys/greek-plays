import { readFile, mkdir, writeFile, access } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { realpathSync } from 'node:fs';
import { repo, parseArgs, writeTsv } from './lib.mjs';
import { loadYaml } from '../lib/load-yaml.mjs';

// Port of shared/components/Reader.svelte:2097-2131 (playOdeIds,
// siglumStem, isChorusEvent, playOde). Keep the last nonempty speaker set.
export function odeIds(segments) {
  const ids = new Set();
  let held = [];
  for (const seg of segments) {
    const own = seg.speakers ?? [];
    if (own.length) held = own;
    const events = own.length ? own : held;
    if (seg.greek.length > 6 && events.length && events.every(isChorusEvent)) ids.add(seg.id);
  }
  return ids;
}
function isChorusEvent(event) {
  const stem = (event.label ?? '').toUpperCase().normalize('NFD').replace(/\p{M}/gu, '');
  if (stem.startsWith('ΧΟ') || stem.startsWith('ΗΜΙΧ') || stem.startsWith('ΒΑΤΡΑΧ')) return true;
  if (stem.startsWith('ΒΑ') && /^frogs$/i.test((event.display ?? '').trim())) return true;
  return /chorus/i.test(event.display ?? '');
}

// WordPopup.svelte:101-108 uses each raw analysis.lsj key as heads[key].
// lsj-heads.json is a map of these keys to {head, hom?} metadata.
export function classify(tokenKey, analyses, heads) {
  const parses = analyses[tokenKey];
  if (!Array.isArray(parses) || !parses.length) return 'no-analysis';
  const keys = parses.flatMap(parse => Array.isArray(parse.lsj) ? parse.lsj : []).filter(Boolean);
  if (!keys.length) return 'no-lsj';
  return keys.some(key => Object.hasOwn(heads, key)) ? 'ok' : 'lsj-unknown';
}
const kinds = ['ok', 'no-analysis', 'no-lsj', 'lsj-unknown'];
function cell(author, play, measure) {
  return { author, play, measure, total:0, ok:0, 'no-analysis':0, 'no-lsj':0, 'lsj-unknown':0 };
}
function finishCell(row) {
  return { ...row, non_ok:row.total-row.ok, non_ok_rate:row.total ? (row.total-row.ok)/row.total : 0,
    severity:row.total && (row.total-row.ok)/row.total > .1 ? 'fail' : 'info' };
}
export async function run(args = parseArgs()) {
  const yaml = await loadYaml();
  const data = join(args.dist, 'data');
  const heads = JSON.parse(await readFile(join(data, 'lsj-heads.json'), 'utf8'));
  const authorCells = new Map(), playCells = [], missing = new Map();
  const { readdir } = await import('node:fs/promises');
  const candidates = (await readdir(data, { withFileTypes:true })).filter(e => e.isDirectory()).map(e => e.name).sort();
  const plays = [];
  for (const name of candidates) { try { await access(join(data,name,'book-01.json')); plays.push(name); } catch(e) { if (e.code !== 'ENOENT') throw e; } }
  for (const play of plays) {
    const manifest = yaml.load(await readFile(join(repo, 'manifests', `${play}.yaml`), 'utf8'));
    const author = manifest.work.author;
    const book = JSON.parse(await readFile(join(data, play, 'book-01.json'), 'utf8'));
    const analyses = JSON.parse(await readFile(join(data, play, 'analyses.json'), 'utf8'));
    const odes = odeIds(book.segments);
    const byMeasure = new Map(['ode','dialogue'].map(m => [m,cell(author,play,m)]));
    for (const seg of book.segments) {
      const measure = odes.has(seg.id) ? 'ode' : 'dialogue';
      const row = byMeasure.get(measure);
      const aKey = `${author}:${measure}`;
      if (!authorCells.has(aKey)) authorCells.set(aKey,cell(author,'ALL',measure));
      const authorRow = authorCells.get(aKey);
      for (const line of seg.greek) for (const token of line.tokens ?? []) {
        const kind = classify(token.k, analyses, heads);
        for (const target of [row,authorRow]) { target.total++; target[kind]++; }
        if (kind !== 'ok' && measure === 'ode') {
          const surface = token.t ?? line.text.slice(token.o).match(/^\S+/u)?.[0] ?? token.k;
          const key = `${author}\0${surface}`;
          missing.set(key,(missing.get(key) ?? 0)+1);
        }
      }
    }
    playCells.push(...[...byMeasure.values()].map(finishCell));
  }
  const authorRows = [...authorCells.values()].map(finishCell).sort((a,b) => a.author.localeCompare(b.author) || a.measure.localeCompare(b.measure));
  const topMissing = [...new Set(authorRows.map(r=>r.author))].flatMap(author =>
    [...missing].filter(([key])=>key.startsWith(`${author}\0`)).map(([key,count])=>({author,measure:'ode',surface:key.split('\0')[1],count}))
      .sort((a,b)=>b.count-a.count || a.surface.localeCompare(b.surface)).slice(0,40));
  await mkdir(args.out,{recursive:true});
  await writeFile(join(args.out,'s7a-analysis-coverage.json'),JSON.stringify({author:authorRows,play:playCells,top_missing_ode:topMissing},null,2)+'\n');
  await writeTsv(join(args.out,'s7a-analysis-coverage-author.tsv'),authorRows);
  await writeTsv(join(args.out,'s7a-analysis-coverage-play.tsv'),playCells);
  await writeTsv(join(args.out,'s7a-analysis-coverage-top-missing-ode.tsv'),topMissing);
  for (const r of authorRows) console.log(`s7a ${r.author} ${r.measure}: ${r.non_ok}/${r.total} ${(100*r.non_ok_rate).toFixed(2)}%`);
  return { author:authorRows, play:playCells, topMissing };
}
if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) await run();
