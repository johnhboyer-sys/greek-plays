// Plays listed first, as one group, on an author's page (docs/redesign/
// DESIGN.md, Author pages; decisions.md, round 4 verdicts): the Oresteia on
// Aeschylus' page, the Oedipus plays in story order on Sophocles'.
// DRAFT copy (the round-4 sketch's wording): John approves.
export interface AuthorGroup {
  title: string;
  works: string[];
  /** Label each play first, second, third (a trilogy staged together). */
  ordinals: boolean;
  /** The group's note. With `fromProduction`, the first play's production
   *  line follows it, less its own "Oresteia, first play · " lead. */
  note: string;
  fromProduction?: boolean;
}

export const AUTHOR_GROUPS: Record<string, AuthorGroup> = {
  aeschylus: {
    title: 'Oresteia',
    works: ['agamemnon', 'libation-bearers', 'eumenides'],
    ordinals: true,
    note: 'City Dionysia, 458 BC · first prize',
  },
  sophocles: {
    title: 'Oedipus cycle',
    works: ['oedipus-tyrannus', 'oedipus-coloneus', 'antigone'],
    ordinals: false,
    note: 'Written years apart, not as a trilogy. Listed in the order of the story.',
  },
};

export const ORDINALS = ['First play', 'Second play', 'Third play'];
