import { describe, expect, it } from 'vitest';
import { orderBySurface } from '../lib/name-order';
import type { Analysis } from '../lib/data';

const a = (lemma: string): Analysis => ({ lemma, gloss: '', parse: '', lsj: [] });
const lemmas = (list: Analysis[]) => list.map((x) => x.lemma);

describe('orderBySurface', () => {
  const dike = [a('di/kh'), a('*di/kh')];

  it('puts name readings first for a capitalised token', () => {
    expect(lemmas(orderBySurface(dike, 'Δίκη'))).toEqual(['*di/kh', 'di/kh']);
    expect(lemmas(orderBySurface(dike, '⟨Δίκη⟩'))).toEqual(['*di/kh', 'di/kh']);
  });

  it('hides name readings for a lowercase token that has a common one', () => {
    expect(lemmas(orderBySurface(dike, 'δίκη'))).toEqual(['di/kh']);
  });

  it('keeps a name reading that is the only one (Γαῖα for γῆς)', () => {
    expect(lemmas(orderBySurface([a('*gai=a')], 'γῆς'))).toEqual(['*gai=a']);
  });

  it('leaves an all-capitals token alone', () => {
    expect(lemmas(orderBySurface(dike, 'ΔΙΚΗ'))).toEqual(['di/kh', '*di/kh']);
  });
});
