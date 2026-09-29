// Keeping the reader's place across an edition switch (plan §4.2): the same
// printed ref if the new edition has it; else through the two concordances
// (edition ref -> TLG ref, either a single ref or a range "112-113"); else the
// nearest lower number.
import type { BookData } from './data';

// data/<work>/ed/<ed>/concordance.json: { "<edition ref>": "<tlg ref | range>" }
export type Concordance = Record<string, string>;

const num = (ref: string): number => Number(ref.match(/\d+/)?.[0]);

/** Every ref in "112-113" (whole numbers only); a plain ref is itself. */
function expand(value: string): string[] {
  const m = value.match(/^(\d+)-(\d+)$/);
  if (!m) return [value];
  const [from, to] = [Number(m[1]), Number(m[2])];
  if (!(to > from) || to - from > 50) return [value];
  return Array.from({ length: to - from + 1 }, (_, i) => String(from + i));
}

/** tlg ref -> edition ref; when several edition lines map to one, the first. */
export function invertConcordance(conc: Concordance): Map<string, string> {
  const out = new Map<string, string>();
  for (const [edRef, tlg] of Object.entries(conc))
    for (const ref of expand(tlg)) if (!out.has(ref)) out.set(ref, edRef);
  return out;
}

function refs(book: BookData): string[] {
  return book.segments.flatMap(segment => segment.greek
    .filter(line => line.ref && line.role !== 'heading' && line.role !== 'context' && line.role !== 'lacuna')
    .map(line => line.ref!));
}

/** The printed ref in `book` that answers to `ref` (itself, or the range line holding it), or null. */
function present(ref: string, available: string[]): string | null {
  if (available.includes(ref)) return ref;
  const n = Number(ref);
  if (Number.isInteger(n))
    for (const a of available) {
      const m = a.match(/^(\d+)-(\d+)$/);
      if (m && Number(m[1]) <= n && n <= Number(m[2])) return a;
    }
  return null;
}

function lower(ref: string, available: string[]): string | null {
  const target = num(ref);
  if (!Number.isFinite(target)) return available[0] ?? null;
  let best: string | null = null;
  let bestNumber = -Infinity;
  for (const candidate of available) {
    const n = num(candidate);
    if (n <= target && n > bestNumber) { best = candidate; bestNumber = n; }
  }
  return best ?? available[0] ?? null;
}

const bare = (ref: string) => ref.replace(/--\d+$/, '');

/** True when `book` prints `ref` itself, so no concordance is needed. */
export function hasRef(ref: string, book: BookData): boolean {
  return present(bare(ref), refs(book)) !== null;
}

/**
 * The ref to open in `nextBook` (edition `newEd`) for a place printed as `ref`
 * in edition `oldEd`. 'tlg' is the reference edition and needs no concordance.
 */
export function editionPlace(
  ref: string | null,
  oldEd: string,
  newEd: string,
  nextBook: BookData,
  oldConcordance: Concordance = {},
  newConcordance: Concordance = {},
): string | null {
  if (!ref) return null;
  const wanted = bare(ref);
  const available = refs(nextBook);
  const same = present(wanted, available);
  if (same) return same;
  const mapped = oldEd === 'tlg' ? wanted : oldConcordance[wanted] ? expand(oldConcordance[wanted]!)[0]! : null;
  if (mapped) {
    const target = newEd === 'tlg' ? mapped : invertConcordance(newConcordance).get(mapped);
    const found = target ? present(target, available) : null;
    if (found) return found;
  }
  return lower(wanted, available);
}
