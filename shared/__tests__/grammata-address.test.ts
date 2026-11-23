import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

// The dictionary entry's address is a build parameter, PUBLIC_GRAMMATA_LOOKUP
// (HANDOFF-PORTABILITY.md, phase 2), read in one place: shared/lib/grammata.ts,
// which the word popup and the lemma page both load through. Vite puts the
// value in at build time, so what can be checked here is that the module
// reads the one parameter with the address the readers have always used as
// its default, and names the address nowhere else.
const READ = "import.meta.env.PUBLIC_GRAMMATA_LOOKUP || 'https://grammata.pages.dev/t8/lookup.js'";
const read = (p: string) => readFileSync(new URL(p, import.meta.url), 'utf8');

describe('PUBLIC_GRAMMATA_LOOKUP build-time address', () => {
  it('shared/lib/grammata.ts reads the parameter, with the old address as its default', () => {
    const text = read('../lib/grammata.ts');
    expect(text.split(READ).length - 1).toBe(1);
    expect(text.split('grammata.pages.dev/t8').length - 1).toBe(1);
    expect(text).toMatch(/import\(\/\* @vite-ignore \*\/ GRAMMATA_LOOKUP\)/);
  });

  it('no other module of the app or the reader core names the lookup address', () => {
    for (const p of ['../components/WordPopup.svelte', '../../app/src/components/LemmaEntry.svelte']) {
      const text = read(p);
      expect(text, p).not.toMatch(/grammata\.pages\.dev\/t8/);
      expect(text, p).toMatch(/loadGrammataLookup/);
    }
  });
});
