// Grammata owns the dictionary entry markup and styles. Keep this URL live:
// one Grammata deploy updates every reader, so do not vendor, proxy, pin, or
// cache-bust it.
const GRAMMATA_LOOKUP = 'https://grammata.pages.dev/t8/lookup.js';

export type GrammataLookup = (
  word: string,
  el: HTMLElement,
  opts?: { lang?: 'grc' | 'lat'; key?: string },
) => Promise<void>;

type GrammataModule = { lookup: GrammataLookup };

export function makeGrammataLoader(
  importModule: () => Promise<GrammataModule>,
): () => Promise<GrammataLookup> {
  let loader: Promise<GrammataLookup> | null = null;
  return () => {
    if (!loader) {
      const pending = importModule().then((mod) => mod.lookup);
      loader = pending;
      pending.catch(() => {
        if (loader === pending) loader = null;
      });
    }
    return loader;
  };
}

// Loaded on the first dictionary request, then reused. Keeping the import in a
// small module also gives tests a local seam to mock; no test imports the remote
// module or fetches the network.
export const loadGrammataLookup = makeGrammataLoader(() => {
  // @vite-ignore keeps the remote specifier out of the bundle graph. Vite
  // cannot resolve an https: import at build time.
  return import(/* @vite-ignore */ GRAMMATA_LOOKUP) as Promise<GrammataModule>;
});
