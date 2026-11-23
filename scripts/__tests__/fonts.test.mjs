// The site's own fonts (app/public/fonts/; aristotle-reader's test, with the
// plays' counts and a check of the pages): fonts.css and the folder must name
// each other and nothing else. A rule whose file is missing shows as a silent
// fallback face in a browser, and an address on another host is an outside
// call, so both are caught here, where they are loud.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const FONTS = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'app', 'public', 'fonts');

// css: the stylesheet's text. files: name -> first four bytes, as latin1.
function fontProblems(css, files) {
  const problems = [];
  const bare = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const rules = [...bare.matchAll(/@font-face\s*\{([^}]*)\}/g)].map((m) => m[1]);
  if (!rules.length) problems.push('examined nothing: no @font-face rule');
  // Nothing but the rules: a "rule" found inside a string, or beside an
  // @import, is not one a browser reads as a face.
  if (bare.replace(/@font-face\s*\{[^}]*\}/g, '').trim()) problems.push('the stylesheet holds something other than @font-face rules');
  const named = new Set();
  const families = new Set();
  for (const rule of rules) {
    const family = (rule.match(/font-family:\s*['"]?([^;'"]+)['"]?\s*;/) || [])[1];
    if (!family) { problems.push('a rule has no font-family'); continue; }
    families.add(family);
    if (!/unicode-range:/.test(rule)) problems.push(`${family}: a rule has no unicode-range`);
    // The file is the one the src descriptor names, and src names one.
    const src = rule.match(/(?:^|;)\s*src:\s*url\(\s*['"]?([^'")\s]+)['"]?\s*\)\s*format\(\s*['"]woff2['"]\s*\)\s*;/);
    if (!src) { problems.push(`${family}: a rule has no src that names one woff2 file`); continue; }
    const url = src[1];
    if (!/^[a-z0-9-]+\.woff2$/.test(url)) problems.push(`${family}: ${url} is not a font file's bare name in this folder`);
    else if (!(url in files)) problems.push(`${family}: ${url} is not in the folder`);
    else named.add(url);
  }
  if (/@import|https?:|\/\//i.test(bare)) problems.push('the stylesheet names an address outside its folder');
  const licences = new Set([...families].map((f) => `OFL-${f.replace(/ /g, '')}.txt`));
  for (const name of licences) if (!(name in files)) problems.push(`no ${name} for a family the stylesheet declares`);
  for (const [name, magic] of Object.entries(files)) {
    if (name === 'fonts.css') continue;
    if (name.endsWith('.woff2')) {
      if (!named.has(name)) problems.push(`${name} is in the folder and no rule names it`);
      if (magic !== 'wOF2') problems.push(`${name} is not a woff2 file`);
    } else if (!licences.has(name)) problems.push(`${name} is in the folder and belongs to no declared family`);
  }
  return { problems, rules: rules.length, files: named.size, families: families.size };
}

const rule = (file, family = 'A Face') => `@font-face { font-family: '${family}'; src: url(${file}) format('woff2'); unicode-range: U+0000-00FF; }\n`;
const good = () => ({ css: rule('a-face-latin.woff2'), files: { 'fonts.css': '@fon', 'a-face-latin.woff2': 'wOF2', 'OFL-AFace.txt': 'Copy' } });

test('fonts: a folder and stylesheet that name each other pass', () => {
  const { css, files } = good();
  assert.deepEqual(fontProblems(css, files), { problems: [], rules: 1, files: 1, families: 1 });
});

for (const [name, change, pattern] of [
  ['an empty stylesheet examines nothing', (g) => { g.css = '/* @font-face { } */'; }, /examined nothing/],
  ['a rule whose file is missing', (g) => { delete g.files['a-face-latin.woff2']; }, /a-face-latin\.woff2 is not in the folder/],
  ['a file no rule names', (g) => { g.files['spare.woff2'] = 'wOF2'; }, /spare\.woff2 is in the folder and no rule names it/],
  ['a file on another host', (g) => { g.css = rule('https://fonts.gstatic.com/s/a.woff2'); }, /not a font file's bare name|outside its folder/],
  ['a protocol-relative address', (g) => { g.css = rule('//fonts.gstatic.com/s/a.woff2'); }, /outside its folder/],
  ['a path out of the folder', (g) => { g.css = rule('../a-face-latin.woff2'); }, /not a font file's bare name/],
  ['an imported stylesheet', (g) => { g.css = `@import url(other.css);\n${g.css}`; }, /outside its folder/],
  ['a rule with no range', (g) => { g.css = g.css.replace(/unicode-range:[^;]+;/, ''); }, /no unicode-range/],
  ['a family with no licence', (g) => { delete g.files['OFL-AFace.txt']; }, /no OFL-AFace\.txt/],
  ['a licence for no family', (g) => { g.files['OFL-Other.txt'] = 'Copy'; }, /OFL-Other\.txt is in the folder and belongs to no declared family/],
  ['a file that is not a font', (g) => { g.files['a-face-latin.woff2'] = '<htm'; }, /is not a woff2 file/],
  ['a rule that is only words in a string', (g) => { g.css = `.x::after { content: "${g.css.trim()}"; }`; }, /something other than @font-face rules/],
  ['another kind of rule beside the faces', (g) => { g.css += 'body { font-family: serif; }\n'; }, /something other than @font-face rules/],
  ['a file named by a descriptor that is not src', (g) => { g.css = g.css.replace('src:', '--unused:'); }, /no src that names one woff2 file/],
  ['a second file in one src', (g) => { g.css = g.css.replace("format('woff2')", "format('woff2'), url(b.woff2) format('woff2')"); }, /no src that names one woff2 file/],
  ['a stray file', (g) => { g.files['.DS_Store'] = '\0\0\0\x01'; }, /\.DS_Store is in the folder/],
]) {
  test(`fonts: ${name} fails`, () => {
    const g = good();
    change(g);
    const r = fontProblems(g.css, g.files);
    assert.ok(r.problems.some((p) => pattern.test(p)), `no problem matched ${pattern}: ${JSON.stringify(r.problems)}`);
  });
}

test('fonts: the site\'s folder and its stylesheet name each other', () => {
  const files = {};
  for (const name of readdirSync(FONTS)) files[name] = readFileSync(path.join(FONTS, name)).subarray(0, 4).toString('latin1');
  const r = fontProblems(readFileSync(path.join(FONTS, 'fonts.css'), 'utf8'), files);
  assert.deepEqual(r.problems, []);
  // The six families the site's styles name; a seventh, or one gone, is a
  // change to make here on purpose.
  assert.deepEqual({ rules: r.rules, files: r.files, families: r.families }, { rules: 66, files: 66, families: 6 });
});

// The pages: no page source names a Google font host, and every page that
// linked Google's stylesheet now links this one, under the site's base.
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
function sources(dir, out = []) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== '__tests__' && e.name !== 'node_modules') sources(p, out); }
    else if (/\.(astro|svelte|ts|css|mjs|js|html)$/.test(e.name)) out.push(p);
  }
  return out;
}

test('fonts: no page, component, or style of the site names a Google font host', () => {
  const files = [...sources(path.join(ROOT, 'app', 'src')), ...sources(path.join(ROOT, 'shared', 'components')),
    ...sources(path.join(ROOT, 'shared', 'styles')), ...sources(path.join(ROOT, 'shared', 'lib'))];
  assert.ok(files.length > 100, `read ${files.length} files`);
  const named = files.filter((f) => /fonts\.(googleapis|gstatic)\.com/.test(readFileSync(f, 'utf8')));
  assert.deepEqual(named.map((f) => path.relative(ROOT, f)), []);
  const linking = files.filter((f) => readFileSync(f, 'utf8').includes('<link rel="stylesheet" href={`${base}/fonts/fonts.css`} />'));
  assert.equal(linking.length, 15, linking.map((f) => path.relative(ROOT, f)).join(', '));
});
