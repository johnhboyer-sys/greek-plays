import test from 'node:test';
import assert from 'node:assert/strict';
import { playOdeIds, probeWord, sampleStrata, stripDiacritics, parseArgs, wordSet } from '../sweeps/tier2-lib.mjs';

const seg = (id, length, speakers = []) => ({ id, greek: Array.from({ length }, () => ({})), speakers });
test('ode rule inherits speakers and excludes short and mixed speeches', () => {
  const chorus = { label: 'ΧΟ.', display: 'Women' }, actor = { label: 'ΒΑ.', display: 'King' };
  assert.deepEqual([...playOdeIds([seg('a',7,[chorus]),seg('b',8),seg('c',6),seg('d',9,[chorus,actor]),seg('e',9,[actor])])], ['a','b']);
  assert.deepEqual([...playOdeIds([seg('frogs',7,[{label:'ΒΑ.',display:'Frogs'}]),seg('queen',7,[{label:'ΒΑ.',display:'Atossa'}])])], ['frogs']);
});
test('probe chooses rare seven-letter word and first ref', () => {
  const lines = [{ text: 'ordinary rareword', ref:'12' },{ text:'rareword', ref:'13' }];
  const got = probeWord(lines,[wordSet([{text:'ordinary'}])]);
  assert.deepEqual(got,{word:'rareword',ref:'12'});
});
test('stratified sample is distinct and seeded', () => {
  const items = ['a','b'].flatMap(author => ['ode','dialogue'].flatMap(kind => Array.from({length:10},(_,i) => ({author,kind,key:`${author}-${kind}-${i}`}))));
  const a=sampleStrata(items,3,17), b=sampleStrata(items,3,17);
  assert.deepEqual(a,b); assert.equal(a.length,12); assert.equal(new Set(a.map(x=>x.key)).size,12);
  assert.notDeepEqual(a,sampleStrata(items,3,18));
});
test('diacritics strip and NFC', () => assert.equal(stripDiacritics('ἄνθρωπος'), 'ανθρωπος'));
test('arguments parse and reject bad values', () => {
  const o=parseArgs(['--match','ag','--limit','2','--seed','9','--out','/tmp/tier2'],{seed:true});
  assert.equal(o.match,'ag'); assert.equal(o.limit,2); assert.equal(o.seed,9); assert.equal(o.out,'/tmp/tier2');
  assert.throws(()=>parseArgs(['--seed','9'])); assert.throws(()=>parseArgs(['--limit','0']));
});
