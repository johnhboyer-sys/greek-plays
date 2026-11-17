// A segment's Greek as the index counts it: token places, lines, and the
// sections a match runs on into. Moved here from the results page so the
// row table (lib/row-table) counts with the same code that draws the rows.
import type { GreekLine, Segment, Token } from './data';

type Lines = Pick<Segment, 'greek'>;

/** A segment's Greek tokens in the order the index counts them. */
export const segTokens = (seg: Lines): Token[] => seg.greek.flatMap(line => line.tokens);

/** The Greek line of the token at index `pos` within a segment. A proximity
 * measure only: the citation is formatted through the work's scheme, which
 * for Stephanus prints the section alone. */
export function lineOfPosition(seg: Lines, pos: number): number {
  let count = 0;
  for (const line of seg.greek) {
    if (pos < count + line.tokens.length) return line.n;
    count += line.tokens.length;
  }
  return seg.greek[seg.greek.length - 1]?.n ?? 1;
}

/** The lettered line's suffix of the token at `pos` ("5a" → "a"), undefined
 * for a plain line or a place past the last line. */
export function subOfPosition(seg: Lines, pos: number): string | undefined {
  let left = pos;
  for (const l of seg.greek) { if (left < l.tokens.length) return l.sub; left -= l.tokens.length; }
  return undefined;
}

/** Each line's tokens in that order: number and suffix → [first, past last). */
export function lineTokens(seg: Lines): Map<string, [number, number]> {
  const out = new Map<string, [number, number]>();
  let at = 0;
  for (const line of seg.greek) { out.set(`${line.n}${line.sub ?? ''}`, [at, at + line.tokens.length]); at += line.tokens.length; }
  return out;
}

/** The sections after `seg` in its book that a match `last` words on from
 * its first reaches into, `reach` words more: none for a match inside it. */
export function sectionsAfter<S extends Lines>(segments: S[], seg: S, last: number, reach: number): S[] {
  let n = segTokens(seg).length;
  const out: S[] = [];
  for (let k = segments.indexOf(seg) + 1; k > 0 && k < segments.length && n <= last + reach; k++) {
    out.push(segments[k]);
    n += segTokens(segments[k]).length;
  }
  return last < segTokens(seg).length ? [] : out;
}

// ── The plays' verse lines (search port, decision 5) ──────────────────────
// Every printed line of a book in order, each with its section and where
// its first word stands counting through the book (`first`), and each
// section's first word (`base`): a hit's words, counted from its section's
// first, may stand in the section before (below 0) or after.
type VerseSeg = Pick<Segment, 'id' | 'greek'>;
export interface VerseLine<S extends VerseSeg = Segment> { seg: S; line: GreekLine; first: number; n: number; at: number }
type VerseBook<S extends VerseSeg> = { segments: S[] };
const verseCache = new WeakMap<object, { lines: VerseLine<VerseSeg>[]; base: Map<string, number> }>();
export function verseOf<S extends VerseSeg>(book: VerseBook<S>): { lines: VerseLine<S>[]; base: Map<string, number> } {
  let v = verseCache.get(book);
  if (!v) {
    const lines: VerseLine<VerseSeg>[] = [];
    const base = new Map<string, number>();
    let t = 0;
    for (const seg of book.segments) {
      base.set(seg.id, t);
      let at = 0;
      for (const line of seg.greek) {
        lines.push({ seg, line, first: t, n: line.tokens.length, at });
        t += line.tokens.length;
        at += line.tokens.length;
      }
    }
    v = { lines, base };
    verseCache.set(book, v);
  }
  return v as { lines: VerseLine<S>[]; base: Map<string, number> };
}
// The line a word stands on: the last to start at or before it (a line
// with no words starts where the next does, so is never it).
function verseLineAt(lines: VerseLine<VerseSeg>[], t: number): number {
  let lo = 0;
  let hi = lines.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (lines[mid].first <= t) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}
/** The lines a hit shows: each word's line, and `around` lines either side. */
export function verseLines<S extends VerseSeg>(book: VerseBook<S>, seg: S, marked: Iterable<number>, around: number): number[] {
  const { lines, base } = verseOf(book);
  const b0 = base.get(seg.id) ?? 0;
  const shown = new Set<number>();
  for (const p of marked) {
    const t = b0 + p;
    if (t < 0 || !lines.length) continue;
    const i = verseLineAt(lines, t);
    for (let k = Math.max(0, i - around); k <= Math.min(lines.length - 1, i + around); k++) shown.add(k);
  }
  return [...shown].sort((a, b) => a - b).filter(i => lines[i].line.text.trim());
}
/** Those lines' reach in the section's own count, for joining hits whose
 * lines meet. */
export function verseReach<S extends VerseSeg>(book: VerseBook<S>, seg: S, marked: number[], around: number): [number, number] {
  const { lines, base } = verseOf(book);
  const b0 = base.get(seg.id) ?? 0;
  const shown = verseLines(book, seg, marked, around);
  if (!shown.length) return [marked[0] ?? 0, (marked[0] ?? 0) + 1];
  const first = lines[shown[0]];
  const last = lines[shown.at(-1)!];
  return [first.first - b0, last.first + Math.max(1, last.n) - b0];
}
