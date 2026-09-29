// The reader page's intro sentence (the visually hidden <p> under the <h1>) and its
// meta / og / twitter / JSON-LD description name the Greek text with
// "(<edition short>)". With PUBLIC_EDITIONS=1 the page server-renders the default
// translation's own Greek edition (Agamemnon: Smyth's Greek beside Smyth), so the
// sentence must name that edition, not the reference (TLG) one. Flag off: the
// reference edition, as before.
//
// The built-HTML block reads app/dist and skips itself, by name, when that build is
// absent (needs a data build of the play plus `PUBLIC_EDITIONS=1 npm run build`);
// the source block always runs.
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { getWork, visibleTranslations } from '@shared/lib/works';

const dist = resolve(process.cwd(), 'dist');
const PAGES = [
  ['aeschylus', 'agamemnon'],
  ['sophocles', 'antigone'],
  ['euripides', 'hecuba'],
  ['aristophanes', 'frogs'],
] as const;

const decode = (s: string) => s.replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"');

/** The Greek text the page names, from the registry: the default translation's own edition when editions are on. */
function expectedShort(workId: string, editionsOn: boolean): string {
  const work = getWork(workId)!;
  if (!editionsOn || !work.greekEditions?.length) return work.greekSource.short;
  const id = work.defaultTranslation ?? visibleTranslations(work).find(t => t.slot === 'english')?.id;
  const ed = work.translations.find(t => t.id === id)?.edition ?? 'tlg';
  return ed === 'tlg' ? work.greekSource.short : work.greekEditions.find(e => e.id === ed)?.short ?? work.greekSource.short;
}

describe('intro sentence: source', () => {
  const src = readFileSync(resolve(process.cwd(), 'src/components/ReaderShell.astro'), 'utf-8');
  it('names the default edition\'s short, not greekSource.short, in the intro and the meta description', () => {
    expect(src).toContain("greekEditions?.find((e) => e.id === defaultEdition)?.short");
    const uses = src.match(/\(\$\{(\w+(?:\.\w+)*)\}\)/g) ?? [];
    expect(uses).toContain('(${shownGreek})');
    expect(uses).not.toContain('(${work.greekSource.short})');
  });
});

for (const [author, work] of PAGES) {
  const file = `${dist}/${author}/${work}/index.html`;
  const html = existsSync(file) ? readFileSync(file, 'utf-8') : '';
  const built = html !== '';
  const editionsOn = html.includes('id="edition-reader"');
  describe.skipIf(!built)(`intro sentence, built ${work} page (skipped when app/dist lacks ${author}/${work}/)`, () => {
    it(`names ${editionsOn ? 'the default translation\'s edition' : 'the reference edition (flag off)'}`, () => {
      const short = expectedShort(work, editionsOn);
      const intro = decode(html.match(/class="sr-only">[\s\S]*?<p>\s*([\s\S]*?)\s*<\/p>/)![1]!);
      const meta = decode(html.match(/<meta name="description" content="([^"]*)"/)![1]!);
      expect(intro).toContain(`in the original Greek (${short})`);
      expect(meta).toContain(`the original Greek (${short})`);
    });
  });
}
