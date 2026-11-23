// The lemma-accents table's inputs, read from a built data tree (the endpoint
// src/pages/data/lemma-accents.json.ts passes public/data/).
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { segTokens } from '@shared/lib/greek-lines';
import type { IndexedWork } from '@shared/lib/lemma-accents';

const readJson = (path: string) => JSON.parse(readFileSync(path, 'utf-8'));

export function lemmaMap(dataDir: string): Record<string, (string | string[])[]> {
  const dir = `${dataDir}lemma-map`;
  const out: Record<string, (string | string[])[]> = {};
  if (!existsSync(dir)) return out;
  for (const f of readdirSync(dir).filter(f => f.endsWith('.json')).sort()) Object.assign(out, readJson(`${dir}/${f}`));
  return out;
}

// One index: a play's own, or a Greek edition's under <play>/ed/<id>/, which
// has the same layout and is searched through the same table.
function indexed(dir: string, name: string): IndexedWork | null {
  if (!existsSync(`${dir}search/greek_lemma.json`)) return null;
  // Without its segment list no posting's word can be read: fail, not skip.
  if (!existsSync(`${dir}search/meta.json`)) throw new Error(`lemma-accents: ${name} has a lemma index but no search/meta.json`);
  const segs = new Map<string, Parameters<typeof segTokens>[0]>();
  for (const file of readdirSync(dir).filter(f => /^book-\d+\.json$/.test(f))) {
    for (const s of readJson(`${dir}${file}`).segments ?? []) segs.set(s.id, s);
  }
  const meta: { id: string }[] = readJson(`${dir}search/meta.json`);
  const tokens = meta.map(m => {
    const s = segs.get(m.id);
    return s ? segTokens(s).map(t => t.t) : null;
  });
  return { lemmaIndex: readJson(`${dir}search/greek_lemma.json`), wordAt: (si, pos) => tokens[si]?.[pos] };
}

export function* works(dataDir: string): Generator<IndexedWork> {
  if (!existsSync(dataDir)) return;
  for (const work of readdirSync(dataDir).sort()) {
    const dir = `${dataDir}${work}/`;
    const own = indexed(dir, work);
    if (own) yield own;
    if (!existsSync(`${dir}ed`)) continue;
    for (const ed of readdirSync(`${dir}ed`).sort()) {
      const edition = indexed(`${dir}ed/${ed}/`, `${work}/ed/${ed}`);
      if (edition) yield edition;
    }
  }
}
