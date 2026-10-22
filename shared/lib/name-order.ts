import type { Analysis } from './data';

// Stage 4 ships a key's common and name readings together when the work
// prints it both ways (δίκη / Δίκη share a key). The printed case decides:
// a capitalised token reads as the name first; a lowercase one drops the
// name readings unless they are all there is (Γαῖα is the lemma of γῆς).
export function orderBySurface(analyses: Analysis[], surface: string): Analysis[] {
  const letters = [...surface.normalize('NFD')].filter((ch) => /\p{L}/u.test(ch));
  if (!letters.length) return analyses;
  const upper = (ch: string) => ch !== ch.toLowerCase();
  if (letters.length > 1 && letters.every(upper)) return analyses;
  const isName = (x: Analysis) => x.lemma.startsWith('*');
  const names = analyses.filter(isName);
  const common = analyses.filter((x) => !isName(x));
  if (!names.length || !common.length) return analyses;
  return upper(letters[0]) ? [...names, ...common] : common;
}
