import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  decodeOffsets, fetchLemmaPickerShard, fetchLemmaGlosses, fetchNgramShard,
  fetchNgramOccurrences, fetchSearchOffsets, fetchEnglishSegments,
} from '../lib/data';

afterEach(() => {
  vi.unstubAllGlobals();
  delete (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__;
});

function stubFetch(body: unknown, ok = true) {
  const fn = vi.fn(async (_url: string) => ({ ok, status: ok ? 200 : 404, json: async () => body }));
  vi.stubGlobal('fetch', fn);
  return fn;
}

describe('search step 2 fetchers', () => {
  it('route every file through the data-root override', async () => {
    (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__ = 'https://data.example';
    const fn = stubFetch({ logos: { n: 3, c: [{ h: 'λόγος', k: 'lo/gos', s: 'logos' }] } });
    await fetchLemmaPickerShard('l');
    await fetchLemmaGlosses('logos-root');
    await fetchNgramShard('form', 'q');
    await fetchNgramOccurrences('lemma', 'q', 2);
    await fetchSearchOffsets('medea');
    await fetchEnglishSegments();
    expect(fn.mock.calls.map(c => c[0])).toEqual([
      'https://data.example/lemma-picker/l.json',
      'https://data.example/lemmata/logos-root.json',
      'https://data.example/ngrams/form/q.json',
      'https://data.example/ngrams/lemma/occ/q-2.json',
      'https://data.example/medea/search/offsets.json',
      'https://data.example/ngrams/english-segments.json',
    ]);
  });

  it('refuses a picker shard of the old shape and retries after a failure', async () => {
    stubFetch({ arete: [['a)reth/']] });
    await expect(fetchLemmaPickerShard('a')).rejects.toThrow(/stale/);
    stubFetch({ arete: { n: 1, c: [] } });
    await expect(fetchLemmaPickerShard('a')).resolves.toEqual({ arete: { n: 1, c: [] } });
  });

  it('gives an empty gloss list for a missing lemma page', async () => {
    stubFetch(null, false);
    await expect(fetchLemmaGlosses('no-such-page')).resolves.toEqual([]);
  });

  it('undoes the delta encoding', () => {
    expect(decodeOffsets([5, 3, 10])).toEqual([5, 8, 18]);
    expect(decodeOffsets([])).toEqual([]);
  });
});
