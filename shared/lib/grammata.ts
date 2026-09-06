// Grammata owns the dictionary entry markup and styles. Keep this URL live:
// one Grammata deploy updates every reader, so do not vendor, proxy, pin, or
// cache-bust it.
const GRAMMATA_LOOKUP = 'https://grammata.pages.dev/t8/lookup.js';

export type GrammataLookup = (
  word: string,
  el: HTMLElement,
  opts?: { lang?: 'grc' | 'lat'; key?: string },
) => Promise<void>;

let loader: Promise<GrammataLookup> | null = null;

// Loaded on the first dictionary request, then reused. Keeping the import in a
// small module also gives tests a local seam to mock; no test imports the remote
// module or fetches the network.
export function loadGrammataLookup(): Promise<GrammataLookup> {
  // @vite-ignore keeps the remote specifier out of the bundle graph. Vite
  // cannot resolve an https: import at build time.
  if (!loader) {
    loader = import(/* @vite-ignore */ GRAMMATA_LOOKUP).then((mod) => mod.lookup);
  }
  return loader;
}
