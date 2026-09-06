# Grammata T8: the site's one dictionary renderer

Every LSJ entry the site shows — the word popup and the `/lemma` pages — is
rendered by Grammata's T8 widget, never by local HTML. See CLAUDE.md's
"Dictionary" ruling (2026-09-05) for the full policy.

## What the site fetches

- `data/lsj-heads.json` — `{ key -> { head, hom? } }`, the Unicode headword
  and LSJ's own homograph letter for every dictionary key. Built by
  `app/scripts/build-lsj-heads.mjs`, wired into `npm run build`
  (`scripts/build-public.mjs`). ~14k keys, well under 200 KB gzipped.
- Nothing else. No LSJ shard HTML ever ships to the browser.

## What Grammata serves

At runtime the site dynamically imports
`https://grammata.pages.dev/t8/lookup.js` and calls
`lookup(word, el, { lang: 'grc' | 'lat', key? })`, which renders the entry's
markup and styles directly into `el`. One Grammata deploy updates every
reader site that uses it.

- `shared/lib/grammata.ts` is the ONE place that imports this URL
  (`loadGrammataLookup()`, `/* @vite-ignore */`, memoized after first load).
  A failed import clears that memo so the next dictionary request retries.
- `shared/components/WordPopup.svelte` mounts a `.grammata-mount` div per
  dictionary-entry card and calls the widget with `{ key }` once the card
  opens — never with the raw surface form, which would re-analyse from
  scratch and discard this reader's own disambiguation.
- `app/src/components/LemmaEntry.svelte` mounts the same widget on
  `/lemma/<lang>/entry/`.

## The never-vendor rule

Do not vendor, pin, proxy, or cache-bust `lookup.js`. Its own deploys are the
update mechanism — pinning it defeats the point of a single shared widget
across reader sites.

## Testing

Never let a test reach the real network module. Mock `../lib/grammata`
(or `@shared/lib/grammata`) and assert on the mocked `loadGrammataLookup`/
`lookup` call — see `shared/__tests__/word-popup.test.ts` for the pattern:

```ts
const { mockLookup } = vi.hoisted(() => ({ mockLookup: vi.fn(async () => undefined) }));
vi.mock('../lib/grammata', () => ({
  loadGrammataLookup: vi.fn(async () => mockLookup),
}));
```

Assert `mockLookup` is called with `('', el, { lang, key })` once a card
opens, and that no `.lsj-entry` (or other local dictionary markup) ever
renders.

The loader test uses `makeGrammataLoader()` with a mocked importer that fails
once and then succeeds; it does not import the live URL.
