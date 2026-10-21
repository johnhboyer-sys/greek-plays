// P4 skin, the running head (docs/p4-plan.md; docs/mockups/2026-09-08-blend.html):
// the chrome a reader actually sees on a play page is ReaderShell.astro's
// <header class="page-header"> — the Contents toggle, this Breadcrumb, and the
// tools. Two things are load-bearing and easy to lose in a restyle: the header
// names the site and links home, and no crumb is ever a work-switcher (John's
// ruling: no play-switcher inside the reader). The .astro files are asserted
// as source text (the no-static-registry.test.ts convention) — Astro pages
// aren't renderable under vitest.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Breadcrumb from '../components/Breadcrumb.svelte';
import { SITE_NAME } from '../lib/site';

// Breadcrumb takes its option lists as plain data; only the two path helpers
// come from the registry, so stubs keep this test off the built registry.
vi.mock('@shared/lib/works', () => ({
  authorPath: (id: string) => `/${id}`,
  workLanding: (id: string) => `/aeschylus/${id}`,
}));

const authors = [{ id: 'aeschylus', name: 'Aeschylus' }];
const works = [{ id: 'agamemnon', title: 'Agamemnon' }];

describe('reader header: the running head', () => {
  it('leads with the site name as a link home, then AUTHOR and PLAY as links back out', () => {
    const { container } = render(Breadcrumb, {
      props: { authorId: 'aeschylus', authors, workId: 'agamemnon', works, readerNav: true },
    });

    expect(screen.getByRole('link', { name: SITE_NAME })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Aeschylus' })).toHaveAttribute('href', '/aeschylus');
    expect(screen.getByRole('link', { name: 'Agamemnon' })).toHaveAttribute('href', '/aeschylus/agamemnon');
    // The site name is the first crumb, before the author.
    const crumbs = [...container.querySelectorAll('a')].map((a) => a.textContent?.trim());
    expect(crumbs).toEqual([SITE_NAME, 'Aeschylus', 'Agamemnon']);
  });

  it('offers no switcher — every crumb is a plain link', () => {
    const { container } = render(Breadcrumb, {
      props: { authorId: 'aeschylus', authors, workId: 'agamemnon', works, readerNav: true },
    });

    expect(container.querySelector('select')).toBeNull();
  });

  it('is the header ReaderShell renders, and that header has no <select>', () => {
    const shell = readFileSync(join(process.cwd(), 'src', 'components', 'ReaderShell.astro'), 'utf8');
    const header = shell.slice(
      shell.indexOf('<header class="page-header">'),
      shell.indexOf('<div class="nav-panel"'),
    );

    expect(header).toContain('<Breadcrumb');
    expect(header).not.toContain('<select');
  });
});

// UI pass 2, direction B: a play's running head is ReaderHead.astro, the
// same claims in its own markup: the site name links home, the author and the
// play are links back out, and nothing in it is a <select> switcher.
describe("a play's running head (direction B)", () => {
  const head = readFileSync(join(process.cwd(), 'src', 'components', 'ReaderHead.astro'), 'utf8');
  const markup = head.slice(head.indexOf('<header class="rh"'), head.indexOf('</header>'));

  it('is the head ReaderShell renders for a play', () => {
    const shell = readFileSync(join(process.cwd(), 'src', 'components', 'ReaderShell.astro'), 'utf8');
    expect(shell).toContain('{isPlayLine ? <ReaderHead work={work} editionsOn={editionsOn} /> : (');
  });

  it('leads with the site name as a link home, then the author and the play as links back out', () => {
    expect(markup).toContain('data-reader-head');
    const crumbs = markup.slice(markup.indexOf('<span class="crumbs">'), markup.indexOf('<span class="ctl">'));
    const hrefs = [...crumbs.matchAll(/href=\{`([^`]+)`\}/g)].map((m) => m[1]);
    expect(hrefs).toEqual(['${base}/', '${base}${authorPath(author.id)}', '${base}${workLanding(work.id)}']);
  });

  it('offers no switcher: no <select> anywhere in it', () => {
    expect(markup).not.toContain('<select');
  });
});

describe('data-genre on <html>', () => {
  it('is set from the author on the reader, the author page and a work landing', () => {
    const shell = readFileSync(join(process.cwd(), 'src', 'components', 'ReaderShell.astro'), 'utf8');
    const authorPage = readFileSync(join(process.cwd(), 'src', 'pages', '[author]', 'index.astro'), 'utf8');
    // P4 Lane E, Grok finding 3: a work landing carried no genre at all.
    const landing = readFileSync(join(process.cwd(), 'src', 'components', 'Landing.astro'), 'utf8');

    expect(shell).toContain('<html lang="en" data-genre={genre}>');
    expect(authorPage).toContain('<html lang="en" data-genre={genre}>');
    expect(authorPage).toContain('const genre = author.genre;');
    expect(landing).toContain('<html lang="en" data-genre={genre}>');
    expect(landing).toContain("const genre = getAuthor(work.author)?.genre;");
  });
});
