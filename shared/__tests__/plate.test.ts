import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import Plate from '../components/Plate.svelte';
import RunningHead from '../components/RunningHead.svelte';
import { assignSpeakerSlots } from '../lib/speaker-colors';
import { buildContents } from '../lib/contents';
import { lastPrintedRef } from '../lib/citation';

const HERE = dirname(fileURLToPath(import.meta.url));
const GLOBAL_CSS = readFileSync(join(HERE, '../styles/global.css'), 'utf8');

// P4, "the skin" (docs/p4-plan.md): the play's opening plate, the genre
// accent, and the running head's ruling that it is NOT a switcher.

const ROSTER = ['Watchman', 'Chorus', 'Clytaemestra', 'Herald', 'Agamemnon', 'Cassandra'];
const slots = assignSpeakerSlots(ROSTER);

const props = {
  greekTitle: 'Ἀγαμέμνων',
  title: 'Agamemnon',
  authorName: 'Aeschylus',
  argument: 'DRAFT — Agamemnon comes home from Troy.',
  production: 'City Dionysia, 458 BC · first prize',
  greekSource: 'Murray, Aeschyli tragoediae, 2nd ed. (OCT, 1955)',
  translations: ['H. W. Smyth (Loeb, 1926)', 'E. D. A. Morshead (1881)'],
  copyAbbr: 'Aesch. Ag.',
  lastLine: '1673',
  persons: ROSTER.map((name) => ({ name, slot: slots.get(name)! })),
  startHref: '#col-1',
};

describe('Plate.svelte', () => {
  it('prints the five labels, in John’s words and no others', () => {
    const { container } = render(Plate, { props });
    expect(container.querySelector('.plate-h')!.textContent).toBe('Persons');
    const margin = Array.from(container.querySelectorAll('.plate-margin b')).map((b) => b.textContent);
    expect(margin).toEqual(['Production', 'Greek text', 'Translations', 'Cite as']);
    // No "how to read this" note anywhere on the plate (John, 2026-09-08).
    expect(container.textContent).not.toMatch(/how to read/i);
  });

  it('lists the persons in order of appearance, each in its own slot colour', () => {
    const { container } = render(Plate, { props });
    const items = Array.from(container.querySelectorAll('.plate-cast li'));
    expect(items.map((li) => li.textContent)).toEqual(ROSTER);
    const styles = items.map((li) => li.getAttribute('style')!.replace(/;$/, ''));
    expect(styles).toEqual(ROSTER.map((name) => `--spk: var(--spk-${slots.get(name)})`));
    // The colours are the reader's own: every slot is a real palette var.
    for (const style of styles) {
      expect(GLOBAL_CSS).toContain(`${style.replace('--spk: var(', '').replace(')', '')}:`);
    }
  });

  // P4 Lane C: Agamemnon's roster carries Elder 1 … Elder 12 (the chorus
  // members who speak singly at 1348–71). Twelve "Elder" lines would swamp
  // the plate; they are one entry, at the first member's place.
  it('collapses a numbered roster family into one entry, uncoloured', () => {
    const roster = [...ROSTER, 'Elder 1', 'Elder 2', 'Elder 3', 'Aegisthus'];
    const s = assignSpeakerSlots(roster);
    const { container } = render(Plate, {
      props: { ...props, persons: roster.map((name) => ({ name, slot: s.get(name)! })) },
    });
    const items = Array.from(container.querySelectorAll('.plate-cast li'));
    expect(items.map((li) => li.textContent)).toEqual([...ROSTER, 'Elders 1–3', 'Aegisthus']);
    // No coloured initial: the members hold different slots, so the collapsed
    // entry takes the plain ink.
    const elders = items.find((li) => li.textContent === 'Elders 1–3')!;
    expect(elders.getAttribute('style')!.replace(/;$/, '')).toBe('--spk: var(--text-mid)');
    expect(items.find((li) => li.textContent === 'Aegisthus')!.getAttribute('style')!.replace(/;$/, ''))
      .toBe(`--spk: var(--spk-${s.get('Aegisthus')})`);
  });

  it('prints each person\'s Greek siglum in parentheses: "Chorus (Χο.)" (John, 2026-09-10)', () => {
    const roster = ['Watchman', 'Chorus', 'Elder 1', 'Elder 2', 'Messenger'];
    const s = assignSpeakerSlots(roster);
    const sig: Record<string, string> = { Watchman: 'Φυ.', Chorus: 'Χο.', 'Elder 1': '1.', 'Elder 2': '2.' };
    const { container } = render(Plate, {
      props: { ...props, persons: roster.map((name) => ({ name, slot: s.get(name)!, siglum: sig[name] ?? null })) },
    });
    const items = Array.from(container.querySelectorAll('.plate-cast li'));
    // The collapsed family carries none (its members print different sigla);
    // a person with no Greek siglum carries none.
    expect(items.map((li) => li.textContent)).toEqual(['Watchman (Φυ.)', 'Chorus (Χο.)', 'Elders 1–2', 'Messenger']);
    expect(items[1]!.querySelector('.plate-sigl')!.getAttribute('lang')).toBe('grc');
  });

  it('leaves ordinal-word names and lone numbered entries alone', () => {
    const roster = ['First Innkeeper', 'Second Innkeeper', 'Elder 1'];
    const s = assignSpeakerSlots(roster);
    const { container } = render(Plate, {
      props: { ...props, persons: roster.map((name) => ({ name, slot: s.get(name)! })) },
    });
    expect(Array.from(container.querySelectorAll('.plate-cast li')).map((li) => li.textContent))
      .toEqual(roster);
  });

  it('strips the DRAFT prefix from the argument and tags it instead', () => {
    const { container } = render(Plate, { props });
    const arg = container.querySelector('.plate-arg')!;
    expect(arg.textContent).toBe('Agamemnon comes home from Troy.draft');
    expect(container.querySelector('.plate-draft')!.textContent).toBe('draft');
  });

  it('leaves approved copy alone (no draft tag)', () => {
    const { container } = render(Plate, {
      props: { ...props, argument: 'Agamemnon comes home from Troy.' },
    });
    expect(container.querySelector('.plate-draft')).toBeNull();
    expect(container.querySelector('.plate-arg')!.textContent).toBe('Agamemnon comes home from Troy.');
  });

  it('prints the synopsis straight under the argument, tagged only while DRAFT', () => {
    const synopsis = 'A watchman sees the beacon. Clytaemestra kills Agamemnon in his bath.';
    const { container } = render(Plate, { props: { ...props, synopsis } });
    const syn = container.querySelector('.plate-syn')!;
    expect(syn.previousElementSibling!.classList.contains('plate-arg')).toBe(true);
    expect(syn.textContent).toBe(synopsis);
    const drafted = render(Plate, { props: { ...props, synopsis: `DRAFT — ${synopsis}` } }).container;
    expect(drafted.querySelector('.plate-syn')!.textContent).toBe(`${synopsis}draft`);
    // No synopsis in the registry, no empty paragraph.
    expect(render(Plate, { props }).container.querySelector('.plate-syn')).toBeNull();
    // The argument contains its floated initial, so a one-line argument
    // cannot leave the drop cap hanging beside the synopsis.
    const arg = GLOBAL_CSS.slice(GLOBAL_CSS.indexOf('.plate-arg {'));
    expect(arg.slice(0, arg.indexOf('}'))).toMatch(/display:\s*flow-root/);
  });

  it('cites the play by its abbreviation and printed extent', () => {
    const { container } = render(Plate, { props });
    const cite = Array.from(container.querySelectorAll('.plate-margin p'))
      .find((p) => p.querySelector('b')!.textContent === 'Cite as')!;
    expect(cite.textContent).toBe('Cite asAesch. Ag. 1–1673');
  });

  // P4 Lane E, Grok finding 2: the extent came off the last SEGMENT's column
  // — a chunk's FIRST ref — so every play was cited short (Ag. 1–1672 of
  // 1673, Frogs 1–1528 of 1533). ReaderShell now feeds `lastLine` from
  // lastPrintedRef, which reads the last segment's last printed greek ref.
  it('ends the citation on the last PRINTED line, not the last chunk start', () => {
    // Agamemnon's real tail: the closing chunk starts at 1672 and prints 1673.
    const agTail = [
      { column: '1666', greek: [{ ref: '1666' }, { ref: '1667' }] },
      { column: '1672', greek: [{ ref: '1672' }, { ref: '1673' }] },
    ];
    expect(lastPrintedRef(agTail)).toBe('1673');
    // Frogs: 1528 opens the chunk the edition prints through 1533.
    expect(lastPrintedRef([{ column: '1528', greek: [{ ref: '1528' }, { ref: '1533' }] }]))
      .toBe('1533');
    // A segment with no Greek lines falls back to its own column, and an
    // empty book has no extent at all (the margin line then drops).
    expect(lastPrintedRef([{ column: '9', greek: [] }])).toBe('9');
    expect(lastPrintedRef([])).toBeNull();
    // P4CE finding 5: a lacuna prints no line of its own, so a trailing
    // lacuna-only segment cites the segment BEFORE it — never the lacuna's
    // "post N" placeholder, and never its own chunk column.
    expect(lastPrintedRef([
      { column: '1220', greek: [{ ref: '1225' }, { ref: '1226' }] },
      { column: '1226', greek: [{ ref: 'post 1226', role: 'lacuna' }] },
    ])).toBe('1226');
    expect(lastPrintedRef([
      { column: '1220', greek: [{ ref: '1226' }] },
      { column: '1227', greek: [{ ref: '1227', role: 'heading' }] },
    ])).toBe('1226');
    const { container } = render(Plate, { props: { ...props, lastLine: lastPrintedRef(agTail) } });
    const cite = Array.from(container.querySelectorAll('.plate-margin p'))
      .find((p) => p.querySelector('b')!.textContent === 'Cite as')!;
    expect(cite.textContent).toBe('Cite asAesch. Ag. 1–1673');
  });

  it('drops a margin line the registry has no value for', () => {
    const { container } = render(Plate, {
      props: { ...props, production: null, copyAbbr: null },
    });
    expect(Array.from(container.querySelectorAll('.plate-margin b')).map((b) => b.textContent))
      .toEqual(['Greek text', 'Translations']);
  });

  it('carries no "Start reading" link: the text follows on the same page (John, 2026-09-09)', () => {
    const { container } = render(Plate, { props });
    expect(container.querySelector('.plate-go')).toBeNull();
    expect(container.textContent).not.toContain('Start reading');
  });
});

describe('data-genre picks the accent and the band', () => {
  it('tragedy takes the rubric red, comedy the malachite', () => {
    expect(GLOBAL_CSS).toMatch(/--accent-tragedy:\s*#b1321c/);
    expect(GLOBAL_CSS).toMatch(/--accent-comedy:\s*#2f6b45/);
    expect(GLOBAL_CSS).toMatch(
      /:root\[data-genre="comedy"\]\s*\{[^}]*--accent:\s*var\(--accent-comedy\)[^}]*--band:\s*var\(--band-comedy\)/s,
    );
    expect(GLOBAL_CSS).toMatch(
      /:root\s*\{[^}]*--accent:\s*var\(--accent-tragedy\)[^}]*--band:\s*var\(--band-tragedy\)/s,
    );
  });

  it('sets --text-light to the contrast-safe skin values (Astra lane A, F13)', () => {
    const light = GLOBAL_CSS.slice(GLOBAL_CSS.indexOf(':root {\n  /* Cardo for everything'));
    expect(light).toMatch(/--text-light:\s*#6d675d;/);
    const dark = GLOBAL_CSS.slice(GLOBAL_CSS.indexOf(':root[data-theme="dark"] {\n  --col-bg:       #24211d'));
    expect(dark).toMatch(/--text-light:\s*#928a7e;/);
  });

  it('lifts the accent in dark mode but keeps the bands deep', () => {
    const dark = GLOBAL_CSS.slice(GLOBAL_CSS.indexOf(':root[data-theme="dark"] {\n  --col-bg:       #24211d'));
    expect(dark).toMatch(/--accent-tragedy:\s*#e0634c/);
    expect(dark).toMatch(/--accent-comedy:\s*#78b892/);
    expect(dark).toMatch(/--band-tragedy:\s*#7a2414/);
    expect(dark).toMatch(/--band-comedy:\s*#1f4a33/);
  });

  it('a hanging Greek siglum does not inherit the hanging indent into the number gutter', () => {
    const at = GLOBAL_CSS.indexOf('.reader-body.play-line:not(.view-greek) .greek-line .line-text > .speaker:first-child {');
    const rule = GLOBAL_CSS.slice(at, GLOBAL_CSS.indexOf('}', at));
    expect(rule).toMatch(/position:\s*absolute/);
    expect(rule).toMatch(/text-indent:\s*0/);
  });

  it('an English lead-in sets its lines close but drops to its speech\'s first baseline', () => {
    // John, 2026-09-10: a plain 1.15 line box set every name 4.5px above its
    // text; John, 2026-09-28: at the prose line-height a stacked name's second
    // line sat on the next speaker. So 1.15, dropped by half the difference
    // from the paragraph's own line box (--para-lh, registered as a length).
    const at = GLOBAL_CSS.indexOf('.reader-body.play-line .turn-stack .turn-para > .speaker:first-child {');
    const rule = GLOBAL_CSS.slice(at, GLOBAL_CSS.indexOf('}', at));
    expect(rule).toMatch(/line-height:\s*1\.15/);
    expect(rule).toMatch(/top:\s*calc\(\(var\(--para-lh\) - 1\.15em\) \/ 2\)/);
    expect(GLOBAL_CSS).toMatch(/@property --para-lh \{ syntax: '<length>'; inherits: true;/);
    expect(GLOBAL_CSS).toMatch(/--para-lh:\s*1lh/);
    expect(rule).toMatch(/text-align:\s*right/);
    const long = GLOBAL_CSS.indexOf('.reader-body.play-line .turn-stack .turn-para > .speaker.spk-long:first-child {');
    expect(GLOBAL_CSS.slice(long, GLOBAL_CSS.indexOf('}', long))).not.toMatch(/line-height/);
  });

  it('the plate band paints itself from --band, never from --accent', () => {
    const band = GLOBAL_CSS.slice(GLOBAL_CSS.indexOf('.plate-band {'));
    expect(band.slice(0, band.indexOf('}'))).toContain('background: var(--band)');
  });
});

describe('RunningHead.svelte is not a switcher', () => {
  const contents = buildContents({
    workTitle: 'Agamemnon',
    groupNoun: 'Book',
    bookLabels: ['1'],
    books: 1,
    currentBook: 1,
    bookless: true,
    unit: { singular: 'line', plural: 'lines' },
    manifestBooks: [],
    chapters: {},
    sections: {},
    philosophers: {},
    chapterTitles: {},
    bookHref: () => '/aeschylus/agamemnon',
  });

  it('names the site and links the author and the play back out — no <select>', () => {
    const { container } = render(RunningHead, {
      props: {
        siteName: 'The Greek Drama Reader',
        author: 'Aeschylus',
        workTitle: 'Agamemnon',
        workId: 'agamemnon',
        contents,
        translations: [],
      },
    });
    expect(container.querySelector('.rhsite')!.textContent).toBe('The Greek Drama Reader');
    expect(Array.from(container.querySelectorAll('.rha a')).map((a) => a.textContent))
      .toEqual(['Aeschylus', 'Agamemnon']);
    expect(container.querySelector('select')).toBeNull();
  });
});
