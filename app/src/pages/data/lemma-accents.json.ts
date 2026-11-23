// Which printed spellings of a shared folded spelling the search index gave
// which keys (shared/lib/lemma-accents): made at site build by reading the
// word at every posting of every work's lemma index. Served at
// data/lemma-accents.json.
import type { APIRoute } from 'astro';
import { fileURLToPath } from 'node:url';
import { publicDir } from 'astro:config/server';
import { buildLemmaAccents } from '@shared/lib/lemma-accents';
import { greekFold } from '@shared/lib/search';
import { lemmaMap, works } from '../../lib/lemma-accents-data';

const dataDir = fileURLToPath(new URL('data/', publicDir));

const json = (body: unknown) => new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });

export const GET: APIRoute = () => {
  const map = lemmaMap(dataDir);
  const { table, missing, postings } = buildLemmaAccents(works(dataDir), map, greekFold);
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
