import { describe, expect, it, vi } from 'vitest';
import { makeGrammataLoader, type GrammataLookup } from '../lib/grammata';

describe('Grammata loader', () => {
  it('retries the import after a rejected request', async () => {
    const lookup: GrammataLookup = vi.fn(async () => undefined);
    const importer = vi.fn()
      .mockRejectedValueOnce(new Error('temporary import failure'))
      .mockResolvedValueOnce({ lookup });
    const load = makeGrammataLoader(importer);

    await expect(load()).rejects.toThrow('temporary import failure');
    await expect(load()).resolves.toBe(lookup);
    expect(importer).toHaveBeenCalledTimes(2);
  });
});
