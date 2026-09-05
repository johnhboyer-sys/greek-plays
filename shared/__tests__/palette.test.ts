import { describe, expect, it } from 'vitest';
import { hasGreek, rankLemmata, rankWorks } from '../lib/palette';
import { lemmaEntryHref, type LemmaRef } from '../lib/data';
import type { Work } from '../lib/works';

// Note: citation parsing for the palette is delegated to the work's own
// citation scheme (shared/lib/citation.ts, tested in citation.test.ts) rather
// than duplicated here — the palette library owns only the Greek/work/lemma
// ranking below.

// rankWorks defaults to the real WORKS registry, which Phase 0 ships empty
// (see shared/lib/works.ts) — a small fixture list stands in so the ranking
// logic itself (tiering, abbr/title/id matching, capping) stays covered
// without depending on real registry content.
function mkWork(id: string, title: string, abbr: string): Work {
  return {
    id, title, abbr,
    author: 'fixture-author',
    language: 'grc',
    workType: 'continuous',
    books: 1,
    bookLabels: ['1'],
    greekEdition: 'Test edition',
    greekSource: { short: 'Test', full: 'Test edition, full citation.' },
    translations: [],
    blurb: 'Fixture work for palette ranking tests.',
  };
}

const fixtureWorks: Work[] = [
  mkWork('Republic', 'Republic', 'Rep.'),
  mkWork('Gorgias', 'Gorgias', 'Grg.'),
  mkWork('Laws', 'Laws', 'Leg.'),
  mkWork('Apology', 'Apology', 'Ap.'),
  mkWork('Alcibiades1', 'Alcibiades I', 'Alc. I'),
  mkWork('Alcibiades2', 'Alcibiades II', 'Alc. II'),
  mkWork('Anonymous', 'Anonymous Work', 'Anon.'),
];

describe('hasGreek', () => {
  it('detects polytonic and monotonic Greek', () => {
    expect(hasGreek('λόγος')).toBe(true);
    expect(hasGreek('ἀρετή')).toBe(true);
    expect(hasGreek('justice')).toBe(false);
    expect(hasGreek('34b')).toBe(false);
  });
});

describe('rankWorks', () => {
  it('ranks a title-prefix match first', () => {
    const r = rankWorks('republic', fixtureWorks);
    expect(r[0]?.id).toBe('Republic');
  });
  it('matches an abbreviation, ignoring its trailing dot', () => {
    // "Rep." → "rep"; "Grg." → "grg"; both are exact-abbr (top-tier) hits.
    expect(rankWorks('rep', fixtureWorks)[0]?.id).toBe('Republic');
    expect(rankWorks('grg', fixtureWorks)[0]?.id).toBe('Gorgias');
  });
  it('matches on the id', () => {
    expect(rankWorks('laws', fixtureWorks).some((w) => w.id === 'Laws')).toBe(true);
  });
  it('returns nothing for an empty query', () => {
    expect(rankWorks('  ', fixtureWorks)).toEqual([]);
  });
  it('caps the result count', () => {
    // Five fixture works start with "a" (title or abbr), so a limit of 3
    // genuinely exercises the cap rather than passing vacuously.
    expect(rankWorks('a', fixtureWorks, 3).length).toBeLessThanOrEqual(3);
  });
  it('is empty against an empty (Phase 0 default) registry', () => {
    expect(rankWorks('republic', [])).toEqual([]);
  });
});

describe('rankLemmata', () => {
  const lemmata: Record<string, LemmaRef> = {
    'lo/gos': { slug: 'logos', head: 'λόγος', count: 100 },
    'le/gw': { slug: 'lego', head: 'λέγω', count: 500 },
    'lu/w': { slug: 'luo', head: 'λύω', count: 5 },
    'a)reth/': { slug: 'arete', head: 'ἀρετή', count: 300 },
  };
  it('prefix-matches on the folded headword, frequency-ranked', () => {
    const r = rankLemmata('λ', lemmata);
    expect(r.map((x) => x.slug)).toEqual(['lego', 'logos', 'luo']);
  });
  it('accent-insensitive matching', () => {
    expect(rankLemmata('λογο', lemmata).map((x) => x.slug)).toEqual(['logos']);
  });
  it('respects the limit', () => {
    expect(rankLemmata('λ', lemmata, 1).map((x) => x.slug)).toEqual(['lego']);
  });
  it('empty for non-matching input', () => {
    expect(rankLemmata('ζζζ', lemmata)).toEqual([]);
  });
});

// The lemma entry URL has ONE definition (data.ts's lemmaEntryHref) because
// it previously had five hand-written ones. When lemma pages became client-
// rendered on 2026-08-04 (`/lemma/<lang>/<slug>/` -> `/lemma/<lang>/entry/
// ?w=<slug>`), four sites were updated and the ⌘K palette was missed, so
// every Greek lexicon hit in the palette 404'd. `scripts/check-links.mjs`
// crawls built HTML and therefore CANNOT see this href — it is constructed
// in client JS at runtime. These assertions are the only gate on that form.
describe('lemmaEntryHref', () => {
  it('builds the client-rendered entry URL, not a per-lemma page path', () => {
    expect(lemmaEntryHref('', 'grc', 'logos')).toBe('/lemma/grc/entry/?w=logos');
    expect(lemmaEntryHref('', 'lat', 'honestas')).toBe('/lemma/lat/entry/?w=honestas');
  });
  it('honors a base path', () => {
    expect(lemmaEntryHref('/reader', 'grc', 'logos')).toBe('/reader/lemma/grc/entry/?w=logos');
  });
  it('encodes the slug so it cannot break out of the query parameter', () => {
    expect(lemmaEntryHref('', 'grc', 'a&b=c')).toBe('/lemma/grc/entry/?w=a%26b%3Dc');
  });
});
