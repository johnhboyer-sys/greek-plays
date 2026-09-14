import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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
        { id: 'storr', name: 'Second Translator (Test, 1912)', short: 'Storr', slot: 'secondary', footnotes: true },
      ],
      citation: { scheme: 'play-line', copyAbbr: 'Fix.' },
      blurb: 'Fixture for play-line Reader tests.',
    },
    // A comedy whose third column carries Arrowsmith's stage directions.
    PLAYDIR: {
      id: 'PLAYDIR', title: 'Fixture Comedy', abbr: 'Fixc.', author: 'Test',
      language: 'grc', workType: 'verse', books: 1, bookLabels: ['1'],
      greekEdition: 'Test edition', greekSource: { short: 'Test', full: 'Test edition, full.' },
      translations: [
        { id: 'smyth', name: 'Test Translator (Test, 1926)', short: 'Smyth', slot: 'english', footnotes: true },
        { id: 'arrowsmith', name: 'William Arrowsmith (Michigan, 1962)', short: 'Arrowsmith', slot: 'third' },
      ],
      citation: { scheme: 'play-line', copyAbbr: 'Fixc.' },
      blurb: 'Fixture for stage directions.',
    },
    // PLAYLINE with each translation's form declared: Smyth prose, Storr verse.
    PLAYPROSE: {
      id: 'PLAYPROSE', title: 'Fixture Prose', abbr: 'Fixp.', author: 'Test',
      language: 'grc', workType: 'verse', books: 1, bookLabels: ['1'],
      greekEdition: 'Test edition', greekSource: { short: 'Test', full: 'Test edition, full.' },
      translations: [
        { id: 'smyth', name: 'Test Translator (Test, 1926)', short: 'Smyth', slot: 'english', footnotes: true, form: 'prose' },
        { id: 'storr', name: 'Second Translator (Test, 1912)', short: 'Storr', slot: 'secondary', footnotes: true, form: 'verse' },
      ],
      citation: { scheme: 'play-line', copyAbbr: 'Fixp.' },
      blurb: 'Fixture for the prose measure.',
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

// A real wait, for the deep-link settle timers (flush() above is a microtask
// drain only, so it cannot advance them).
async function wait(ms: number) {
  await new Promise((r) => setTimeout(r, ms));
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
    expect(line1!.querySelector('.speaker')).toBeTruthy();
  });

  // P4 Lane C: the Greek speaker gutter is sized for sigla, so the full name
  // an edition prints at a speaker's first appearance (ΦΥΛΑΞ at Ag. 1) is
  // shown as that play's siglum for the speaker and keeps the printed label
  // in its title. The siglum is the play's, not the line's: the same speaker
  // wears it on every line.
  it('shows the play\'s siglum in the gutter and the printed label in the title', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const first = container.querySelector('.greek-line[id="L1-1"] .speaker')!;
    expect(first.textContent).toBe('Φυ.');
    expect(first.getAttribute('title')).toBe('ΦΥΛΑΞ');
    expect(first.getAttribute('aria-label')).toBe('ΦΥΛΑΞ');
    // The line that already prints the siglum shows it unchanged, with no
    // title to add (label and siglum are the same string).
    const second = container.querySelector('.greek-line[id="L5a-2"] .speaker')!;
    expect(second.textContent).toBe('Φυ.');
    expect(second.hasAttribute('title')).toBe(false);
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
    // The Greek wears the play's siglum (P4 Lane C); the English column is
    // untouched, and both are keyed by the same canonical speaker.
    expect(greek?.textContent).toBe('Φυ.');
    expect(english?.textContent).toBe('Watchman');
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

  it('replaces the footnote body when moving to another marker (Astra lane A, F5)', async () => {
    const data = book();
    data.segments = [{
      id: '1:1',
      column: '1',
      greek: [
        { n: 1, text: 'πρῶτος λόγος', tokens: [{ t: 'πρῶτος', o: 0, k: 'prwtos' }], ref: '1' },
      ],
      speakers: [{ line: 1, offset: 0, label: 'ΦΥΛΑΞ', display: 'Watchman' }],
      english: {
        text: 'First [^1] then another [^2] later.',
        notes: [],
        markers: [],
        turns: [{ offset: 0, speaker: 'Watchman', display: 'WATCHMAN' }],
      },
    }];
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (String(url).includes('footnotes.json')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            '1': '<p>First unique body ALPHA.</p>',
            '2': '<p>Second unique body BETA.</p>',
          }),
        } as Response);
      }
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
    try {
      const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
      await flush();
      const markers = container.querySelectorAll('.fn-marker');
      expect(markers).toHaveLength(2);
      await fireEvent.click(markers[0]!);
      await waitFor(() => expect(document.querySelector('.footnote-text')?.textContent).toContain('ALPHA'));
      expect(document.querySelector('.footnote-num')?.textContent).toContain('1');
      await fireEvent.click(markers[1]!);
      await waitFor(() => {
        expect(document.querySelector('.footnote-num')?.textContent).toContain('2');
        expect(document.querySelector('.footnote-text')?.textContent).toContain('BETA');
      });
      expect(document.querySelector('.footnote-text')?.textContent).not.toContain('ALPHA');
    } finally {
      vi.restoreAllMocks();
    }
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
    expect(english?.textContent).toBe('Watchman');
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
    expect(lead?.textContent).toBe('Chorus');
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
    expect(marked[0].textContent).toBe('Chorus');
    const leads = [...container.querySelectorAll('.english-col .turn-para .speaker')].map(el => el.textContent);
    expect(leads).toEqual(['Chorus', 'Watchman']);
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

  it('prints each antilabe share on its own line and puts each English turn beside its share', async () => {
    // John, 2026-09-09: an antilabe line is printed one line per share, the
    // OCT way -- the second share starts a new line set to the right, with
    // its siglum run in and no number -- so every English turn sits level
    // with its own Greek share, and the phone stacks them in that order.
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: packedBook(packedTurns, packedText) } });
    await flush();
    const rows = [...container.querySelectorAll('.play-row')];
    expect(rows).toHaveLength(3);
    const lines = [...container.querySelectorAll('.greek-line')];
    expect(lines.map((l) => l.id)).toEqual(['L6-6', '', 'L7-7', '']);
    expect(lines.map((l) => l.classList.contains('antilabe-share'))).toEqual([false, true, false, true]);
    expect(lines.map((l) => l.querySelector('.line-text')?.textContent?.trim())).toEqual([
      'Ξα.Τί δαί; Τὸ πάνυ γέλοιον εἴπω;', 'Δι.Νὴ Δία', 'θαρρῶν γε· μόνον ἐκεῖν᾽ ὅπως μὴ ᾽ρεῖς—', 'Ξα.Τὸ τί;',
    ]);
    // A later share carries no number and is set to the right of its predecessor.
    expect(lines[1].querySelector('.line-num')?.textContent).toBe('');
    expect((lines[1].querySelector('.line-text') as HTMLElement).style.getPropertyValue('--share-indent')).toBe('30ch');
    // Rows: line 6's first share | Xanthias; line 6's second share + line 7's
    // first | Dionysus; line 7's second share | Xanthias.
    expect(rowLeads(container)).toEqual([['Xanthias'], ['Dionysus'], ['Xanthias']]);
    expect(rows[1].querySelectorAll('.greek-line')).toHaveLength(2);
    expect(rows[1].querySelector('.english-col')?.textContent).toContain('Come, take courage');
    expect(rows[2].querySelector('.english-col')?.textContent).toContain('Only what?');
  });

  it('runs a marker-less single speech down its Greek, but leaves a mid-segment speaker to the dialogue rows (Grok review of 5748b3f)', async () => {
    const greek = Array.from({ length: 12 }, (_, i) => ({ n: i + 1, text: `στίχος ${i + 1} ἐστίν.`, tokens: [], ref: String(200 + i) }));
    const english = {
      text: 'First sentence here. Second sentence here. Third sentence here. Fourth sentence here.',
      notes: [], markers: [], turns: [{ offset: 0, speaker: 'Chorus', display: 'CHORUS' }],
    };
    const book = (speakers: BookData['segments'][number]['speakers']): BookData => ({
      book: 1, speakerRoster: ['Chorus'],
      segments: [{ id: '1:200', column: '200', greek, speakers, english }],
    });
    const rowOf = (c: HTMLElement, s: string) =>
      [...c.querySelectorAll('.play-row')].findIndex((r) => r.querySelector('.english-col')?.textContent?.includes(s));
    // One speech opening the segment: its sentences run down the lines.
    const one = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book([{ line: 1, offset: 0, label: 'ΧΟ.', display: 'Chorus' }]) } });
    await flush();
    expect(rowOf(one.container, 'Fourth')).toBeGreaterThan(rowOf(one.container, 'First'));
    one.unmount();
    // A lone speaker event further in (an antilabe) is dialogue: not spread.
    const mid = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book([{ line: 6, offset: 4, label: 'ΧΟ.', display: 'Chorus' }]) } });
    await flush();
    expect(rowOf(mid.container, 'Fourth')).toBe(rowOf(mid.container, 'First'));
  });

  it('keeps an editor\'s bracket with the share it opens, never on a line of its own (Rhesus 16)', async () => {
    // Diggle prints "[ΧΟ. θάρσει. ΕΚ. θαρσῶ." -- the Chorus's siglum starts
    // after the bracket, so a cut there stranded "[" as a printed line
    // (John, 2026-09-10).
    const book: BookData = {
      book: 1,
      speakerRoster: ['Chorus', 'Hector'],
      segments: [{
        id: '1:16',
        column: '16',
        greek: [{ n: 16, text: '[ θάρσει. θαρσῶ.', tokens: [], ref: '16' }],
        speakers: [
          { line: 16, offset: 2, label: 'ΧΟ.', display: 'Chorus' },
          { line: 16, offset: 10, label: 'ΕΚ.', display: 'Hector' },
        ],
        english: {
          text: 'Courage. I have it.', notes: [], markers: [],
          turns: [{ offset: 0, speaker: 'Chorus', display: 'CHORUS' }, { offset: 9, speaker: 'Hector', display: 'HECTOR' }],
        },
      }],
    };
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book } });
    await flush();
    const texts = [...container.querySelectorAll('.greek-line .line-text')].map((el) => el.textContent?.replace(/\s+/g, ' ').trim());
    expect(texts).toHaveLength(2);
    expect(texts).not.toContain('[');
    expect(texts[0]).toMatch(/^\[ ?Χο\. ?θάρσει\.$/);
    expect(texts[1]).toMatch(/^Εκ\. ?θαρσῶ\.$/);
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
    expect(rowLeads(container)).toEqual([['Xanthias'], ['Dionysus'], ['Xanthias', 'Dionysus']]);
    const rows = [...container.querySelectorAll('.play-row')];
    expect(rows[2].querySelector('.english-col')?.textContent).toContain('A fourth speech.');
  });

  it('keeps a mid-line speaker change inline in the Greek, not in the gutter', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: packedBook(packedTurns, packedText) } });
    await flush();
    const parts = [...container.querySelectorAll('.greek-line[id="L6-6"] .line-text > *')];
    // The line-opening siglum is the FIRST child (the CSS hangs only that one).
    expect(parts[0].className).toContain('speaker');
    expect(parts[0].textContent).toBe('Ξα.');
    const sigla = [...container.querySelectorAll('.greek-line[id="L6-6"] .speaker')].map((el) => el.textContent);
    expect(sigla).toEqual(['Ξα.']);
    // The antilabe share is its own printed line (John, 2026-09-09), its
    // siglum run in as the first child of that line, which the CSS keeps in
    // the flow (.antilabe-share), never in the gutter.
    const share = container.querySelector('.greek-line.antilabe-share');
    expect(share?.querySelector('.line-text')?.textContent?.trim()).toBe('Δι.Νὴ Δία');
    const shareParts = [...share!.querySelectorAll('.line-text > *')];
    expect(shareParts[0].className).toContain('speaker');
    expect(shareParts[0].textContent).toBe('Δι.');
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
    expect(marked[0].textContent).toBe('Dionysus');
    expect(container.querySelector('.eng-covered')?.textContent).toContain('Translated with the speech above');
  });

  it('does not position English cells in English-only view (Astra lane A, F1)', async () => {
    const origRect = Element.prototype.getBoundingClientRect;
    const origStyle = window.getComputedStyle;
    Element.prototype.getBoundingClientRect = function (this: Element) {
      const empty = { x: 0, y: 0, width: 0, height: 0, top: 0, right: 0, bottom: 0, left: 0, toJSON() {} };
      const el = this as HTMLElement;
      if (el.classList?.contains('play-row-split')) {
        return { ...empty, top: 1000, y: 1000 };
      }
      if (el.classList?.contains('greek-col')) {
        if (el.closest('.view-english')) return empty;
        return { ...empty, top: 1000, y: 1000, height: 20, bottom: 1020 };
      }
      if (el.classList?.contains('turn-stack')) {
        return { ...empty, top: 1000, y: 1000, height: 100, width: 200, right: 200, bottom: 1100 };
      }
      return origRect.call(this);
    };
    window.getComputedStyle = ((elt: Element, pseudo?: string | null) => {
      const style = origStyle.call(window, elt, pseudo);
      if ((elt as HTMLElement).classList?.contains('play-row-split')) {
        return new Proxy(style, { get: (t, k) => (k === 'fontSize' ? '16px' : Reflect.get(t, k)) });
      }
      return style;
    }) as typeof window.getComputedStyle;
    try {
      const { container, getByRole } = render(Reader, {
        props: { work: 'PLAYLINE', bookNum: 1, bookData: packedBook(packedTurns, packedText) },
      });
      await wait(20);
      const bilingual = [...container.querySelectorAll('.play-row .english-col > *')]
        .map((el) => (el as HTMLElement).style.transform);
      expect(bilingual.some((t) => t.includes('translateY'))).toBe(true);
      await fireEvent.click(getByRole('button', { name: 'English' }));
      await wait(20);
      const english = [...container.querySelectorAll('.play-row .english-col > *')]
        .map((el) => (el as HTMLElement).style.transform);
      expect(english.every((t) => !t)).toBe(true);
      expect((container.querySelector('.play-row-split') as HTMLElement).style.paddingBottom).toBe('');
    } finally {
      Element.prototype.getBoundingClientRect = origRect;
      window.getComputedStyle = origStyle;
    }
  });
});

// John, 2026-09-12: "Keep stage directions but have a break in the Greek
// where the stage directions are so english stays aligned with its Greek."
describe('Reader.svelte stage directions (Arrowsmith)', () => {
  beforeEach(() => localStorage.clear());

  const LAMP = 'Suddenly the oil lamp sputters and goes out.';
  function dirBook(): BookData {
    const seg = (n: number, display: string, label: string, third: Record<string, unknown>) => ({
      id: `1:${54 + n}`,
      column: String(54 + n),
      greek: [{ n, text: `λόγος ${n}`, tokens: [], ref: String(54 + n) }],
      speakers: [{ line: n, offset: 0, label, display }],
      english: { text: `Primary ${n}.`, notes: [], markers: [], turns: [{ offset: 0, speaker: display, display: display.toUpperCase() }] },
      third: [{ chapter: String(54 + n), cont: false, ...third }],
    });
    return {
      book: 1,
      speakerRoster: ['Strepsiades', 'Slave'],
      segments: [
        seg(1, 'Strepsiades', 'Στ.', { text: 'STREPSIADES. Or a goat?' }),
        seg(2, 'Slave', 'Ξα.', { text: "XANTHIAS. There's no oil left in the lamp.", directionsBefore: [LAMP] }),
        seg(3, 'Strepsiades', 'Στ.', { text: 'STREPSIADES. Jackass!\n_He lunges at Xanthias._\nCome here and be whipped.' }),
      ],
    } as unknown as BookData;
  }

  it('gives a direction between speeches a row of its own, the Greek cell empty', async () => {
    localStorage.setItem('reader-trans-PLAYDIR', 'arrowsmith');
    const { container } = render(Reader, { props: { work: 'PLAYDIR', bookNum: 1, bookData: dirBook() } });
    await flush();
    const rows = container.querySelectorAll('.play-direction-row');
    expect(rows).toHaveLength(1);
    const row = rows[0]!;
    expect(row.closest('.segment')?.id).toBe('col-56');
    expect(row.querySelector('.greek-col')?.textContent?.trim()).toBe('');
    expect(row.querySelector('.english-col .stage-dir')?.textContent).toBe(LAMP);
    // It comes before the speech's own Greek and English.
    const line = container.querySelector('#col-56 .greek-line')!;
    expect(row.compareDocumentPosition(line) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('prints a direction inside a speech inline, in italics, with no row', async () => {
    localStorage.setItem('reader-trans-PLAYDIR', 'arrowsmith');
    const { container } = render(Reader, { props: { work: 'PLAYDIR', bookNum: 1, bookData: dirBook() } });
    await flush();
    const para = container.querySelector('#col-57 .english-col .turn-para')!;
    expect(para.querySelector('.stage-dir')?.textContent).toBe('He lunges at Xanthias.');
    expect(para.textContent).not.toContain('_');
    expect(container.querySelector('#col-57 .play-direction-row')).toBeNull();
  });

  // Clouds 1:866 (Codex review of 7a9a16d): two speeches in one Greek
  // segment, a direction between them.
  const ENTER = 'Enter Sokrates from the Thinkery.';
  function splitBook(): BookData {
    return {
      book: 1,
      speakerRoster: ['Strepsiades', 'Socrates'],
      segments: [{
        id: '1:866',
        column: '866',
        greek: [
          { n: 866, text: 'λόγος ἕν', tokens: [], ref: '866' },
          { n: 867, text: 'λόγος δύο', tokens: [], ref: '867' },
          { n: 868, text: 'λόγος τρία', tokens: [], ref: '868' },
        ],
        speakers: [
          { line: 866, offset: 0, label: 'Στ.', display: 'Strepsiades' },
          { line: 868, offset: 0, label: 'Σω.', display: 'Socrates' },
        ],
        english: {
          text: 'Primary one. Primary two.', notes: [], markers: [],
          turns: [
            { offset: 0, speaker: 'Strepsiades', display: 'STREPSIADES' },
            { offset: 13, speaker: 'Socrates', display: 'SOCRATES' },
          ],
        },
        third: [{
          chapter: '866', cont: false,
          text: 'STREPSIADES. Ah, good dutiful boy.\n\nSOKRATES. Why, he is still a baby.',
          turnDirections: [{ turn: 1, directions: [ENTER] }],
        }],
      }],
    } as unknown as BookData;
  }

  it('gives a direction before a later speech of one segment a row between the two speeches', async () => {
    localStorage.setItem('reader-trans-PLAYDIR', 'arrowsmith');
    const { container } = render(Reader, { props: { work: 'PLAYDIR', bookNum: 1, bookData: splitBook() } });
    await flush();
    const seg = container.querySelector('#col-866')!;
    const kids = [...seg.querySelectorAll('.play-row-split, .play-direction-row')];
    expect(kids.map((el) => (el.classList.contains('play-direction-row') ? 'dir' : 'rows'))).toEqual(['rows', 'dir', 'rows']);
    const dir = kids[1]!;
    expect(dir.querySelector('.greek-col')?.textContent?.trim()).toBe('');
    expect(dir.querySelector('.english-col .stage-dir')?.textContent).toBe(ENTER);
    expect(kids[0]!.querySelector('.english-col')?.textContent).toContain('Ah, good dutiful boy.');
    expect(kids[0]!.textContent).not.toContain(ENTER);
    expect(kids[2]!.querySelector('.greek-col')?.textContent).toContain('λόγος τρία');
    expect(kids[2]!.querySelector('.english-col')?.textContent).toContain('Why, he is still a baby.');
    expect(seg.querySelectorAll('.stage-dir')).toHaveLength(1);
  });

  it('adds no row between speeches when Arrowsmith is not on screen', async () => {
    const primary = render(Reader, { props: { work: 'PLAYDIR', bookNum: 1, bookData: splitBook() } });
    await flush();
    expect(primary.container.querySelector('.play-direction-row')).toBeNull();
    expect(primary.container.querySelectorAll('.play-row-split')).toHaveLength(1);
    primary.unmount();

    localStorage.setItem('reader-trans-PLAYDIR', 'arrowsmith');
    localStorage.setItem('reader-view', 'greek');
    const greek = render(Reader, { props: { work: 'PLAYDIR', bookNum: 1, bookData: splitBook() } });
    await flush();
    expect(greek.container.querySelector('.play-direction-row')).toBeNull();
    expect(greek.container.querySelectorAll('.play-row-split')).toHaveLength(1);
  });

  it('adds no row when Arrowsmith is not on screen', async () => {
    const primary = render(Reader, { props: { work: 'PLAYDIR', bookNum: 1, bookData: dirBook() } });
    await flush();
    expect(primary.container.querySelector('.play-direction-row')).toBeNull();
    expect(primary.container.querySelector('.stage-dir')).toBeNull();
    primary.unmount();

    localStorage.setItem('reader-trans-PLAYDIR', 'arrowsmith');
    localStorage.setItem('reader-view', 'greek');
    const greek = render(Reader, { props: { work: 'PLAYDIR', bookNum: 1, bookData: dirBook() } });
    await flush();
    expect(greek.container.querySelector('.play-direction-row')).toBeNull();
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
    expect(heads).toEqual(['Chorus · 40–41', 'Smyth · 1926', 'Storr · 1912']);
    expect(container.querySelector('.greek-col .play-greek-head')).toBeTruthy();
  });

  it('keeps each column\'s speaker label as its own lead-in block', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: compareBook() } });
    await flush();
    const compare = container.querySelectorAll('input[name="trans-mode"]')[1] as HTMLInputElement;
    await fireEvent.change(compare);
    await flush();
    expect(container.querySelector('.english-col .turn-para .speaker')?.textContent).toBe('Chorus');
    expect(container.querySelector('.overlay-col .turn-para .speaker')?.textContent).toBe('Chorus');
    expect(container.querySelector('.greek-line .line-text > .speaker')?.textContent).toBe('Χο.');
  });
});

describe('Reader.svelte play-line ode measure (P4)', () => {
  beforeEach(() => localStorage.clear());

  // The Greek siglum is part of the fixture: P4 Lane E reads the chorus off
  // the printed label first (finding 5), so a non-chorus speaker must carry a
  // non-chorus siglum here, exactly as the edition prints one.
  function chorusSegment(lines: number, display: string, label = 'Χο.') {
    return {
      id: '1:40',
      column: '40',
      greek: Array.from({ length: lines }, (_, i) => ({
        n: i + 1, text: `λόγος ${i + 1}`, tokens: [], ref: String(40 + i),
      })),
      speakers: [{ line: 1, offset: 0, label, display }],
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

    const spoken: BookData = { book: 1, speakerRoster: ['Watchman'], segments: [chorusSegment(9, 'Watchman', 'Φυ.')] };
    const { container: b } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: spoken } });
    await flush();
    expect(b.querySelector('.segment.play-ode')).toBeNull();
  });
});

// ── P4 fix round (docs/reviews/2026-09-08-grok-p4a.md) ───────────────────
// Findings 1–4: the ode measure inherits across a 40-line split; English turns
// pair with Greek events BY SPEAKER (the pipeline emits a crossed pair in
// English order); the compare Greek heading starts on the verse; the strophe
// marker never becomes the row's first baseline.
describe('Reader.svelte play-line turn pairing by speaker (P4 fix, finding 2)', () => {
  beforeEach(() => localStorage.clear());

  // Frogs 1:414 as built: Greek 414/415 (internal n 405/406), events
  // Xanthias@405 and Dionysus@406 — and the English of the pair in ENGLISH
  // order, Dionysus first. k-th ↔ k-th would put Dionysus' words on Xanthias'
  // line.
  function crossedBook(turns: EnglishTurn[], text: string): BookData {
    return {
      book: 1,
      speakerRoster: ['Xanthias', 'Dionysus'],
      segments: [{
        id: '1:414',
        column: '414',
        greek: [
          { n: 405, text: 'ἐγὼ δ᾽ ἀεί πως φιλακόλουθός εἰμι καὶ', tokens: [], ref: '414' },
          { n: 406, text: 'μετ᾽ αὐτῆς παίζων χορεύειν βούλομαι. Κἄγωγε.', tokens: [], ref: '415' },
        ],
        speakers: [
          { line: 405, offset: 0, label: 'ΞΑ.', display: 'Xanthias' },
          { line: 406, offset: 37, label: 'ΔΙ.', display: 'Dionysus' },
        ],
        english: { text, notes: [], markers: [], turns },
      }],
    };
  }

  const crossedText = 'Aye, I like to mingle with these choruses. And I too.';
  const crossedTurns: EnglishTurn[] = [
    { offset: 0, speaker: 'Dionysus', display: 'DIONYSUS' },
    { offset: 43, speaker: 'Xanthias', display: 'XANTHIAS' },
  ];

  it('puts each turn on its own speaker\'s line when the pair is emitted in English order', async () => {
    const { container } = render(Reader, {
      props: { work: 'PLAYLINE', bookNum: 1, bookData: crossedBook(crossedTurns, crossedText) },
    });
    await flush();
    const rows = [...container.querySelectorAll('.play-row')];
    expect(rows).toHaveLength(2);
    // Line 415 is an antilabe: its first share continues Xanthias and stays
    // in his row; Dionysus' share is its own printed line and its own row.
    expect([...rows[0].querySelectorAll('.greek-line')].map((l) => l.id)).toEqual(['L414-405', 'L415-406']);
    const share = rows[1].querySelector('.greek-line');
    expect(share?.id).toBe('');
    expect(share?.classList.contains('antilabe-share')).toBe(true);
    expect(share?.querySelector('.line-text')?.textContent?.trim()).toBe('Δι.Κἄγωγε.');
    // Xanthias speaks line 414, Dionysus line 415 — each English turn follows
    // its own speaker, not its position in the English.
    expect(rows[0].querySelector('.english-col .turn-para .speaker')?.textContent).toBe('Xanthias');
    expect(rows[0].querySelector('.english-col')?.textContent).toContain('And I too.');
    expect(rows[1].querySelector('.english-col .turn-para .speaker')?.textContent).toBe('Dionysus');
    expect(rows[1].querySelector('.english-col')?.textContent).toContain('Aye, I like to mingle');
  });
});

describe('Reader.svelte play-line row edges (P4 fix, review item 5c–5e)', () => {
  beforeEach(() => localStorage.clear());

  // Frogs 6–7 again: two Greek lines, three events (two shares of line 6).
  function packed(turns: EnglishTurn[], text: string): BookData {
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
  const text = 'Then what witty thing shall I say? Come, take courage; only … Only what?';
  function leads(container: HTMLElement): string[][] {
    return [...container.querySelectorAll('.play-row')].map((row) =>
      [...row.querySelectorAll('.english-col .turn-para .speaker')].map((el) => el.textContent ?? ''),
    );
  }

  // (c) buildEnglishTurnBlocks drops an EMPTY UNLABELED turn, so a block's
  // position in the array is not its turn index — and the pairing must not
  // slide by one because of it.
  it('keeps the pairing when an empty unlabeled turn is dropped from the blocks', async () => {
    const turns: EnglishTurn[] = [
      { offset: 0, speaker: 'Xanthias', display: 'XANTHIAS' },
      { offset: 35, speaker: null, display: null },
      { offset: 35, speaker: 'Dionysus', display: 'DIONYSUS' },
      { offset: 62, speaker: 'Xanthias', display: 'XANTHIAS' },
    ];
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: packed(turns, text) } });
    await flush();
    expect(leads(container)).toEqual([['Xanthias'], ['Dionysus'], ['Xanthias']]);
  });

  // (d) The tail of a speech begun in an earlier chunk carries turnIndex -1:
  // it claims no event and stays on the split's first row.
  it('keeps a pre-turn continuation lead on the first row of a split', async () => {
    const lead = 'A tail of the speech begun above. ';
    const turns: EnglishTurn[] = [
      { offset: lead.length, speaker: 'Xanthias', display: 'XANTHIAS' },
      { offset: lead.length + 35, speaker: 'Dionysus', display: 'DIONYSUS' },
      { offset: lead.length + 62, speaker: 'Xanthias', display: 'XANTHIAS' },
    ];
    const { container } = render(Reader, {
      props: { work: 'PLAYLINE', bookNum: 1, bookData: packed(turns, lead + text) },
    });
    await flush();
    const rows = [...container.querySelectorAll('.play-row')];
    expect(rows[0].querySelector('.english-col')?.textContent).toContain('A tail of the speech begun above.');
    expect(rows[1].querySelector('.english-col')?.textContent).not.toContain('A tail of the speech');
    expect(leads(container)).toEqual([['Xanthias'], ['Dionysus'], ['Xanthias']]);
  });

  // (e) More Greek events than English turns: the unmatched event's line keeps
  // an empty English cell — no turn is duplicated into it and none is dropped.
  it('leaves the unmatched event\'s row empty when there are more events than turns', async () => {
    const turns: EnglishTurn[] = [
      { offset: 0, speaker: 'Xanthias', display: 'XANTHIAS' },
      { offset: 62, speaker: 'Xanthias', display: 'XANTHIAS' },
    ];
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: packed(turns, text) } });
    await flush();
    // Both turns are Xanthias', so they take his two events (lines 6 and 7);
    // Dionysus' share of line 6 simply has no English of its own.
    expect(leads(container)).toEqual([['Xanthias'], ['Xanthias']]);
    const rows = [...container.querySelectorAll('.play-row')];
    expect(rows[1].querySelector('.english-col')?.textContent).toContain('Only what?');
  });
});

describe('Reader.svelte play-line ode across a 40-line split (P4 fix, finding 1)', () => {
  beforeEach(() => localStorage.clear());

  // Stage 1 splits a speech at 40 lines: Ag. 1:40 (Chorus, 40 lines) is
  // followed by 1:80, forty more lines of the same ode with no speaker event
  // of its own.
  function splitPair(display: string, label = 'Χο.'): BookData {
    const lines = (from: number, n: number) =>
      Array.from({ length: n }, (_, i) => ({ n: from + i, text: `λόγος ${from + i}`, tokens: [], ref: String(from + i) }));
    return {
      book: 1,
      speakerRoster: [display],
      segments: [
        { id: '1:40', column: '40', greek: lines(40, 40), speakers: [{ line: 40, offset: 0, label, display }], english: null },
        { id: '1:80', column: '80', greek: lines(80, 40), english: null },
      ],
    };
  }

  it('gives a speakerless tail the ode measure it inherits from the chorus speech before it', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: splitPair('Chorus') } });
    await flush();
    expect(container.querySelectorAll('.segment.play-ode')).toHaveLength(2);
    expect(container.querySelector('#col-80')?.classList.contains('play-ode')).toBe(true);
  });

  it('leaves a spoken 40-line tail at the dialogue measure', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: splitPair('Clytaemestra', 'Κλ.') } });
    await flush();
    expect(container.querySelector('.segment.play-ode')).toBeNull();
  });
});

const PLAY_CSS = readFileSync(join(dirname(fileURLToPath(import.meta.url)), '../styles/global.css'), 'utf8')
  .replace(/\/\*[\s\S]*?\*\//g, '');

describe('play-line stylesheet (P4 fix, findings 3 and 4)', () => {
  it('starts the compare Greek heading on the verse, not at the column edge', () => {
    expect(PLAY_CSS).toMatch(
      /\.reader-body\.play-line\.trans-compare \.play-greek-head \{[^}]*padding-left:\s*var\(--pl-num-w\)/,
    );
  });

  it('applies the zero-height split-row English rule only in the bilingual view (Astra lane A, F1)', () => {
    expect(PLAY_CSS).toMatch(
      /\.reader-body\.play-line\.view-both:not\(\.trans-compare\) \.play-row-split \.play-row > \.english-col\s*\{[^}]*height:\s*0/,
    );
    expect(PLAY_CSS).not.toMatch(
      /\.reader-body\.play-line:not\(\.trans-compare\) \.play-row-split \.play-row > \.english-col\s*\{[^}]*height:\s*0/,
    );
  });

  it('takes the strophe marker out of flow, so a row aligns on the first verse line', () => {
    // `.seg-row { align-items: baseline }` uses a grid item's FIRST baseline:
    // an in-flow marker before the verse would be it (Ag. 1:681).
    expect(PLAY_CSS).toMatch(/\.reader-body\.play-line \.strophe-marker \{[^}]*float:\s*left/);
    expect(PLAY_CSS).toMatch(/\.reader-body\.play-line \.strophe-marker \{[^}]*width:\s*100%/);
    // …and the line it labels clears the band, so the float never sits on top
    // of the verse (measured in a browser: a flex `.greek-line` does not shift
    // for the float on its own).
    expect(PLAY_CSS).toContain('.reader-body.play-line .strophe-marker + .greek-line { clear: left; }');
  });

  it('renders the marker before the verse line inside the Greek cell', async () => {
    const data = book();
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    const marker = container.querySelector('.strophe-marker')!;
    expect(marker).toBeTruthy();
    // A child of the Greek cell itself, immediately before the line it labels —
    // the shape the float rule above is written against.
    expect(marker.parentElement?.classList.contains('greek-col')).toBe(true);
    expect(marker.nextElementSibling?.classList.contains('greek-line')).toBe(true);
  });
});

// ── P4 Lane E (docs/reviews/2026-09-08-grok-p4b.md findings 4–5; the
// deep-link settle of build/p4/lane-d-brief.md) ──────────────────────────
describe('Reader.svelte play-line turn pairing edges (P4 Lane E, finding 4)', () => {
  beforeEach(() => localStorage.clear());

  // Septem's half-choruses: two speaker events on two lines that print the
  // SAME canonical display, so no name can tell them apart.
  function twoLineBook(
    speakers: BookData['segments'][number]['speakers'],
    turns: EnglishTurn[],
    text: string,
  ): BookData {
    return {
      book: 1,
      speakerRoster: ['Semichorus', 'Xanthias', 'Dionysus'],
      segments: [{
        id: '1:1054',
        column: '1054',
        greek: [
          { n: 1054, text: 'πρῶτος στίχος', tokens: [], ref: '1054' },
          { n: 1055, text: 'δεύτερος στίχος', tokens: [], ref: '1055' },
        ],
        speakers,
        english: { text, notes: [], markers: [], turns },
      }],
    };
  }

  it('never hands a positional turn an event another turn already claimed', async () => {
    // P4CE finding 4. Four printed lines, four events; the first two English
    // turns name their speakers and claim events 2 and 3, so when the third
    // (a mismatch, which may not pair by name) reaches for its positional
    // slot k=2 that event is already spoken. It must stack in the last mapped
    // row, not walk back up to Dionysus' line and sit under his own speech.
    const { container } = render(Reader, {
      props: {
        work: 'PLAYLINE', bookNum: 1,
        bookData: {
          book: 1,
          speakerRoster: ['Watchman', 'Dionysus', 'Aeacus'],
          segments: [{
            id: '1:1054',
            column: '1054',
            greek: [1054, 1055, 1056, 1057].map((n) => ({
              n, text: `στίχος ${n}`, tokens: [], ref: String(n),
            })),
            speakers: [
              { line: 1054, offset: 0, label: 'Φυ.', display: 'Watchman' },
              { line: 1055, offset: 0, label: 'Φυ.', display: 'Watchman' },
              { line: 1056, offset: 0, label: 'ΔΙ.', display: 'Dionysus' },
              { line: 1057, offset: 0, label: 'ΑΙ.', display: 'Aeacus' },
            ],
            english: {
              text: 'First. Second. Third.',
              notes: [], markers: [],
              turns: [
                { offset: 0, speaker: 'Dionysus', display: 'DIONYSUS' },
                { offset: 7, speaker: 'Aeacus', display: 'AEACUS' },
                {
                  offset: 15, speaker: 'Dionysus', display: 'DIONYSUS',
                  speakerMismatch: { english: 'Dionysus', greek: 'Watchman' },
                },
              ],
            },
          }],
        },
      },
    });
    await flush();
    // Rows run from one English-bearing line to the next (John, 2026-09-09):
    // the Watchman's two untranslated lines share the first row.
    const rows = [...container.querySelectorAll('.play-row')];
    expect(rows).toHaveLength(3);
    expect(rows[0].querySelectorAll('.greek-line')).toHaveLength(2);
    expect(rows[1].querySelector('.english-col')?.textContent).toContain('First.');
    expect(rows[1].querySelector('.english-col')?.textContent).not.toContain('Third.');
    expect(rows[2].querySelector('.english-col')?.textContent).toContain('Second.');
    expect(rows[2].querySelector('.english-col')?.textContent).toContain('Third.');
  });

  it('gives two events that share one display a turn each, in printed order', async () => {
    const { container } = render(Reader, {
      props: {
        work: 'PLAYLINE', bookNum: 1,
        bookData: twoLineBook(
          [
            { line: 1054, offset: 0, label: 'ΗΜΙΧ. Α.', display: 'Semichorus' },
            { line: 1055, offset: 0, label: 'ΗΜΙΧ. Β.', display: 'Semichorus' },
          ],
          [
            { offset: 0, speaker: 'Semichorus', display: 'SEMICHORUS' },
            { offset: 18, speaker: 'Semichorus', display: 'SEMICHORUS' },
          ],
          'We will bury him. The city forbids it.',
        ),
      },
    });
    await flush();
    const rows = [...container.querySelectorAll('.play-row')];
    expect(rows).toHaveLength(2);
    expect(rows[0].querySelector('.greek-line')?.id).toBe('L1054-1054');
    expect(rows[1].querySelector('.greek-line')?.id).toBe('L1055-1055');
    // One turn per line: neither half-chorus swallows the other's speech.
    expect(rows[0].querySelector('.english-col')?.textContent).toContain('We will bury him.');
    expect(rows[1].querySelector('.english-col')?.textContent).toContain('The city forbids it.');
  });

  it('keeps a speakerMismatch turn on its positional line, not on its namesake’s', async () => {
    // The Greek gives 1054 to Xanthias and 1055 to Dionysus; the English
    // edition gives the FIRST speech to Dionysus. Pairing by that name would
    // drag it down to 1055 and push Xanthias' own words up to 1054 — the two
    // speeches crossed. The mismatch turn takes its positional slot instead.
    const { container } = render(Reader, {
      props: {
        work: 'PLAYLINE', bookNum: 1,
        bookData: twoLineBook(
          [
            { line: 1054, offset: 0, label: 'ΞΑ.', display: 'Xanthias' },
            { line: 1055, offset: 0, label: 'ΔΙ.', display: 'Dionysus' },
          ],
          [
            {
              offset: 0, speaker: 'Dionysus', display: 'DIONYSUS',
              speakerMismatch: { english: 'Dionysus', greek: 'Xanthias' },
            },
            { offset: 18, speaker: 'Dionysus', display: 'DIONYSUS' },
          ],
          'The first speech. The second speech.',
        ),
      },
    });
    await flush();
    const rows = [...container.querySelectorAll('.play-row')];
    expect(rows).toHaveLength(2);
    expect(rows[0].querySelector('.english-col')?.textContent).toContain('The first speech.');
    expect(rows[1].querySelector('.english-col')?.textContent).toContain('The second speech.');
  });
});

describe('Reader.svelte play-line ode by the printed siglum (P4 Lane E, finding 5)', () => {
  beforeEach(() => localStorage.clear());

  function odeBook(label: string, display: string): BookData {
    return {
      book: 1,
      speakerRoster: [display],
      segments: [{
        id: '1:40',
        column: '40',
        greek: Array.from({ length: 7 }, (_, i) => ({
          n: i + 1, text: `λόγος ${i + 1}`, tokens: [], ref: String(40 + i),
        })),
        speakers: [{ line: 1, offset: 0, label, display }],
        english: null,
      }],
    };
  }

  it('reads the chorus off the Greek siglum when the English name hides it', async () => {
    // Smyth calls the chorus of the Suppliants "Danaids"; the Greek prints Χο.
    const { container } = render(Reader, {
      props: { work: 'PLAYLINE', bookNum: 1, bookData: odeBook('Χο.', 'Danaids') },
    });
    await flush();
    expect(container.querySelector('.segment.play-ode')).toBeTruthy();
  });

  it('still reads it off the English name when the siglum does not say chorus', async () => {
    const { container } = render(Reader, {
      props: { work: 'PLAYLINE', bookNum: 1, bookData: odeBook('Α.', 'Semichorus A') },
    });
    await flush();
    expect(container.querySelector('.segment.play-ode')).toBeTruthy();
  });

  it('takes the frogs for a chorus, siglum and all (P4CE finding 2)', async () => {
    // Coulon prints ΒΑΤΡΑΧΟΙ, then ΒΑ.; the translators call them "Frogs".
    for (const label of ['ΒΑΤΡΑΧΟΙ', 'ΒΑ.']) {
      const { container } = render(Reader, {
        props: { work: 'PLAYLINE', bookNum: 1, bookData: odeBook(label, 'Frogs') },
      });
      await flush();
      expect(container.querySelector('.segment.play-ode')).toBeTruthy();
    }
  });

  it('keeps the OTHER Βα. — Atossa, Pelasgus — at the dialogue measure', async () => {
    // Persians and Suppliants abbreviate ΒΑΣΙΛΕΙΑ/ΒΑΣΙΛΕΥΣ the same way; their
    // long rheseis are speeches, so the siglum alone cannot decide.
    const { container } = render(Reader, {
      props: { work: 'PLAYLINE', bookNum: 1, bookData: odeBook('Βα.', 'Atossa') },
    });
    await flush();
    expect(container.querySelector('.segment.play-ode')).toBeNull();
  });

  it('leaves a speaking character at the dialogue measure', async () => {
    const { container } = render(Reader, {
      props: { work: 'PLAYLINE', bookNum: 1, bookData: odeBook('Φυ.', 'Watchman') },
    });
    await flush();
    expect(container.querySelector('.segment.play-ode')).toBeNull();
  });
});

describe('Reader.svelte deep-link settle (P4 Lane E, build/p4/lane-d-brief.md)', () => {
  const spy = () => Element.prototype.scrollIntoView as unknown as ReturnType<typeof vi.fn>;
  const behaviours = (target: Element) =>
    spy().mock.calls
      .filter((_c, i) => spy().mock.instances[i] === target)
      .map((c) => (c[0] as ScrollIntoViewOptions | undefined)?.behavior);

  beforeEach(() => {
    localStorage.clear();
    spy().mockClear();
    window.history.replaceState(null, '', '/PLAYLINE/book/1?loc=6');
  });
  afterEach(() => window.history.replaceState(null, '', '/'));

  it('jumps the target into view when it is still off screen after the page settles', async () => {
    render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const target = document.getElementById('L6-4')!;
    expect(target).toBeTruthy();
    expect(behaviours(target)).toEqual(['smooth']);
    // happy-dom has no layout, so getBoundingClientRect is all zeros — which
    // reads as off screen: exactly the stranded state Lane D observed.
    await wait(1200);
    expect(behaviours(target)).toEqual(['smooth', 'auto']);
    // Once, then stop — the later check never fires a second correction.
    await wait(1600);
    expect(behaviours(target)).toEqual(['smooth', 'auto']);
  });

  it('abandons the settle as soon as the reader scrolls for themselves', async () => {
    // P4CE finding 1: the 2500ms check fires only when the target is OFF
    // screen — which is exactly where a reader who scrolled away has put it.
    // Their wheel wins: no snap back, ever.
    render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const target = document.getElementById('L6-4')!;
    expect(behaviours(target)).toEqual(['smooth']);
    window.dispatchEvent(new Event('wheel'));
    await wait(2800);
    expect(behaviours(target)).toEqual(['smooth']);
  });

  it('treats a scrollbar-thumb drag (pointerdown, no wheel) as the reader scrolling', async () => {
    render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const target = document.getElementById('L6-4')!;
    expect(behaviours(target)).toEqual(['smooth']);
    window.dispatchEvent(new Event('pointerdown'));
    await wait(2800);
    expect(behaviours(target)).toEqual(['smooth']);
  });

  it('leaves a deep link that landed alone', async () => {
    render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const target = document.getElementById('L6-4')!;
    target.getBoundingClientRect = () =>
      ({ top: 200, bottom: 240, left: 0, right: 0, width: 0, height: 40, x: 0, y: 200,
         toJSON: () => ({}) }) as DOMRect;
    await wait(2800);
    expect(behaviours(target)).toEqual(['smooth']);
  });
});


// ── John's review of the built site, 2026-09-09 ─────────────────────────────
describe('Reader.svelte play-line gutter after John\'s review (2026-09-09)', () => {
  beforeEach(() => localStorage.clear());

  function transposedBook(): BookData {
    return {
      book: 1,
      speakerRoster: ['Cassandra', 'Helen', 'Theoclymenus'],
      segments: [
        {
          id: '1:1282', column: '1282',
          greek: [
            { n: 1, text: 'α', tokens: [], ref: '1282' },
            { n: 2, text: 'β', tokens: [], ref: '1283' },
            { n: 3, text: 'γ', tokens: [], ref: '1290' },
            { n: 4, text: 'δ', tokens: [], ref: '1284' },
            { n: 5, text: 'ε', tokens: [], ref: '1285' },
            { n: 6, text: '', tokens: [], ref: 'post 1285', role: 'lacuna' },
            { n: 7, text: '', tokens: [], ref: 'post 1285', role: 'lacuna' },
            { n: 8, text: 'ζ', tokens: [], ref: '1286' },
          ],
          speakers: [
            { line: 1, offset: 0, label: 'Κα.', display: 'Cassandra' },
            { line: 6, offset: 0, label: '<Ελ. >', display: 'Helen' },
            { line: 7, offset: 0, label: '<Θε. >', display: 'Theoclymenus' },
          ],
          english: null,
        },
      ],
    };
  }

  it('numbers a transposed line and the line that resumes after it, as the OCT margin does', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: transposedBook() } });
    await flush();
    const nums = [...container.querySelectorAll('.greek-line .line-num')].map((el) => el.textContent?.trim());
    // Line 1 always; 1290 (jumped ahead) and 1284 (resumes) even off the fifth-line grid;
    // 1285 on the grid; the lacuna placeholders carry their own "post" ref as before.
    expect(nums.slice(0, 5)).toEqual(['1282', '', '1290', '1284', '1285']);
  });

  it("prints a lacuna line's bracketed sigla, the speakers whose lines are lost", async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: transposedBook() } });
    await flush();
    const gaps = [...container.querySelectorAll('.greek-line.lacuna .lacuna-gap')];
    expect(gaps.map((g) => g.querySelector('.speaker')?.textContent)).toEqual(['<Ελ.>', '<Θε.>']);
    expect(gaps[0]!.querySelector('.speaker')?.getAttribute('title')).toBe('<Ελ. >');
  });
});


describe('Reader.svelte play-line: a by-speech translation across a split speech (2026-09-09)', () => {
  beforeEach(() => localStorage.clear());

  function splitBook(): BookData {
    const line = (n: number, ref: string) => ({ n, text: 'λόγος', tokens: [], ref });
    return {
      book: 1,
      speakerRoster: ['Chorus', 'Creon'],
      segments: [
        { id: '1:100', column: '100', greek: [line(1, '100'), line(2, '101')],
          speakers: [{ line: 1, offset: 0, label: 'Χο.', display: 'Chorus' }],
          english: { text: 'Chorus sings.', notes: [], markers: [], turns: [{ offset: 0, speaker: 'Chorus', display: 'CHORUS' }] },
          ross: [{ chapter: '100', text: 'CHORUS. Sunbeam of all, the whole ode in one block.', cont: false }] },
        { id: '1:140', column: '140', greek: [line(3, '140'), line(4, '141')],
          speakers: [{ line: 3, offset: 0, label: 'Χο.', display: 'Chorus' }],
          english: { text: 'Chorus goes on.', notes: [], markers: [], turns: [{ offset: 0, speaker: 'Chorus', display: 'CHORUS' }] } },
        { id: '1:162', column: '162', greek: [line(5, '162'), line(6, '163')],
          speakers: [{ line: 5, offset: 0, label: 'Κρ.', display: 'Creon' }],
          english: { text: 'Creon speaks.', notes: [], markers: [], turns: [{ offset: 0, speaker: 'Creon', display: 'CREON' }] },
          ross: [{ chapter: '162', text: 'CREON. The whole edict in one block.', cont: false }] },
        { id: '1:202', column: '202', greek: [line(7, '202'), line(8, '203')],
          speakers: [],
          english: { text: 'Creon still speaks.', notes: [], markers: [], turns: [] } },
      ],
    } as unknown as BookData;
  }

  it('shows "Translated with the speech above" where the same speaker continues in a new Greek speech, and nothing at all under a 40-line tail', async () => {
    localStorage.setItem('reader-trans-PLAYLINE', 'storr');
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: splitBook() } });
    await flush();
    const cells = [...container.querySelectorAll('.segment')].map((seg) => ({
      id: seg.id,
      covered: !!seg.querySelector('.eng-covered'),
      dash: !!seg.querySelector('.eng-missing'),
      empty: !!seg.querySelector('.eng-continues'),
    }));
    const by = Object.fromEntries(cells.map((c) => [c.id, c]));
    expect(by['col-140']).toMatchObject({ covered: true, dash: false });
    expect(by['col-202']).toMatchObject({ empty: true, dash: false, covered: false });
  });
});

describe('editor notes on repeated and transposed numbers (REVIEW-CHECKLIST 3)', () => {
  beforeEach(() => localStorage.clear());
  function bookWithEditorNumbers(): BookData {
    return {
      book: 1,
      speakerRoster: ['Chorus'],
      segments: [{
        id: '1:1', column: '1',
        greek: [
          { n: 1, text: 'α', tokens: [], ref: '801' },
          { n: 2, text: 'β', tokens: [], ref: '802' },
          { n: 3, text: 'γ', tokens: [], ref: '803' },
          { n: 4, text: 'δ', tokens: [], ref: '810' },
          { n: 5, text: 'ε', tokens: [], ref: '804' },
          { n: 6, text: 'ζ', tokens: [], ref: '805' },
          { n: 7, text: 'η', tokens: [], ref: '803' },
        ],
        speakers: [{ line: 1, offset: 0, label: 'Χο.', display: 'Chorus' }],
        english: null,
      }],
    };
  }
  it('renders the repeated and transposed numbers as buttons whose note names the editor', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: bookWithEditorNumbers() } });
    await flush();
    const btns = [...container.querySelectorAll('.line-num-btn')].map((b) => b.textContent);
    expect(btns).toEqual(['803', '810', '803']);
    expect(container.querySelector('.line-note')).toBeNull();
    await fireEvent.click(container.querySelectorAll('.line-num-btn')[1]);
    expect(container.querySelector('.line-note')?.textContent).toBe('Printed here by the editor: Test places line 810 at this point, out of numerical order.');
    await fireEvent.click(container.querySelectorAll('.line-num-btn')[2]);
    const notes = container.querySelectorAll('.line-note');
    expect(notes.length).toBe(1);
    expect(notes[0].textContent).toBe('Numbered twice by the editor: Test gives the number 803 to two lines. Both stay as printed.');
    await fireEvent.keyDown(window, { key: 'Escape' });
    expect(container.querySelector('.line-note')).toBeNull();
  });
});

describe('English lead-ins and the gutter (John, 2026-09-09)', () => {
  beforeEach(() => localStorage.clear());
  it('sizes the English gutter to the roster and puts an over-long joint label on its own line', async () => {
    const data: BookData = {
      book: 1,
      speakerRoster: ['Dionysus', 'Sausage-Seller'],
      segments: [{
        id: '1:1', column: '1',
        greek: [
          { n: 1, text: 'α', tokens: [], ref: '1' },
          { n: 2, text: 'β', tokens: [], ref: '2' },
        ],
        speakers: [
          { line: 1, offset: 0, label: 'Δι.', display: 'Dionysus' },
          { line: 2, offset: 0, label: 'Αι.', display: 'Sausage-Seller' },
        ],
        english: {
          text: 'Come. Here we are.', notes: [], markers: [],
          turns: [
            { offset: 0, speaker: 'Dionysus', display: 'DIONYSUS' },
            { offset: 6, speaker: 'Sausage-Seller', display: 'AESCHYLUS AND EURIPIDES' },
          ],
        },
      }],
    };
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    const body = container.querySelector('.reader-body') as HTMLElement;
    expect(body.style.getPropertyValue('--pl-spk-w-play')).toBe('8.84rem');
    const leads = [...container.querySelectorAll('.turn-para > .speaker')];
    expect(leads.map((l) => l.classList.contains('spk-long'))).toEqual([false, true]);
  });
});

describe('line-keyed rows: a translation paragraph sits beside the Greek line it is keyed to (REVIEW-CHECKLIST 15)', () => {
  beforeEach(() => localStorage.clear());

  // An ode segment of five Greek lines under one Chorus event, with Smyth's
  // chunk keyed at 175, 180 and 184: three ticks, three rows. Before the
  // change the whole paragraph sat beside 175 and drifted off its lines.
  function odeBook(): BookData {
    return {
      book: 1,
      speakerRoster: ['Chorus'],
      segments: [{
        id: '1:175',
        column: '175',
        greek: [
          { n: 1, text: 'Ζεύς, ὅστις ποτ᾽ ἐστίν', tokens: [], ref: '175' },
          { n: 2, text: 'εἰ τόδ᾽ αὐτῷ φίλον κεκλημένῳ', tokens: [], ref: '176' },
          { n: 3, text: 'οὐκ ἔχω προσεικάσαι', tokens: [], ref: '180' },
          { n: 4, text: 'πλὴν Διός', tokens: [], ref: '182' },
          { n: 5, text: 'τὸν φρονεῖν βροτοὺς ὁδώσαντα', tokens: [], ref: '184' },
        ],
        speakers: [{ line: 1, offset: 0, label: 'Χο.', display: 'Chorus' }],
        english: {
          text: 'Zeus, whoever he may be, if this name pleases him. I cannot compare him to anything but Zeus. Zeus, who sets mortals on the path.',
          notes: [], markers: [],
          bekker: [
            { n: 175, offset: 0, real: true },
            { n: 180, offset: 51, real: true },
            { n: 184, offset: 94, real: true },
          ],
          turns: [{ offset: 0, speaker: 'Chorus', display: 'CHORUS' }],
        },
      }],
    };
  }

  it('cuts the segment into one row per real tick, each with the English keyed to it', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: odeBook() } });
    await flush();
    const rows = [...container.querySelectorAll('.play-row')];
    expect(rows).toHaveLength(3);
    expect(rows.map((r) => [...r.querySelectorAll('.greek-line')].map((l) => l.id))).toEqual([
      ['L175-1', 'L176-2'], ['L180-3', 'L182-4'], ['L184-5'],
    ]);
    const eng = rows.map((r) => r.querySelector('.english-col')?.textContent?.trim() ?? '');
    expect(eng[0]).toContain('Zeus, whoever he may be');
    expect(eng[0]).not.toContain('I cannot compare');
    expect(eng[1]).toContain('I cannot compare him to anything but Zeus.');
    expect(eng[2]).toContain('Zeus, who sets mortals on the path.');
    // The turn lead-in rides in the first row only.
    expect(rows[0].querySelector('.english-col .speaker')?.textContent).toBe('Chorus');
    expect(rows[1].querySelector('.english-col .speaker')).toBeNull();
  });

  it('a real line marker keeps its own row even within minSpan of the piece before it (Codex review of gap-layout: 184 must not merge into 180)', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYPROSE', bookNum: 1, bookData: odeBook() } });
    await flush();
    const rows = [...container.querySelectorAll('.play-row')];
    // 184 is 4 lines after 180 -- inside the 5-line minSpan window -- but it
    // is the translator's OWN printed marker, not an interpolated sentence
    // start, so minSpan thinning must never drop it (defect 1, review-
    // gap-layout-findings.md #1: englishFlow can't restore a dropped anchor).
    expect(rows).toHaveLength(3);
    expect(rows.map((r) => [...r.querySelectorAll('.greek-line')].map((l) => l.id))).toEqual([
      ['L175-1', 'L176-2'], ['L180-3', 'L182-4'], ['L184-5'],
    ]);
    const eng = rows.map((r) => r.querySelector('.english-col')?.textContent?.trim() ?? '');
    expect(eng[1]).toContain('I cannot compare him to anything but Zeus.');
    expect(eng[1]).not.toContain('Zeus, who sets mortals');
    expect(eng[2]).toContain('Zeus, who sets mortals on the path.');
  });

  // A prose speech with no line markers at all (Morshead, Storr, Way): one
  // synthetic tick at the segment's first line, sentence starts interpolated
  // by proportion (John, 2026-09-11, Agamemnon 140-159). The segment's own
  // printed refs skip "6" (an editorial numbering gap, same shape as the ode
  // above skipping 177-179 and 181/183): the 2nd sentence interpolates to
  // that missing number and the 3rd to line 8 -- verified directly against
  // sentenceTicks before wiring this fixture. The unmapped candidate must
  // never survive to consume minSpan's budget against the real candidate
  // after it (defect 2, review-gap-layout-findings.md #2: spacing must run
  // only over cuts that map to a line the segment actually prints).
  function gapNumberedSpeech() {
    const bank = ['alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot', 'golf', 'hotel', 'india', 'juliet', 'kilo', 'lima', 'mike', 'november', 'oscar', 'papa', 'quebec', 'romeo', 'sierra', 'tango'];
    const words = (len: number) => { let out = ''; let i = 0; while (out.length < len) out += (out ? ' ' : '') + bank[i++ % bank.length]; return out.slice(0, len).trim(); };
    const sentence = (len: number) => { const w = words(len - 1); return `${w[0]!.toUpperCase()}${w.slice(1)}.`; };
    const s1 = sentence(149);
    const s2 = sentence(59);
    const s3 = sentence(30);
    const text = `${s1} ${s2} ${s3}`;
    const book: BookData = {
      book: 1,
      speakerRoster: ['Chorus'],
      segments: [{
        id: '1:1',
        column: '1',
        greek: [1, 2, 3, 4, 5, 7, 8].map((ref, i) => ({ n: i + 1, text: 'λόγος ἄλλος', tokens: [], ref: String(ref) })),
        speakers: [{ line: 1, offset: 0, label: 'Χο.', display: 'Chorus' }],
        english: { text, notes: [], markers: [], turns: [{ offset: 0, speaker: 'Chorus', display: 'CHORUS' }] },
      }],
    };
    return { book, s1, s2, s3 };
  }

  it('a candidate on a line the segment does not print does not suppress the valid cut after it', async () => {
    const { book, s1, s2, s3 } = gapNumberedSpeech();
    const { container } = render(Reader, { props: { work: 'PLAYPROSE', bookNum: 1, bookData: book } });
    await flush();
    const rows = [...container.querySelectorAll('.play-row')];
    // The unmapped candidate at line 6 must be dropped from consideration
    // before minSpan is judged, so the valid candidate at line 8 (7 lines
    // after the piece at line 1) keeps its own row: two rows, not the
    // fewer-than-two-cuts fallback (speech-by-speech via playRows). Line 7
    // (ref "7") has no cut before it, so it stays in the first row along
    // with the merged-up 2nd sentence (its own candidate never mapped).
    expect(rows).toHaveLength(2);
    expect(rows.map((r) => [...r.querySelectorAll('.greek-line')].map((l) => l.id))).toEqual([
      ['L1-1', 'L2-2', 'L3-3', 'L4-4', 'L5-5', 'L7-6'], ['L8-7'],
    ]);
    const eng = rows.map((r) => r.querySelector('.english-col')?.textContent?.trim() ?? '');
    expect(eng[0]).toContain(`${s1} ${s2}`);
    expect(eng[1]).toBe(s3);
  });
});

describe('prose measure: a prose translation gets the narrower English column', () => {
  beforeEach(() => localStorage.clear());

  function oneSpeech(): BookData {
    return {
      book: 1,
      speakerRoster: ['Watchman'],
      segments: [{
        id: '1:1', column: '1',
        greek: [{ n: 1, text: 'πρῶτος λόγος', tokens: [], ref: '1' }],
        speakers: [{ line: 1, offset: 0, label: 'ΦΥΛΑΞ', display: 'Watchman' }],
        english: { text: 'Primary words.', notes: [], markers: [], turns: [{ offset: 0, speaker: 'Watchman', display: 'WATCHMAN' }] },
        secondary: [{ chapter: '1', text: 'WATCHMAN. Secondary words.', cont: false }],
      }],
    };
  }

  it('marks the English column of a prose translation, and not of a verse one', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYPROSE', bookNum: 1, bookData: oneSpeech() } });
    await flush();
    expect(container.querySelector('.english-col')?.classList.contains('prose-measure')).toBe(true);
    const picker = container.querySelector('.rc-trans-select') as HTMLSelectElement;
    await fireEvent.change(picker, { target: { value: 'storr' } });
    await flush();
    expect(container.querySelector('.english-col')?.textContent).toContain('Secondary words.');
    expect(container.querySelector('.english-col')?.classList.contains('prose-measure')).toBe(false);
  });

  it('marks each compare column by its own translation', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYPROSE', bookNum: 1, bookData: oneSpeech() } });
    await flush();
    await fireEvent.change(container.querySelectorAll('input[name="trans-mode"]')[1] as HTMLInputElement);
    await flush();
    expect(container.querySelector('.english-col')?.classList.contains('prose-measure')).toBe(true);
    expect(container.querySelector('.overlay-col')?.classList.contains('prose-measure')).toBe(false);
  });

  it('leaves a translation with no declared form as today', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: oneSpeech() } });
    await flush();
    expect(container.querySelector('.prose-measure')).toBeNull();
  });

  it('marks the whole reader as a prose page for a prose translation, not for verse or compare', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYPROSE', bookNum: 1, bookData: oneSpeech() } });
    await flush();
    expect(container.querySelector('.reader-body')?.classList.contains('prose-page')).toBe(true);
    const picker = container.querySelector('.rc-trans-select') as HTMLSelectElement;
    await fireEvent.change(picker, { target: { value: 'storr' } });
    await flush();
    expect(container.querySelector('.reader-body')?.classList.contains('prose-page')).toBe(false);
    await fireEvent.change(container.querySelectorAll('input[name="trans-mode"]')[1] as HTMLInputElement);
    await flush();
    expect(container.querySelector('.reader-body')?.classList.contains('prose-page')).toBe(false);
  });

  it('narrows the prose English track and centres the two columns above the phone width (option 3)', () => {
    const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), '../styles/global.css'), 'utf8');
    expect(css).toMatch(/\.reader-body\.play-line\.view-both\.prose-page:not\(\.trans-compare\) \.seg-row \{\s*grid-template-columns: minmax\(0, 0\.85fr\) minmax\(0, 1\.035fr\);\s*max-width: 94\.25%;\s*margin-inline: auto;/);
    expect(css).toMatch(/\.reader-body\.play-line\.view-both\.trans-compare \.english-col\.prose-measure,\s*\.reader-body\.play-line\.view-both\.trans-compare \.overlay-col\.prose-measure \{ max-width: 90%; \}/);
  });
});

// ── Astra lane A (F2, F3, F6, F7, F8) ─────────────────────────────────────
function fireCopy(container: HTMLElement): string | undefined {
  const target = container.querySelector('.reader-body');
  if (!target) throw new Error('no .reader-body rendered');
  let captured: string | undefined;
  const event = new Event('copy', { bubbles: true, cancelable: true });
  Object.defineProperty(event, 'clipboardData', {
    value: { setData: (_type: string, value: string) => { captured = value; } },
  });
  target.dispatchEvent(event);
  return captured;
}

function selectNode(el: Element): void {
  const range = document.createRange();
  range.selectNodeContents(el);
  const sel = window.getSelection();
  sel?.removeAllRanges();
  sel?.addRange(range);
}

describe('Reader.svelte loc-query hash update (Astra lane A, F2)', () => {
  it('drops ?loc= when the scroll-spy writes a new hash, keeping the other query params', async () => {
    window.history.replaceState(null, '', '/PLAYLINE/book/1?loc=100&view=both&trans=smyth&hlg=foo');
    let ioCallback: IntersectionObserverCallback | undefined;
    class CapturingIO {
      constructor(cb: IntersectionObserverCallback) { ioCallback = cb; }
      observe() {}
      unobserve() {}
      disconnect() {}
      takeRecords() { return []; }
    }
    vi.stubGlobal('IntersectionObserver', CapturingIO);

    const data: BookData = {
      book: 1,
      speakerRoster: ['Watchman'],
      segments: [
        {
          id: '1:100', column: '100',
          greek: [{ n: 100, text: 'α', tokens: [], ref: '100' }],
          speakers: [{ line: 100, offset: 0, label: 'Φυ.', display: 'Watchman' }],
          english: { text: 'Hundred.', notes: [], markers: [], turns: [{ offset: 0, speaker: 'Watchman', display: 'WATCHMAN' }] },
        },
        {
          id: '1:200', column: '200',
          greek: [{ n: 200, text: 'β', tokens: [], ref: '200' }],
          speakers: [{ line: 200, offset: 0, label: 'Φυ.', display: 'Watchman' }],
          english: { text: 'Two hundred.', notes: [], markers: [], turns: [{ offset: 0, speaker: 'Watchman', display: 'WATCHMAN' }] },
        },
      ],
    };
    render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();

    // loc restore + settleDeepLink hold a ~4s suppress window; wait it out
    // so onScrollArm actually constructs the spy observer.
    await wait(4200);
    window.dispatchEvent(new Event('scroll'));
    await flush();
    expect(ioCallback).toBeTruthy();

    const target = document.getElementById('L200-200');
    expect(target).toBeTruthy();
    ioCallback!(
      [{ target, isIntersecting: true, boundingClientRect: { top: 5 } } as unknown as IntersectionObserverEntry],
      {} as IntersectionObserver,
    );

    expect(window.location.search).not.toMatch(/(?:^|[?&])loc=/);
    expect(window.location.search).toContain('view=both');
    expect(window.location.search).toContain('trans=smyth');
    expect(window.location.search).toContain('hlg=foo');
    expect(window.location.hash).toBe('#200');
    vi.unstubAllGlobals();
    window.history.replaceState(null, '', '/');
  }, 10000);
});

describe('Reader.svelte English-only hash scroll (Astra lane A, F3)', () => {
  const offsetParentDesc = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetParent');

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('reader-view', 'english');
    Object.defineProperty(HTMLElement.prototype, 'offsetParent', {
      configurable: true,
      get() {
        const el = this as HTMLElement;
        if (el.closest('.greek-col')) return null;
        return document.body;
      },
    });
    (Element.prototype.scrollIntoView as unknown as { mockClear: () => void }).mockClear();
    window.history.replaceState(null, '', '/PLAYLINE/book/1#200');
  });
  afterEach(() => {
    if (offsetParentDesc) Object.defineProperty(HTMLElement.prototype, 'offsetParent', offsetParentDesc);
    else delete (HTMLElement.prototype as { offsetParent?: unknown }).offsetParent;
    window.history.replaceState(null, '', '/');
  });

  it('scrolls the English cell when the Greek line is hidden, without switching to bilingual view', async () => {
    const data: BookData = {
      book: 1,
      speakerRoster: ['Watchman'],
      segments: [{
        id: '1:200', column: '200',
        greek: [{ n: 200, text: 'β', tokens: [], ref: '200' }],
        speakers: [{ line: 200, offset: 0, label: 'Φυ.', display: 'Watchman' }],
        english: { text: 'Two hundred.', notes: [], markers: [], turns: [{ offset: 0, speaker: 'Watchman', display: 'WATCHMAN' }] },
      }],
    };
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();

    expect(container.querySelector('.reader-body')?.classList.contains('view-english')).toBe(true);
    expect(container.querySelector('.reader-body')?.classList.contains('view-both')).toBe(false);

    const greek = document.getElementById('L200-200');
    const eng = container.querySelector('.english-col');
    expect(greek).toBeTruthy();
    expect(eng).toBeTruthy();
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
    const instances = (Element.prototype.scrollIntoView as ReturnType<typeof vi.fn>).mock.instances;
    expect(instances).not.toContain(greek);
    expect(instances.some((n) => n === eng || (n instanceof Element && (eng!.contains(n) || n.contains(eng!))))).toBe(true);
  });
});

describe('Reader.svelte English copy citation (Astra lane A, F6)', () => {
  beforeEach(() => localStorage.clear());

  function engBook(): BookData {
    return {
      book: 1,
      speakerRoster: ['Watchman'],
      segments: [{
        id: '1:1', column: '1',
        greek: [
          { n: 1, text: 'πρῶτος λόγος', tokens: [], ref: '1' },
          { n: 2, text: 'δεύτερος λόγος', tokens: [], ref: '2' },
        ],
        speakers: [{ line: 1, offset: 0, label: 'Φυ.', display: 'Watchman' }],
        english: {
          text: 'Ordinary Athenian Society English.',
          notes: [], markers: [],
          turns: [{ offset: 0, speaker: 'Watchman', display: 'WATCHMAN' }],
        },
      }],
    };
  }

  it('appends a play-line citation and tr. credit when copying ordinary English', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: engBook() } });
    await flush();
    const eng = container.querySelector('.english-col');
    expect(eng).toBeTruthy();
    selectNode(eng!);
    const copied = fireCopy(container);
    expect(copied).toContain('Ordinary Athenian Society English.');
    expect(copied).toContain('(Fix. 1–2)');
    expect(copied).toContain('tr. Test Translator (Test, 1926)');
    const lines = copied!.split('\n');
    expect(lines.at(-2)).toBe('(Fix. 1–2)');
    expect(lines.at(-1)).toBe('tr. Test Translator (Test, 1926)');
  });

  it('does not append citation or credit when citeCopy is off', async () => {
    localStorage.setItem('reader-cite-copy', 'false');
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: engBook() } });
    await flush();
    selectNode(container.querySelector('.english-col')!);
    expect(fireCopy(container)).toBeUndefined();
  });

  it('keeps the Greek citation and does not add a second one when the selection already has one', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: engBook() } });
    await flush();
    selectNode(container.querySelector('#L1-1')!);
    const copied = fireCopy(container);
    expect(copied).toContain('(Fix. 1)');
    expect(copied).not.toContain('(Fix. 1–2)');
    expect(copied?.match(/\(Fix\./g)).toHaveLength(1);
  });
});

describe('Reader.svelte later antilabe share citation (Astra lane A, F7)', () => {
  beforeEach(() => localStorage.clear());

  it('cites the later share of Frogs 7 as line 7, not the segment start', async () => {
    const data: BookData = {
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
        english: {
          text: 'Then what witty thing shall I say? Come, take courage; only … Only what?',
          notes: [], markers: [],
          turns: [
            { offset: 0, speaker: 'Xanthias', display: 'XANTHIAS' },
            { offset: 35, speaker: 'Dionysus', display: 'DIONYSUS' },
            { offset: 62, speaker: 'Xanthias', display: 'XANTHIAS' },
          ],
        },
      }],
    };
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: data } });
    await flush();
    const shares = [...container.querySelectorAll('.greek-line.antilabe-share')];
    expect(shares).toHaveLength(2);
    // The second antilabe share is Xanthias' later half of line 7.
    selectNode(shares[1]!);
    const copied = fireCopy(container);
    expect(copied).toContain('(Fix. 7)');
    expect(copied).not.toContain('(Fix. 6)');
  });
});

describe('Reader.svelte repeated printed refs (Astra lane A, F8)', () => {
  beforeEach(() => localStorage.clear());

  function doubletBook(): BookData {
    return {
      book: 1,
      speakerRoster: ['Messenger'],
      segments: [
        {
          id: '1:803', column: '803',
          greek: [{ n: 803, text: 'πρῶτος 803', tokens: [], ref: '803' }],
          speakers: [{ line: 803, offset: 0, label: 'Αγ.', display: 'Messenger' }],
          english: { text: 'First 803.', notes: [], markers: [], turns: [{ offset: 0, speaker: 'Messenger', display: 'MESSENGER' }] },
        },
        {
          id: '1:803.2', column: '803',
          greek: [{ n: 900, text: 'δεύτερος 803', tokens: [], ref: '803' }],
          speakers: [{ line: 900, offset: 0, label: 'Αγ.', display: 'Messenger' }],
          english: { text: 'Second 803.', notes: [], markers: [], turns: [{ offset: 0, speaker: 'Messenger', display: 'MESSENGER' }] },
        },
        {
          id: '1:810', column: '810',
          greek: [{ n: 810, text: 'πρῶτος 810', tokens: [], ref: '810' }],
          speakers: [{ line: 810, offset: 0, label: 'Αγ.', display: 'Messenger' }],
          english: { text: 'First 810.', notes: [], markers: [], turns: [{ offset: 0, speaker: 'Messenger', display: 'MESSENGER' }] },
        },
        {
          id: '1:810.2', column: '810',
          greek: [{ n: 910, text: 'δεύτερος 810', tokens: [], ref: '810' }],
          speakers: [{ line: 910, offset: 0, label: 'Αγ.', display: 'Messenger' }],
          english: { text: 'Second 810.', notes: [], markers: [], turns: [{ offset: 0, speaker: 'Messenger', display: 'MESSENGER' }] },
        },
      ],
    };
  }

  it('gives a later occurrence of a printed ref a unique segment id col-<ref>--<k>', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: doubletBook() } });
    await flush();
    expect(container.querySelectorAll('#col-803')).toHaveLength(1);
    expect(container.querySelectorAll('#col-803--2')).toHaveLength(1);
    expect(container.querySelectorAll('#col-810')).toHaveLength(1);
    expect(container.querySelectorAll('#col-810--2')).toHaveLength(1);
    expect(container.querySelector('#col-803')?.textContent).toContain('πρῶτος 803');
    expect(container.querySelector('#col-803--2')?.textContent).toContain('δεύτερος 803');
  });

  it('a bare #803 / ?loc=803 still lands on the first occurrence', async () => {
    window.history.replaceState(null, '', '/PLAYLINE/book/1?loc=803');
    (Element.prototype.scrollIntoView as unknown as { mockClear: () => void }).mockClear();
    render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: doubletBook() } });
    await flush();
    const first = document.getElementById('L803-803');
    const second = document.getElementById('L803-900');
    expect(first).toBeTruthy();
    expect((Element.prototype.scrollIntoView as ReturnType<typeof vi.fn>).mock.instances).toContain(first);
    expect((Element.prototype.scrollIntoView as ReturnType<typeof vi.fn>).mock.instances).not.toContain(second);
    window.history.replaceState(null, '', '/');
  });

  it('restores #803--2 to the second occurrence and saves that occurrence on scroll', async () => {
    window.history.replaceState(null, '', '/PLAYLINE/book/1#803--2');
    let ioCallback: IntersectionObserverCallback | undefined;
    class CapturingIO {
      constructor(cb: IntersectionObserverCallback) { ioCallback = cb; }
      observe() {}
      unobserve() {}
      disconnect() {}
      takeRecords() { return []; }
    }
    vi.stubGlobal('IntersectionObserver', CapturingIO);
    (Element.prototype.scrollIntoView as unknown as { mockClear: () => void }).mockClear();

    render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: doubletBook() } });
    await flush();
    const secondSeg = document.getElementById('col-803--2');
    expect(secondSeg).toBeTruthy();
    expect((Element.prototype.scrollIntoView as ReturnType<typeof vi.fn>).mock.instances).toContain(secondSeg);

    await wait(4200);
    window.dispatchEvent(new Event('scroll'));
    await flush();
    expect(ioCallback).toBeTruthy();
    const line = document.getElementById('L803-900');
    ioCallback!(
      [{ target: line, isIntersecting: true, boundingClientRect: { top: 5 } } as unknown as IntersectionObserverEntry],
      {} as IntersectionObserver,
    );
    expect(window.location.hash).toBe('#803--2');
    expect(localStorage.getItem('reader-loc-PLAYLINE')).toBe('803--2');
    vi.unstubAllGlobals();
    window.history.replaceState(null, '', '/');
  }, 10000);
});

