// The search page's row tables (shared/lib/row-table.ts): for each play, and
// each Greek edition of it, what the results page needs to count its rows and
// pages without reading the books. Written beside the books, as
// build/dist/<play>/rows.json and build/dist/<play>/ed/<id>/rows.json, so the
// data root serves them wherever it serves the books (R2 in production; the
// Astro build copies build/dist for a same-origin site).
//
// Made from the built books by the page's own functions (encodeRowBook),
// bundled with app/'s esbuild as verify-registry-roundtrip.mjs bundles
// works.ts. encodeRowBook checks a sample of its English units against
// unitAtEnglish and throws on the first that differs: the build fails.
//
// Run after the books exist (and after the alternate translations are
// aligned into them), before the Astro build.
// Usage: node scripts/build-row-tables.mjs [build/dist]
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { gzipSync } from 'node:zlib';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const DIST = process.argv[2] ?? join(ROOT, 'build', 'dist');

// The env the Astro build sees: PUBLIC_* as the shell sets them, private
// translations off (build-public.mjs forces them off for the app).
const env = { BASE_URL: '/' };
for (const [k, v] of Object.entries(process.env)) if (k.startsWith('PUBLIC_')) env[k] = v;
env.PUBLIC_SHOW_PRIVATE = '0';

const esbuildPath = join(ROOT, 'app', 'node_modules', 'esbuild', 'lib', 'main.js');
const { default: esbuild } = await import(pathToFileURL(esbuildPath).href);
const bundled = await esbuild.build({
  stdin: {
    contents: `export { encodeRowBook } from './shared/lib/row-table.ts';
export { WORKS, searchableTranslations } from './shared/lib/works.ts';`,
    resolveDir: ROOT,
    loader: 'ts',
  },
  bundle: true,
  format: 'esm',
  platform: 'node',
  write: false,
  logLevel: 'error',
  define: { 'import.meta.env': JSON.stringify(env) },
  // Vite's `?raw` imports (the glossary's Markdown), as text.
  plugins: [{
    name: 'raw',
    setup(build) {
      build.onResolve({ filter: /\?raw$/ }, (a) => ({ path: join(a.resolveDir, a.path.slice(0, -4)), namespace: 'raw' }));
      build.onLoad({ filter: /.*/, namespace: 'raw' }, (a) => ({ contents: readFileSync(a.path, 'utf8'), loader: 'text' }));
    },
  }],
});
const tmp = mkdtempSync(join(tmpdir(), 'build-row-tables-'));
const modPath = join(tmp, 'row-table.mjs');
writeFileSync(modPath, bundled.outputFiles[0].text);
const { encodeRowBook, WORKS, searchableTranslations } = await import(pathToFileURL(modPath).href);
rmSync(tmp, { recursive: true, force: true });

const bookFiles = (dir) => readdirSync(dir).filter((f) => /^book-\d+\.json$/.test(f)).sort();
function writeTable(dir, translations) {
  const books = {};
  for (const file of bookFiles(dir)) {
    const book = JSON.parse(readFileSync(join(dir, file), 'utf8'));
    books[String(Number(file.slice(5, -5)))] = encodeRowBook(book, translations);
  }
  const text = JSON.stringify({ v: 1, t: translations.map((t) => t.id), books });
  writeFileSync(join(dir, 'rows.json'), text);
  return [text.length, gzipSync(text).length];
}

const started = Date.now();
let tables = 0;
let raw = 0;
let gz = 0;
for (const work of WORKS) {
  const dir = join(DIST, work.id);
  if (!existsSync(dir) || !bookFiles(dir).length) continue;
  const translations = searchableTranslations(work);
  const dirs = [dir];
  const eds = join(dir, 'ed');
  if (existsSync(eds)) {
    for (const ed of readdirSync(eds).sort()) {
      const edDir = join(eds, ed);
      if (statSync(edDir).isDirectory() && bookFiles(edDir).length) dirs.push(edDir);
    }
  }
  for (const d of dirs) {
    const [r, g] = writeTable(d, translations);
    tables++;
    raw += r;
    gz += g;
  }
}
const kb = (n) => `${(n / 1024).toFixed(0)} KB`;
console.log(`  ${tables} row table(s), ${kb(raw)} (${kb(gz)} gzip), ${((Date.now() - started) / 1000).toFixed(1)} s`);
