// Partner-catalog alias routes: /texts/<author>/<work>/ (one per built work,
// see src/pages/texts/[author]/[work]/index.astro) and
// /read/<author>/<work>/section-<n>/ (one per section of every flat
// section-scheme work, see src/pages/read/_section-routes.ts and
// src/pages/read/[author]/[work]/section-[n].astro). built-works.ts and
// _section-routes.ts check cwd-relative public/data/... with the real fs
// (same convention as built-works.test.ts), so each test chdirs into a temp
// dir seeded with exactly the manifest.json/columns.json it wants "built".
//
// The zero-works registry (drama fork P0, docs/plan.md §1) carries no real
// section-scheme work (Epictetus' Enchiridion is gone along with the rest of
// the CPR corpus), so a fixture registry stands in for the section-scheme
// and book-section-scheme works these routes dispatch on.
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

vi.mock('@shared/lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@shared/lib/works')>();
  const fixtures = [
    { id: 'section-work', title: 'Section Work', abbr: 'SW', author: 'fixture-author', citation: { scheme: 'section' } },
    { id: 'book-section-work', title: 'Book Section Work', abbr: 'BSW', author: 'fixture-author', citation: { scheme: 'book-section' } },
  ];
  const byId = new Map(fixtures.map((w) => [w.id, w]));
  return {
    ...actual,
    WORKS: [...actual.WORKS, ...fixtures],
    getWork: (id: string) => byId.get(id) ?? actual.getWork(id),
    workSlug: (w: { id: string; slug?: string }) => w.slug ?? w.id,
  };
});
vi.mock('@shared/lib/authors', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@shared/lib/authors')>();
  const fixtureAuthor = { id: 'fixture-author', name: 'Fixture Author', works: ['section-work', 'book-section-work'] };
  return {
    ...actual,
    getAuthor: (id: string) => (id === 'fixture-author' ? fixtureAuthor : actual.getAuthor(id)),
  };
});

const realCwd = process.cwd();

function seed(files: Record<string, Record<string, unknown>>) {
  const dir = mkdtempSync(path.join(tmpdir(), 'alias-routes-'));
  for (const [workId, columns] of Object.entries(files)) {
    const workDir = path.join(dir, 'public', 'data', workId);
    mkdirSync(workDir, { recursive: true });
    writeFileSync(path.join(workDir, 'manifest.json'), '{}');
    writeFileSync(path.join(workDir, 'columns.json'), JSON.stringify(columns));
  }
  process.chdir(dir);
}

async function load() {
  vi.resetModules();
  const builtWorks = (await import('../lib/built-works')).builtWorks;
  const sectionRoutes = (await import('../pages/read/_section-routes')).sectionRoutes;
  return { builtWorks, sectionRoutes };
}

beforeEach(() => {
  vi.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
  process.chdir(realCwd);
});

describe('texts/[author]/[work] route set', () => {
  it('yields exactly one /texts/ path per built work, matching [author]/[work]/index.astro\'s own getStaticPaths mapping', async () => {
    seed({ 'section-work': { '1': [{ book: 1 }] }, 'book-section-work': { '1.1': [{ book: 1 }] } });
    const { builtWorks } = await load();
    const { getAuthor } = await import('@shared/lib/authors');
    const { workSlug } = await import('@shared/lib/works');
    const works = builtWorks();
    expect(works.length).toBeGreaterThan(0);
    const paths = works.map((w) => {
      const author = getAuthor(w.author);
      expect(author, `work '${w.id}' must resolve to a known author`).toBeTruthy();
      return { author: author!.id, work: workSlug(w) };
    });
    expect(paths).toHaveLength(works.length);
    const keys = paths.map((p) => `${p.author}/${p.work}`);
    expect(new Set(keys).size).toBe(keys.length); // no two works collide on the same alias URL
  });
});

describe('[author]/[work]/[cite] play-line stride route set', () => {
  it('emits and deduplicates a multiple of 50 contained in a printed range', async () => {
    seed({ agamemnon: {} });
    const workDir = path.join(process.cwd(), 'public', 'data', 'agamemnon');
    writeFileSync(path.join(workDir, 'book-01.json'), JSON.stringify({
      segments: [
        { greek: [{ ref: '147-150' }, { ref: '150' }] },
      ],
    }));
    vi.resetModules();
    const { citationRoutes } = await import('../lib/citation-routes');
    const matches = citationRoutes.filter(
      (route) => route.author === 'aeschylus' && route.work === 'agamemnon' && route.cite === '150',
    );
    expect(matches).toEqual([
      { author: 'aeschylus', work: 'agamemnon', cite: '150', bookN: 1 },
    ]);
  });
});

describe('read/[author]/[work]/section-[n] route set', () => {
  it('yields one section-N page for every section of a section-scheme work, gapped numbering included', async () => {
    // Regression guard for the Vatican Sayings-style gap (a real CPR-corpus
    // fact, now gone with the corpus — the mechanism it exercised is
    // reproduced here with a synthetic gap instead): section "2" is
    // deliberately absent, matching a real gapped ancient numbering.
    seed({ 'section-work': { '1': [{ book: 1 }], '3': [{ book: 1 }], '4': [{ book: 1 }] } });
    const { sectionRoutes } = await load();
    const routes = sectionRoutes().filter((r) => r.author === 'fixture-author' && r.work === 'section-work');
    const ns = routes.map((r) => r.n).sort();
    expect(ns).toEqual(['1', '3', '4']);
    expect(routes.every((r) => r.bookN === 1)).toBe(true);
  });

  it('emits no /read/ pages for a book-section-scheme work', async () => {
    seed({ 'book-section-work': { '1.1': [{ book: 1 }] } });
    const { sectionRoutes } = await load();
    const routes = sectionRoutes().filter((r) => r.work === 'book-section-work');
    expect(routes).toHaveLength(0);
  });

  it('emits, per section-scheme work, exactly the section tokens present as keys in that work\'s columns.json (handles gapped numbering)', async () => {
    // Regression guard for the Vatican Sayings-style gap: routes must come
    // from columns.json's real keys, never a contiguous manifest start..end
    // range that would point ?loc= at a non-existent col-<n> anchor. A
    // "nonempty" check would pass even if the route set diverged from
    // columns.json (e.g. included a stale or missing token); set equality is
    // the real assertion.
    const columns = { '1': [{ book: 1 }], '2': [{ book: 1 }], '5': [{ book: 1 }] };
    seed({ 'section-work': columns });
    const { builtWorks, sectionRoutes } = await load();
    const sectionWorks = builtWorks().filter((w) => w.citation?.scheme === 'section');
    expect(sectionWorks.length).toBeGreaterThan(0);
    const routes = sectionRoutes();
    for (const work of sectionWorks) {
      const { getAuthor } = await import('@shared/lib/authors');
      const { workSlug } = await import('@shared/lib/works');
      const author = getAuthor(work.author)!;
      const slug = workSlug(work);
      const expectedTokens = new Set(Object.keys(JSON.parse(
        (await import('node:fs')).readFileSync(`public/data/${work.id}/columns.json`, 'utf8'),
      )));
      const actualTokens = new Set(
        routes.filter((r) => r.author === author.id && r.work === slug).map((r) => r.n),
      );
      expect(actualTokens, `${author.id}/${slug} section token set`).toEqual(expectedTokens);
    }
  });
});
