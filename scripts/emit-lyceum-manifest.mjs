// Build-time view of each work's manifest.json for the partner WordPress
// plugin (Lyceum Reader Manager 0.5.0). Our manifest.json stays the
// authority; this file is derived and never hand-maintained.
//
// Validation approach mirrors pipeline/drama_pipeline/validate_contracts.py:
// walk <dist>/*/manifest.json, load a draft 2020-12 schema, fail the run on
// the first invalid instance. Node has no jsonschema package in this repo,
// so validateAgainstSchema implements the dialect features this schema uses.

import { existsSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const GENERATED_REGISTRY = join(ROOT, 'shared', 'lib', 'registry.generated.ts');
const SCHEMA_PATH = join(ROOT, 'schemas', 'lyceum-manifest.v1.json');
const DEFAULT_DIST = join(ROOT, 'build', 'dist');

const WORK_PATTERN = /^lyceum:[a-z0-9-]+\.[a-z0-9-]+$/;
const ROUTE_PATTERN = /^\/texts\/[a-z0-9-]+\/[a-z0-9-]+\/$/;

const KIND_LABEL = { tlg: 'TLG', phi: 'PHI' };

const LICENSE_STATUS = {
  'public-domain-us': 'public-domain',
  licensed: 'licensed',
  unverified: 'unverified',
};

// Partner apparatus labels, in the order the template listed them.
const APPARATUS_LABELS = [
  ['sections', 'Section numbers'],
  ['footnotes', 'Footnotes'],
  ['sidenotes', 'Marginal notes'],
  ['paratext', 'Editorial headings'],
  ['figures', 'Figures'],
  ['philosophers', 'Philosopher index'],
];

export const LYCEUM_KEY_ORDER = [
  'work',
  'author',
  'title',
  'latin_title',
  'language',
  'date_label',
  'route',
  'reading_route',
  'reading_route_note',
  'citation',
  'editions',
  'translations',
  'apparatus',
  'schema_version',
  'corpus_version',
  'source_manifest',
  'generator',
];

export function parseArgs(argv) {
  let dist = DEFAULT_DIST;
  let work = null;
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--dist') {
      const value = argv[++i];
      if (!value) throw new Error('--dist requires a directory');
      dist = resolve(value);
    } else if (arg === '--work') {
      const value = argv[++i];
      if (!value) throw new Error('--work requires a work id');
      work = value;
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  return { dist, work };
}

export function mapLanguage(language) {
  if (language === 'grc') return 'grc';
  if (language === 'lat') return 'la';
  return null;
}

export function mapLicense(status) {
  if (status == null) return null;
  return Object.hasOwn(LICENSE_STATUS, status) ? LICENSE_STATUS[status] : null;
}

// Stopgap: take a four-digit year from the translation `name` only when the
// string contains exactly one number in 1500–2030. Zero or two-or-more
// matches → null (the partner sees the gap rather than a guessed year).
export function yearFromName(name) {
  if (typeof name !== 'string') return null;
  const matches = name.match(/\d{4}/g) ?? [];
  const years = matches.map(Number).filter((year) => year >= 1500 && year <= 2030);
  return years.length === 1 ? years[0] : null;
}

export function reorderCorpusVersion(ours) {
  if (typeof ours !== 'string') return null;
  const match = /^(.*)-(\d{4})-(\d{2})-(\d{2})$/.exec(ours);
  if (!match) return null;
  return `${match[2]}.${match[3]}.${match[4]}-${match[1]}`;
}

export function latinTitle(ourManifest, work) {
  if (typeof work?.greekTitle === 'string' && work.greekTitle.length > 0) {
    return work.greekTitle;
  }
  if (ourManifest?.language === 'lat' || work?.language === 'lat') {
    return ourManifest?.title ?? null;
  }
  return null;
}

export function countNullFields(value, counts = {}) {
  if (value === null) return counts;
  if (Array.isArray(value)) {
    for (const item of value) countNullFields(item, counts);
    return counts;
  }
  if (value && typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) {
      if (child === null) {
        counts[key] = (counts[key] ?? 0) + 1;
      } else {
        countNullFields(child, counts);
      }
    }
  }
  return counts;
}

// Our own manifest.route is the route-ownership authority (never the id or
// author fields, which can diverge from it -- e.g. Aristotle's EN id routes
// at /aristotle/nicomachean-ethics). Segments come back lowercased only when
// they aren't already -- the route/reading_route fields below use the route
// string verbatim, so a non-lowercase route fails the partner's ROUTE_PATTERN
// check further down rather than being silently normalized here.
function routeSegments(ourManifest) {
  const route = ourManifest?.route;
  if (typeof route !== 'string') {
    throw new Error(`missing input: manifest route (got ${JSON.stringify(route)})`);
  }
  const match = /^\/([^/]+)\/([^/]+)$/.exec(route);
  if (!match) {
    throw new Error(`missing input: manifest route ${JSON.stringify(route)} is not in /<author>/<work> form`);
  }
  const lower = (value) => (value === value.toLowerCase() ? value : value.toLowerCase());
  return { authorSegment: lower(match[1]), workSegment: lower(match[2]) };
}

function citationBooks(ourManifest) {
  const books = ourManifest?.citation?.books;
  return Array.isArray(books) ? books : [];
}

function topLevelBooks(ourManifest) {
  const books = ourManifest?.books;
  return Array.isArray(books) ? books : [];
}

// `book.start`/`book.end` already carry the book-dotted column ("1.1") for
// book-section works; a flat scheme's single book carries the bare column
// ("1"). Either way the range is the column pair verbatim -- prepending
// book.n again (the old behaviour) double-counted the book for book-section
// works, yielding "1.1.1-1.1.17" instead of "1.1-1.17".
function citationRanges(books) {
  return books.map((book) => `${book.start}-${book.end}`);
}

function citationExtent(books) {
  if (books.length === 0) return null;
  const counts = books.map((book) => book.segments);
  if (counts.some((count) => typeof count !== 'number')) return null;
  if (books.length === 1) return `${counts[0]} sections`;
  const total = counts.reduce((sum, count) => sum + count, 0);
  return `${books.length} books · ${total} sections`;
}

function editionView(edition) {
  const source = edition?.source ?? {};
  const kind = source.kind;
  const author = source.author;
  const work = source.work;
  const id =
    kind && author && work ? `${kind}-${author}-${work}` : null;
  const kindLabel = KIND_LABEL[kind] ?? null;
  const sourceText =
    edition?.edition && kindLabel && author && work
      ? `${edition.edition} (${kindLabel} ${author}.${work})`
      : null;
  const status = edition?.license?.status;
  return {
    id,
    source: sourceText,
    license: mapLicense(status),
    verified: status === 'public-domain-us',
  };
}

// The partner template's `aligned` is the alignment GRAIN (a citation unit:
// "section", "line", ...), not our internal alignment strategy name
// (archive/freeman/chapter_concordance/...). Map scheme -> grain here; the
// strategy itself moves to the additive `alignment_method` field so it isn't
// lost, just relabeled to the right slot.
const ALIGNMENT_GRAIN_BY_SCHEME = {
  section: 'section',
  'book-section': 'section',
  'verse-line': 'line',
  bekker: 'column',
  stephanus: 'column',
  dk: 'fragment',
  letter: 'letter',
};

export function alignmentGrain(scheme) {
  return Object.hasOwn(ALIGNMENT_GRAIN_BY_SCHEME, scheme) ? ALIGNMENT_GRAIN_BY_SCHEME[scheme] : null;
}

function translationView(translation, work, scheme) {
  if (!translation?.id) {
    throw new Error('translation missing required id');
  }
  const refs = Array.isArray(work?.translations) ? work.translations : [];
  const ref = refs.find((entry) => entry?.id === translation.id) ?? {};
  const translator = Object.hasOwn(ref, 'translator') ? ref.translator : null;
  const hasAlignment = translation.alignment != null;
  return {
    id: translation.id,
    label: ref.short ?? null,
    translator,
    date: yearFromName(translation.name),
    rights: mapLicense(translation.license?.status),
    aligned: hasAlignment ? alignmentGrain(scheme) : null,
    alignment_method: hasAlignment ? translation.alignment : null,
    default: typeof translation.default === 'boolean' ? translation.default : null,
  };
}

function apparatusView(ourManifest, language) {
  const flags = ourManifest?.apparatus && typeof ourManifest.apparatus === 'object'
    ? ourManifest.apparatus
    : {};
  const items = [];
  for (const [id, label] of APPARATUS_LABELS) {
    if (flags[id] === true) items.push({ id, label });
  }
  items.push({ id: 'search', label: 'Full-text search' });
  if (language === 'grc') {
    items.push({ id: 'lexicon', label: 'Greek dictionary lookup' });
  } else if (language === 'la') {
    items.push({ id: 'lexicon', label: 'Latin dictionary lookup' });
  }
  return items;
}

function ordered(object) {
  const out = {};
  for (const key of LYCEUM_KEY_ORDER) {
    if (Object.hasOwn(object, key) && object[key] !== undefined) {
      out[key] = object[key];
    }
  }
  for (const [key, value] of Object.entries(object)) {
    if (!Object.hasOwn(out, key) && value !== undefined) out[key] = value;
  }
  return out;
}

export function toLyceumManifest(ourManifest, work, author) {
  if (!ourManifest || typeof ourManifest !== 'object') {
    throw new Error('missing input: our manifest');
  }
  if (!work || typeof work !== 'object') {
    throw new Error(`missing input: registry work '${ourManifest.id ?? '<unknown>'}'`);
  }
  if (!author || typeof author !== 'object' || !author.name) {
    throw new Error(`unknown author '${ourManifest.author ?? '<missing>'}'`);
  }

  const { authorSegment, workSegment } = routeSegments(ourManifest);
  const workKey = `lyceum:${authorSegment}.${workSegment}`;
  const route = `/texts${ourManifest.route}/`;
  if (!WORK_PATTERN.test(workKey)) {
    throw new Error(`work ${JSON.stringify(workKey)} fails partner rules`);
  }
  if (!ROUTE_PATTERN.test(route)) {
    throw new Error(`route ${JSON.stringify(route)} fails partner rules`);
  }

  const language = mapLanguage(ourManifest.language);
  const books = citationBooks(ourManifest);
  const scheme = ourManifest.citation?.scheme ?? null;
  // Alias pages (/read/<author>/<work>/section-<n>) exist ONLY for
  // section-scheme works -- see app/src/pages/read/_section-routes.ts. Every
  // other scheme has no alias page, so pointing reading_route at the alias
  // form would advertise a 404; point it at the real, always-built reader
  // page instead (app/src/pages/[author]/[work]/book/[n].astro generates
  // /<author>/<work>/book/<n> for every work, n=1..books). The alias-form
  // grammar for non-section schemes is not yet agreed with the partner --
  // reading_route_note carries that caveat below.
  const readingRoute =
    scheme === 'section'
      ? books[0]?.start != null
        ? `/read${ourManifest.route}/section-${books[0].start}`
        : null
      : books[0]?.n != null
        ? `${ourManifest.route}/book/${books[0].n}`
        : null;

  const result = {
    work: workKey,
    author: author.name,
    title: ourManifest.title ?? null,
    latin_title: latinTitle(ourManifest, work),
    language,
    date_label: author.floruit ?? null,
    route,
    reading_route: readingRoute,
    citation: {
      scheme,
      ranges: citationRanges(books),
      extent: citationExtent(topLevelBooks(ourManifest)),
    },
    editions: Array.isArray(ourManifest.editions)
      ? ourManifest.editions.map(editionView)
      : [],
    translations: Array.isArray(ourManifest.translations)
      ? ourManifest.translations.map((entry) => translationView(entry, work, scheme))
      : [],
    apparatus: apparatusView(ourManifest, language),
    schema_version: '1.0',
    corpus_version: reorderCorpusVersion(ourManifest.corpus_version),
    source_manifest: 'manifest.json',
    generator: 'scripts/emit-lyceum-manifest.mjs',
  };

  if (scheme && scheme !== 'section') {
    result.reading_route_note =
      `scheme ${scheme}; route grammar for this scheme not yet agreed`;
  }

  return ordered(result);
}

function jsonType(value) {
  if (value === null) return 'null';
  if (Array.isArray(value)) return 'array';
  if (typeof value === 'number') return Number.isInteger(value) ? 'integer' : 'number';
  return typeof value;
}

function resolveRef(schema, root) {
  if (!schema || typeof schema !== 'object' || typeof schema.$ref !== 'string') {
    return schema;
  }
  const ref = schema.$ref;
  if (!ref.startsWith('#/')) {
    throw new Error(`unsupported $ref: ${ref}`);
  }
  let current = root;
  for (const part of ref.slice(2).split('/')) {
    current = current?.[part];
  }
  if (current == null) throw new Error(`unresolved $ref: ${ref}`);
  return current;
}

function pointer(path) {
  return path === '' ? '/' : path;
}

export function validateAgainstSchema(instance, schema, root = schema, path = '') {
  const resolved = resolveRef(schema, root);
  const errors = [];
  const fail = (message, at = path) => {
    errors.push({ path: pointer(at), message });
  };

  if (resolved.const !== undefined && instance !== resolved.const) {
    fail(`must be ${JSON.stringify(resolved.const)}`);
  }
  if (Array.isArray(resolved.enum) && !resolved.enum.includes(instance)) {
    fail(`must be one of ${resolved.enum.map((value) => JSON.stringify(value)).join(', ')}`);
  }

  if (resolved.type !== undefined) {
    const types = Array.isArray(resolved.type) ? resolved.type : [resolved.type];
    const actual = jsonType(instance);
    const ok = types.some((type) => {
      if (type === 'number') return actual === 'number' || actual === 'integer';
      return actual === type;
    });
    if (!ok) fail(`must be type ${types.join('|')}, got ${actual}`);
  }

  if (typeof instance === 'string') {
    if (typeof resolved.minLength === 'number' && instance.length < resolved.minLength) {
      fail(`shorter than minLength ${resolved.minLength}`);
    }
    if (typeof resolved.pattern === 'string' && !new RegExp(resolved.pattern).test(instance)) {
      fail(`does not match pattern ${resolved.pattern}`);
    }
  }

  const isObject = instance !== null && typeof instance === 'object' && !Array.isArray(instance);
  if (isObject) {
    for (const key of resolved.required ?? []) {
      if (!Object.hasOwn(instance, key)) fail('is required', `${path}/${key}`);
    }
    const properties = resolved.properties ?? {};
    for (const [key, value] of Object.entries(instance)) {
      if (Object.hasOwn(properties, key)) {
        errors.push(...validateAgainstSchema(value, properties[key], root, `${path}/${key}`));
      } else if (resolved.additionalProperties === false) {
        fail('additional property not allowed', `${path}/${key}`);
      } else if (resolved.additionalProperties && typeof resolved.additionalProperties === 'object') {
        errors.push(
          ...validateAgainstSchema(value, resolved.additionalProperties, root, `${path}/${key}`),
        );
      }
    }
  }

  if (Array.isArray(instance)) {
    if (typeof resolved.minItems === 'number' && instance.length < resolved.minItems) {
      fail(`fewer than minItems ${resolved.minItems}`);
    }
    if (resolved.items) {
      instance.forEach((item, index) => {
        errors.push(...validateAgainstSchema(item, resolved.items, root, `${path}/${index}`));
      });
    }
  }

  return errors;
}

export function loadLyceumSchema(root = ROOT) {
  return JSON.parse(readFileSync(join(root, 'schemas', 'lyceum-manifest.v1.json'), 'utf8'));
}

export function formatNullCounts(counts) {
  const names = Object.keys(counts).sort((a, b) => a.localeCompare(b));
  if (names.length === 0) return 'null fields: (none)';
  return `null fields: ${names.map((name) => `${name}=${counts[name]}`).join(' ')}`;
}

async function loadRegistry() {
  try {
    return await import(pathToFileURL(GENERATED_REGISTRY).href);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(
      `could not import ${GENERATED_REGISTRY}. Run node scripts/build-registry.mjs first. ${message}`,
    );
  }
}

function listManifests(dist, workId) {
  if (!existsSync(dist)) {
    throw new Error(`missing input: dist directory ${dist} does not exist`);
  }
  if (workId) {
    const path = join(dist, workId, 'manifest.json');
    if (!existsSync(path)) {
      throw new Error(`missing input: ${path}`);
    }
    return [path];
  }
  const found = readdirSync(dist, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => join(dist, entry.name, 'manifest.json'))
    .filter((path) => existsSync(path))
    .sort((a, b) => a.localeCompare(b));
  // A zero-works build (docs/plan.md §1: manifests/* stripped to
  // authors.yaml only) legitimately emits no work manifest.json at all --
  // not a bug to fail loudly on (an explicit --work with no match still is,
  // handled above).
  return found;
}

export async function main(argv = process.argv.slice(2)) {
  const { dist, work: workFilter } = parseArgs(argv);
  const schema = JSON.parse(readFileSync(SCHEMA_PATH, 'utf8'));
  const registry = await loadRegistry();
  const worksById = new Map(registry.CORPUS_WORKS.map((entry) => [entry.id, entry]));
  const authorsById = new Map(registry.CORPUS_AUTHORS.map((entry) => [entry.id, entry]));

  const paths = listManifests(dist, workFilter);
  const totals = {};
  let failed = false;

  for (const path of paths) {
    const workDir = dirname(path);
    const workId = workDir.slice(dist.length).replace(/^[/\\]/, '');
    let ourManifest;
    try {
      ourManifest = JSON.parse(readFileSync(path, 'utf8'));
    } catch (error) {
      console.error(`ERROR ${path}: missing input (${error instanceof Error ? error.message : error})`);
      failed = true;
      continue;
    }

    const id = ourManifest.id ?? workId;
    const author = authorsById.get(ourManifest.author);
    if (!author) {
      console.error(`ERROR ${id}: unknown author '${ourManifest.author}'`);
      failed = true;
      continue;
    }
    const work = worksById.get(ourManifest.id);
    if (!work) {
      console.error(`ERROR ${id}: missing input: registry work '${ourManifest.id}'`);
      failed = true;
      continue;
    }

    let lyceum;
    try {
      lyceum = toLyceumManifest(ourManifest, work, author);
    } catch (error) {
      console.error(`ERROR ${id}: ${error instanceof Error ? error.message : error}`);
      failed = true;
      continue;
    }

    const errors = validateAgainstSchema(lyceum, schema);
    if (errors.length) {
      for (const error of errors) {
        console.error(`ERROR ${id} ${error.path}: ${error.message}`);
      }
      failed = true;
      continue;
    }

    const outPath = join(workDir, 'manifest.lyceum.json');
    writeFileSync(outPath, `${JSON.stringify(lyceum, null, 2)}\n`);
    const nulls = countNullFields(lyceum);
    for (const [name, count] of Object.entries(nulls)) {
      totals[name] = (totals[name] ?? 0) + count;
    }
    const nullSummary = Object.keys(nulls).length
      ? ` ${formatNullCounts(nulls)}`
      : '';
    console.log(`${id} ${lyceum.work}${nullSummary}`);
  }

  console.log(formatNullCounts(totals));
  return failed ? 1 : 0;
}

const isMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) process.exitCode = await main();
