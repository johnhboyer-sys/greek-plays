// node --test scripts/__tests__/deploy-cloudflare.test.mjs
// scripts/deploy-cloudflare.mjs for the plays, with no build, no network,
// and no Cloudflare: the deploy's every branch runs with fakes for the
// programs it calls (git, node, npx wrangler), the live sitemap, and the
// data gates. The tag tests (tagPlan, tagDeploy, tagCommits, uncleanFiles)
// are homer-reader's, against a real checkout with a bare origin.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

import {
  MAX_FILES, Refusal, auditDistScale, countSitemapPages, deploy, distProblems, parseArgs,
  tagCommits, tagDeploy, tagPlan, uncleanFiles, walk,
} from '../deploy-cloudflare.mjs';

test('parseArgs: a rehearsal by default; --deploy deploys; flags with and without values; refusals', () => {
  assert.deepEqual(parseArgs([]), { deploy: false, dryRun: false, site: 'https://greekdrama.johnhboyer.com', minPagesRatio: 0.9, skipLinkCheck: false, noTag: false, help: false });
  assert.equal(parseArgs(['--deploy']).deploy, true);
  assert.equal(parseArgs(['--dry-run']).deploy, false);
  assert.equal(parseArgs(['--site=https://x.example/']).site, 'https://x.example');
  assert.equal(parseArgs(['--min-pages-ratio=0.5']).minPagesRatio, 0.5);
  for (const bad of [['--deploy', '--dry-run'], ['--deploy=yes'], ['--site='], ['--min-pages-ratio=x'], ['--min-pages-ratio='], ['--force'], ['deploy']]) {
    assert.throws(() => parseArgs(bad), Error, JSON.stringify(bad));
  }
});

test('countSitemapPages and auditDistScale', () => {
  assert.equal(countSitemapPages('<urlset><url><loc>a</loc></url><url><loc>b</loc></url></urlset>'), 2);
  assert.equal(countSitemapPages(''), 0);
  assert.equal(auditDistScale(90, 100, 0.9).ok, true);
  assert.match(auditDistScale(89, 100, 0.9).reason, /below the 90% floor \(90\)/);
  assert.equal(auditDistScale(0, 100, 0).ok, true);
});

// A build in small: the pages, a worker with no data root, data, and the
// marker that shows the feedback form. `change` damages it.
function site(change = () => {}) {
  const root = mkdtempSync(path.join(tmpdir(), 'deploy-plays-'));
  const dist = path.join(root, 'app', 'dist');
  const put = (rel, text) => { mkdirSync(path.dirname(path.join(dist, rel)), { recursive: true }); writeFileSync(path.join(dist, rel), text); };
  put('index.html', '<h1>Plays</h1>');
  put('read/euripides/medea/index.html', '<p>Medea</p>');
  put('sw.js', "const DATA_ROOT = '';\n");
  put('feedback-endpoint.json', '{"post":"/api/feedback"}');
  put('data/medea/manifest.json', '{}');
  change({ dist, put, root });
  return { root, dist, done: () => rmSync(root, { recursive: true, force: true }) };
}

test('distProblems: a fit build has none, and walk leaves Finder files out', () => {
  const s = site(({ put }) => put('data/.DS_Store', 'x'));
  try {
    const files = [...walk(s.dist)];
    assert.deepEqual(distProblems(s.dist, files), []);
    assert.equal(files.some((f) => f.path.endsWith('.DS_Store')), false);
  } finally { s.done(); }
});

for (const [name, change, pattern, extra] of [
  ['no home page', ({ dist }) => rmSync(path.join(dist, 'index.html')), /has no index\.html/],
  ['no worker', ({ dist }) => rmSync(path.join(dist, 'sw.js')), /no sw\.js/],
  ['a worker with no data-root line', ({ put }) => put('sw.js', '// drifted\n'), /no DATA_ROOT line/],
  ['data on another host', ({ put }) => put('sw.js', 'const DATA_ROOT = "https://data.example.org";\n'), /reads its data from https:\/\/data\.example\.org/],
  ['no data', ({ dist }) => rmSync(path.join(dist, 'data'), { recursive: true }), /no data\/ in the build/],
  ['data left out of the upload', ({ put }) => put('.assetsignore', 'data/\n'), /leaves data\/ out/],
  ['data left out of the upload, rooted', ({ put }) => put('.assetsignore', '/data\n'), /leaves data\/ out/],
  ['no feedback marker', ({ dist }) => rmSync(path.join(dist, 'feedback-endpoint.json')), /no feedback-endpoint\.json/],
]) {
  test(`distProblems: ${name}`, () => {
    const s = site(change);
    try { assert.match(distProblems(s.dist, [...walk(s.dist)]).join('\n'), pattern); } finally { s.done(); }
  });
}

test('distProblems: over the Worker\'s file count, or a file over 25 MiB', () => {
  const s = site();
  try {
    const files = [...walk(s.dist)];
    const many = [...files, ...Array.from({ length: MAX_FILES }, (_, i) => ({ path: `x/${i}.json`, bytes: 1 }))];
    assert.match(distProblems(s.dist, many).join('\n'), new RegExp(`${many.length} files, over the ${MAX_FILES}`));
    const big = [...files, { path: 'data/huge.json', bytes: 25 * 1024 * 1024 + 1 }];
    assert.match(distProblems(s.dist, big).join('\n'), /1 file\(s\) over 25 MiB, which a Worker will not serve, first: data\/huge\.json/);
    assert.deepEqual(distProblems(s.dist, [...files, { path: 'data/max.json', bytes: 25 * 1024 * 1024 }]), []);
  } finally { s.done(); }
});

// The fakes. `calls` records every program run; `fails` names the ones that
// throw (by a word of their arguments).
function fakes({ fails = [], sitemap = '<loc>a</loc>', gates = 'ok', head = 'c'.repeat(40), status = '', tags = '' } = {}) {
  const calls = [];
  const exec = (command, args, opts = {}) => {
    const line = [command, ...args].join(' ');
    calls.push({ line, cwd: opts.cwd, env: opts.env });
    if (fails.some((word) => line.includes(word))) throw new Error(`${line} failed with status 1`);
    if (line === 'git rev-parse HEAD') return `${head}\n`;
    if (line.startsWith('git status')) return status;
    if (line.startsWith('git ls-remote')) return tags;
    if (line.startsWith('git tag --list')) return '';
    return '';
  };
  const gateRuns = [];
  const fakeGates = (served, ctx) => {
    gateRuns.push({ ctx, read: [...served(() => true)].map((f) => f.path) });
    if (gates === 'none') return [];
    return [['preflight', { ok: gates === 'ok', problems: gates === 'ok' ? [] : ['exit 1', 'medea: book-01.json: no text'] }], ['JSON', { ok: true, problems: [] }]];
  };
  const lines = [];
  const deps = (root) => ({ root, exec, getText: async () => sitemap, gates: fakeGates, log: (l) => lines.push(l), today: () => '2026-11-23' });
  return { calls, gateRuns, lines, deps, ran: (word) => calls.filter((c) => c.line.includes(word)) };
}

test('deploy: by default a rehearsal: every gate, wrangler deploy --dry-run, no deploy, no tag', async () => {
  const s = site(), f = fakes();
  try {
    const r = await deploy(parseArgs([]), f.deps(s.root));
    assert.deepEqual(r, { deployed: false });
    assert.equal(f.ran('check-links.mjs').length, 1);
    assert.equal(f.gateRuns.length, 1);
    assert.deepEqual(f.gateRuns[0].read, ['data/medea/manifest.json']);   // the data, and only the data
    assert.equal(f.gateRuns[0].ctx.dataDir, path.join(s.dist, 'data'));
    const wrangler = f.ran('wrangler@4');
    assert.deepEqual(wrangler.map((c) => c.line), ['npx -y wrangler@4 deploy --dry-run']);
    assert.equal(wrangler[0].cwd, path.join(s.root, 'app'));
    assert.equal(wrangler[0].env.CLOUDFLARE_ACCOUNT_ID, '6ff75c6d6c06d1092df2c7efd42077ba');
    assert.equal(f.ran('git tag').length + f.ran('git push').length + f.ran('ls-remote').length, 0);
    assert.equal(r.deployed, false);
    // --dry-run says the same
    const g = fakes();
    assert.deepEqual(await deploy(parseArgs(['--dry-run']), g.deps(s.root)), { deployed: false });
    assert.equal(g.ran('wrangler@4 deploy --dry-run').length, 1);
  } finally { s.done(); }
});

test('deploy: --deploy deploys, then tags the commit and pushes the tag', async () => {
  const s = site(), f = fakes();
  try {
    const r = await deploy(parseArgs(['--deploy']), f.deps(s.root));
    assert.deepEqual(r, { deployed: true, tag: 'deploy/2026-11-23' });
    const order = f.calls.map((c) => c.line).filter((l) => /wrangler|git tag (?!--list)|git push/.test(l));
    assert.deepEqual(order, ['npx -y wrangler@4 deploy', `git tag deploy/2026-11-23 ${'c'.repeat(40)}`, 'git push --quiet origin refs/tags/deploy/2026-11-23']);
    assert.equal(f.ran('--dry-run').length, 0);
  } finally { s.done(); }
});

test('deploy: --deploy --no-tag, and an unclean tree, deploy and do not tag', async () => {
  const s = site();
  try {
    const f = fakes();
    assert.deepEqual(await deploy(parseArgs(['--deploy', '--no-tag']), f.deps(s.root)), { deployed: true, skip: '--no-tag' });
    assert.equal(f.ran('git tag').length + f.ran('git push').length, 0);
    const g = fakes({ status: '?? app/src/pages/new.astro\n' });
    const r = await deploy(parseArgs(['--deploy']), g.deps(s.root));
    assert.equal(r.deployed, true);
    assert.match(r.skip, /app\/src\/pages\/new\.astro/);
    assert.equal(g.ran('git tag').length, 0);
    assert.ok(g.lines.some((l) => /NOT TAGGED/.test(l)));
  } finally { s.done(); }
});

test('deploy: a deploy that fails is not tagged', async () => {
  const s = site(), f = fakes({ fails: ['wrangler@4 deploy'] });
  try {
    await assert.rejects(deploy(parseArgs(['--deploy']), f.deps(s.root)), /wrangler@4 deploy failed/);
    assert.equal(f.ran('git tag').length + f.ran('git push').length + f.ran('ls-remote').length, 0);
  } finally { s.done(); }
});

test('deploy: a tag that fails after a deploy that succeeded reads as a deploy, with the commands to tag by hand', async () => {
  const s = site(), f = fakes({ fails: ['git push'] });
  try {
    const r = await deploy(parseArgs(['--deploy']), f.deps(s.root));
    assert.equal(r.deployed, true);
    assert.match(r.skip, /git push --quiet origin refs\/tags\/deploy\/2026-11-23 failed/);
    assert.ok(f.lines.some((l) => l.includes('git tag deploy/<date>')), f.lines.join('\n'));
    assert.ok(f.ran('git tag --delete deploy/2026-11-23').length, 'the tag that did not reach origin is removed here');
  } finally { s.done(); }
});

for (const [name, setup, pattern, args = []] of [
  ['a build unfit for the Worker', { change: ({ dist }) => rmSync(path.join(dist, 'feedback-endpoint.json')) }, /no feedback-endpoint\.json/],
  ['no build at all', { change: ({ dist }) => rmSync(dist, { recursive: true }) }, /has no index\.html; build first/],
  ['a live sitemap with no pages', { fakes: { sitemap: '<urlset/>' } }, /lists no pages/],
  ['a build with too few pages', { fakes: { sitemap: '<loc>a</loc>'.repeat(10) } }, /below the 90% floor/],
  ['a broken link', { fakes: { fails: ['check-links.mjs'] } }, /link check did not pass/],
  ['a data gate that fails', { fakes: { gates: 'fail' } }, /preflight did not pass: exit 1; medea: book-01\.json: no text/],
  ['no data gate at all', { fakes: { gates: 'none' } }, /no data gate ran/],
  ['a rehearsal wrangler refuses', { fakes: { fails: ['--dry-run'] }, rehearsalOnly: true }, /the rehearsal did not pass/],
]) {
  test(`deploy: refused, nothing deployed, nothing tagged: ${name}`, async () => {
    const s = site(setup.change), f = fakes(setup.fakes);
    try {
      for (const flags of setup.rehearsalOnly ? [args] : [args, [...args, '--deploy']]) {
        await assert.rejects(deploy(parseArgs(flags), f.deps(s.root)), (e) => e instanceof Refusal && pattern.test(e.message));
      }
      assert.equal(f.calls.filter((c) => c.line === 'npx -y wrangler@4 deploy').length, 0);
      assert.equal(f.ran('git tag').length + f.ran('git push').length, 0);
    } finally { s.done(); }
  });
}

test('deploy: --skip-link-check skips only the link check', async () => {
  const s = site(), f = fakes({ fails: ['check-links.mjs'] });
  try {
    assert.deepEqual(await deploy(parseArgs(['--skip-link-check']), f.deps(s.root)), { deployed: false });
    assert.equal(f.ran('check-links.mjs').length, 0);
    assert.equal(f.gateRuns.length, 1);
  } finally { s.done(); }
});

const HEAD = 'a'.repeat(40), OTHER = 'b'.repeat(40);
const plan = (over = {}) => tagPlan({ unclean: [], noTag: false, head: HEAD, tags: new Map(), date: '2026-11-21', ...over });

test('tagPlan: a deploy from a tree with changed or untracked files is not tagged, and the files are named', () => {
  const p = plan({ unclean: ['app/src/pages/new.astro'] });
  assert.equal(p.tag, undefined);
  assert.match(p.skip, /app\/src\/pages\/new\.astro/);
  assert.match(plan({ unclean: ['a', 'b', 'c', 'd', 'e'] }).skip, /a, b, c, and 2 more/);
});

test('tagPlan: --no-tag is not tagged, and says so', () => {
  const p = plan({ noTag: true });
  assert.equal(p.tag, undefined);
  assert.match(p.skip, /--no-tag/);
  assert.equal(parseArgs(['--no-tag']).noTag, true);
  assert.equal(parseArgs([]).noTag, false);
});

test('tagPlan: a commit that already has a deploy tag on origin gets no second one', () => {
  const p = plan({ tags: new Map([['deploy/2026-11-20', HEAD]]) });
  assert.equal(p.tag, undefined);
  assert.match(p.skip, /deploy\/2026-11-20/);
  // A tag of another kind at this commit is no deploy tag.
  assert.deepEqual(plan({ tags: new Map([['v1', HEAD]]) }), { tag: 'deploy/2026-11-21' });
});

test('tagPlan: a date that is not a date is refused', () => {
  for (const date of ['', '21 Nov', '2026-11-21 ', '2026-11-21\nx']) {
    assert.throws(() => plan({ date }), /date/, JSON.stringify(date));
  }
});

test('tagPlan: the first deploy of a day is deploy/<date>; later ones go one past the highest number, here or on origin', () => {
  const on = (tags, local) => plan({ tags: new Map(tags), local });
  assert.deepEqual(on([]), { tag: 'deploy/2026-11-21' });
  assert.deepEqual(on([['deploy/2026-11-20', OTHER]]), { tag: 'deploy/2026-11-21' });
  assert.deepEqual(on([['deploy/2026-11-21', OTHER]]), { tag: 'deploy/2026-11-21.2' });
  assert.deepEqual(on([['deploy/2026-11-21', OTHER], ['deploy/2026-11-21.2', OTHER]]), { tag: 'deploy/2026-11-21.3' });
  // A gap is not filled: .2 is gone, .3 exists, the next is .4.
  assert.deepEqual(on([['deploy/2026-11-21', OTHER], ['deploy/2026-11-21.3', OTHER]]), { tag: 'deploy/2026-11-21.4' });
  // A name this checkout holds and origin does not is not given out again.
  assert.deepEqual(on([['deploy/2026-11-21', OTHER]], ['deploy/2026-11-21.2']), { tag: 'deploy/2026-11-21.3' });
  assert.deepEqual(on([], ['deploy/2026-11-21']), { tag: 'deploy/2026-11-21.2' });
});

// tagDeploy against a real checkout with a bare origin beside it.
function checkout() {
  const dir = mkdtempSync(path.join(tmpdir(), 'deploy-tag-'));
  const env = { ...process.env, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_SYSTEM: '/dev/null' };
  const git = (cwd, ...args) => execFileSync('git', args, { cwd, encoding: 'utf8', env }).trim();
  const origin = path.join(dir, 'origin.git'), work = path.join(dir, 'work');
  git(dir, 'init', '-q', '--bare', origin);
  git(dir, 'init', '-q', '-b', 'main', work);
  git(work, 'config', 'user.email', 't@example.invalid');
  git(work, 'config', 'user.name', 't');
  git(work, 'remote', 'add', 'origin', origin);
  const commit = () => { git(work, 'commit', '-q', '--allow-empty', '-m', 'c'); git(work, 'push', '-q', 'origin', 'main'); return git(work, 'rev-parse', 'HEAD'); };
  const deploy = (head, over = {}) => tagDeploy({ cwd: work, head, unclean: [], noTag: false, date: '2026-11-21', ...over });
  return { git, origin, work, commit, deploy, done: () => rmSync(dir, { recursive: true, force: true }) };
}

test('tagDeploy: an origin that cannot be read throws, and no tag is left here', () => {
  const c = checkout();
  try {
    const head = c.commit();
    c.git(c.work, 'remote', 'set-url', 'origin', path.join(c.work, 'nowhere.git'));
    assert.throws(() => c.deploy(head), /git ls-remote/);
    assert.equal(c.git(c.work, 'tag', '--list'), '');
  } finally { c.done(); }
});

test('tagDeploy: an origin that refuses the tag throws, and the tag is not left here to block the next try', () => {
  const c = checkout();
  try {
    const head = c.commit();
    const hook = path.join(c.origin, 'hooks', 'pre-receive');
    writeFileSync(hook, '#!/bin/sh\nexit 1\n', { mode: 0o755 });
    assert.throws(() => c.deploy(head), /git push/);
    assert.equal(c.git(c.work, 'tag', '--list'), '');
    rmSync(hook);
    assert.deepEqual(c.deploy(head), { tag: 'deploy/2026-11-21' });
    assert.equal(c.git(c.origin, 'rev-parse', 'refs/tags/deploy/2026-11-21'), head);
  } finally { c.done(); }
});

test('tagDeploy: an unclean tree or --no-tag tags nothing, here or on origin, and asks origin nothing', () => {
  const c = checkout();
  try {
    const head = c.commit();
    c.git(c.work, 'remote', 'set-url', 'origin', path.join(c.work, 'nowhere.git'));   // a read of origin would throw
    assert.match(c.deploy(head, { unclean: ['x.astro'] }).skip, /x\.astro/);
    assert.match(c.deploy(head, { noTag: true }).skip, /--no-tag/);
    assert.equal(c.git(c.work, 'tag', '--list'), '');
    assert.equal(c.git(c.origin, 'tag', '--list'), '');
  } finally { c.done(); }
});

test('tagDeploy: the tag lands on origin at the deployed commit; a name used on origin alone is not used again', () => {
  const c = checkout();
  try {
    const first = c.commit();
    assert.deepEqual(c.deploy(first), { tag: 'deploy/2026-11-21' });
    assert.equal(c.git(c.origin, 'rev-parse', 'refs/tags/deploy/2026-11-21'), first);
    // The same commit deployed again: no second tag.
    assert.match(c.deploy(first).skip, /already tagged deploy\/2026-11-21/);
    // Another machine tagged .2 on origin, annotated; this checkout has never seen it.
    const second = c.commit();
    c.git(c.origin, '-c', 'user.email=t@example.invalid', '-c', 'user.name=t', 'tag', '-a', 'deploy/2026-11-21.2', '-m', 'elsewhere', second);
    assert.match(c.deploy(second).skip, /already tagged deploy\/2026-11-21\.2/);   // the annotated tag's commit, not its own object
    const third = c.commit();
    assert.deepEqual(c.deploy(third), { tag: 'deploy/2026-11-21.3' });
    assert.equal(c.git(c.origin, 'rev-parse', 'refs/tags/deploy/2026-11-21.3'), third);
    assert.equal(c.git(c.work, 'tag', '--list', 'deploy/2026-11-21.2'), '');   // reading origin wrote nothing here
  } finally { c.done(); }
});

test('tagDeploy: a local tag of another name that differs from origin\'s does not stand in the way', () => {
  const c = checkout();
  try {
    const first = c.commit();
    c.git(c.origin, 'tag', 'v1', first);
    const second = c.commit();
    c.git(c.work, 'tag', 'v1', second);
    assert.deepEqual(c.deploy(second), { tag: 'deploy/2026-11-21' });
  } finally { c.done(); }
});

test('tagCommits: a plain tag gives its commit, an annotated one the commit it names', () => {
  const tags = tagCommits(`${'c'.repeat(40)}\trefs/tags/deploy/a\n${'d'.repeat(40)}\trefs/tags/deploy/b\n${'e'.repeat(40)}\trefs/tags/deploy/b^{}\n`);
  assert.deepEqual([...tags], [['deploy/a', 'c'.repeat(40)], ['deploy/b', 'e'.repeat(40)]]);
  assert.equal(tagCommits('').size, 0);
});

test('uncleanFiles: an untracked page counts even where git is set to hide untracked files; ignored build output does not', () => {
  // Codex's review of the Plato port.
  const c = checkout();
  try {
    c.commit();
    writeFileSync(path.join(c.work, '.gitignore'), 'build/\n');
    c.git(c.work, 'add', '.gitignore');
    c.git(c.work, 'commit', '-q', '-m', 'ignore');
    assert.deepEqual(uncleanFiles(c.work), []);
    execFileSync('mkdir', ['-p', path.join(c.work, 'build'), path.join(c.work, 'pages')]);
    writeFileSync(path.join(c.work, 'build', 'out.json'), '{}');
    assert.deepEqual(uncleanFiles(c.work), [], 'git-ignored build output');
    c.git(c.work, 'config', 'status.showUntrackedFiles', 'no');
    writeFileSync(path.join(c.work, 'pages', 'new.astro'), 'x');
    assert.deepEqual(uncleanFiles(c.work), ['pages/new.astro']);
    writeFileSync(path.join(c.work, '.gitignore'), 'build/\nmore/\n');
    assert.deepEqual(uncleanFiles(c.work).sort(), ['.gitignore', 'pages/new.astro']);
  } finally { c.done(); }
});
