import test from 'node:test';
import assert from 'node:assert/strict';
import { odeIds, classify } from '../sweeps/s7a-analysis-coverage.mjs';
import { censusBook, addCorpusFindings } from '../sweeps/s9-census.mjs';

const manifest={work:{title:'Test Play'},english:{primary:{id:'tester',name:'Jane Tester',form:'verse'}},registry:{translations:[{id:'tester',form:'verse',short:'Tester'}]},speakers:{english:{HERO:'Hero',FOE:'Foe'}}};
function scan(text, extras={}) { return censusBook('test-play',{segments:[{english:{text,...extras}}]},manifest).rows; }

test('ode rule follows inherited speakers, chorus sigla and six-line threshold',()=>{
  const seg=(id,n,speakers)=>({id,greek:Array.from({length:n},()=>({tokens:[]})),speakers});
  const ids=odeIds([seg('a',7,[{label:'Χο.',display:'Chorus'}]),seg('b',8,[]),seg('c',7,[{label:'Βα.',display:'Queen'}]),seg('d',7,[{label:'Βα.',display:'Frogs'}]),seg('e',6,[]),seg('f',7,[{label:'ΦΥΛΑΞ',display:'Watchman'}])]);
  assert.deepEqual([...ids],['a','b','d']);
});
test('analysis classes use exact LSJ keys',()=>{
  const a={none:[],bare:[{lemma:'x'}],lost:[{lsj:['x']}],good:[{lsj:['x','head#A']}]};
  const h={'head#A':{head:'Head',hom:'A'}};
  assert.deepEqual(['absent','none','bare','lost','good'].map(k=>classify(k,a,h)),['no-analysis','no-analysis','no-lsj','lsj-unknown','ok']);
});
test('each local S9 finder and a clean string',()=>{
  const cases=[
    ['greek-in-english','A Greek α word.'],
    ['page-number','Text\n123\nNext'],
    ['glued-digit','Athene2 spoke.'],
    ['asterisks','A *** B'],
    ['running-head','Test Play\nA line.'],
    ['underscore','A _broken mark.'],
    ['entity','A &amp; B'],
    ['tag','A <NAME word> B'],
    ['inline-cue','A line. HERO. Another line.'],
    ['c1-or-odd-char','A � mark.'],
  ];
  for (const [category,value] of cases) assert.ok(scan(value).some(r=>r.category===category),category);
  assert.equal(scan('A clean sentence with 300 Spartans.').length,0);
});
test('turn starts, notes, directions, and Greek footnotes',()=>{
  const turns=[{offset:0,speaker:'Hero'},{offset:6,speaker:'Foe'}];
  const result=censusBook('test-play',{segments:[{english:{text:'Done. lower begins.',turns,notes:['A &amp; note'],directions:['A � cue']}}]},manifest,{footnotes:{'1.2':'The Greek α word.'}}).rows;
  for (const category of ['lowercase-start','entity','c1-or-odd-char','greek-in-footnote']) assert.ok(result.some(r=>r.category===category),category);
  assert.equal(result.find(r=>r.category==='greek-in-footnote').severity,'info');
});

test('corpus percentile finds a long cell',()=>{
  const rows=[], cells=[];
  for (let i=0;i<200;i++) cells.push({meta:{play:'test-play',id:'tester'},path:`$.segments[${i}].english.text`,text:i===199?'A'.repeat(100):'Short.',form:'verse'});
  addCorpusFindings(rows,cells);
  assert.equal(rows.filter(r=>r.category==='long-cell').length,1);
});
