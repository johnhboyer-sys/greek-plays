// LemmaPage.astro's citation-pill formatting (app/src/lib/lemma-instance.ts),
// extracted so the scheme-dispatch + sentinel-line handling is testable
// without an Astro render pass. Covers the Sol-review regression: hand-
// concatenation baked in Bekker's no-separator convention for every scheme
// (DK verse's dot separator got dropped: "B834" instead of "B8.34"), and a
// dk verse fragment's negative sentinel `n` (role='context' lines,
// stage1_greek._parse_fragments) rendered a garbled "B1-1" citation instead
// of being treated as "no line".
import { describe, expect, it, vi } from 'vitest';

// The zero-works registry (drama fork P0, docs/plan.md §1) carries none of
// the real works these schemes used to be exercised against (Cicero's De
// Officiis, Parmenides' fragments, Heraclitus' fragments) — fixtures stand
// in so instHref's workPath() call resolves instead of throwing for an
// unregistered id.
vi.mock('@shared/lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@shared/lib/works')>();
  const fixtures: Record<string, unknown> = {
    'book-section-work': { id: 'book-section-work', citation: { scheme: 'book-section' } },
    'dk-verse-work': { id: 'dk-verse-work', citation: { scheme: 'dk', series: 'B', lines: true } },
    'dk-lineless-work': { id: 'dk-lineless-work', citation: { scheme: 'dk', series: 'B' } },
  };
  return {
    ...actual,
    getWork: (id: string) => fixtures[id] ?? actual.getWork(id),
    workPath: (id: string, book = 1) =>
      fixtures[id] ? `/test-author/${id}/book/${book}` : actual.workPath(id, book),
  };
});

const { instHref, instLabel } = await import('../lib/lemma-instance');

describe('lemma-instance citation pills', () => {
  it('Bekker (unregistered work id defaults to bekker, per schemeFor): concatenates column+line with no separator', () => {
    // instHref isn't exercised here: workPath() throws for an unregistered
    // work id (by design — it's a caller-bug guard), and no bekker-scheme
    // work is in the zero-works registry (drama fork P0). formatCite/
    // formatLocValue dispatch through schemeFor, which defaults an
    // unregistered id to bekker (documented in citation.ts), so instLabel
    // alone still exercises the real regression: bekker's own concatenation
    // convention, undisturbed by the fix below.
    expect(instLabel('unregistered-bekker-work', ['1097a', 15, 'ἀγαθόν'])).toBe('1097a15');
  });

  it('book-section (de-officiis-shaped fixture): drops the line entirely (no user-facing line axis)', () => {
    expect(instLabel('book-section-work', ['1.101', 4, 'honestum'])).toBe('1.101');
    const href = instHref('/base', 'book-section-work', 1, ['1.101', 4, 'honestum']);
    expect(href).toContain('loc=1.101');
    expect(href).not.toContain(':4');
  });

  it('DK verse (parmenides-fragments-shaped fixture, citation.lines: true): dot-joins column and line — NOT "B834"', () => {
    expect(instLabel('dk-verse-work', ['B8', 34, 'ἐόν'])).toBe('B8.34');
    const href = instHref('/base', 'dk-verse-work', 1, ['B8', 34, 'ἐόν']);
    expect(href).toContain('loc=B8:34');
  });

  it('DK verse sentinel line (-1, role=\'context\' block): renders the bare column, not "B1-1"', () => {
    expect(instLabel('dk-verse-work', ['B1', -1, 'μῦθος'])).toBe('B1');
    const href = instHref('/base', 'dk-verse-work', 1, ['B1', -1, 'μῦθος']);
    expect(href).toContain('loc=B1');
    expect(href).not.toContain('-1');
  });

  it('line-less DK fragment (heraclitus-fragments-shaped fixture, no citation.lines): line is ignored regardless of sign', () => {
    expect(instLabel('dk-lineless-work', ['B30', 5, 'κόσμον'])).toBe('B30');
    expect(instLabel('dk-lineless-work', ['B30', -1, 'κόσμον'])).toBe('B30');
    const href = instHref('/base', 'dk-lineless-work', 1, ['B30', 5, 'κόσμον']);
    expect(href).toContain('loc=B30');
  });
});
