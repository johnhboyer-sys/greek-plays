import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  AUTHOR_PERIOD_ORDER, AUTHORS, PERIOD_LABEL, SCHOOL_GROUP_ORDER,
  authorGroups, authorsByPeriod, getAuthor, holdingsLabel,
  type Author, type AuthorPeriod,
} from '../lib/authors';
import { WORKS, getWork } from '../lib/works';

/** Minimal Author for synthetic grouping / holdings tests (no live registry). */
function synthAuthor(partial: Partial<Author> & Pick<Author, 'id'>): Author {
  return {
    name: partial.id,
    nativeName: '',
    languages: ['grc'],
    period: 'presocratic',
    schools: [],
    floruit: '',
    blurb: '',
    works: [],
    holdings: 'complete',
    ...partial,
  };
}

describe('AUTHORS registry invariants (N >= 0 — Phase 0 ships no real authors)', () => {
  it('has unique, kebab-case ids', () => {
    const ids = AUTHORS.map((a) => a.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) expect(id, `'${id}' should be kebab-case`).toMatch(/^[a-z0-9]+(-[a-z0-9]+)*$/);
  });

  it('has a period drawn from AUTHOR_PERIOD_ORDER', () => {
    for (const a of AUTHORS) expect(AUTHOR_PERIOD_ORDER).toContain(a.period);
  });

  it('has at least one language per author', () => {
    for (const a of AUTHORS) {
      expect(a.languages.length).toBeGreaterThan(0);
      for (const lang of a.languages) expect(['grc', 'lat']).toContain(lang);
    }
  });

  it('has a holdings value of complete or partial', () => {
    for (const a of AUTHORS) expect(['complete', 'partial']).toContain(a.holdings);
  });
});

describe('AUTHORS/WORKS bidirectional consistency', () => {
  it('every author.works entry resolves in WORKS, and every work.author resolves back to an author that lists it', () => {
    for (const a of AUTHORS) {
      for (const workId of a.works) {
        expect(getWork(workId), `${a.id}.works lists '${workId}', not found in WORKS`).toBeDefined();
      }
    }
    for (const w of WORKS) {
      const author = getAuthor(w.author);
      expect(author, `${w.id}.author ('${w.author}') should resolve via getAuthor`).toBeDefined();
      expect(author?.works, `${author?.id}.works should list back ${w.id}`).toContain(w.id);
    }
  });
});

describe('period ordering helpers', () => {
  it('AUTHOR_PERIOD_ORDER lists the seven periods in canonical chronological order', () => {
    expect(AUTHOR_PERIOD_ORDER).toEqual(['presocratic', 'sophists', 'classical', 'hellenistic', 'roman', 'imperial', 'late-antique']);
  });

  it('PERIOD_LABEL gives every period a display name', () => {
    for (const p of AUTHOR_PERIOD_ORDER) expect(typeof PERIOD_LABEL[p]).toBe('string');
  });

  it('authorsByPeriod groups authors under their period, period-ordered, with every period present', () => {
    const grouped = authorsByPeriod();
    expect([...grouped.keys()]).toEqual(AUTHOR_PERIOD_ORDER);
    for (const [period, authors] of grouped) {
      for (const a of authors) expect(a.period).toBe(period as AuthorPeriod);
    }
  });
});

describe('authorGroups (home-page school clusters)', () => {
  afterEach(() => {
    vi.doUnmock('../lib/registry.generated');
    vi.resetModules();
  });

  it('never drops or duplicates an author, for every period', () => {
    for (const period of AUTHOR_PERIOD_ORDER) {
      const authors = AUTHORS.filter((a) => a.period === period);
      const groups = authorGroups(period, authors);
      const seen = groups.flatMap((g) => g.authors.map((a) => a.id));
      expect(new Set(seen).size).toBe(seen.length);
      expect(new Set(seen)).toEqual(new Set(authors.map((a) => a.id)));
    }
  });

  it('clusters a period into a curated school teaching-sequence order, an unclaimed author standalone', async () => {
    // manifests/authors.yaml's school_groups is empty in the zero-works
    // registry (drama fork P0), so this exercises authorGroups' slot/order
    // branch against a synthetic SCHOOL_GROUP_ORDER instead of the real
    // (now-deleted) presocratic curation — same shape (school slots, an
    // author-list order override, an author no slot claims).
    vi.doMock('../lib/registry.generated', async (importOriginal) => ({
      ...(await importOriginal<typeof import('../lib/registry.generated')>()),
      SCHOOL_GROUP_ORDER_DATA: {
        presocratic: [
          { school: 'milesian' },
          { school: 'eleatic', order: ['xenophanes', 'parmenides'] },
        ],
      },
    }));
    vi.resetModules();
    const fresh = await import('../lib/authors');
    const authors = [
      synthAuthor({ id: 'thales', schools: ['milesian'] }),
      synthAuthor({ id: 'heraclitus', schools: [] }),
      synthAuthor({ id: 'parmenides', schools: ['eleatic'] }),
      synthAuthor({ id: 'xenophanes', schools: ['eleatic'] }),
    ];
    const groups = fresh.authorGroups('presocratic', authors);
    expect(groups.map((g) => [g.heading, g.authors.map((a) => a.id)])).toEqual([
      ['Milesians', ['thales']],
      ['Eleatics', ['xenophanes', 'parmenides']],
      [null, ['heraclitus']],
    ]);
    vi.doUnmock('../lib/registry.generated');
  });

  it('leaves a period with no established sequence (e.g. Sophists) as one unheaded group', () => {
    const authors = [synthAuthor({ id: 'protagoras', period: 'sophists' }), synthAuthor({ id: 'gorgias', period: 'sophists' })];
    const groups = authorGroups('sophists', authors);
    expect(groups).toEqual([{ heading: null, authors }]);
  });

  it('leaves a small period (Imperial) as one unheaded group, no sub-headings', () => {
    const authors = [synthAuthor({ id: 'epictetus', period: 'imperial' })];
    const groups = authorGroups('imperial', authors);
    expect(groups).toEqual([{ heading: null, authors }]);
  });

  // ── Synthetic inputs (do not depend on the live registry) ──────────────

  it('returns a populated hellenistic period as one unheaded group of all its authors', () => {
    expect(SCHOOL_GROUP_ORDER.hellenistic).toBeUndefined();
    const authors = [
      synthAuthor({ id: 'z-stoic', period: 'hellenistic', schools: ['stoic'] }),
      synthAuthor({ id: 'a-epicurean', period: 'hellenistic', schools: ['epicurean'] }),
      synthAuthor({ id: 'm-skeptic', period: 'hellenistic', schools: ['skeptic'] }),
    ];
    const groups = authorGroups('hellenistic', authors);
    expect(groups).toEqual([{ heading: null, authors }]);
    expect(groups[0].authors.map((a) => a.id)).toEqual(['z-stoic', 'a-epicurean', 'm-skeptic']);
  });

  // manifests/authors.yaml's school_groups is empty in the zero-works
  // registry (drama fork P0), so SCHOOL_GROUP_ORDER.presocratic is real but
  // has no slots today — these three exercise authorGroups' slot logic
  // against a synthetic order, same idiom as the clustering test above.
  async function authorGroupsWithSyntheticPresocraticOrder() {
    vi.doMock('../lib/registry.generated', async (importOriginal) => ({
      ...(await importOriginal<typeof import('../lib/registry.generated')>()),
      SCHOOL_GROUP_ORDER_DATA: {
        presocratic: [{ school: 'milesian' }, { school: 'eleatic' }],
      },
    }));
    vi.resetModules();
    const fresh = await import('../lib/authors');
    return fresh.authorGroups;
  }

  it('claims a multi-school author exactly once, by the first matching SCHOOL_GROUP_ORDER slot', async () => {
    // milesian is before eleatic in the synthetic SCHOOL_GROUP_ORDER.presocratic
    const groupBy = await authorGroupsWithSyntheticPresocraticOrder();
    const dual = synthAuthor({ id: 'dual-school', schools: ['eleatic', 'milesian'] });
    const groups = groupBy('presocratic', [dual]);
    const seen = groups.flatMap((g) => g.authors.map((a) => a.id));
    expect(seen).toEqual(['dual-school']);
    expect(groups).toEqual([
      { heading: 'Milesians', authors: [dual] },
    ]);
    vi.doUnmock('../lib/registry.generated');
  });

  it('appends an author whose school has an order override but who is not named in it after ranked members', async () => {
    vi.doMock('../lib/registry.generated', async (importOriginal) => ({
      ...(await importOriginal<typeof import('../lib/registry.generated')>()),
      SCHOOL_GROUP_ORDER_DATA: {
        presocratic: [{ school: 'eleatic', order: ['xenophanes', 'parmenides'] }],
      },
    }));
    vi.resetModules();
    const fresh = await import('../lib/authors');
    const ranked = [
      synthAuthor({ id: 'xenophanes', schools: ['eleatic'] }),
      synthAuthor({ id: 'parmenides', schools: ['eleatic'] }),
    ];
    const unranked = synthAuthor({ id: 'late-eleatic', schools: ['eleatic'] });
    const groups = fresh.authorGroups('presocratic', [unranked, ...ranked]);
    const eleatics = groups.find((g) => g.heading === 'Eleatics');
    expect(eleatics?.authors.map((a) => a.id)).toEqual([
      'xenophanes',
      'parmenides',
      'late-eleatic',
    ]);
    vi.doUnmock('../lib/registry.generated');
  });

  it('lands an author with an unknown school in the trailing ungrouped safety-net group', async () => {
    const groupBy = await authorGroupsWithSyntheticPresocraticOrder();
    const known = synthAuthor({ id: 'thales', schools: ['milesian'] });
    const unknown = synthAuthor({ id: 'orphan', schools: ['no-such-school'] });
    const groups = groupBy('presocratic', [known, unknown]);
    expect(groups.map((g) => [g.heading, g.authors.map((a) => a.id)])).toEqual([
      ['Milesians', ['thales']],
      [null, ['orphan']],
    ]);
    vi.doUnmock('../lib/registry.generated');
  });
});

describe('holdingsLabel', () => {
  it('lists work titles for partial holdings', () => {
    expect(holdingsLabel('partial', [
      { title: 'Fragments', workType: 'fragments' },
      { title: 'Testimonia', workType: 'fragments' },
    ])).toBe('Fragments, Testimonia');
  });

  it('returns Complete works when every work is continuous', () => {
    expect(holdingsLabel('complete', [
      { title: 'Meditations', workType: 'continuous' },
      { title: 'Letters', workType: 'continuous' },
    ])).toBe('Complete works');
  });

  it('returns Complete fragments & testimonia when every work is fragments', () => {
    expect(holdingsLabel('complete', [
      { title: 'Fragments', workType: 'fragments' },
      { title: 'Testimonia', workType: 'fragments' },
    ])).toBe('Complete fragments & testimonia');
  });

  it('returns Complete surviving works for a mixed continuous + fragments set', () => {
    expect(holdingsLabel('complete', [
      { title: 'On Nature', workType: 'continuous' },
      { title: 'Fragments', workType: 'fragments' },
    ])).toBe('Complete surviving works');
  });
});

// PUBLIC_READER_FIXTURES gates a sample author+work into the registries (see
// authors.ts/works.ts doc comments) — mirrors the PUBLIC_SHOW_PRIVATE pattern
// already used for copyright-encumbered translations. The flag is read once
// at module load (a top-level const, so Vite/Astro can statically eliminate
// it from a client bundle when off), so exercising both states here requires
// vi.stubEnv + vi.resetModules() + a fresh dynamic import per state.
describe('fixture-flag gating (PUBLIC_READER_FIXTURES)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('excludes the fixture author when the flag is unset', async () => {
    vi.stubEnv('PUBLIC_READER_FIXTURES', '');
    vi.resetModules();
    const fresh = await import('../lib/authors');
    expect(fresh.getAuthor('sample-author')).toBeUndefined();
    expect(fresh.AUTHORS.find((a) => a.id === 'sample-author')).toBeUndefined();
  });

  it('includes the fixture author, pointing at the fixture work, when the flag is set', async () => {
    vi.stubEnv('PUBLIC_READER_FIXTURES', '1');
    vi.resetModules();
    const freshAuthors = await import('../lib/authors');
    const freshWorks = await import('../lib/works');
    const author = freshAuthors.getAuthor('sample-author');
    expect(author).toBeDefined();
    expect(author?.works).toEqual(['sample-work']);
    expect(freshWorks.getWork('sample-work')).toBeDefined();
    expect(freshWorks.getWork('sample-work')?.author).toBe('sample-author');
  });

  it('fixture author has a present, valid holdings value when the flag is set', async () => {
    vi.stubEnv('PUBLIC_READER_FIXTURES', '1');
    vi.resetModules();
    const freshAuthors = await import('../lib/authors');
    const author = freshAuthors.getAuthor('sample-author');
    expect(author).toBeDefined();
    expect(['complete', 'partial']).toContain(author!.holdings);
  });
});

// PUBLIC_WING scopes AUTHORS to one corpus's authors for a P6 standalone wing
// build (docs/p6-plan.md, Settled decision 4) — same module-scope
// import.meta.env read + fresh-dynamic-import idiom as the fixture-flag block
// above. No author mixes works across corpora today, so "aristotle" scopes
// to exactly the two authors owning aristotle-corpus works.
describe('corpus-scoping (PUBLIC_WING)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('leaves AUTHORS unfiltered when unset', async () => {
    vi.stubEnv('PUBLIC_WING', '');
    vi.resetModules();
    const fresh = await import('../lib/authors');
    expect(fresh.AUTHORS.length).toBe(0);
  });

  it('scopes AUTHORS to zero authors when set to aristotle (zero-works registry, drama fork P0)', async () => {
    vi.stubEnv('PUBLIC_WING', 'aristotle');
    vi.resetModules();
    const fresh = await import('../lib/authors');
    expect(fresh.AUTHORS.length).toBe(0);
  });

  it('scopes AUTHORS to zero authors when set to classical (zero-works registry, drama fork P0)', async () => {
    vi.stubEnv('PUBLIC_WING', 'classical');
    vi.resetModules();
    const fresh = await import('../lib/authors');
    expect(fresh.AUTHORS.length).toBe(0);
  });

  it('rides the fixture author along unfiltered when both PUBLIC_WING and PUBLIC_READER_FIXTURES are set', async () => {
    vi.stubEnv('PUBLIC_WING', 'aristotle');
    vi.stubEnv('PUBLIC_READER_FIXTURES', '1');
    vi.resetModules();
    const fresh = await import('../lib/authors');
    expect(fresh.getAuthor('sample-author')).toBeDefined();
    expect(fresh.AUTHORS.map((a) => a.id).sort()).toEqual(['sample-author']);
  });

  it('an unknown corpus id scopes AUTHORS to empty (no author owns a work in it)', async () => {
    vi.stubEnv('PUBLIC_WING', 'no-such-corpus');
    vi.resetModules();
    const fresh = await import('../lib/authors');
    expect(fresh.AUTHORS.length).toBe(0);
  });
});
