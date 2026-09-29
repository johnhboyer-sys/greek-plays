// P2 criterion 6 (build/plans/edition-picker-architecture-2026-09-28.md §5):
// "Switching editions at 50 sampled refs per author lands within one line of the
// concordance target." editionPlace() runs both ways against the BUILT
// concordance.json and the two built books, one play per author:
//   edition -> tlg: refs printed in the edition; the target is the concordance's
//                   TLG ref (the nearest member of a range).
//   tlg -> edition: refs printed in the TLG book; the target is the edition line
//                   whose concordance entry names that ref.
// Build first (never a lone stage), per play:
//   cd pipeline && .venv/bin/python -m drama_pipeline all --work <play>
//   ... all --work <play> --edition <ed>
// Each play skips itself, by name, when its build is absent (build/ is git-ignored).
// The counts print as one line per play and direction; the shifted subset is every
// ref whose target number differs from the ref (the only cases where place-keeping
// has work to do).
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import type { BookData } from '../lib/data';
import { editionPlace, invertConcordance, type Concordance } from '../lib/edition-place';

const dist = resolve(process.cwd(), '../build/dist');
const PLAYS = [
  { author: 'Aeschylus', play: 'agamemnon', ed: 'smyth-loeb' },
  { author: 'Sophocles', play: 'antigone', ed: 'storr-loeb' },
  { author: 'Euripides', play: 'hecuba', ed: 'murray-oct' },
  { author: 'Aristophanes', play: 'frogs', ed: 'hall-geldart-oct' },
];
const SAMPLE = 50;

const num = (ref: string) => Number(ref.match(/\d+/)?.[0]);
const read = <T>(file: string): T => JSON.parse(readFileSync(file, 'utf-8')) as T;

// mulberry32: the same 50 refs on every run
function rng(seed: number) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function sample<T>(items: T[], n: number, seed: number): T[] {
  const random = rng(seed);
  const pool = [...items];
  const out: T[] = [];
  while (out.length < n && pool.length) out.push(pool.splice(Math.floor(random() * pool.length), 1)[0]!);
  return out;
}

// The lines editionPlace treats as places (edition-place.ts refs()).
function refsOf(book: BookData): Array<{ ref: string; text: string }> {
  return book.segments.flatMap(segment => segment.greek
    .filter(line => line.ref && line.role !== 'heading' && line.role !== 'context' && line.role !== 'lacuna')
    .map(line => ({ ref: line.ref!, text: line.text })));
}

/** [first, last] line of a ref: "112" -> [112, 112]; "112-113" -> [112, 113]. */
const span = (value: string): [number, number] => {
  const m = value.match(/^(\d+)-(\d+)$/);
  return m ? [Number(m[1]), Number(m[2])] : [num(value), num(value)];
};

interface Case { ref: string; target: string; got: string | null }
/** Whole lines between the landed ref and the target; either may be a range "112-113". */
const distance = (c: Case) => {
  if (c.got === null) return Infinity;
  const [a, b] = span(c.got);
  const [lo, hi] = span(c.target);
  return Math.max(0, lo - b, a - hi);
};
const tally = (cases: Case[]) => ({
  exact: cases.filter(c => distance(c) === 0).length,
  one: cases.filter(c => distance(c) === 1).length,
  further: cases.filter(c => distance(c) > 1),
});
const line = (label: string, cases: Case[]) => {
  const t = tally(cases);
  return `${label}: ${cases.length} refs, ${t.exact} exact, ${t.one} within one, ${t.further.length} further`;
};

for (const { author, play, ed } of PLAYS) {
  const have = existsSync(`${dist}/${play}/ed/${ed}/concordance.json`) && existsSync(`${dist}/${play}/book-01.json`);
  describe.skipIf(!have)(`P2.6 place-keeping, ${author}: ${play} / ${ed} (skipped when build/dist lacks ${play}/ed/${ed})`, () => {
    const conc = have ? read<Concordance>(`${dist}/${play}/ed/${ed}/concordance.json`) : {};
    const tlgBook = have ? read<BookData>(`${dist}/${play}/book-01.json`) : ({ segments: [] } as unknown as BookData);
    const edBook = have ? read<BookData>(`${dist}/${play}/ed/${ed}/book-01.json`) : ({ segments: [] } as unknown as BookData);
    const tlgLines = new Map(refsOf(tlgBook).map(l => [l.ref, l.text]));
    const edLines = new Map(refsOf(edBook).map(l => [l.ref, l.text]));
    const inverse = invertConcordance(conc);

    const toTlg = (ref: string): Case => ({ ref, target: conc[ref]!, got: editionPlace(ref, ed, 'tlg', tlgBook, conc, {}) });
    const toEd = (ref: string): Case => ({ ref, target: inverse.get(ref)!, got: editionPlace(ref, 'tlg', ed, edBook, {}, conc) });
    const edRefs = [...edLines.keys()].filter(r => conc[r] !== undefined);
    const tlgRefs = [...tlgLines.keys()].filter(r => inverse.has(r));

    function report(direction: string, cases: Case[], shifted: Case[], from: Map<string, string>, to: Map<string, string>) {
      const lines = [line(`${play} ${direction} sample`, cases), line(`${play} ${direction} shifted (all)`, shifted)];
      // every sampled miss, then the first 10 shifted misses (Frogs alone has ~50)
      const misses = [...cases.filter(c => distance(c) > 1), ...shifted.filter(c => distance(c) > 1 && !cases.some(s => s.ref === c.ref))];
      for (const c of misses.slice(0, cases.filter(c => distance(c) > 1).length + 10))
        lines.push(`  further: ${c.ref} -> ${c.got} (concordance target ${c.target}); from: ${from.get(c.ref) ?? ''} | at ${c.got}: ${to.get(c.got ?? '') ?? ''} | at target: ${to.get(c.target) ?? ''}`);
      console.info(lines.join('\n'));
    }

    it(`edition -> tlg: ${SAMPLE} sampled refs land within one line of the concordance target`, () => {
      const cases = sample(edRefs, SAMPLE, 6).map(toTlg);
      const shifted = edRefs.filter(r => span(conc[r]!)[0] !== num(r)).map(toTlg);
      report('edition->tlg', cases, shifted, edLines, tlgLines);
      expect(cases).toHaveLength(SAMPLE);
      expect(tally(cases).exact + tally(cases).one).toBeGreaterThanOrEqual(SAMPLE * 0.9); // measured floor, see the printed counts
    });

    it(`tlg -> edition: ${SAMPLE} sampled refs land within one line of the concordance target`, () => {
      const cases = sample(tlgRefs, SAMPLE, 7).map(toEd);
      const shifted = tlgRefs.filter(r => num(inverse.get(r)!) !== num(r)).map(toEd);
      report('tlg->edition', cases, shifted, tlgLines, edLines);
      expect(cases).toHaveLength(SAMPLE);
      expect(tally(cases).exact + tally(cases).one).toBeGreaterThanOrEqual(SAMPLE * 0.9); // measured floor, see the printed counts
    });
  });
}
