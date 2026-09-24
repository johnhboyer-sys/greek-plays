import { readFile, readdir, access } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { realpathSync } from 'node:fs';
import { repo, parseArgs, writeReport, writeTsv } from './lib.mjs';
import { loadYaml } from '../lib/load-yaml.mjs';

const greek = /[\u0370-\u03ff\u1f00-\u1fff]/gu;
const odd = /[\u0080-\u009f\ufffd\u0400-\u052f\u2500-\u259f\u25a0-\u25ff]/gu;
const patterns = {
  'glued-digit': /(?:[\p{L}][0-9]{1,4}|[\p{L}][,;:][0-9]{1,4})\b/gu,
  asterisks: /\*\*\*|\*\s+\*\s+\*/gu,
  entity: /&(?:[a-zA-Z]+|#\d+);/gu,
  tag: /[<>][A-Za-z]/gu,
  'c1-or-odd-char': odd,
};
const fail = new Set(['greek-in-english','page-number','glued-digit','entity','c1-or-odd-char','inline-cue']);
const context = (value, index, length) => value.slice(Math.max(0,index-65),Math.min(value.length,index+length+65)).replace(/\s+/g,' ').slice(0,160);
function leafStrings(value, path) {
  if (typeof value === 'string') return [{ value, path }];
  if (Array.isArray(value)) return value.flatMap((v,i)=>leafStrings(v,`${path}[${i}]`));
  if (value && typeof value === 'object') return Object.entries(value).flatMap(([k,v])=>leafStrings(v,`${path}.${k}`));
  return [];
}
function roster(manifest, chunk) {
  const names = new Set();
  const add = value => { if (typeof value === 'string' && value.trim()) names.add(value.trim().replace(/\.$/, '').toUpperCase()); };
  for (const t of chunk.turns ?? []) { add(t.speaker); add(t.display); }
  for (const value of Object.values(manifest.speakers ?? {})) {
    if (Array.isArray(value)) continue;
    if (value && typeof value === 'object') for (const [name, display] of Object.entries(value)) { add(name); add(display); }
  }
  return names;
}
function lacunaDeclared(manifest) {
  const items = [manifest.citation?.lacunae,manifest.english?.lacunae].filter(Boolean).flat();
  return items.some(item=>typeof item === 'string' ? /\*/.test(item) : /\*/.test(JSON.stringify(item)));
}
function slotInfo(manifest, key) {
  const registry = manifest.registry?.translations ?? [];
  const source = key === 'english' ? manifest.english?.primary : key === 'ross' ? manifest.english?.secondary : key === 'third' ? manifest.english?.third : manifest.english?.overlays?.find(x=>x.id === key.slice(9));
  const id = key.startsWith('overlays.') ? key.slice(9) : source?.id;
  const entry = registry.find(x=>x.id === id);
  return { id:id ?? key, form:entry?.form ?? source?.form ?? 'prose', name:entry?.name ?? source?.name ?? '', short:entry?.short ?? source?.short ?? '' };
}
function chunksOf(segment) {
  const slots = ['english','ross','third'].flatMap(key=>segment[key] == null ? [] : [[key,segment[key]]]);
  for (const [id,value] of Object.entries(segment.overlays ?? {})) slots.push([`overlays.${id}`,value]);
  return slots.flatMap(([key,value])=>(Array.isArray(value)?value:[value]).map((chunk,i)=>({key,chunk,index:Array.isArray(value)?`[${i}]`:''})));
}
function scanString(rows, meta, value, path, role, names, title, surname, hasLacuna) {
  if (typeof value !== 'string' || !value) return;
  const add = (category, match, index, severity=fail.has(category)?'fail':'info') => rows.push({category,severity,play:meta.play,slot_id:meta.id,json_path:path,match,context:context(value,index,match.length)});
  if (role === 'text' || role === 'footnote') for (const m of value.matchAll(greek)) add(role === 'footnote' ? 'greek-in-footnote' : 'greek-in-english',m[0],m.index,role === 'footnote' ? 'info' : 'fail');
  if (role !== 'footnote') {
    for (const m of value.matchAll(/(?:^|\n)([ \t]*\d{1,4}[ \t]*)(?=\n|$)|[ \t]{2,}(\d{1,4})[ \t]*(?=\n|$)/gm)) {
      const digits = m[1]?.trim() ?? m[2];
      const offset = m.index + m[0].indexOf(digits);
      if (!/\[\^[^\]]*$/.test(value.slice(Math.max(0,offset-60),offset))) add('page-number',digits,offset);
    }
    for (const [category,regex] of Object.entries(patterns)) for (const m of value.matchAll(regex)) {
      if (category === 'asterisks' && hasLacuna) continue;
      add(category,m[0],m.index,category === 'tag' && /johnston/i.test(meta.name) ? 'info' : undefined);
    }
    if ((value.match(/_/g) ?? []).length % 2) add('underscore','_',value.lastIndexOf('_'));
    const lines = value.split('\n'); let pos = 0;
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed && [title,surname,'ARGUMENT'].some(x=>x && trimmed.toUpperCase()===x.toUpperCase())) add('running-head',trimmed,pos+line.indexOf(trimmed));
      pos += line.length+1;
    }
    if (role === 'text') {
      for (const m of value.matchAll(/([.!?][ \t]+)([A-Z][A-Z]{2,}|[A-Z][a-z]{1,4})\.\s/g)) {
        const start = m.index + m[1].length;
        if (start > 0 && names.has(m[2].toUpperCase())) add('inline-cue',m[2]+'.',start);
      }
    }
  }
}

// Exported for tests; percentile and repeated-head checks run over all books in run().
export function censusBook(play, book, manifest, options={}) {
  const rows=[], cells=[];
  const title = manifest.work?.title ?? play;
  const lacuna = lacunaDeclared(manifest);
  for (const [si,segment] of book.segments.entries()) for (const {key,chunk,index} of chunksOf(segment)) {
    if (!chunk || typeof chunk !== 'object') continue;
    const slot = slotInfo(manifest,key);
    const meta = {play,id:slot.id,name:slot.name};
    const path = `$.segments[${si}].${key}${index}`;
    const names = roster(manifest,chunk);
    const surname = slot.short?.split(/\s+/).at(-1) ?? '';
    if (typeof chunk.text === 'string') {
      scanString(rows,meta,chunk.text,`${path}.text`,'text',names,title,surname,lacuna);
      cells.push({meta,path:`${path}.text`,text:chunk.text,form:slot.form});
      const turns = chunk.turns ?? [];
      for (let i=1;i<turns.length;i++) {
        const prev=chunk.text.slice(turns[i-1].offset,turns[i].offset).trimEnd();
        const next=chunk.text.slice(turns[i].offset,turns[i+1]?.offset ?? chunk.text.length).trimStart();
        if (/[.!?]["'”’)]?$/.test(prev) && /^\p{Ll}/u.test(next)) {
          const offset=chunk.text.indexOf(next,turns[i].offset);
          rows.push({category:'lowercase-start',severity:'info',play,slot_id:slot.id,json_path:`${path}.text`,match:next.match(/^\p{L}+/u)?.[0] ?? next[0],context:context(chunk.text,offset,1)});
        }
      }
    }
    for (const field of ['notes','directions','directionsBefore']) for (const leaf of leafStrings(chunk[field],`${path}.${field}`)) scanString(rows,meta,leaf.value,leaf.path,field,names,title,surname,lacuna);
    for (const [ti,turn] of (chunk.turns ?? []).entries()) for (const field of ['directions','directionsBefore']) for (const leaf of leafStrings(turn[field],`${path}.turns[${ti}].${field}`)) scanString(rows,meta,leaf.value,leaf.path,field,names,title,surname,lacuna);
  }
  if (options.footnotes) for (const [key,value] of Object.entries(options.footnotes)) for (const leaf of leafStrings(value,`$.footnotes[${JSON.stringify(key)}]`)) scanString(rows,{play,id:'footnotes',name:''},leaf.value,leaf.path,'footnote',new Set(),title,'',false);
  return {rows,cells};
}
export function addCorpusFindings(rows,cells) {
  for (const form of ['verse','prose']) {
    const lengths=cells.filter(c=>c.form===form).map(c=>c.text.length).sort((a,b)=>a-b);
    if (!lengths.length) continue;
    const cutoff=lengths[Math.ceil(.995*lengths.length)-1];
    for (const cell of cells) if (cell.form===form && cell.text.length>cutoff) rows.push({category:'long-cell',severity:'info',play:cell.meta.play,slot_id:cell.meta.id,json_path:cell.path,match:String(cell.text.length),context:context(cell.text,0,60)});
  }
  // Count all-caps lines within each play and slot, then mark repeat lines.
  const caps=new Map();
  for (const cell of cells) for (const line of cell.text.split('\n')) {
    const s=line.trim(); if (!/^[A-Z][A-Z\s'-]+$/.test(s)) continue;
    const key=`${cell.meta.play}\0${cell.meta.id}\0${s}`; caps.set(key,(caps.get(key)??0)+1);
  }
  const existingHeads=new Set(rows.filter(r=>r.category==='running-head').map(r=>`${r.json_path}\0${r.match}`));
  for (const cell of cells) {
    let pos=0;
    for (const line of cell.text.split('\n')) {
      const s=line.trim(), key=`${cell.meta.play}\0${cell.meta.id}\0${s}`;
      if (s && (caps.get(key)??0)>=3 && !existingHeads.has(`${cell.path}\0${s}`)) rows.push({category:'running-head',severity:'info',play:cell.meta.play,slot_id:cell.meta.id,json_path:cell.path,match:s,context:context(cell.text,pos+line.indexOf(s),s.length)});
      pos+=line.length+1;
    }
  }
  return rows;
}

export async function run(args=parseArgs()) {
  const yaml=await loadYaml(), data=join(args.dist,'data'), rows=[], cells=[];
  const candidates=(await readdir(data,{withFileTypes:true})).filter(e=>e.isDirectory()).map(e=>e.name).sort();
  const plays=[]; for (const name of candidates) { try { await access(join(data,name,'book-01.json')); plays.push(name); } catch(e) { if(e.code!=='ENOENT') throw e; } }
  for (const play of plays) {
    const manifest=yaml.load(await readFile(join(repo,'manifests',`${play}.yaml`),'utf8'));
    const book=JSON.parse(await readFile(join(data,play,'book-01.json'),'utf8'));
    let footnotes={}; try { footnotes=JSON.parse(await readFile(join(data,play,'footnotes.json'),'utf8')); } catch(e) { if(e.code!=='ENOENT') throw e; }
    const result=censusBook(play,book,manifest,{footnotes}); rows.push(...result.rows); cells.push(...result.cells);
  }
  addCorpusFindings(rows,cells);
  rows.sort((a,b)=>a.play.localeCompare(b.play)||a.slot_id.localeCompare(b.slot_id)||a.json_path.localeCompare(b.json_path)||a.category.localeCompare(b.category));
  await writeReport('s9-census',rows,args.out);
  const counts=new Map(); for (const row of rows) { const key=`${row.category}\0${row.slot_id}`; counts.set(key,(counts.get(key)??0)+1); }
  await writeTsv(join(args.out,'s9-census-summary.tsv'),[...counts].map(([key,count])=>({category:key.split('\0')[0],translation_id:key.split('\0')[1],count})).sort((a,b)=>a.category.localeCompare(b.category)||a.translation_id.localeCompare(b.translation_id)),['category','translation_id','count']);
  for (const [category,count] of Object.entries(Object.groupBy(rows,r=>r.category)).sort()) console.log(`s9 ${category}: ${count.length}`);
  return rows;
}
if (process.argv[1] && realpathSync(process.argv[1])===fileURLToPath(import.meta.url)) await run();
