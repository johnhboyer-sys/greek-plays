import type { Work } from './works';

export type ReaderView = 'both' | 'english' | 'greek';
export interface EditionState { ed: string; trans: string; view: ReaderView }
export const ownEdition = (work: Work, trans: string) => work.translations.find(t => t.id === trans)?.edition ?? 'tlg';
export const aligned = (work: Work, trans: string, ed: string) => ed === 'tlg' || ed === ownEdition(work, trans);
export function loadEdition(work: Work, input: { trans: string; view: ReaderView; ed?: string | null; loc?: string | null }): EditionState {
  let { trans, view } = input;
  const valid = work.greekEditions?.some(e => e.id === input.ed);
  let ed = valid ? input.ed! : ownEdition(work, trans);
  if (view === 'greek') return { ed, trans, view };
  if (trans === 'compare') return { ed: 'tlg', trans, view };
  if (valid && !aligned(work, trans, ed)) {
    const pair = work.greekEditions?.find(e => e.id === ed)?.pairs?.[0];
    if (pair) trans = pair;
    else view = 'greek';
  } else if (!valid && input.loc) ed = 'tlg';
  return { ed, trans, view };
}
export function changeEdition(work: Work, state: EditionState, change: { trans?: string; view?: ReaderView; ed?: string }): EditionState {
  const trans = change.trans ?? state.trans;
  const view = change.view ?? state.view;
  if (trans === 'compare') return { ed: 'tlg', trans, view };
  if (change.ed && view === 'greek') return { ed: change.ed, trans, view };
  if (change.trans && view !== 'greek') return { ed: ownEdition(work, trans), trans, view };
  if (state.view === 'greek' && view !== 'greek' && !aligned(work, trans, state.ed))
    return { ed: ownEdition(work, trans), trans, view };
  return { ed: state.ed, trans, view };
}
