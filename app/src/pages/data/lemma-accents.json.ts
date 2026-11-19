// Which printed spellings of a shared folded spelling the search index gave
// which keys (shared/lib/lemma-accents): made at site build by reading the
// word at every posting of every work's lemma index. Served at
// data/lemma-accents.json.
import type { APIRoute } from 'astro';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { publicDir } from 'astro:config/server';
import { segTokens } from '@shared/lib/greek-lines';
import { buildLemmaAccents, type IndexedWork } from '@shared/lib/lemma-accents';
import { greekFold } from '@shared/lib/search';

const dataDir = fileURLToPath(new URL('data/', publicDir));
const readJson = (path: string) => JSON.parse(readFileSync(path, 'utf-8'));

function lemmaMap(): Record<string, (string | string[])[]> {
  const dir = `${dataDir}lemma-map`;
  const out: Record<string, (string | string[])[]> = {};
  if (!existsSync(dir)) return out;
  for (const f of readdirSync(dir).filter(f => f.endsWith('.json')).sort()) Object.assign(out, readJson(`${dir}/${f}`));
  return out;
}

function* works(): Generator<IndexedWork> {
  if (!existsSync(dataDir)) return;
  for (const work of readdirSync(dataDir).sort()) {
    const dir = `${dataDir}${work}/`;
    if (!existsSync(`${dir}search/greek_lemma.json`) || !existsSync(`${dir}search/meta.json`)) continue;
    const segs = new Map<string, Parameters<typeof segTokens>[0]>();
    for (const file of readdirSync(dir).filter(f => /^book-\d+\.json$/.test(f))) {
      for (const s of readJson(`${dir}${file}`).segments ?? []) segs.set(s.id, s);
    }
    const meta: { id: string }[] = readJson(`${dir}search/meta.json`);
    const tokens = meta.map(m => {
      const s = segs.get(m.id);
      return s ? segTokens(s).map(t => t.t) : null;
    });
    yield { lemmaIndex: readJson(`${dir}search/greek_lemma.json`), wordAt: (si, pos) => tokens[si]?.[pos] };
  }
}

const json = (body: unknown) => new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });

export const GET: APIRoute = () => {
  const map = lemmaMap();
  const { table, missing, postings } = buildLemmaAccents(works(), map, greekFold);
  // CI's zero-works and fixture builds carry neither a lemma map nor a search
  // index: there is nothing to narrow, so the table is empty. A map without
  // postings, postings without a map, or an index whose positions the books do
  // not bear out would serve a table that narrows wrongly or not at all: fail
  // the build instead.
  if (!Object.keys(map).length && !postings) return json({});
  if (!Object.keys(map).length || !postings || missing) {
    throw new Error(`lemma-accents: lemma map ${Object.keys(map).length} spellings, ${postings} postings, ${missing} unreadable`);
  }
  return json(table);
};
