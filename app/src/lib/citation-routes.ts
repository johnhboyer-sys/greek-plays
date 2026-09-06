// Build-time citation shim paths. Like built-works.ts, this reads cwd-relative
// files while Astro runs from app/: public/data is the build/dist symlink, and
// corpus mount files live one directory above the app package.
import { existsSync, readFileSync } from 'node:fs';
import { load } from 'js-yaml';
import { getAuthor } from '@shared/lib/authors';
import { WORK_CORPUS_DATA } from '@shared/lib/registry.generated';
import { workSlug } from '@shared/lib/works';
import { builtWorks } from './built-works';

interface CitationIndexEntry {
  work: string;
  book: number;
}

type CitationIndex = Record<string, CitationIndexEntry[]>;

interface MountConfig {
  corpus?: string;
  citationRoutes?: boolean;
}

export interface CitationRoute {
  author: string;
  work: string;
  cite: string;
  bookN: number;
}

const INDEX_PATH = 'public/data/citation-index.json';
const WORK_CORPUS = WORK_CORPUS_DATA as Record<string, string>;

function enabledCorpora(): Set<string> {
  const enabled = new Set<string>();
  for (const corpus of new Set(Object.values(WORK_CORPUS))) {
    const mountPath = `../corpora/${corpus}/mount.yaml`;
    if (!existsSync(mountPath)) continue;
    const config = load(readFileSync(mountPath, 'utf8')) as MountConfig | null;
    if (config?.corpus === corpus && config.citationRoutes === true) enabled.add(corpus);
  }
  return enabled;
}

function buildCitationRoutes(): CitationRoute[] {
  if (!existsSync(INDEX_PATH)) return [];

  const enabled = enabledCorpora();
  if (enabled.size === 0) return [];

  const eligibleWorks = new Map(
    builtWorks()
      .filter((work) => enabled.has(WORK_CORPUS[work.id]))
      .map((work) => [work.id, work]),
  );
  if (eligibleWorks.size === 0) return [];

  const index = JSON.parse(readFileSync(INDEX_PATH, 'utf8')) as CitationIndex;
  const routes: CitationRoute[] = [];

  for (const [cite, entries] of Object.entries(index)) {
    const seenWorks = new Set<string>();
    for (const entry of entries) {
      if (seenWorks.has(entry.work)) continue;
      seenWorks.add(entry.work);

      const work = eligibleWorks.get(entry.work);
      if (!work) continue;
      const author = getAuthor(work.author);
      if (!author) {
        throw new Error(
          `[citation-routes] work '${work.id}' has unresolvable author '${work.author}'`,
        );
      }
      routes.push({ author: author.id, work: workSlug(work), cite, bookN: entry.book });
    }
  }

  return routes;
}

// play-line (P1, docs/p1-probe.md): a static page per PRINTED line would be
// ~1600+ pages for Agamemnon alone (~70k across the eventual 44-play
// corpus) — instead, one static shim page every 50 printed lines (a round
// multiple of 50, e.g. "/aeschylus/agamemnon/1250"), each redirecting to
// the reader's own `?loc=` jump (the reader resolves any OTHER number
// client-side; see shared/components/Reader.svelte's play-line jump
// resolution). Independent of `enabledCorpora()`/`corpora/*/mount.yaml`
// above (a Lyceum-hub-mount concept for the bekker/busse cross-corpus
// index) — the drama site is standalone through P5, so this reads the
// already-built book data directly rather than the hub's citation-index.json
// (which only ever indexes bekker/busse, see scripts/build-citation-
// index.mjs's own `INDEXED_SCHEMES`).
const PLAY_LINE_STRIDE = 50;

interface PlayLineBookLine {
  ref?: string;
  role?: string;
}
interface PlayLineBookData {
  segments: { greek: PlayLineBookLine[] }[];
}

function buildPlayLineStrideRoutes(): CitationRoute[] {
  const routes: CitationRoute[] = [];
  for (const work of builtWorks()) {
    if (work.citation?.scheme !== 'play-line') continue;
    const bookPath = `public/data/${work.id}/book-01.json`;
    if (!existsSync(bookPath)) continue;
    const author = getAuthor(work.author);
    if (!author) {
      throw new Error(
        `[citation-routes] work '${work.id}' has unresolvable author '${work.author}'`,
      );
    }
    const book = JSON.parse(readFileSync(bookPath, 'utf8')) as PlayLineBookData;
    for (const seg of book.segments) {
      for (const line of seg.greek) {
        // A "post N" lacuna line and a lyric range ("106-107") are never
        // stride targets: only a plain printed integer can be an exact
        // multiple of 50 in the first place.
        if (line.role === 'lacuna' || !line.ref || !/^[0-9]+$/.test(line.ref)) continue;
        if (Number(line.ref) % PLAY_LINE_STRIDE === 0) {
          routes.push({ author: author.id, work: workSlug(work), cite: line.ref, bookN: 1 });
        }
      }
    }
  }
  return routes;
}

export const citationRoutes: CitationRoute[] = [
  ...buildCitationRoutes(),
  ...buildPlayLineStrideRoutes(),
];
