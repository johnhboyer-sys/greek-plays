// Compare each English translation with the other translations of its play.
import { readdir, readFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const WINDOW = 10;
export const MARGIN_THRESHOLD = 0.34;
export const ROW_THRESHOLD = 0.1;
export const RUN_GAP = 2;
export const MIN_RUN = 3;
export const SOLO_MARGIN = 0.5;
const STOPWORDS = new Set(`a about above after again against all am an and any are as at be because been before being below between both but by can cannot could did do does doing down during each either else enough even ever every few for from further get gets got had has have having he her here hers herself him himself his how i if in into is it its itself just let like may me might mine more most much must my myself neither no nor not now of off on once one only or other our ours ourselves out over own same shall she should since so some such than that the their theirs them themselves then there these they this those through till to too under until up upon us very was we were what when where which while who whom whose why will with would you your yours yourself yourselves yet hath hast doth art dost wilt tis twas o oh ah aye nay ere thus thee thou thy ye`.split(/\s+/));

export function stripCue(text) {
  return String(text ?? '').replace(/^\s*(?:(?:[A-Z][A-Z'-]*)(?:[ \t]+[A-Z][A-Z'-]*)*\.)[ \t]*/gm, '').trim();
}
export function stem(word) {
  for (const suffix of ["'s", 'ing', 'edly', 'ed', 'ly', 'es', 's']) {
    if (word.endsWith(suffix) && word.length - suffix.length >= 4) return word.slice(0, -suffix.length);
  }
  return word;
}
export function tokenize(text) {
  const clean = stripCue(text);
  const out = [];
  // Names inside a sentence count twice; the first word after sentence punctuation does not.
  for (const match of clean.matchAll(/[A-Za-z]+(?:'[A-Za-z]+)?/g)) {
    const raw = match[0];
    const lower = raw.toLowerCase();
    if (STOPWORDS.has(lower)) continue;
    const before = clean.slice(0, match.index).trimEnd();
    const initial = !before || /[.!?]["')\]]?$/.test(before);
    out.push({ token: stem(lower), weight: /^[A-Z]/.test(raw) && !initial ? 2 : 1 });
  }
  return out;
}
export function cosine(a, b) {
  if (!a.size || !b.size) return 0;
  let dot = 0, na = 0, nb = 0;
  for (const [key, value] of a) { na += value * value; dot += value * (b.get(key) ?? 0); }
  for (const value of b.values()) nb += value * value;
  return na && nb ? dot / Math.sqrt(na * nb) : 0;
}
function textOf(segment, column) {
  if (column === 'english') return segment.english?.text ?? '';
  const pieces = column === 'ross' ? segment.ross : column === 'third' ? segment.third : segment.overlays?.[column.slice(8)];
  return Array.isArray(pieces) ? pieces.map(piece => piece.text ?? '').join(' ') : '';
}
function columnsOf(segments) {
  const names = new Set(['english', 'ross', 'third']);
  for (const s of segments) for (const key of Object.keys(s.overlays ?? {})) names.add(`overlay:${key}`);
  return [...names].filter(name => segments.some(s => textOf(s, name).trim()));
}
function weighted(tokens, idf) {
  const map = new Map();
  for (const { token, weight } of tokens) map.set(token, (map.get(token) ?? 0) + weight * (idf.get(token) ?? 1));
  return map;
}
function median(numbers) {
  const sorted = [...numbers].sort((a, b) => a - b);
  return sorted[Math.floor((sorted.length - 1) / 2)];
}
export function flagRule(matches, peerCount, threshold = MARGIN_THRESHOLD) {
  const qualifying = matches.filter(m => m.offset !== 0 && m.margin >= threshold);
  const required = peerCount === 1 ? 1 : 2;
  const positive = qualifying.filter(m => m.offset > 0);
  const negative = qualifying.filter(m => m.offset < 0);
  const agreed = positive.length >= required && positive.length > negative.length ? positive
    : negative.length >= required && negative.length > positive.length ? negative : null;
  if (!agreed) return null;
  return { offset: median(agreed.map(m => m.offset)), margin: agreed.reduce((sum, m) => sum + m.margin, 0) / agreed.length,
    match: agreed.reduce((best, m) => m.margin > best.margin ? m : best) };
}
export function groupFlags(play, columns, flags) {
  const stretches = [];
  for (const column of columns) {
    const list = flags.filter(f => f.column === column).sort((a, b) => a.index - b.index);
    let run = [];
    const flush = () => {
      if (!run.length) return;
      const maxMargin = Math.max(...run.map(f => f.margin));
      if (run.length >= MIN_RUN || maxMargin >= SOLO_MARGIN) {
        stretches.push({ id: `${play}:${column}:${run[0].index}-${run.at(-1).index}`,
          play, column, firstRef: run[0].ref, lastRef: run.at(-1).ref,
          offsets: run.map(f => f.offset).join(','), count: run.length, maxMargin,
          meanMargin: run.reduce((sum, f) => sum + f.margin, 0) / run.length, flags: run });
      }
      run = [];
    };
    for (const flag of list) {
      const previous = run.at(-1);
      if (previous && (flag.index - previous.index > RUN_GAP + 1 ||
        Math.sign(flag.offset) !== Math.sign(previous.offset) ||
        Math.abs(flag.offset - previous.offset) > 1)) flush();
      run.push(flag);
    }
    flush();
  }
  return stretches;
}
export function checkPlay(play, segments, threshold = ROW_THRESHOLD) {
  const columns = columnsOf(segments);
  const cells = new Map();
  const df = new Map();
  let documents = 0;
  for (const column of columns) {
    const texts = segments.map(s => stripCue(textOf(s, column)));
    const tokens = texts.map(tokenize);
    cells.set(column, { texts, tokens });
    for (const row of tokens) if (row.length) {
      documents++;
      for (const token of new Set(row.map(t => t.token))) df.set(token, (df.get(token) ?? 0) + 1);
    }
  }
  const idf = new Map([...df].map(([word, count]) => [word, Math.log((documents + 1) / (count + 1)) + 1]));
  for (const cell of cells.values()) cell.vectors = cell.tokens.map(row => weighted(row, idf));
  const flags = [];
  for (const column of columns) {
    const a = cells.get(column);
    for (let i = 0; i < segments.length; i++) {
      if (a.tokens[i].length < 3) continue;
      const matches = [];
      let peerCount = 0;
      for (const other of columns) {
        if (other === column) continue;
        const b = cells.get(other);
        if (b.tokens[i].length < 3) continue;
        peerCount++;
        const same = cosine(a.vectors[i], b.vectors[i]);
        let best = { j: i, sim: same };
        for (let j = Math.max(0, i - WINDOW); j <= Math.min(segments.length - 1, i + WINDOW); j++) {
          if (j === i || b.tokens[j].length < 3) continue;
          const sim = cosine(a.vectors[i], b.vectors[j]);
          if (sim > best.sim) best = { j, sim };
        }
        matches.push({ other, j: best.j, offset: best.j - i, margin: best.sim - same });
      }
      const result = flagRule(matches, peerCount, threshold);
      if (!result) continue;
      const target = i + result.offset;
      flags.push({ play, column, index: i, id: segments[i].id, ref: segments[i].column,
        offset: result.offset, targetRef: segments[target]?.column ?? '', margin: result.margin,
        text: a.texts[i].slice(0, 80), matchText: cells.get(result.match.other).texts[result.match.j].slice(0, 80) });
    }
  }
  const stretches = groupFlags(play, columns, flags);
  return { flags: stretches.flatMap(s => s.flags.map(f => ({ ...f, stretch: s.id }))), stretches, columns };
}
function tsv(header, rows) {
  const clean = value => String(value ?? '').replace(/[\t\r\n]+/g, ' ');
  return [header, ...rows.map(row => row.map(clean).join('\t'))].join('\n') + '\n';
}
function argsOf(argv) {
  const args = { books: [], out: 'build/sweeps/s16' };
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    if (!['--dist', '--out', '--play', '--book'].includes(key) || !argv[i + 1]) throw new Error(`Bad argument: ${key}`);
    const value = argv[++i];
    if (key === '--book') args.books.push(value);
    else args[key.slice(2)] = value;
  }
  if (!args.dist && !args.books.length) throw new Error('Give --dist or --book');
  return args;
}
async function main() {
  const args = argsOf(process.argv.slice(2));
  const books = [...args.books];
  if (args.dist) {
    const data = path.join(args.dist, 'data');
    for (const entry of await readdir(data, { withFileTypes: true })) {
      if (!entry.isDirectory() || args.play && args.play !== entry.name) continue;
      const file = path.join(data, entry.name, 'book-01.json');
      try { await readFile(file); books.push(file); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    }
  }
  const allFlags = [], allStretches = [], counts = [];
  for (const file of [...new Set(books)].sort()) {
    const book = JSON.parse(await readFile(file, 'utf8'));
    const play = path.basename(path.dirname(file));
    if (args.play && play !== args.play) continue;
    const result = checkPlay(play, book.segments, ROW_THRESHOLD);
    allFlags.push(...result.flags); allStretches.push(...result.stretches);
    for (const column of result.columns) counts.push({ play, column,
      flags: result.flags.filter(f => f.column === column).length,
      stretches: result.stretches.filter(s => s.column === column).length });
  }
  await mkdir(args.out, { recursive: true });
  await writeFile(path.join(args.out, 's16-flags.tsv'), tsv('play\tcolumn\tsegment id\tgreek ref\tconsensus offset in segments\tseems to belong to\tmargin\ttext\tbest matching text\tstretch', allFlags.map(f => [f.play, f.column, f.id, f.ref, f.offset, f.targetRef, f.margin.toFixed(3), f.text, f.matchText, f.stretch])));
  await writeFile(path.join(args.out, 's16-stretches.tsv'), tsv('play\tcolumn\tfirst ref\tlast ref\trow offsets\tflag count\tmax margin\tmean margin', allStretches.map(s => [s.play, s.column, s.firstRef, s.lastRef, s.offsets, s.count, s.maxMargin.toFixed(3), s.meanMargin.toFixed(3)])));
  await writeFile(path.join(args.out, 's16-summary.txt'), [`Plays: ${new Set(counts.map(c => c.play)).size}`, `Flags: ${allFlags.length}`, `Stretches: ${allStretches.length}`, `Window: ${WINDOW}`, `Row threshold: ${ROW_THRESHOLD}`, `Run gap: ${RUN_GAP}`, `Minimum run: ${MIN_RUN}`, `Solo margin: ${SOLO_MARGIN}`, '', 'play\tcolumn\tflags\tstretches', ...counts.map(c => `${c.play}\t${c.column}\t${c.flags}\t${c.stretches}`)].join('\n') + '\n');
  console.log(`${allFlags.length} flags, ${allStretches.length} stretches across ${new Set(counts.map(c => c.play)).size} plays`);
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main().catch(error => { console.error(error); process.exitCode = 1; });
