import { describe, expect, it } from 'vitest';
import { searchableTranslations, getWork } from '../lib/works';
import { translationCredit } from '../lib/search';

// Each English hit names its translator, from the registry, as the old page
// did (hard rule: credit every translator). Persians has three translations.
describe('the credit beside an English hit', () => {
  it('names each translation of a play by its registry label', () => {
    const w = getWork('persians')!;
    const ts = searchableTranslations(w);
    expect(ts.length).toBeGreaterThanOrEqual(3);
    for (const t of ts) {
      expect(t.short).toBeTruthy();
      expect(translationCredit('persians', t.id)).toBe(t.short);
    }
    expect(translationCredit('persians', 'smyth')).toBe('Smyth');
    expect(translationCredit('persians', 'morshead')).toBe('Morshead');
    expect(translationCredit('persians', 'johnston')).toBe('Johnston');
  });

  it('adds a passage\'s own credit to the primary translation only', () => {
    const passage = 'Tr. Jurgen R. Gatt (2022) — CC BY-NC-ND 4.0.';
    expect(translationCredit('persians', 'smyth', passage)).toBe(`Smyth · ${passage}`);
    expect(translationCredit('persians', 'morshead', passage)).toBe('Morshead');
  });

  it('is empty for a translation the registry does not know', () => {
    expect(translationCredit('persians', 'nobody')).toBe('');
  });
});
