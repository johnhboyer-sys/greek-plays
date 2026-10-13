// The redesign's vase drawings (docs/redesign/drawings/, records in its
// drawings.json). Read at build time, as ReaderShell reads public/data, with
// paths relative to app/. Pages draw a figure with <use> pointing at the copy
// /drawings/<name>.svg emits (pages/drawings/[name].svg.ts), so the file is
// fetched once and cached, and the page can still colour it: the lines take
// the page's `color`, the body takes `--fig-body` (clay in the dark theme,
// docs/redesign/DESIGN.md, Drawings).
import { readFileSync } from 'node:fs';

const DIR = '../docs/redesign/drawings';

interface Record { slug: string; file: string; alt: string }

const RECORDS: Record[] = JSON.parse(readFileSync(`${DIR}/drawings.json`, 'utf-8')).drawings;

/** The playwrights' home-page figures, by author id. */
export const HOME_FIGURES = ['aeschylus', 'sophocles', 'euripides', 'aristophanes'];

export interface Drawing {
  name: string;     // file name without .svg
  alt: string;
  viewBox: string;
  width: number;
  height: number;
}

function record(slug: string): Record | undefined {
  return RECORDS.find((r) => r.slug === slug);
}

function source(file: string): string {
  return readFileSync(`${DIR}/${file}`, 'utf-8');
}

/** The drawing recorded under `slug`, or undefined when none exists yet. */
export function drawing(slug: string): Drawing | undefined {
  const r = record(slug);
  if (!r) return undefined;
  const viewBox = /viewBox="([^"]+)"/.exec(source(r.file))![1];
  const [, , width, height] = viewBox.split(/\s+/).map(Number);
  return { name: r.file.replace(/\.svg$/, ''), alt: r.alt, viewBox, width, height };
}

/** The home figures' files, for the endpoint's static paths. */
export function homeFigureNames(): string[] {
  return HOME_FIGURES.map((s) => record(s)).filter((r): r is Record => Boolean(r))
    .map((r) => r.file.replace(/\.svg$/, ''));
}

/** The SVG as served: the figure wrapped in <g id="fig"> for <use>, and the
 *  body's fill taken from --fig-body (a page's CSS can't reach into a <use>
 *  copy, but custom properties inherit into it). */
export function servedSvg(name: string): string {
  const svg = source(`${name}.svg`);
  return svg
    .replace(/<path class="body" fill="none"/g, '<path class="body" style="fill:var(--fig-body,none)"')
    .replace(/(<svg\b[^>]*>)/, '$1<g id="fig">')
    .replace(/<\/svg>\s*$/, '</g></svg>\n');
}
