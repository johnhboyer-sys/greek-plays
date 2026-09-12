import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  SHELVES, START_HERE, WORK_ORDER, WORKS,
  authorPath, bookLabel, furtherReading, getWork, getWorkBySlug, inPrintHref, isBookless,
  languageLabel, visibleTranslations, workByDkCitation, workLanding, workPath, workSlug, type Work,
} from '../lib/works';
import { getAuthor } from '../lib/authors';

// A fixture multi-book Work exercises bookLabel/isBookless/visibleTranslations'
// generic logic without depending on a real registry entry — Phase 0 carries
// no real works at all (see works.ts's doc comment), so every test here is
// either a fixture-driven unit test or an N>=0 invariant over the (possibly
// empty) live registry.
const multiBookFixture: Work = {
  id: 'FixtureMultiBook',
  title: 'Fixture Multi-Book Work',
  abbr: 'Fix.',
  author: 'fixture-author',
  language: 'grc',
  workType: 'continuous',
  books: 10,
  bookLabels: ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'],
  greekEdition: 'Test edition',
  greekSource: { short: 'Test', full: 'Test edition, full citation.' },
  translations: [{ id: 'test', name: 'Test Translator (Test, 1900)', short: 'Test', slot: 'english' }],
  blurb: 'A fixture multi-book work for exercising bookLabel/isBookless generic logic.',
};

describe('works registry helpers (fixture-driven, registry-independent)', () => {
  it('normalizes book labels using a fixture multi-book work', () => {
    expect(bookLabel(multiBookFixture, 1)).toBe('I');
    expect(bookLabel(multiBookFixture, 99)).toBe('99'); // out of range -> falls back to the raw number
  });

  it('reports bookless vs multi-book works', () => {
    expect(isBookless(multiBookFixture)).toBe(false);
    const bookless: Work = { ...multiBookFixture, id: 'FixtureBookless', books: 1, bookLabels: ['1'] };
    expect(isBookless(bookless)).toBe(true);
  });

  it('derives a human language label from the registry language field, not the author', () => {
    // Regression for task #66: PHI-sourced (Latin) works must not render
    // "Greek" metadata just because most of the registry is TLG/Greek.
    expect(languageLabel(multiBookFixture)).toBe('Greek');
    const latinFixture: Work = { ...multiBookFixture, id: 'FixtureLatinWork', language: 'lat' };
    expect(languageLabel(latinFixture)).toBe('Latin');
  });

  it('throws rather than emitting a broken URL for an unresolvable work', () => {
    // 'FixtureMultiBook' is a local fixture object, never registered in WORKS
    // (Phase 0 ships no real works — see the doc comment above), so it has no
    // author to resolve against.
    expect(() => workPath('FixtureMultiBook', 3)).toThrow(/unknown work/);
    expect(() => workLanding('FixtureMultiBook')).toThrow(/unknown work/);
  });

  it('authorPath throws for an unknown author id', () => {
    expect(() => authorPath('no-such-author')).toThrow(/unknown author/);
  });

  it('filters private translations unless the runtime flag is set, and never mutates the registry entry', () => {
    expect(visibleTranslations(multiBookFixture).every((t) => !t.private)).toBe(true);
    (globalThis as { __READER_EXTRA_TRANSLATIONS__?: unknown }).__READER_EXTRA_TRANSLATIONS__ = {
      FixtureMultiBook: [{ id: 'mine', name: 'Local Import', short: 'Local', slot: 'overlay' }],
    };
    expect(visibleTranslations(multiBookFixture).map((t) => t.id)).toContain('mine');
    delete (globalThis as { __READER_EXTRA_TRANSLATIONS__?: unknown }).__READER_EXTRA_TRANSLATIONS__;
  });

  it('creates stable in-print links from curated metadata (empty for this rollout)', () => {
    expect(furtherReading('FixtureMultiBook')).toEqual([]);
    expect(inPrintHref({ kind: 'translation', cite: 'A <em>Book</em> & commentary' })).toBe(
      'https://www.google.com/search?tbm=bks&q=A%20Book%20%26%20commentary',
    );
  });
});

describe('WORKS registry invariants (N >= 0 — Phase 0 ships no real works)', () => {
  it('has unique work ids', () => {
    const ids = WORKS.map((w) => w.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('every work.author resolves via getAuthor', () => {
    for (const w of WORKS) {
      expect(getAuthor(w.author), `${w.id}.author ('${w.author}') should resolve via getAuthor`).toBeDefined();
    }
  });

  it('every work has a valid language', () => {
    for (const w of WORKS) expect(['grc', 'lat']).toContain(w.language);
  });

  it('every work has a valid workType', () => {
    for (const w of WORKS) {
      expect(['continuous', 'fragments', 'verse', 'letters']).toContain(w.workType);
    }
  });

  // Multiple works may share an id PREFIX under one author (DK's
  // `<author>-fragments`/`<author>-testimonia`), so `slug` — not `id` — is
  // the uniqueness axis that actually matters for routing: two works of the
  // SAME author must never publish at the same URL segment.
  it('every work\'s URL slug is unique within its author', () => {
    const byAuthor = new Map<string, string[]>();
    for (const w of WORKS) {
      const slugs = byAuthor.get(w.author) ?? [];
      slugs.push(workSlug(w));
      byAuthor.set(w.author, slugs);
    }
    for (const [author, slugs] of byAuthor) {
      expect(new Set(slugs).size, `author '${author}' has a duplicate work slug: ${slugs}`).toBe(slugs.length);
    }
  });

  // Fix round, finding 3 (Sol xhigh review): Landing.astro's work-level
  // "translated by" line is built entirely from `translations`
  // (visibleTranslations), which never sees the per-passage credit swap
  // B11 (Helen)/B11a (Palamedes) carry (EnglishChunk.credit — the DK
  // column_sources override) — Landing's static build has no access to
  // segment data (see Work.alsoCredits' own doc comment for why). This
  // pins the one place that override note lives: the registry entry
  // itself, never duplicated as a literal string in the astro template.
  it('gorgias-fragments names its per-passage credit override via Work.alsoCredits, not a template string', () => {
    const gorgiasFragments = WORKS.find((w) => w.id === 'gorgias-fragments');
    if (!gorgiasFragments) return; // registry doesn't carry this work in every build (Phase 0 fixture builds)
    expect(gorgiasFragments.alsoCredits).toBe(
      'the Encomium of Helen and Defence of Palamedes are translated by J. R. Gatt and G. A. Gazis'
    );
  });

  // Fix round, finding 6 (Sol xhigh review): the freeman-summary overlay is
  // a SUMMARY, not a translation — Reader.svelte's engCreditFor reads this
  // flag to label a copy of the summary text "(summary)" rather than
  // clearing its data-eng-credit outright (which made a copy of the
  // summary indistinguishable from a copy of the real translation).
  it('gorgias-fragments\' freeman-summary overlay is marked kind: \'summary\'', () => {
    const gorgiasFragments = WORKS.find((w) => w.id === 'gorgias-fragments');
    if (!gorgiasFragments) return;
    const summary = gorgiasFragments.translations.find((t) => t.id === 'freeman-summary');
    expect(summary?.kind).toBe('summary');
  });
});

describe('workSlug / getWorkBySlug', () => {
  it('workSlug defaults to id when no slug is declared', () => {
    for (const w of WORKS) {
      if (!w.slug) expect(workSlug(w)).toBe(w.id);
    }
  });

  it('getWorkBySlug resolves the (author, slug) pair back to the work', () => {
    for (const w of WORKS) {
      expect(getWorkBySlug(w.author, workSlug(w))?.id).toBe(w.id);
    }
  });

  it('getWorkBySlug returns undefined for an unknown author or slug', () => {
    expect(getWorkBySlug('no-such-author', 'anything')).toBeUndefined();
    if (WORKS.length > 0) {
      expect(getWorkBySlug(WORKS[0].author, 'no-such-slug-xyz')).toBeUndefined();
    }
  });
});

describe('workByDkCitation — the ⌘K palette\'s dkChapter -> work resolver', () => {
  it('returns undefined for an unregistered chapter/series pairing', () => {
    expect(workByDkCitation(999, 'B')).toBeUndefined();
  });

  it('every dk WORKS entry with dkChapter+series is resolvable via its own pair', () => {
    for (const w of WORKS) {
      const c = w.citation;
      if (c?.scheme === 'dk' && c.dkChapter != null && c.series) {
        expect(workByDkCitation(c.dkChapter, c.series)?.id).toBe(w.id);
      }
    }
  });
});

describe('SHELVES — period-ordered home-page taxonomy', () => {
  it('partitions every registered work exactly once', () => {
    const shelfIds = SHELVES.flatMap((s) => s.works.map((w) => w.id).filter((id): id is string => Boolean(id)));
    for (const w of WORKS) {
      const count = shelfIds.filter((id) => id === w.id).length;
      expect(count, `${w.id} should appear in exactly one shelf, found ${count}`).toBe(1);
    }
    // No stray/unknown ids and no duplicates overall.
    expect(shelfIds.length).toBe(WORKS.length);
    expect(new Set(shelfIds).size).toBe(shelfIds.length);
    for (const id of shelfIds) expect(getWork(id)).toBeDefined();
  });
});

describe('"Start here" featured strip (START_HERE)', () => {
  it('is empty in Phase 0, and any future entry must resolve to a real work', () => {
    expect(START_HERE).toEqual([]);
    for (const id of START_HERE) expect(getWork(id), `${id} should be a real WORKS entry`).toBeDefined();
  });
});

describe('WORK_ORDER — search cross-work ordering', () => {
  it('assigns every registered work an order index, with no stray ids', () => {
    for (const w of WORKS) expect(WORK_ORDER.has(w.id)).toBe(true);
    for (const id of WORK_ORDER.keys()) expect(getWork(id), `WORK_ORDER has a stray id: ${id}`).toBeDefined();
  });
});

// workPath/workLanding/authorPath's real author-resolution path needs a work
// that's actually IN the registry with an author that's actually in AUTHORS —
// Phase 0 ships neither for real, so this exercises the PUBLIC_READER_FIXTURES
// gate (see authors.ts/works.ts doc comments) the same way authors.test.ts's
// 'fixture-flag gating' block does: a fresh dynamic import per env state.
describe('author-scoped URL resolution (PUBLIC_READER_FIXTURES)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('workPath/workLanding/authorPath resolve through the fixture author+work', async () => {
    vi.stubEnv('PUBLIC_READER_FIXTURES', '1');
    vi.resetModules();
    const fresh = await import('../lib/works');
    expect(fresh.workLanding('sample-work')).toBe('/sample-author/sample-work');
    expect(fresh.workPath('sample-work', 2)).toBe('/sample-author/sample-work/book/2');
    expect(fresh.authorPath('sample-author')).toBe('/sample-author');
  });

  it('uses the bare work path for a one-book play-line work', async () => {
    const fresh = await import('../lib/works');
    expect(fresh.workPath('agamemnon', 1)).toBe('/aeschylus/agamemnon');
  });

  it('workPath falls back to book 1 for non-finite/non-integer book numbers before clamping', async () => {
    vi.stubEnv('PUBLIC_READER_FIXTURES', '1');
    vi.resetModules();
    const fresh = await import('../lib/works');
    // sample-work has books: 2 — none of these malformed inputs should
    // survive to produce a fractional or NaN path segment.
    expect(fresh.workPath('sample-work', NaN)).toBe('/sample-author/sample-work/book/1');
    expect(fresh.workPath('sample-work', 1.5)).toBe('/sample-author/sample-work/book/1');
    expect(fresh.workPath('sample-work', Infinity)).toBe('/sample-author/sample-work/book/1');
  });
});

// The "WORKS registry invariants"/"SHELVES"/"WORK_ORDER" blocks above only
// ever ran against the flag-off (N === 0) registry, so a shelf/order gap that
// only shows up once a work is actually present would pass silently. Re-run
// the same core invariants against the fixture (PUBLIC_READER_FIXTURES=1)
// registry — same fresh-dynamic-import idiom as authors.test.ts's
// 'fixture-flag gating' block and the describe above.
describe('WORKS/SHELVES/WORK_ORDER invariants against the fixture (PUBLIC_READER_FIXTURES=1) registry', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('holds unique ids, bidirectional author resolution, full SHELVES partition, and full WORK_ORDER coverage', async () => {
    vi.stubEnv('PUBLIC_READER_FIXTURES', '1');
    vi.resetModules();
    const fresh = await import('../lib/works');
    const { getAuthor } = await import('../lib/authors');
    expect(fresh.WORKS.length).toBeGreaterThan(0); // sanity: the fixture actually loaded

    // unique ids
    const ids = fresh.WORKS.map((w) => w.id);
    expect(new Set(ids).size).toBe(ids.length);

    // author resolves bidirectionally
    for (const w of fresh.WORKS) {
      const author = getAuthor(w.author);
      expect(author, `${w.id}.author ('${w.author}') should resolve via getAuthor`).toBeDefined();
      expect(author?.works, `${author?.id}.works should list back ${w.id}`).toContain(w.id);
    }

    // SHELVES partitions every registered work exactly once
    const shelfIds = fresh.SHELVES.flatMap(
      (s) => s.works.map((w) => w.id).filter((id): id is string => Boolean(id)),
    );
    for (const w of fresh.WORKS) {
      const count = shelfIds.filter((id) => id === w.id).length;
      expect(count, `${w.id} should appear in exactly one shelf, found ${count}`).toBe(1);
    }
    expect(shelfIds.length).toBe(fresh.WORKS.length);
    expect(new Set(shelfIds).size).toBe(shelfIds.length);

    // WORK_ORDER covers every work, with no stray ids
    for (const w of fresh.WORKS) expect(fresh.WORK_ORDER.has(w.id)).toBe(true);
    for (const id of fresh.WORK_ORDER.keys()) {
      expect(fresh.getWork(id), `WORK_ORDER has a stray id: ${id}`).toBeDefined();
    }
  });
});

// PUBLIC_WING scopes WORKS to one corpus's works for a P6 standalone wing
// build (docs/p6-plan.md, Settled decision 4) — same module-scope
// import.meta.env read + fresh-dynamic-import idiom as the fixture-flag
// blocks above. WORK_GROUPS/SHELVES/WORK_ORDER are all derived from the
// (module-scope-composed) WORKS/AUTHORS, so a correct filter at the
// composition point scopes them for free — asserted here, not just on WORKS.
describe('corpus-scoping (PUBLIC_WING)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('leaves WORKS unfiltered when unset', async () => {
    vi.stubEnv('PUBLIC_WING', '');
    vi.resetModules();
    const fresh = await import('../lib/works');
    // P1: the first real work (agamemnon, corpus 'classical') has landed.
    expect(fresh.WORKS.length).toBe(44); // P2: the 44 plays
  });

  it('scopes WORKS to zero works when set to aristotle (zero-works registry, drama fork P0)', async () => {
    vi.stubEnv('PUBLIC_WING', 'aristotle');
    vi.resetModules();
    const fresh = await import('../lib/works');
    expect(fresh.WORKS.length).toBe(0);
  });

  it('scopes WORKS to the classical corpus works when set to classical (P2: 44 plays)', async () => {
    vi.stubEnv('PUBLIC_WING', 'classical');
    vi.resetModules();
    const fresh = await import('../lib/works');
    expect(fresh.WORKS.length).toBe(44); // P2: the 44 plays
    expect(fresh.getWork('agamemnon')).toBeDefined();
  });

  it('SHELVES/WORK_ORDER partition only the scoped works when set to aristotle', async () => {
    vi.stubEnv('PUBLIC_WING', 'aristotle');
    vi.resetModules();
    const fresh = await import('../lib/works');

    const shelfIds = fresh.SHELVES.flatMap(
      (s) => s.works.map((w) => w.id).filter((id): id is string => Boolean(id)),
    );
    for (const w of fresh.WORKS) {
      const count = shelfIds.filter((id) => id === w.id).length;
      expect(count, `${w.id} should appear in exactly one shelf, found ${count}`).toBe(1);
    }
    expect(shelfIds.length).toBe(fresh.WORKS.length);

    for (const w of fresh.WORKS) expect(fresh.WORK_ORDER.has(w.id)).toBe(true);
    for (const id of fresh.WORK_ORDER.keys()) {
      expect(fresh.getWork(id), `WORK_ORDER has a stray id: ${id}`).toBeDefined();
    }
  });

  it('rides the fixture work along unfiltered when both PUBLIC_WING and PUBLIC_READER_FIXTURES are set', async () => {
    vi.stubEnv('PUBLIC_WING', 'aristotle');
    vi.stubEnv('PUBLIC_READER_FIXTURES', '1');
    vi.resetModules();
    const fresh = await import('../lib/works');
    expect(fresh.getWork('sample-work')).toBeDefined();
    expect(fresh.WORKS.length).toBe(1); // 0 aristotle (zero-works registry) + 1 fixture
  });

  it('an unknown corpus id scopes WORKS to empty (no work belongs to it)', async () => {
    vi.stubEnv('PUBLIC_WING', 'no-such-corpus');
    vi.resetModules();
    const fresh = await import('../lib/works');
    expect(fresh.WORKS.length).toBe(0);
  });
});

describe('translation form (prose or verse) drives the prose measure', () => {
  const PROSE = ['athenian-society', 'buckley', 'coleridge', 'hickie', 'jebb', 'smyth'];
  it('every corpus translation declares its form, and only the prose translators say prose', () => {
    const all = WORKS.flatMap((w) => w.translations);
    expect(all.length).toBeGreaterThan(0);
    for (const t of all) expect(['prose', 'verse'], `${t.id} form`).toContain(t.form);
    const prose = [...new Set(all.filter((t) => t.form === 'prose').map((t) => t.id))].sort();
    expect(prose).toEqual(PROSE);
  });
});
