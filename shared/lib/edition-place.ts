import type { BookData } from './data';

type Concordance = Record<string, string>;

function refs(book: BookData): string[] {
  return book.segments.flatMap(segment => segment.greek
    .filter(line => line.ref && line.role !== 'heading' && line.role !== 'context' && line.role !== 'lacuna')
    .map(line => line.ref!));
}

function lower(ref: string, available: string[]): string | null {
  const target = Number(ref.match(/\d+/)?.[0]);
  if (!Number.isFinite(target)) return available[0] ?? null;
  let best: string | null = null;
  let bestNumber = -Infinity;
  for (const candidate of available) {
    const number = Number(candidate.match(/\d+/)?.[0]);
    if (number <= target && number > bestNumber) { best = candidate; bestNumber = number; }
  }
  return best ?? available[0] ?? null;
}

export function editionPlace(
  ref: string | null,
  oldEd: string,
  newEd: string,
  nextBook: BookData,
  oldConcordance: Concordance = {},
  newConcordance: Concordance = {},
): string | null {
  if (!ref) return null;
  const wanted = ref.replace(/--\d+$/, '');
  const available = refs(nextBook);
  if (available.includes(wanted)) return wanted;
  const tlgRef = oldEd === 'tlg' ? wanted : oldConcordance[wanted];
  const mapped = newEd === 'tlg'
    ? tlgRef
    : Object.entries(newConcordance).find(([, tlg]) => tlg === tlgRef)?.[0];
  if (mapped && available.includes(mapped)) return mapped;
  return lower(wanted, available);
}
