import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

// The emitter is a plain .mjs module with no declaration file; the
// directive must sit on the line the checker flags (the specifier).
import {
  toLyceumManifest,
  validateAgainstSchema,
  yearFromName,
  alignmentGrain,
  // @ts-expect-error untyped .mjs module
} from '../../scripts/emit-lyceum-manifest.mjs';

const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const SCHEMA = JSON.parse(
  readFileSync(join(REPO_ROOT, 'schemas', 'lyceum-manifest.v1.json'), 'utf8'),
);

function expectValid(doc: unknown) {
  const errors = validateAgainstSchema(doc, SCHEMA);
  expect(errors).toEqual([]);
}

// Shaped on app/public/data/enchiridion/manifest.json (section, one book).
const ENCHIRIDION_MANIFEST = {
  schema_version: 'manifest.v1',
  id: 'enchiridion',
  author: 'epictetus',
  title: 'Enchiridion',
  language: 'grc',
  route: '/epictetus/enchiridion',
  citation: {
    scheme: 'section',
    books: [{ n: 1, start: '1', end: '53' }],
  },
  editions: [
    {
      language: 'grc',
      edition:
        'Schenkl, H. (ed.), Epicteti dissertationes ab Arriano digestae (Leipzig: Teubner, 1916, repr. 1965)',
      source: { kind: 'tlg', author: '0557', work: '002' },
      license: { status: 'unverified' },
    },
  ],
  translations: [
    {
      id: 'oldfather',
      name: 'W. A. Oldfather (Loeb Classical Library, vol. II, 1928)',
      slot: 'primary',
      default: true,
      alignment: 'archive',
      license: { status: 'unverified' },
    },
    {
      id: 'long',
      name: 'George Long (1877; Bell & Sons, 1890)',
      slot: 'secondary',
      default: false,
      alignment: 'archive',
      license: { status: 'unverified' },
    },
  ],
  apparatus: {
    footnotes: false,
    sidenotes: false,
    paratext: false,
    figures: false,
    sections: true,
    philosophers: false,
  },
  corpus_version: 'c5b8ecf-2026-09-01',
  books: [{ book: 1, segments: 53, first_column: '1', last_column: '53' }],
};

const ENCHIRIDION_WORK = {
  id: 'enchiridion',
  title: 'Enchiridion',
  greekTitle: 'Ἐγχειρίδιον',
  abbr: 'Ench.',
  author: 'epictetus',
  language: 'grc',
  translations: [
    {
      id: 'oldfather',
      name: 'W. A. Oldfather (Loeb Classical Library, vol. II, 1928)',
      short: 'Oldfather',
      slot: 'english',
    },
    {
      id: 'long',
      name: 'George Long (1877; Bell & Sons, 1890)',
      short: 'Long',
      slot: 'secondary',
    },
  ],
};

const EPICTETUS = {
  id: 'epictetus',
  name: 'Epictetus',
  nativeName: 'Ἐπίκτητος',
  floruit: 'c. AD 55–135',
};

// Shaped on app/public/data/meditations/manifest.json (book-section, 12 books).
const MEDITATIONS_MANIFEST = {
  schema_version: 'manifest.v1',
  id: 'meditations',
  author: 'marcus-aurelius',
  title: 'Meditations',
  language: 'grc',
  route: '/marcus-aurelius/meditations',
  citation: {
    scheme: 'book-section',
    books: [
      { n: 1, start: '1.1', end: '1.17' },
      { n: 2, start: '2.1', end: '2.17' },
      { n: 3, start: '3.1', end: '3.16' },
      { n: 4, start: '4.1', end: '4.51' },
      { n: 5, start: '5.1', end: '5.37' },
      { n: 6, start: '6.1', end: '6.59' },
      { n: 7, start: '7.1', end: '7.75' },
      { n: 8, start: '8.1', end: '8.61' },
      { n: 9, start: '9.1', end: '9.42' },
      { n: 10, start: '10.1', end: '10.38' },
      { n: 11, start: '11.1', end: '11.39' },
      { n: 12, start: '12.1', end: '12.36' },
    ],
  },
  editions: [
    {
      language: 'grc',
      edition:
        'Farquharson, A. S. L. (ed.), The Meditations of the Emperor Marcus Aurelius, vol. 1 (Oxford: Clarendon Press, 1944, repr. 1968)',
      source: { kind: 'tlg', author: '0562', work: '001' },
      license: { status: 'unverified' },
    },
  ],
  translations: [
    {
      id: 'haines',
      name: 'C. R. Haines (Loeb Classical Library, 1916)',
      slot: 'primary',
      default: true,
      alignment: 'archive',
      license: { status: 'public-domain-us' },
    },
    {
      id: 'long',
      name: 'George Long (1862)',
      slot: 'secondary',
      default: false,
      alignment: 'archive',
      license: { status: 'unverified' },
    },
  ],
  apparatus: {
    footnotes: false,
    sidenotes: false,
    paratext: false,
    figures: false,
    sections: true,
    philosophers: false,
  },
  corpus_version: 'c5b8ecf-2026-09-01',
  books: [
    { book: 1, segments: 17, first_column: '1.1', last_column: '1.17' },
    { book: 2, segments: 17, first_column: '2.1', last_column: '2.17' },
    { book: 3, segments: 16, first_column: '3.1', last_column: '3.16' },
    { book: 4, segments: 51, first_column: '4.1', last_column: '4.51' },
    { book: 5, segments: 37, first_column: '5.1', last_column: '5.37' },
    { book: 6, segments: 59, first_column: '6.1', last_column: '6.59' },
    { book: 7, segments: 75, first_column: '7.1', last_column: '7.75' },
    { book: 8, segments: 61, first_column: '8.1', last_column: '8.61' },
    { book: 9, segments: 42, first_column: '9.1', last_column: '9.42' },
    { book: 10, segments: 38, first_column: '10.1', last_column: '10.38' },
    { book: 11, segments: 39, first_column: '11.1', last_column: '11.39' },
    { book: 12, segments: 36, first_column: '12.1', last_column: '12.36' },
  ],
};

const MEDITATIONS_WORK = {
  id: 'meditations',
  title: 'Meditations',
  greekTitle: 'Τὰ εἰς ἑαυτόν',
  abbr: 'Med.',
  author: 'marcus-aurelius',
  language: 'grc',
  translations: [
    {
      id: 'haines',
      name: 'C. R. Haines (Loeb Classical Library, 1916)',
      short: 'Haines',
      slot: 'english',
    },
    {
      id: 'long',
      name: 'George Long (1862)',
      short: 'Long',
      slot: 'secondary',
    },
  ],
};

const MARCUS = {
  id: 'marcus-aurelius',
  name: 'Marcus Aurelius',
  nativeName: 'Μᾶρκος Αὐρήλιος',
  floruit: 'AD 121–180',
};

const DE_OFFICIIS_MANIFEST = {
  schema_version: 'manifest.v1',
  id: 'de-officiis',
  author: 'cicero',
  title: 'De Officiis',
  language: 'lat',
  route: '/cicero/de-officiis',
  citation: {
    scheme: 'book-section',
    books: [
      { n: 1, start: '1.1', end: '1.161' },
      { n: 2, start: '2.1', end: '2.90' },
      { n: 3, start: '3.1', end: '3.121' },
    ],
  },
  editions: [
    {
      language: 'lat',
      edition:
        'Atzert, C. (ed.), M. Tulli Ciceronis Scripta Quae Manserunt Omnia, Fasc. 48 (Leipzig: Teubner, 1932)',
      source: { kind: 'phi', author: '0474', work: '055' },
      license: { status: 'unverified' },
    },
  ],
  translations: [
    {
      id: 'miller',
      name: 'Walter Miller (Loeb Classical Library, 1913)',
      slot: 'primary',
      default: true,
      alignment: 'archive',
      license: { status: 'public-domain-us' },
    },
  ],
  apparatus: {
    footnotes: false,
    sidenotes: false,
    paratext: false,
    figures: false,
    sections: true,
    philosophers: false,
  },
  corpus_version: 'c5b8ecf-2026-09-01',
  books: [
    { book: 1, segments: 161, first_column: '1.1', last_column: '1.161' },
    { book: 2, segments: 90, first_column: '2.1', last_column: '2.90' },
    { book: 3, segments: 121, first_column: '3.1', last_column: '3.121' },
  ],
};

const DE_OFFICIIS_WORK = {
  id: 'de-officiis',
  title: 'De Officiis',
  abbr: 'Off.',
  author: 'cicero',
  language: 'lat',
  translations: [
    { id: 'miller', name: 'Walter Miller (Loeb Classical Library, 1913)', short: 'Miller', slot: 'english' },
  ],
};

const CICERO = {
  id: 'cicero',
  name: 'Cicero',
  nativeName: 'Marcus Tullius Cicero',
  floruit: '106–43 BC',
};

// Shaped on build/dist/agamemnon/manifest.json (play-line, one book) --
// Astra lane B F2, owner ruling 2026-09-11: a single-book play reads at its
// bare work route, since app/src/pages/[author]/[work]/book/[n].astro never
// builds a /book/1 page for one.
const AGAMEMNON_MANIFEST = {
  schema_version: 'manifest.v1',
  id: 'agamemnon',
  author: 'aeschylus',
  title: 'Agamemnon',
  language: 'grc',
  route: '/aeschylus/agamemnon',
  citation: {
    scheme: 'play-line',
    books: [{ n: 1, start: '1', end: '1673' }],
  },
  editions: [
    {
      language: 'grc',
      edition: 'Murray, Aeschyli tragoediae, 2nd ed. (OCT, 1955)',
      source: { kind: 'tlg', author: '0085', work: '005' },
      license: { status: 'unverified' },
    },
  ],
  translations: [
    {
      id: 'smyth',
      name: 'Herbert Weir Smyth (Loeb Classical Library, 1926)',
      slot: 'primary',
      default: true,
      alignment: 'archive',
      license: { status: 'public-domain-us' },
    },
  ],
  apparatus: {
    footnotes: false,
    sidenotes: false,
    paratext: false,
    figures: false,
    sections: false,
    philosophers: false,
  },
  corpus_version: 'c5b8ecf-2026-09-01',
  books: [{ book: 1, segments: 226, first_column: '1', last_column: '1672' }],
};

const AGAMEMNON_WORK = {
  id: 'agamemnon',
  title: 'Agamemnon',
  greekTitle: 'Ἀγαμέμνων',
  abbr: 'Ag.',
  author: 'aeschylus',
  language: 'grc',
  translations: [
    {
      id: 'smyth',
      name: 'Herbert Weir Smyth (Loeb Classical Library, 1926)',
      short: 'Smyth',
      slot: 'english',
    },
  ],
};

const AESCHYLUS = {
  id: 'aeschylus',
  name: 'Aeschylus',
  nativeName: 'Αἰσχύλος',
  floruit: 'c. 525–456 BC',
};

describe('toLyceumManifest', () => {
  it('maps the enchiridion (section, one book) fixture', () => {
    const out = toLyceumManifest(ENCHIRIDION_MANIFEST, ENCHIRIDION_WORK, EPICTETUS);

    expect(out.work).toBe('lyceum:epictetus.enchiridion');
    expect(out.author).toBe('Epictetus');
    expect(out.title).toBe('Enchiridion');
    expect(out.latin_title).toBe('Ἐγχειρίδιον');
    expect(out.language).toBe('grc');
    expect(out.date_label).toBe('c. AD 55–135');
    expect(out.route).toBe('/texts/epictetus/enchiridion/');
    expect(out.reading_route).toBe('/read/epictetus/enchiridion/section-1');
    expect(out.reading_route_note).toBeUndefined();
    expect(out.citation).toEqual({
      scheme: 'section',
      ranges: ['1-53'],
      extent: '53 sections',
    });
    expect(out.editions).toEqual([
      {
        id: 'tlg-0557-002',
        reference: true,
        source:
          'Schenkl, H. (ed.), Epicteti dissertationes ab Arriano digestae (Leipzig: Teubner, 1916, repr. 1965) (TLG 0557.002)',
        license: 'unverified',
        verified: false,
      },
    ]);
    expect(out.translations).toEqual([
      {
        id: 'oldfather',
        label: 'Oldfather',
        translator: null,
        date: 1928,
        rights: 'unverified',
        aligned: 'section',
        alignment_method: 'archive',
        default: true,
      },
      {
        id: 'long',
        label: 'Long',
        translator: null,
        date: null,
        rights: 'unverified',
        aligned: 'section',
        alignment_method: 'archive',
        default: false,
      },
    ]);
    expect(out.apparatus).toEqual([
      { id: 'sections', label: 'Section numbers' },
      { id: 'search', label: 'Full-text search' },
      { id: 'lexicon', label: 'Greek dictionary lookup' },
    ]);
    expect(out.schema_version).toBe('1.0');
    expect(out.corpus_version).toBe('2026.09.01-c5b8ecf');
    expect(out.source_manifest).toBe('manifest.json');
    expect(out.generator).toBe('scripts/emit-lyceum-manifest.mjs');
    expect(Object.keys(out)).toEqual([
      'work',
      'author',
      'title',
      'latin_title',
      'language',
      'date_label',
      'route',
      'reading_route',
      'citation',
      'editions',
      'translations',
      'apparatus',
      'schema_version',
      'corpus_version',
      'source_manifest',
      'generator',
    ]);
    expectValid(out);
  });

  it('maps the meditations (book-section, multi-book) fixture', () => {
    const out = toLyceumManifest(MEDITATIONS_MANIFEST, MEDITATIONS_WORK, MARCUS);

    expect(out.work).toBe('lyceum:marcus-aurelius.meditations');
    expect(out.author).toBe('Marcus Aurelius');
    expect(out.latin_title).toBe('Τὰ εἰς ἑαυτόν');
    expect(out.language).toBe('grc');
    expect(out.date_label).toBe('AD 121–180');
    expect(out.route).toBe('/texts/marcus-aurelius/meditations/');
    expect(out.reading_route).toBe('/marcus-aurelius/meditations/book/1');
    expect(out.reading_route_note).toBe(
      'scheme book-section; route grammar for this scheme not yet agreed',
    );
    expect(out.citation.scheme).toBe('book-section');
    expect(out.citation.ranges).toEqual([
      '1.1-1.17',
      '2.1-2.17',
      '3.1-3.16',
      '4.1-4.51',
      '5.1-5.37',
      '6.1-6.59',
      '7.1-7.75',
      '8.1-8.61',
      '9.1-9.42',
      '10.1-10.38',
      '11.1-11.39',
      '12.1-12.36',
    ]);
    expect(out.citation.extent).toBe('12 books · 488 sections');
    expect(out.editions[0]).toEqual({
      id: 'tlg-0562-001',
      reference: true,
      source:
        'Farquharson, A. S. L. (ed.), The Meditations of the Emperor Marcus Aurelius, vol. 1 (Oxford: Clarendon Press, 1944, repr. 1968) (TLG 0562.001)',
      license: 'unverified',
      verified: false,
    });
    expect(out.translations[0]).toEqual({
      id: 'haines',
      label: 'Haines',
      translator: null,
      date: 1916,
      rights: 'public-domain',
      aligned: 'section',
      alignment_method: 'archive',
      default: true,
    });
    expect(out.translations[1].date).toBe(1862);
    expect(out.translations[1].rights).toBe('unverified');
    expect(out.corpus_version).toBe('2026.09.01-c5b8ecf');
    expectValid(out);
  });

  it('maps lat → la, uses the Latin title, and labels the Latin lexicon', () => {
    const out = toLyceumManifest(DE_OFFICIIS_MANIFEST, DE_OFFICIIS_WORK, CICERO);

    expect(out.language).toBe('la');
    expect(out.latin_title).toBe('De Officiis');
    expect(out.work).toBe('lyceum:cicero.de-officiis');
    expect(out.route).toBe('/texts/cicero/de-officiis/');
    expect(out.editions[0].id).toBe('phi-0474-055');
    expect(out.editions[0].source).toContain('(PHI 0474.055)');
    expect(out.translations[0].rights).toBe('public-domain');
    expect(out.editions[0].license).toBe('unverified');
    expect(out.translations[0].date).toBe(1913);
    expect(out.apparatus.at(-1)).toEqual({
      id: 'lexicon',
      label: 'Latin dictionary lookup',
    });
    expect(out.citation.extent).toBe('3 books · 372 sections');
    expectValid(out);
  });

  it('year heuristic: one 1500–2030 match → year; zero or two → null', () => {
    expect(yearFromName('W. A. Oldfather (Loeb Classical Library, vol. II, 1928)')).toBe(1928);
    expect(yearFromName('C. R. Haines (Loeb Classical Library, 1916)')).toBe(1916);
    expect(yearFromName('George Long (1862)')).toBe(1862);
    expect(yearFromName('George Long (1877; Bell & Sons, 1890)')).toBe(null);
    expect(yearFromName('Anonymous')).toBe(null);
    expect(yearFromName('Revised 1499 then 1910')).toBe(1910);
    expect(yearFromName('1910 and 1920 reprints')).toBe(null);

    const noYear = structuredClone(ENCHIRIDION_MANIFEST);
    noYear.translations = [
      {
        id: 'oldfather',
        name: 'W. A. Oldfather',
        slot: 'primary',
        default: true,
        alignment: 'archive',
        license: { status: 'unverified' },
      },
    ];
    const out = toLyceumManifest(noYear, ENCHIRIDION_WORK, EPICTETUS);
    expect(out.translations[0].date).toBe(null);
    expectValid(out);
  });

  it('marks public-domain-us editions verified and maps licensed/unverified', () => {
    const manifest = structuredClone(ENCHIRIDION_MANIFEST);
    manifest.editions[0].license.status = 'public-domain-us';
    const pd = toLyceumManifest(manifest, ENCHIRIDION_WORK, EPICTETUS);
    expect(pd.editions[0].license).toBe('public-domain');
    expect(pd.editions[0].verified).toBe(true);

    manifest.editions[0].license.status = 'licensed';
    const licensed = toLyceumManifest(manifest, ENCHIRIDION_WORK, EPICTETUS);
    expect(licensed.editions[0].license).toBe('licensed');
    expect(licensed.editions[0].verified).toBe(false);
  });

  it('derives work/route/reading_route from our manifest route, not from id or author casing (Aristotle EN)', () => {
    // Shaped on build/dist/EN/manifest.json: id 'EN' routes at
    // /aristotle/nicomachean-ethics (the registry `slug`, not the id
    // lowercased) -- the old id-lowercasing logic produced the dead address
    // /texts/aristotle/en/.
    const manifest = {
      ...ENCHIRIDION_MANIFEST,
      id: 'EN',
      author: 'aristotle',
      title: 'Nicomachean Ethics',
      route: '/aristotle/nicomachean-ethics',
    };
    const work = { ...ENCHIRIDION_WORK, id: 'EN', slug: 'nicomachean-ethics', author: 'aristotle' };
    const author = { id: 'aristotle', name: 'Aristotle', floruit: '384–322 BC' };
    const out = toLyceumManifest(manifest, work, author);
    expect(out.work).toBe('lyceum:aristotle.nicomachean-ethics');
    expect(out.route).toBe('/texts/aristotle/nicomachean-ethics/');
    expect(out.reading_route).toBe('/read/aristotle/nicomachean-ethics/section-1');
    expectValid(out);
  });

  it('throws when our manifest has no route or an unroutable shape', () => {
    const noRoute = { ...ENCHIRIDION_MANIFEST, route: undefined };
    expect(() => toLyceumManifest(noRoute, ENCHIRIDION_WORK, EPICTETUS)).toThrow(
      /missing input: manifest route/,
    );
    const badRoute = { ...ENCHIRIDION_MANIFEST, route: '/epictetus/enchiridion/extra' };
    expect(() => toLyceumManifest(badRoute, ENCHIRIDION_WORK, EPICTETUS)).toThrow(
      /not in \/<author>\/<work> form/,
    );
  });

  it('reads translator from the matching registry translation, defaulting to null', () => {
    const workWithTranslator = {
      ...ENCHIRIDION_WORK,
      translations: [
        { ...ENCHIRIDION_WORK.translations[0], translator: 'W. A. Oldfather' },
        ENCHIRIDION_WORK.translations[1],
      ],
    };
    const out = toLyceumManifest(ENCHIRIDION_MANIFEST, workWithTranslator, EPICTETUS);
    expect(out.translations[0].translator).toBe('W. A. Oldfather');
    expect(out.translations[1].translator).toBeNull();
    expectValid(out);
  });

  it('throws on an unknown author and on a translation without id', () => {
    expect(() => toLyceumManifest(ENCHIRIDION_MANIFEST, ENCHIRIDION_WORK, null)).toThrow(
      /unknown author/,
    );
    const missingId = structuredClone(ENCHIRIDION_MANIFEST);
    delete (missingId.translations[0] as { id?: string }).id;
    expect(() => toLyceumManifest(missingId, ENCHIRIDION_WORK, EPICTETUS)).toThrow(
      /translation missing required id/,
    );
  });

  it('rejects a generated document that fails the partner schema', () => {
    const out = toLyceumManifest(ENCHIRIDION_MANIFEST, ENCHIRIDION_WORK, EPICTETUS);
    const broken = { ...out, route: '/Texts/Epictetus/Enchiridion' };
    const errors = validateAgainstSchema(broken, SCHEMA);
    expect(errors.some((error: { path: string }) => error.path === '/route')).toBe(true);
  });

  it('rejects an unsafe reading_route and a null corpus_version', () => {
    const out = toLyceumManifest(ENCHIRIDION_MANIFEST, ENCHIRIDION_WORK, EPICTETUS);

    const badRoute = { ...out, reading_route: 'javascript:alert(1)' };
    const routeErrors = validateAgainstSchema(badRoute, SCHEMA);
    expect(routeErrors.some((error: { path: string }) => error.path === '/reading_route')).toBe(true);

    const nullCorpusVersion = { ...out, corpus_version: null };
    const corpusErrors = validateAgainstSchema(nullCorpusVersion, SCHEMA);
    expect(corpusErrors.some((error: { path: string }) => error.path === '/corpus_version')).toBe(true);
  });
});

// Alias pages (/read/<author>/<work>/section-<n>) exist only for
// section-scheme works (app/src/pages/read/_section-routes.ts); every other
// scheme routes at the always-built /<author>/<work>/book/<n> reader page.
describe('reading_route grammar by citation scheme', () => {
  const schemeCases: Array<{ scheme: string; expected: string }> = [
    { scheme: 'section', expected: '/read/epictetus/enchiridion/section-1' },
    { scheme: 'book-section', expected: '/epictetus/enchiridion/book/1' },
    { scheme: 'bekker', expected: '/epictetus/enchiridion/book/1' },
    { scheme: 'stephanus', expected: '/epictetus/enchiridion/book/1' },
    { scheme: 'dk', expected: '/epictetus/enchiridion/book/1' },
    { scheme: 'verse-line', expected: '/epictetus/enchiridion/book/1' },
    { scheme: 'letter', expected: '/epictetus/enchiridion/book/1' },
  ];

  it.each(schemeCases)('emits the expected reading_route form for scheme $scheme', ({ scheme, expected }) => {
    const manifest = structuredClone(ENCHIRIDION_MANIFEST);
    manifest.citation = { scheme, books: [{ n: 1, start: '1', end: '53' }] };
    const out = toLyceumManifest(manifest, ENCHIRIDION_WORK, EPICTETUS);
    expect(out.reading_route).toBe(expected);
    if (scheme === 'section') {
      expect(out.reading_route_note).toBeUndefined();
    } else {
      expect(out.reading_route_note).toBe(`scheme ${scheme}; route grammar for this scheme not yet agreed`);
    }
    expectValid(out);
  });
});

// Astra lane B F2, owner ruling 2026-09-11: the fix (F2 in
// build/review/astra/B-findings.md).
describe('reading_route for single-book plays (owner ruling 2026-09-11)', () => {
  it('emits the bare work route for a single-book play-line work', () => {
    const out = toLyceumManifest(AGAMEMNON_MANIFEST, AGAMEMNON_WORK, AESCHYLUS);
    expect(out.reading_route).toBe('/aeschylus/agamemnon');
    expect(out.reading_route_note).toBe(
      'scheme play-line; single-book plays read at the bare work route -- ' +
        'owner ruled the shorter address 2026-09-11, partner to accept it',
    );
    expectValid(out);
  });

  it('keeps /book/<n> for a multi-book play-line work', () => {
    const twoBooks = structuredClone(AGAMEMNON_MANIFEST);
    twoBooks.citation.books = [
      { n: 1, start: '1', end: '800' },
      { n: 2, start: '801', end: '1673' },
    ];
    const out = toLyceumManifest(twoBooks, AGAMEMNON_WORK, AESCHYLUS);
    expect(out.reading_route).toBe('/aeschylus/agamemnon/book/1');
    expect(out.reading_route_note).toBe(
      'scheme play-line; route grammar for this scheme not yet agreed',
    );
    expectValid(out);
  });

  it('schema: accepts the bare-route and /book/<n> forms, rejects a malformed one', () => {
    const bare = toLyceumManifest(AGAMEMNON_MANIFEST, AGAMEMNON_WORK, AESCHYLUS);
    expectValid(bare);

    const withBook = { ...bare, reading_route: '/aeschylus/agamemnon/book/1' };
    expectValid(withBook);

    const malformed = { ...bare, reading_route: '/aeschylus/agamemnon/extra/path' };
    const errors = validateAgainstSchema(malformed, SCHEMA);
    expect(errors.some((error: { path: string }) => error.path === '/reading_route')).toBe(true);
  });
});

describe('alignmentGrain', () => {
  it('maps citation schemes to the partner alignment-grain vocabulary', () => {
    expect(alignmentGrain('section')).toBe('section');
    expect(alignmentGrain('book-section')).toBe('section');
    expect(alignmentGrain('verse-line')).toBe('line');
    expect(alignmentGrain('bekker')).toBe('column');
    expect(alignmentGrain('stephanus')).toBe('column');
    expect(alignmentGrain('dk')).toBe('fragment');
    expect(alignmentGrain('letter')).toBe('letter');
    expect(alignmentGrain('unknown-scheme')).toBeNull();
    expect(alignmentGrain(null)).toBeNull();
  });
});

describe('translation aligned/alignment_method', () => {
  it('emits both null when the translation carries no alignment value', () => {
    const manifest = structuredClone(ENCHIRIDION_MANIFEST);
    delete (manifest.translations[0] as { alignment?: string }).alignment;
    const out = toLyceumManifest(manifest, ENCHIRIDION_WORK, EPICTETUS);
    expect(out.translations[0].aligned).toBeNull();
    expect(out.translations[0].alignment_method).toBeNull();
    expectValid(out);
  });
});
