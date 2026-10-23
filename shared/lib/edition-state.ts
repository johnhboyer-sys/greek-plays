import { visibleTranslations, type Work } from './works';

export type ReaderView = 'both' | 'english' | 'greek';
export type Pair = [string, string];
// `pair`: the two translations of a comparison; read only when trans is 'compare'.
export interface EditionState { ed: string; trans: string; view: ReaderView; pair?: Pair }
export const ownEdition = (work: Work, trans: string) => work.translations.find(t => t.id === trans)?.edition ?? 'tlg';
export const aligned = (work: Work, trans: string, ed: string) => ed === 'tlg' || ed === ownEdition(work, trans);

// A comparison's Greek (John, 2026-10-23): an edition's book carries the English
// of its own translations only (pipeline config.py for_edition), the reference
// book every translation's, so a comparison can stand beside the reference text
// or an edition both its translations were made from.
type EditionPairs = { id: string; pairs?: string[] };
export const compareEditions = (editions: EditionPairs[] | undefined, pair: Pair): string[] =>
  ['tlg', ...(editions ?? []).filter(e => e.id !== 'tlg' && pair.every(id => e.pairs?.includes(id))).map(e => e.id)];
/** The edition both translations were made from when they share one, else the reference text. */
export function compareEdition(work: Work, pair: Pair): string {
  const own = ownEdition(work, pair[0]);
  return own === ownEdition(work, pair[1]) && compareEditions(work.greekEditions, pair).includes(own) ? own : 'tlg';
}
/** The edition a reader shows when the URL names none. */
export const defaultEdition = (work: Work, trans: string, pair?: Pair) =>
  trans === 'compare' && pair ? compareEdition(work, pair) : ownEdition(work, trans);
/** The compare pair Reader.svelte restores: the saved ids if still offered, else the first translation and the next; never one twice. */
export function comparePair(work: Work, saved: [string | null, string | null] = [null, null]): Pair {
  const translations = visibleTranslations(work);
  const ids = new Set(translations.map(t => t.id));
  const engSlot = translations.find(t => t.slot === 'english');
  const secondary = translations.find(t => t.slot !== 'english');
  let left = engSlot?.id ?? translations[0]?.id ?? 'english';
  let right = secondary?.id ?? translations[1]?.id ?? left;
  if (saved[0] && ids.has(saved[0])) left = saved[0];
  if (saved[1] && ids.has(saved[1])) right = saved[1];
  if (left === right) right = translations.find(t => t.id !== left)?.id ?? left;
  return [left, right];
}

export function loadEdition(work: Work, input: { trans: string; view: ReaderView; ed?: string | null; loc?: string | null; pair?: Pair }): EditionState {
  let { trans, view } = input;
  const pair = input.pair;
  const valid = work.greekEditions?.some(e => e.id === input.ed);
  // A bare ?loc= reads in TLG numbering (plan 4.1 rule 4).
  let ed = valid ? input.ed! : input.loc ? 'tlg' : defaultEdition(work, trans, pair);
  if (view === 'greek') return { ed, trans, view, ...(pair ? { pair } : {}) };
  if (trans === 'compare') {
    if (!pair) return { ed: 'tlg', trans, view };
    if (!valid) return { ed, trans, view, pair };
    if (compareEditions(work.greekEditions, pair).includes(ed)) return { ed, trans, view, pair };
    // A linked edition the comparison cannot stand beside: the link wins, as below.
    trans = work.greekEditions?.find(e => e.id === ed)?.pairs?.[0] ?? trans;
    if (trans === 'compare') view = 'greek';
    return { ed, trans, view };
  }
  if (valid && !aligned(work, trans, ed)) {
    const first = work.greekEditions?.find(e => e.id === ed)?.pairs?.[0];
    if (first) trans = first;
    else view = 'greek';
  }
  return { ed, trans, view };
}
export function changeEdition(work: Work, state: EditionState, change: { trans?: string; view?: ReaderView; ed?: string; pair?: Pair }): EditionState {
  const trans = change.trans ?? state.trans;
  const view = change.view ?? state.view;
  if (change.ed && view === 'greek') return { ed: change.ed, trans, view, ...(change.pair ?? state.pair ? { pair: change.pair ?? state.pair } : {}) };
  if (trans === 'compare') {
    const pair = change.pair ?? state.pair;
    if (!pair) return { ed: 'tlg', trans, view };
    const offered = compareEditions(work.greekEditions, pair);
    // A Greek text picked for the comparison, if it can stand beside both.
    if (change.ed && offered.includes(change.ed)) return { ed: change.ed, trans, view, pair };
    // The same comparison keeps its Greek; a new pair, or entering compare, takes the pair's default.
    const same = state.trans === 'compare' && state.pair?.[0] === pair[0] && state.pair?.[1] === pair[1];
    return { ed: same && offered.includes(state.ed) ? state.ed : compareEdition(work, pair), trans, view, pair };
  }
  // Reader always sends its translation, so only a different one is a translation change.
  if (change.trans && change.trans !== state.trans && view !== 'greek') return { ed: ownEdition(work, trans), trans, view };
  if (state.view === 'greek' && view !== 'greek' && !aligned(work, trans, state.ed))
    return { ed: ownEdition(work, trans), trans, view };
  return { ed: state.ed, trans, view };
}

/** The `reader:set` a click on a Greek text in the head's texts menu sends (ReaderHead.astro). */
export function headEditionPick(
  state: { view: string; trans: string; compareLeft: string; compareRight: string },
  ed: { id: string; pairs?: string[] },
  editions: EditionPairs[],
): Record<string, unknown> | null {
  // The Greek view takes any edition.
  if (state.view === 'greek') return { edition: ed.id };
  // A comparison takes a text both its translations can stand beside, and no other.
  if (state.trans === 'compare')
    return compareEditions(editions, [state.compareLeft, state.compareRight]).includes(ed.id) ? { edition: ed.id } : null;
  // Both and English show a translation beside its own Greek, so a text with a
  // translation of its own brings that translation, and a text without one
  // opens in the Greek view (loadEdition above).
  return ed.pairs?.[0] ? { trans: ed.pairs[0] } : { view: 'greek', edition: ed.id };
}
