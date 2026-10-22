// The redesign's vase drawings (docs/redesign/drawings/, records in its
// drawings.json). Read at build time, as ReaderShell reads public/data, with
// paths relative to app/. Pages draw a figure with <use> pointing at the copy
// /drawings/<name>.svg emits (pages/drawings/[name].svg.ts), so the file is
// fetched once and cached, and the page can still colour it: the lines take
// the page's `color`, the body takes `--fig-body` (clay in the dark theme,
// docs/redesign/DESIGN.md, Drawings).
import { readFileSync } from 'node:fs';

const DIR = '../docs/redesign/drawings';

interface Record { slug: string; file: string; alt: string; method?: string }

const RECORDS: Record[] = JSON.parse(readFileSync(`${DIR}/drawings.json`, 'utf-8')).drawings;

// Each play's drawing, or drawings laid side by side (Alcestis), from the
// image plan's `final_image` (paths from the repo root).
const PLAN: { work_id: string; final_image?: string | string[] }[] =
  JSON.parse(readFileSync('../docs/redesign/research/play-image-plan.json', 'utf-8')).plays;

/** The playwrights' home-page figures, by author id. */
export const HOME_FIGURES = ['aeschylus', 'sophocles', 'euripides', 'aristophanes'];

export interface Drawing {
  name: string;     // file name without .svg
  alt: string;
  viewBox: string;
  width: number;
  height: number;
  credit: string;   // the SVG's <desc>: source and licence
  silhouette: boolean; // black-figure: black solid, the incisions open in it
}

function record(slug: string): Record | undefined {
  return RECORDS.find((r) => r.slug === slug);
}

function source(file: string): string {
  return readFileSync(`${DIR}/${file}`, 'utf-8');
}

function read(file: string, alt?: string): Drawing {
  const svg = source(file);
  const viewBox = /viewBox="([^"]+)"/.exec(svg)![1];
  const [, , width, height] = viewBox.split(/\s+/).map(Number);
  const title = /<title>([^<]*)<\/title>/.exec(svg)?.[1] ?? '';
  const credit = /<desc>([^<]*)<\/desc>/.exec(svg)?.[1] ?? '';
  const silhouette = /silhouette/i.test(RECORDS.find((r) => r.file === file)?.method ?? '');
  return { name: file.replace(/\.svg$/, ''), alt: alt ?? title, viewBox, width, height, credit, silhouette };
}

/** The drawing recorded under `slug`, or undefined when none exists yet. */
export function drawing(slug: string): Drawing | undefined {
  const r = record(slug);
  return r ? read(r.file, r.alt) : undefined;
}

/** An author page's figure: its own record (`<author>-author`, Aristophanes'
 *  Getty krater) where one exists, else the home figure (commit d6d7d77). */
export function authorDrawing(authorId: string): Drawing | undefined {
  return drawing(`${authorId}-author`) ?? drawing(authorId);
}

/** A play's drawings (none when it is not drawn yet). */
export function playDrawings(workId: string): Drawing[] {
  const fi = PLAN.find((p) => p.work_id === workId)?.final_image;
  return (Array.isArray(fi) ? fi : fi ? [fi] : [])
    .map((path) => read(path.replace(/^docs\/redesign\/drawings\//, '')));
}

/** Every file a page draws, for the endpoint's static paths. */
export function servedNames(): string[] {
  const home = HOME_FIGURES.flatMap((s) => [record(s), record(`${s}-author`)])
    .filter((r): r is Record => Boolean(r))
    .map((r) => r.file.replace(/\.svg$/, ''));
  const plays = PLAN.flatMap((p) => p.final_image || []).filter(Boolean)
    .map((path) => path.replace(/^docs\/redesign\/drawings\//, '').replace(/\.svg$/, ''));
  return [...new Set([...home, ...plays])];
}

/** Every served drawing, for the credits on the Texts and licences page. */
export function servedDrawings(): Drawing[] {
  return servedNames().map((name) => {
    const r = RECORDS.find((x) => x.file === `${name}.svg`);
    return read(`${name}.svg`, r?.alt);
  });
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
