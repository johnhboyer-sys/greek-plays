import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, beforeEach, describe, expect, it } from 'vitest';
import { buildLemmaAccents } from '@shared/lib/lemma-accents';
import { greekFold } from '@shared/lib/search';
import { lemmaMap, works } from '../lib/lemma-accents-data';

// The endpoint reads public/data at build; here, a temporary tree.
const root = mkdtempSync(join(tmpdir(), 'lemma-accents-'));
const dataDir = join(root, 'data') + '/';

const put = (rel: string, data: unknown) => {
  const path = join(root, 'data', rel);
  mkdirSync(join(path, '..'), { recursive: true });
  writeFileSync(path, JSON.stringify(data));
};
const segment = (words: string[]) => ({ segments: [{ id: 's1', greek: [{ n: 1, tokens: words.map(t => ({ t })) }] }] });

// One play: the reference text prints αὐτή as αὐτός and αὕτη as οὗτος.
function play(dir: string, words: string[], index: Record<string, [number, number][]>, meta = true) {
  put(`${dir}/book-01.json`, segment(words));
  put(`${dir}/search/greek_lemma.json`, index);
  if (meta) put(`${dir}/search/meta.json`, [{ id: 's1' }]);
}

const build = () => buildLemmaAccents(works(dataDir), lemmaMap(dataDir), greekFold);
const table = () => build().table;

beforeEach(() => {
  rmSync(join(root, 'data'), { recursive: true, force: true });
  put('lemma-map/a.json', { auth: [['outos', 'ou(=tos'], ['autos', 'au)to/s']] });
  play('persians', ['αὐτή', 'αὕτη'], { autos: [[0, 0]], outos: [[0, 1]] });
});
afterAll(() => rmSync(root, { recursive: true, force: true }));

describe('the lemma-accents table, from the data tree', () => {
  it('narrows by the reference text alone', () => {
    expect(table().auth).toEqual({ 'αὐτή': ['auth', 'autos'], 'αὕτη': ['auth', 'outos'] });
  });

  // An edition is searched through the same table, so what its index gives a
  // spelling must count: here it gives αὐτή οὗτος, and narrowing αὐτή to
  // αὐτός would lose that hit in the edition.
  it("reads a Greek edition's index as well", () => {
    play('persians/ed/oct', ['αὐτή'], { outos: [[0, 0]] });
    expect(table().auth).toEqual({ 'αὕτη': ['auth', 'outos'] });
  });

  it('counts an edition word it cannot read', () => {
    play('persians/ed/oct', ['αὐτή'], { outos: [[0, 3]] });
    expect(build().missing).toBe(1);
  });

  it('fails on a lemma index without meta.json', () => {
    play('persians/ed/oct', ['αὐτή'], { outos: [[0, 0]] }, false);
    expect(table).toThrow(/persians\/ed\/oct has a lemma index but no search\/meta\.json/);
  });
});
