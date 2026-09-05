// The service worker follows the data root off-origin.
//
// public/sw.js is static, so the build substitutes PUBLIC_DATA_ROOT into it
// (app/scripts/postbuild-sw.mjs). These tests run that real build step over the
// real public/sw.js and then execute the emitted worker against stubbed
// caches/fetch — a worker that ignored off-origin corpus fetches, or one whose
// DATA_ROOT placeholder had drifted out of the source, would fail here rather
// than silently break offline reading (docs/cloudflare-setup.md §3a).
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const APP = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const SW_SOURCE = join(APP, 'public', 'sw.js');
const POSTBUILD = join(APP, 'scripts', 'postbuild-sw.mjs');
const ORIGIN = 'https://reader.example';
const R2 = 'https://pub-4ed50262412e44deb78c78b952f07f03.r2.dev';

/** Runs the real postbuild step over a dist copy of sw.js; returns the result. */
function build(dataRoot = '', source = readFileSync(SW_SOURCE, 'utf8')): string {
  const dir = mkdtempSync(join(tmpdir(), 'sw-'));
  mkdirSync(join(dir, 'dist'));
  writeFileSync(join(dir, 'dist', 'sw.js'), source);
  execFileSync('node', [POSTBUILD], {
    cwd: dir,
    env: { ...process.env, PUBLIC_DATA_ROOT: dataRoot },
    stdio: 'pipe',
  });
  return readFileSync(join(dir, 'dist', 'sw.js'), 'utf8');
}

const keyOf = (req: { url: string } | string) => (typeof req === 'string' ? req : req.url);

function makeResponse(body: string) {
  const res: Record<string, unknown> = { ok: true, type: 'cors', body };
  res.clone = () => ({ ...res, clone: res.clone });
  return res;
}

/** Executes a worker source with stubbed globals and returns a driver for it. */
function start(source: string) {
  const handlers: Record<string, (event: unknown) => void> = {};
  const store = new Map<string, unknown>();
  const net = { offline: false, calls: [] as string[] };

  const cache = {
    match: async (req: unknown) => store.get(keyOf(req as { url: string })),
    put: async (req: unknown, res: unknown) => { store.set(keyOf(req as { url: string }), res); },
    addAll: async () => {},
  };
  const caches = { open: async () => cache, keys: async () => [], delete: async () => true };
  const fetchStub = async (req: unknown) => {
    const key = keyOf(req as { url: string });
    net.calls.push(key);
    if (net.offline) throw new TypeError('offline');
    return makeResponse(`fresh:${key}`);
  };
  const self = {
    registration: { scope: `${ORIGIN}/` },
    addEventListener: (type: string, fn: (event: unknown) => void) => { handlers[type] = fn; },
    skipWaiting: () => {},
    clients: { claim: () => {} },
  };

  // eslint-disable-next-line no-new-func
  new Function('self', 'caches', 'location', 'fetch', source)(
    self, caches, new URL(`${ORIGIN}/sw.js`), fetchStub,
  );

  return {
    net,
    async get(url: string, mode = 'cors') {
      const request = { method: 'GET', url, mode };
      let promise: Promise<unknown> | undefined;
      handlers.fetch({ request, respondWith: (p: Promise<unknown>) => { promise = p; } });
      if (promise === undefined) return { handled: false, body: null };
      return { handled: true, body: ((await promise) as { body: string }).body };
    },
  };
}

describe('service worker with an off-origin data root', () => {
  it('caches corpus data from the data root and serves it when offline', async () => {
    const sw = start(build(R2));
    const url = `${R2}/plato-republic/analyses.json`;

    const online = await sw.get(url);
    expect(online.handled).toBe(true);
    expect(online.body).toBe(`fresh:${url}`);

    sw.net.offline = true;
    const offline = await sw.get(url);
    expect(offline.handled).toBe(true);
    expect(offline.body).toBe(`fresh:${url}`);
    // Network-first, not cache-first: the second read tried the network first
    // and only fell back to cache because it failed.
    expect(sw.net.calls).toEqual([url, url]);
  });

  it('claims only the data root, not the whole bucket origin', async () => {
    const sw = start(build(`${R2}/corpus/`));

    expect((await sw.get(`${R2}/corpus/plato-republic/book-1.json`)).handled).toBe(true);
    expect((await sw.get(`${R2}/elsewhere.json`)).handled).toBe(false);
  });
});

describe('service worker with same-origin data (no PUBLIC_DATA_ROOT)', () => {
  it('leaves the shipped worker byte-identical', () => {
    expect(build()).toBe(readFileSync(SW_SOURCE, 'utf8'));
  });

  it('keeps network-first data, cache-first assets, and ignores other origins', async () => {
    const sw = start(build());

    expect((await sw.get(`${ORIGIN}/data/plato-republic/analyses.json`)).handled).toBe(true);
    expect(sw.net.calls).toHaveLength(1);

    await sw.get(`${ORIGIN}/_astro/app.js`);
    await sw.get(`${ORIGIN}/_astro/app.js`);
    expect(sw.net.calls).toHaveLength(2); // asset fetched once, then cache-first

    expect((await sw.get('https://example.com/tracker.json')).handled).toBe(false);
  });
});

describe('postbuild-sw', () => {
  it('fails the build if the DATA_ROOT placeholder drifts out of sw.js', () => {
    const drifted = readFileSync(SW_SOURCE, 'utf8').replace("const DATA_ROOT = '';", 'const DATA_ROOT = self.x;');
    expect(() => build(R2, drifted)).toThrow();
  });
});
