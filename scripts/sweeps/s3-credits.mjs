import { readFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { realpathSync } from 'node:fs';
import { loadYaml } from '../lib/load-yaml.mjs';
import { repo, walkFiles, visibleText, parseArgs, writeReport, writeTsv, allowlist, allowed, finish } from './lib.mjs';
const word = short => new RegExp(`(?<![\\p{L}\\p{N}])${String(short).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}(?![\\p{L}\\p{N}])`, 'u');
async function textOrEmpty(path) { try { return await readFile(path,'utf8'); } catch(e) { if(e.code === 'ENOENT') return ''; throw e; } }
export async function run(args = parseArgs()) {
  const yaml = await loadYaml(), rows = [], summary = new Map();
  const allow = (await allowlist()).s3;
  const publicList = yaml.load(await readFile(join(repo,'pipeline/drama_pipeline/public_domain_translations.yaml'),'utf8')).translations ?? [];
  const publicById = new Map(publicList.map(item => [item.id,item]));
  const attribution = visibleText(await textOrEmpty(join(args.dist,'attribution/index.html')));
  for await (const path of walkFiles(join(repo,'manifests'),['.yaml'])) {
    if (path.endsWith('/authors.yaml') || path.endsWith('-public.yaml')) continue;
    const manifest = yaml.load(await readFile(path,'utf8'));
    if (!manifest?.registry || !manifest?.english) continue;
    const registry = manifest.registry, play = registry.id;
    const slots = [];
    for (const [key,value] of Object.entries(manifest.english)) {
      if (key === 'overlays' && Array.isArray(value)) value.forEach((slot,i) => { if(slot?.id) slots.push({slot:`overlays[${i}]`, ...slot}); });
      else if (value && !Array.isArray(value) && typeof value === 'object' && value.id) slots.push({slot:key,...value});
    }
    const registryIds = new Set((registry.translations ?? []).map(t => t.id));
    const pageFile = `${registry.author}/${registry.slug}/index.html`;
    const page = visibleText(await textOrEmpty(join(args.dist,pageFile)));
    const primary = slots.find(s => s.slot === 'primary');
    const pageStatic = !!(primary?.short && word(primary.short).test(page));
    const publishedIds = new Set(slots.filter(s => !s.private).map(s => s.id));
    for (const slot of slots) {
      const isPrivate = !!slot.private, inAllowlist = publicById.has(slot.id), inRegistry = registryIds.has(slot.id);
      const onAttribution = !!(slot.short && word(slot.short).test(attribution));
      const onPlayPage = pageStatic ? !!(slot.short && word(slot.short).test(page)) : 'n/a: page not static';
      const reasons = [];
      if (!isPrivate) {
        if (!inAllowlist) reasons.push('missing allowlist');
        if (!inRegistry) reasons.push('missing registry');
        if (!onAttribution) reasons.push('missing attribution');
      } else {
        if (inRegistry) reasons.push('private in registry');
        if (onPlayPage === true) reasons.push('private on play page');
      }
      const severity = !isPrivate && reasons.length ? 'fail' : 'info';
      const category = reasons.join(', ') || (isPrivate ? 'private slot' : 'reconciled slot');
      rows.push({ sweep:'s3', severity, category, file:pageFile, where:'text', match:slot.short ?? slot.id, context:`${play} ${slot.slot}: ${category}; page static checked using primary short ${primary?.short ?? '(none)'}`.slice(0,120), play, slot:slot.slot, id:slot.id, short:slot.short ?? '', private:isPrivate, in_allowlist:inAllowlist, in_registry:inRegistry, on_attribution:onAttribution, on_play_page:onPlayPage });
      const key = slot.short ?? slot.id, sum = summary.get(key) ?? { short:key, published:new Set(), private:new Set(), on_attribution:'no', allowlist_translator:'', allowlist_year:'' };
      (isPrivate ? sum.private : sum.published).add(play);
      if (onAttribution) sum.on_attribution = 'yes';
      const publicEntry = publicById.get(slot.id);
      if (publicEntry) { sum.allowlist_translator = publicEntry.translator ?? ''; sum.allowlist_year = publicEntry.year ?? ''; }
      summary.set(key,sum);
    }
    for (const id of registryIds) if (!publishedIds.has(id)) rows.push({ sweep:'s3', severity:'fail', category:'registry id without published slot', file:pageFile, where:'text', match:id, context:`${play}: registry translation ${id} has no published slot`, play, slot:'registry', id, short:'', private:false, in_allowlist:publicById.has(id), in_registry:true, on_attribution:false, on_play_page:pageStatic ? false : 'n/a: page not static' });
  }
  const kept = rows.filter(row => !allowed(row,allow));
  await writeReport('s3-credits',kept,args.out);
  await mkdir(args.out,{recursive:true});
  await writeTsv(join(args.out,'s3-credits-summary.tsv'), [...summary.values()].sort((a,b)=>a.short.localeCompare(b.short)).map(s => ({ short:s.short, plays_published:[...s.published].sort().join(', '), plays_private:[...s.private].sort().join(', '), on_attribution:s.on_attribution, allowlist_translator:s.allowlist_translator, allowlist_year:s.allowlist_year })), ['short','plays_published','plays_private','on_attribution','allowlist_translator','allowlist_year']);
  finish('s3',kept);
  return kept;
}
if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) await run();
