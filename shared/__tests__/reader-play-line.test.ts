import { fireEvent, render } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Reader from '../components/Reader.svelte';
import type { BookData, EnglishTurn } from '../lib/data';
import type { Work } from '../lib/works';

// Reader-layer acceptance for P1 (docs/p1-probe.md): a play-line segment's
// strophe marker renders as its own element (never part of the clickable
// Greek text), its speaker renders as an ordinary lead-in via the existing
// speakers.ts path (speakerWork generalization of the old `stephanus &&`
// gates), and its DOM id/gutter are keyed by the line's own printed ref —
// mirrors reader-prose-flow.test.ts's fixture-mocking pattern.

vi.mock('../lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/works')>();
  const fixtures: Record<string, Work> = {
    PLAYLINE: {
      id: 'PLAYLINE', title: 'Fixture Play', abbr: 'Fix.', author: 'Test',
      language: 'grc', workType: 'verse', books: 1, bookLabels: ['1'],
      greekEdition: 'Test edition', greekSource: { short: 'Test', full: 'Test edition, full.' },
      translations: [
        { id: 'smyth', name: 'Test Translator (Test, 1926)', short: 'Smyth', slot: 'english', footnotes: true },
        { id: 'storr', name: 'Second Translator (Test, 1912) — by speech', short: 'Storr', slot: 'secondary', footnotes: true },
      ],
      citation: { scheme: 'play-line', copyAbbr: 'Fix.' },
      blurb: 'Fixture for play-line Reader tests.',
    },
  };
  return {
    ...actual,
    getWork: (id: string) => fixtures[id] ?? actual.getWork(id),
    getWorkBySlug: (author: string, slug: string) =>
      fixtures[slug.toUpperCase()] ?? actual.getWorkBySlug(author, slug),
  };
});

async function flush() {
  await new Promise((r) => setTimeout(r, 0));
}

function book(): BookData {
  return {
    book: 1,
    speakerRoster: ['Watchman', 'Chorus'],
    segments: [
      {
        id: '1:1',
        column: '1',
        greek: [
          { n: 1, text: 'πρῶτος λόγος', tokens: [{ t: 'πρῶτος', o: 0, k: 'prwtos' }], ref: '1' },
        ],
        speakers: [{ line: 1, offset: 0, label: 'ΦΥΛΑΞ', display: 'Watchman' }],
        english: null,
      },
      {
        id: '1:5',
        column: '5',
        greek: [
          { n: 2, text: 'δεύτερος λόγος', tokens: [{ t: 'δεύτερος', o: 0, k: 'deuteros' }], ref: '5a' },
          { n: 3, text: 'πέμπτος λόγος', tokens: [{ t: 'πέμπτος', o: 0, k: 'pemptos' }], ref: '5b', label: 'στρ. α.' },
          { n: 4, text: 'ἕκτος λόγος', tokens: [], ref: '6' },
          { n: 5, text: 'ἕβδομος λόγος', tokens: [], ref: '7' },
          { n: 6, text: 'δέκατος λόγος', tokens: [], ref: '10' },
          { n: 7, text: 'μέλος', tokens: [], ref: '106-107' },
          { n: 8, text: '', tokens: [], ref: 'post 107', role: 'lacuna' },
        ],
        speakers: [
          { line: 2, offset: 0, label: 'Φυ.', display: 'Watchman' },
          { line: 3, offset: 0, label: 'Χο.', display: 'Chorus' },
          { line: 4, offset: 0, label: '—', display: null },
        ],
        english: null,
      },
    ],
  };
}

describe('Reader.svelte play-line rendering (P1)', () => {
  beforeEach(() => localStorage.clear());

  it('renders a strophe marker as its own element, separate from the line text', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const marker = container.querySelector('.strophe-marker');
    expect(marker).toBeTruthy();
    expect(marker!.textContent).toBe('στρ. α.');
    // Never part of the clickable Greek text.
    const line = container.querySelector('.greek-line[id="L5b-3"]');
    expect(line).toBeTruthy();
    expect(line!.textContent).not.toContain('στρ');
  });

  it('renders the speaker as an ordinary lead-in (speakers.ts path)', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const line1 = container.querySelector('.greek-line[id="L1-1"]');
    expect(line1).toBeTruthy();
    expect(line1!.querySelector('.speaker')?.textContent).toBe('ΦΥΛΑΞ');
  });

  it('keys colours by canonical display while printing each source label', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const speakers = Array.from(container.querySelectorAll('.speaker'));
    const watchman = speakers.filter((el) => ['ΦΥΛΑΞ', 'Φυ.'].includes(el.textContent ?? ''));
    const chorus = speakers.find((el) => el.textContent === 'Χο.');
    const dash = speakers.find((el) => el.textContent === '—');
    expect(watchman).toHaveLength(2);
    expect(watchman[0].getAttribute('data-spk')).toBe(watchman[1].getAttribute('data-spk'));
    expect(chorus?.getAttribute('data-spk')).not.toBe(watchman[0].getAttribute('data-spk'));
    expect(dash?.hasAttribute('data-spk')).toBe(false);
  });

  it('builds the DOM id from the line\'s own ref, not the internal segment column', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    // Segment "1:5"'s column is "5", but its one line's own ref is also "5"
    // here — pick a case where they'd diverge: segment id "1:1" carries
    // column "1" and its line's ref is "1" too in this fixture, so assert
    // the id is ref-derived generally by checking the reader never falls
    // back to the generic `L{seg.column}-{n}` (dense n) shape for a work
    // whose printed ref and dense ordinal already coincide is not a
    // discriminating case — assert via the reader's play-line jump helper
    // instead (exported for this purpose is out of scope; the id itself,
    // L{ref}-{n}, is asserted directly).
    expect(container.querySelector('#L1-1')).toBeTruthy();
    expect(container.querySelector('#L5b-3')).toBeTruthy();
  });

  it('keys gutter labels to printed refs and always shows suffixes and ranges', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const nums = Array.from(container.querySelectorAll('.line-num')).map((el) => el.textContent);
    // Line 1 (n=1, ref "1"): always shown. "5a" (n=2, not a multiple of 5,
    // not the first line): shown anyway because it isn't a plain integer.
    expect(nums).toContain('1');
    expect(nums).toContain('5a');
    expect(nums).toContain('5b');
    expect(nums).toContain('10');
    expect(nums).toContain('106-107');
    expect(nums).not.toContain('7');
  });

  it('keeps a lacuna out of the citation and scroll-spy target set', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const lacuna = container.querySelector('.greek-line.lacuna');
    expect(lacuna).toBeTruthy();
    expect(lacuna!.hasAttribute('id')).toBe(false);
    expect(lacuna!.classList.contains('target')).toBe(false);
    expect(container.querySelector('#Lpost_107-8')).toBeNull();
  });

  it('keys Greek and English lead-ins by the same canonical speaker', async () => {
    const data = book();
    data.segments = [{
      id: '1:1',
      column: '1',
      greek: [
        { n: 1, text: 'πρῶτος λόγος', tokens: [{ t: 'πρῶτος', o: 0, k: 'prwtos' }], ref: '1' },
      ],
      speakers: [{ line: 1, offset: 0, label: 'ΦΥΛΑΞ', display: 'Watchman' }],
      english: {
        text: 'I pray the gods deliver me.',
        notes: [],
        markers: [],
        turns: [{ offset: 0, speaker: 'Watchman', display: 'WATCHMAN' }],
      },
    }];
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    const greek = container.querySelector('.greek-line .speaker');
    const english = container.querySelector('.english-col .speaker');
    expect(greek?.textContent).toBe('ΦΥΛΑΞ');
    expect(english?.textContent).toBe('WATCHMAN');
    expect(greek?.getAttribute('data-spk')).toBeTruthy();
    expect(english?.getAttribute('data-spk')).toBe(greek?.getAttribute('data-spk'));
  });

  it('falls back to the printed display when an English turn lacks speaker', async () => {
    const data = book();
    data.segments = [{
      id: '1:1',
      column: '1',
      greek: [
        { n: 1, text: 'πρῶτος λόγος', tokens: [{ t: 'πρῶτος', o: 0, k: 'prwtos' }], ref: '1' },
      ],
      speakers: [{ line: 1, offset: 0, label: 'ΦΥΛΑΞ', display: 'Watchman' }],
      english: {
        text: 'I pray the gods deliver me.',
        notes: [],
        markers: [],
        turns: [{ offset: 0, display: 'Watchman' } as EnglishTurn],
      },
    }];
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    const greek = container.querySelector('.greek-line .speaker');
    const english = container.querySelector('.english-col .speaker');
    expect(english?.textContent).toBe('Watchman');
    expect(english?.getAttribute('data-spk')).toBe(greek?.getAttribute('data-spk'));
  });

  it('renders a play-line English [^3.69_71] marker as a footnote control', async () => {
    const data = book();
    data.segments = [{
      id: '1:1',
      column: '1',
      greek: [
        { n: 1, text: 'πρῶτος λόγος', tokens: [{ t: 'πρῶτος', o: 0, k: 'prwtos' }], ref: '1' },
      ],
      speakers: [{ line: 1, offset: 0, label: 'ΦΥΛΑΞ', display: 'Watchman' }],
      english: {
        text: 'I pray the gods [^3.69_71] deliver me.',
        notes: [],
        markers: [],
        turns: [{ offset: 0, speaker: 'Watchman', display: 'WATCHMAN' }],
      },
    }];
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    const marker = container.querySelector('.fn-marker');
    expect(marker).toBeTruthy();
    expect(marker!.tagName).toBe('BUTTON');
    expect(marker!.getAttribute('data-fn')).toBe('3.69_71');
  });

  function comparisonBook(withSecondary = true): BookData {
    return {
      book: 1,
      speakerRoster: ['Watchman'],
      segments: [{
        id: '1:1',
        column: '1',
        greek: [{ n: 1, text: 'πρῶτος λόγος', tokens: [], ref: '1' }],
        speakers: [{ line: 1, offset: 0, label: 'ΦΥΛΑΞ', display: 'Watchman' }],
        english: {
          text: 'Primary words.', notes: [], markers: [],
          turns: [{ offset: 0, speaker: 'Watchman', display: 'WATCHMAN' }],
        },
        ...(withSecondary ? {
          secondary: [{
            chapter: '1', text: 'WATCHMAN. Secondary words.', cont: false,
          }],
        } : {}),
      }],
    };
  }

  async function pickSecondary(container: HTMLElement) {
    const picker = container.querySelector('.rc-trans-select') as HTMLSelectElement;
    await fireEvent.change(picker, { target: { value: 'storr' } });
    await flush();
  }

  it('renders the secondary turn stack when the secondary translation is selected', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: comparisonBook() } });
    await flush();
    await pickSecondary(container);

    const english = container.querySelector('.english-col');
    expect(english?.textContent).toContain('Secondary words.');
    expect(english?.textContent).not.toContain('Primary words.');
  });

  it('renders distinct primary-left and secondary-right texts in compare mode', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: comparisonBook() } });
    await flush();
    const compare = container.querySelectorAll('input[name="trans-mode"]')[1] as HTMLInputElement;
    await fireEvent.change(compare);
    await flush();

    expect(container.querySelector('.english-col')?.textContent).toContain('Primary words.');
    expect(container.querySelector('.english-col')?.textContent).not.toContain('Secondary words.');
    expect(container.querySelector('.overlay-col')?.textContent).toContain('Secondary words.');
    expect(container.querySelector('.overlay-col')?.textContent).not.toContain('Primary words.');
  });

  it('keys a secondary lead-in to the same speaker colour as the Greek lead-in', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: comparisonBook() } });
    await flush();
    await pickSecondary(container);

    const greek = container.querySelector('.greek-line .speaker');
    const english = container.querySelector('.english-col .speaker');
    expect(english?.textContent).toBe('WATCHMAN');
    expect(english?.getAttribute('data-spk')).toBe(greek?.getAttribute('data-spk'));
  });

  it('shows the missing-passage affordance when the selected secondary is absent', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: comparisonBook(false) } });
    await flush();
    await pickSecondary(container);

    expect(container.querySelector('.english-col .eng-missing')?.getAttribute('title'))
      .toBe('No aligned passage in this translation');
  });
});

describe('Reader.svelte play-line continuation coverage (P2e)', () => {
  beforeEach(() => localStorage.clear());
  it('shows "translated with the speech above" instead of a missing passage when englishCoveredBy is set', async () => {
    const data = book();
    data.segments[0].english = {
      text: 'A block the translator anchored once.',
      notes: [],
      markers: [],
      turns: [{ offset: 0, speaker: 'Watchman', display: 'WATCHMAN' }],
    };
    data.segments[1].englishCoveredBy = '1:1';
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    const covered = container.querySelector('.eng-covered');
    expect(covered?.textContent).toContain('Translated with the speech above');
    // The affordance replaces the missing-passage dash for that segment only.
    expect(container.querySelectorAll('.eng-covered')).toHaveLength(1);
  });
});


describe('Reader.svelte play-line attribution differences (P2f)', () => {
  beforeEach(() => localStorage.clear());
  it('marks the English lead-in with the edition disagreement when speakerMismatch is set', async () => {
    const data = book();
    data.segments[0].english = {
      text: 'Words the translator gives to the Chorus.',
      notes: [],
      markers: [],
      turns: [{ offset: 0, speaker: 'Chorus', display: 'CHORUS', speakerMismatch: { english: 'Chorus', greek: 'Watchman' } }],
      speakerMismatch: { english: 'Chorus', greek: 'Watchman' },
    };
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    const lead = container.querySelector('.english-col .speaker[data-mismatch]');
    expect(lead?.textContent).toBe('CHORUS');
    expect(lead?.getAttribute('title')).toContain('Watchman');
  });

  // P2h finding 3: a packed Greek speech (Seven 1:1004 = Ismene's shares of
  // the antilabe plus the Herald's speech) holds several English turns, and
  // only the disagreeing one may be marked.
  it('marks only the turn that carries the disagreement, not its neighbours', async () => {
    const data = book();
    data.segments[0].english = {
      text: 'Words the translator gives to the Chorus. The herald announces the decree.',
      notes: [],
      markers: [],
      turns: [
        { offset: 0, speaker: 'Chorus', display: 'CHORUS', speakerMismatch: { english: 'Chorus', greek: 'Watchman' } },
        { offset: 41, speaker: 'Watchman', display: 'WATCHMAN' },
      ],
    };
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    const marked = container.querySelectorAll('.english-col .speaker[data-mismatch]');
    expect(marked).toHaveLength(1);
    expect(marked[0].textContent).toBe('CHORUS');
    const leads = [...container.querySelectorAll('.english-col .turn-para .speaker')].map(el => el.textContent);
    expect(leads).toEqual(['CHORUS', 'WATCHMAN']);
  });
});



// ── P4 (docs/p4-plan.md): the per-line turn row model ────────────────────
// Every English turn sits on the row of the Greek line it starts on. The k-th
// English turn of a chunk pairs with the k-th Greek speaker EVENT of that
// segment in document order; turns beginning mid-line (an antilabe share) stack
// in that line's own row; a surplus turn stacks in the row of the last mapped
// line; a chunk with no turns at all stays on the segment's first line, in the
// single Greek-beside-English row that scheme always rendered.
describe('Reader.svelte play-line per-line turn rows (P4)', () => {
  beforeEach(() => localStorage.clear());

  // Frogs 6–7 as built: two Greek lines, three speaker events (two of them
  // shares of line 6), three English turns.
  function packedBook(turns: EnglishTurn[], text: string): BookData {
    return {
      book: 1,
      speakerRoster: ['Xanthias', 'Dionysus'],
      segments: [{
        id: '1:6',
        column: '6',
        greek: [
          { n: 6, text: 'Τί δαί; Τὸ πάνυ γέλοιον εἴπω; Νὴ Δία', tokens: [], ref: '6' },
          { n: 7, text: 'θαρρῶν γε· μόνον ἐκεῖν᾽ ὅπως μὴ ᾽ρεῖς— Τὸ τί;', tokens: [], ref: '7' },
        ],
        speakers: [
          { line: 6, offset: 0, label: 'ΞΑ.', display: 'Xanthias' },
          { line: 6, offset: 30, label: 'ΔΙ.', display: 'Dionysus' },
          { line: 7, offset: 39, label: 'ΞΑ.', display: 'Xanthias' },
        ],
        english: { text, notes: [], markers: [], turns },
      }],
    };
  }

  const packedTurns: EnglishTurn[] = [
    { offset: 0, speaker: 'Xanthias', display: 'XANTHIAS' },
    { offset: 35, speaker: 'Dionysus', display: 'DIONYSUS' },
    { offset: 62, speaker: 'Xanthias', display: 'XANTHIAS' },
  ];
  const packedText =
    'Then what witty thing shall I say? Come, take courage; only … Only what?';

  function rowLeads(container: HTMLElement): string[][] {
    return [...container.querySelectorAll('.play-row')].map((row) =>
      [...row.querySelectorAll('.english-col .turn-para .speaker')].map((el) => el.textContent ?? ''),
    );
  }

  it('puts each English turn in the row of the Greek line its speaker event starts on', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: packedBook(packedTurns, packedText) } });
    await flush();
    const rows = [...container.querySelectorAll('.play-row')];
    expect(rows).toHaveLength(2);
    // Row 1 is Greek line 6, row 2 is line 7 — one Greek line per row.
    expect(rows[0].querySelector('.greek-line')?.id).toBe('L6-6');
    expect(rows[1].querySelector('.greek-line')?.id).toBe('L7-7');
    // The two shares of line 6 stack in line 6's row; line 7's share is alone.
    expect(rowLeads(container)).toEqual([['XANTHIAS', 'DIONYSUS'], ['XANTHIAS']]);
    expect(rows[0].querySelector('.english-col')?.textContent).toContain('Come, take courage');
    expect(rows[1].querySelector('.english-col')?.textContent).toContain('Only what?');
  });

  it('stacks a surplus English turn in the row of the last mapped line', async () => {
    // A fourth turn with no Greek event of its own: it belongs to line 7's row,
    // never to a row of its own and never back at the top.
    const turns: EnglishTurn[] = [
      ...packedTurns,
      { offset: 73, speaker: 'Dionysus', display: 'DIONYSUS' },
    ];
    const { container } = render(Reader, {
      props: { work: 'PLAYLINE', bookNum: 1, bookData: packedBook(turns, `${packedText} A fourth speech.`) },
    });
    await flush();
    expect(rowLeads(container)).toEqual([['XANTHIAS', 'DIONYSUS'], ['XANTHIAS', 'DIONYSUS']]);
    const rows = [...container.querySelectorAll('.play-row')];
    expect(rows[1].querySelector('.english-col')?.textContent).toContain('A fourth speech.');
  });

  it('keeps a mid-line speaker change inline in the Greek, not in the gutter', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: packedBook(packedTurns, packedText) } });
    await flush();
    const parts = [...container.querySelectorAll('.greek-line[id="L6-6"] .line-text > *')];
    // The line-opening siglum is the FIRST child (the CSS hangs only that one);
    // the antilabe share's siglum stays inside the line's own flow.
    expect(parts[0].className).toContain('speaker');
    expect(parts[0].textContent).toBe('ΞΑ.');
    const sigla = [...container.querySelectorAll('.greek-line[id="L6-6"] .speaker')].map((el) => el.textContent);
    expect(sigla).toEqual(['ΞΑ.', 'ΔΙ.']);
  });

  it('leaves a single-speech chunk on the segment\'s first line (no row split)', async () => {
    const data = book();
    data.segments[1].english = {
      text: 'One block of translation for the whole speech.',
      notes: [], markers: [], turns: [],
    };
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    expect(container.querySelector('.play-row-split')).toBeNull();
    // Still one Greek column beside one English column, as before P4.
    expect(container.querySelectorAll('.segment')[1].querySelectorAll('.greek-col')).toHaveLength(1);
  });

  it('carries the coverage and mismatch markings through the split rows', async () => {
    const turns: EnglishTurn[] = [
      packedTurns[0],
      { ...packedTurns[1], speakerMismatch: { english: 'Dionysus', greek: 'Xanthias' } },
      packedTurns[2],
    ];
    const data = packedBook(turns, packedText);
    data.segments.push({
      id: '1:8',
      column: '8',
      greek: [{ n: 8, text: 'ὄγδοος λόγος', tokens: [], ref: '8' }],
      speakers: [{ line: 8, offset: 0, label: 'ΔΙ.', display: 'Dionysus' }],
      english: null,
      englishCoveredBy: '1:6',
    });
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    const marked = container.querySelectorAll('.play-row .english-col .speaker[data-mismatch]');
    expect(marked).toHaveLength(1);
    expect(marked[0].textContent).toBe('DIONYSUS');
    expect(container.querySelector('.eng-covered')?.textContent).toContain('Translated with the speech above');
  });
});

describe('Reader.svelte play-line compare columns (P4)', () => {
  beforeEach(() => localStorage.clear());

  function compareBook(): BookData {
    return {
      book: 1,
      speakerRoster: ['Chorus'],
      segments: [{
        id: '1:40',
        column: '40',
        greek: [
          { n: 1, text: 'δέκατον μὲν ἔτος τόδ᾽ ἐπεὶ Πριάμῳ', tokens: [], ref: '40' },
          { n: 2, text: 'μέγας ἀντίδικος,', tokens: [], ref: '41' },
        ],
        speakers: [{ line: 1, offset: 0, label: 'Χο.', display: 'Chorus' }],
        english: {
          text: 'Primary words.', notes: [], markers: [],
          turns: [{ offset: 0, speaker: 'Chorus', display: 'CHORUS' }],
        },
        secondary: [{ chapter: '40', text: 'CHORUS. Secondary words.', cont: false }],
      }],
    };
  }

  it('renders three columns headed by translator, year and alignment model', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: compareBook() } });
    await flush();
    const compare = container.querySelectorAll('input[name="trans-mode"]')[1] as HTMLInputElement;
    await fireEvent.change(compare);
    await flush();

    expect(container.querySelector('.greek-col')).toBeTruthy();
    expect(container.querySelector('.english-col')).toBeTruthy();
    expect(container.querySelector('.overlay-col')).toBeTruthy();
    const heads = [...container.querySelectorAll('.col-label.play-col-head')].map((el) => el.textContent);
    // The Greek column's own heading, level with the two translation headers;
    // "by speech" comes from the registry name's own suffix, "by line" is the
    // line-anchored default.
    expect(heads).toEqual(['Chorus · 40–41', 'Smyth · 1926 · by line', 'Storr · 1912 · by speech']);
    expect(container.querySelector('.greek-col .play-greek-head')).toBeTruthy();
  });

  it('keeps each column\'s speaker label as its own lead-in block', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: compareBook() } });
    await flush();
    const compare = container.querySelectorAll('input[name="trans-mode"]')[1] as HTMLInputElement;
    await fireEvent.change(compare);
    await flush();
    expect(container.querySelector('.english-col .turn-para .speaker')?.textContent).toBe('CHORUS');
    expect(container.querySelector('.overlay-col .turn-para .speaker')?.textContent).toBe('CHORUS');
    expect(container.querySelector('.greek-line .line-text > .speaker')?.textContent).toBe('Χο.');
  });
});

describe('Reader.svelte play-line ode measure (P4)', () => {
  beforeEach(() => localStorage.clear());

  function chorusSegment(lines: number, display: string) {
    return {
      id: '1:40',
      column: '40',
      greek: Array.from({ length: lines }, (_, i) => ({
        n: i + 1, text: `λόγος ${i + 1}`, tokens: [], ref: String(40 + i),
      })),
      speakers: [{ line: 1, offset: 0, label: 'Χο.', display }],
      english: null,
    };
  }

  it('marks a chorus speech of more than six lines as an ode', async () => {
    const data: BookData = { book: 1, speakerRoster: ['Chorus'], segments: [chorusSegment(7, 'Chorus')] };
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    expect(container.querySelector('.segment.play-ode')).toBeTruthy();
  });

  it('leaves choral stichomythia and a non-chorus speech at the dialogue measure', async () => {
    const short: BookData = { book: 1, speakerRoster: ['Chorus'], segments: [chorusSegment(6, 'Chorus')] };
    const { container: a } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: short } });
    await flush();
    expect(a.querySelector('.segment.play-ode')).toBeNull();

    const spoken: BookData = { book: 1, speakerRoster: ['Watchman'], segments: [chorusSegment(9, 'Watchman')] };
    const { container: b } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: spoken } });
    await flush();
    expect(b.querySelector('.segment.play-ode')).toBeNull();
  });
});
