import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, cp, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { repo } from '../sweeps/lib.mjs';
const node = process.execPath;
async function put(path, text) { await mkdir(dirname(path),{recursive:true}); await writeFile(path,text); }
async function fixture() { const base = await mkdtemp(join(tmpdir(),'sweeps-')); const dist=join(base,'dist'), out=join(base,'out'); await mkdir(dist); return {base,dist,out}; }
function run(script, f, cwd=repo) { return spawnSync(node,[join(cwd,'scripts/sweeps',script), '--dist',f.dist,'--out',f.out],{cwd,encoding:'utf8'}); }
async function rows(f,name) { return JSON.parse(await readFile(join(f.out,name+'.json'),'utf8')); }

test('s1 finds identity in visible text and data, with identifier hits informational',async()=>{
  const f=await fixture();
  await put(join(f.dist,'index.html'),'<h1>Latin theatre</h1>');
  await put(join(f.dist,'data/x/a.json'),JSON.stringify({id:'plato',line:'Socrates speaks'}));
  const result=run('s1-identity.mjs',f);
  assert.equal(result.status,1,result.stderr);
  const found=await rows(f,'s1-identity');
  assert.ok(found.some(r=>r.match==='Latin'&&r.severity==='fail'));
  assert.ok(found.some(r=>r.match==='plato'&&r.severity==='info'));
  assert.ok(found.some(r=>r.match==='Socrates'&&r.severity==='fail'));
});
test('s1 passes clean HTML and makes image inventory',async()=>{
  const f=await fixture(); await put(join(f.dist,'index.html'),'<h1>Greek drama</h1>'); await put(join(f.dist,'icon.svg'),'<svg><title>Mask</title></svg>');
  const result=run('s1-identity.mjs',f); assert.equal(result.status,0,result.stderr);
  assert.match(await readFile(join(f.out,'s1-images.tsv'),'utf8'),/icon\.svg/);
});
test('s2 finds placeholder text and structural faults',async()=>{
  const f=await fixture(); await put(join(f.dist,'index.html'),'<title></title><h1></h1><a href="/x"></a><p>TODO &amp;amp; {x}</p>');
  const result=run('s2-placeholders.mjs',f); assert.equal(result.status,1,result.stderr);
  const found=await rows(f,'s2-placeholders');
  for(const category of ['marker','leftover entity','brace','empty title','empty heading','empty link']) assert.ok(found.some(r=>r.category===category),category);
});
test('s2 passes clean page and treats repeated data words as info',async()=>{
  const f=await fixture(); await put(join(f.dist,'index.html'),'<title>Drama</title><h1>Drama</h1><input placeholder="Find a play">'); await put(join(f.dist,'data/x/a.json'),'{"text":"the the"}');
  const result=run('s2-placeholders.mjs',f); assert.equal(result.status,0,result.stderr);
  assert.ok((await rows(f,'s2-placeholders')).some(r=>r.category==='repeated word'));
});
async function s3Fixture(credit) {
  const f=await fixture(), root=join(f.base,'repo');
  await mkdir(join(root,'scripts/sweeps'),{recursive:true});
  for(const file of ['lib.mjs','s3-credits.mjs','allowlist.json']) await cp(join(repo,'scripts/sweeps',file),join(root,'scripts/sweeps',file));
  await mkdir(join(root,'scripts/lib'),{recursive:true}); await cp(join(repo,'scripts/lib/load-yaml.mjs'),join(root,'scripts/lib/load-yaml.mjs'));
  await mkdir(join(root,'app'),{recursive:true}); await symlink(join(repo,'app/node_modules'),join(root,'app/node_modules'));
  await put(join(root,'pipeline/drama_pipeline/public_domain_translations.yaml'),'translations:\n  - {id: rogers, translator: B. Rogers, year: 1900}\n');
  await put(join(root,'manifests/birds.yaml'),'english:\n  primary: {id: rogers, name: B. Rogers, short: Rogers}\nregistry:\n  id: birds\n  author: aristophanes\n  slug: birds\n  translations:\n    - {id: rogers}\n');
  await put(join(f.dist,'attribution/index.html'),`<h1>Credits</h1><p>${credit}</p>`);
  await put(join(f.dist,'aristophanes/birds/index.html'),'<h1>Birds</h1>');
  return {...f,root};
}
test('s3 fails a published Rogers slot absent from attribution',async()=>{
  const f=await s3Fixture('Other names'); const result=run('s3-credits.mjs',f,f.root); assert.equal(result.status,1,result.stderr);
  const found=await rows(f,'s3-credits'); assert.ok(found.some(r=>r.category.includes('missing attribution')&&r.short==='Rogers'));
  assert.equal(found[0].on_play_page,'n/a: page not static');
});
test('s3 passes a reconciled slot',async()=>{
  const f=await s3Fixture('B. Rogers'); const result=run('s3-credits.mjs',f,f.root); assert.equal(result.status,0,result.stderr);
  const found=await rows(f,'s3-credits'); assert.equal(found[0].severity,'info');
  assert.match(await readFile(join(f.out,'s3-credits-summary.tsv'),'utf8'),/Rogers/);
});
