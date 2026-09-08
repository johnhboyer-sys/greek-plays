import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import Plate from '../components/Plate.svelte';
import RunningHead from '../components/RunningHead.svelte';
import { assignSpeakerSlots } from '../lib/speaker-colors';
import { buildContents } from '../lib/contents';

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
  lastLine: '1672',
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

  it('cites the play by its abbreviation and printed extent', () => {
    const { container } = render(Plate, { props });
    const cite = Array.from(container.querySelectorAll('.plate-margin p'))
      .find((p) => p.querySelector('b')!.textContent === 'Cite as')!;
    expect(cite.textContent).toBe('Cite asAesch. Ag. 1–1672');
  });

  it('drops a margin line the registry has no value for', () => {
    const { container } = render(Plate, {
      props: { ...props, production: null, copyAbbr: null },
    });
    expect(Array.from(container.querySelectorAll('.plate-margin b')).map((b) => b.textContent))
      .toEqual(['Greek text', 'Translations']);
  });

  it('starts the reader on line 1, not on the plate', () => {
    const { container } = render(Plate, { props });
    const go = container.querySelector('.plate-go')!;
    expect(go.textContent).toBe('Start reading →');
    expect(go.getAttribute('href')).toBe('#col-1');
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

  it('lifts the accent in dark mode but keeps the bands deep', () => {
    const dark = GLOBAL_CSS.slice(GLOBAL_CSS.indexOf(':root[data-theme="dark"] {\n  --col-bg:       #24211d'));
    expect(dark).toMatch(/--accent-tragedy:\s*#e0634c/);
    expect(dark).toMatch(/--accent-comedy:\s*#78b892/);
    expect(dark).toMatch(/--band-tragedy:\s*#7a2414/);
    expect(dark).toMatch(/--band-comedy:\s*#1f4a33/);
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
