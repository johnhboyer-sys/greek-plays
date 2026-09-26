import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tokenize, stem, stripCue, cosine, flagRule, checkPlay, groupFlags } from '../sweeps/s16-content-check.mjs';

test('tokenize drops common words, stems words, and weights names inside sentences', () => {
  assert.equal(stem('singing'), 'sing');
  assert.equal(stem('buses'), 'buse');
  assert.equal(stem('cats'), 'cats');
  assert.deepEqual(tokenize('The queen spoke. Then Orestes greeted Argos.'), [
    { token: 'queen', weight: 1 }, { token: 'spoke', weight: 1 },
    { token: 'orest', weight: 2 }, { token: 'greet', weight: 1 }, { token: 'argo', weight: 2 },
  ]);
});
test('strips an all-caps cue at each line start', () => {
  assert.equal(stripCue('HERALD. Speak now.\nTHE OLD MAN. Go home.'), 'Speak now.\nGo home.');
  assert.equal(stripCue('The Herald. Speak now.'), 'The Herald. Speak now.');
});
test('cosine gives one for identical vectors and zero for disjoint vectors', () => {
  const a = new Map([['ship', 2], ['sea', 1]]);
  assert.equal(cosine(a, a), 1);
  assert.equal(cosine(a, new Map([['land', 3]])), 0);
});
test('flag rule needs two peers with matching direction, or one in a two-column play', () => {
  const match = (offset, margin) => ({ offset, margin, other: 'ross', j: 0 });
  assert.equal(flagRule([match(-2, .4), match(-1, .35)], 2)?.offset, -2);
  assert.equal(flagRule([match(-2, .4), match(1, .35)], 2), null);
  assert.equal(flagRule([match(-2, .1), match(-1, .35)], 2), null);
  assert.equal(flagRule([match(1, .35)], 1)?.offset, 1);
});
const flag = (index, offset = 1, margin = .2, column = 'english') =>
  ({ index, offset, margin, column, ref: String(index) });
test('groups flags across two unflagged rows but splits across three', () => {
  const stretches = groupFlags('sample', ['english'], [flag(1), flag(4), flag(7), flag(11), flag(14), flag(17)]);
  assert.deepEqual(stretches.map(s => [s.firstRef, s.lastRef, s.count]), [['1', '7', 3], ['11', '17', 3]]);
});
test('splits runs on sign change and an offset jump over one', () => {
  const stretches = groupFlags('sample', ['english'], [
    flag(1, 1), flag(2, 1), flag(3, 1),
    flag(4, -1), flag(5, -2), flag(6, -2),
    flag(7, -4), flag(8, -4), flag(9, -4),
  ]);
  assert.deepEqual(stretches.map(s => s.offsets), ['1,1,1', '-1,-2,-2', '-4,-4,-4']);
});
test('keeps runs of three or a strong single flag, drops weaker short runs, and separates columns', () => {
  const stretches = groupFlags('sample', ['english', 'ross'], [
    flag(1), flag(2), flag(3), flag(8, 1, .5), flag(13, 1, .49),
    flag(1, -1, .6, 'ross'),
  ]);
  assert.deepEqual(stretches.map(s => [s.column, s.firstRef, s.count, s.maxMargin]),
    [['english', '1', 3, .2], ['english', '8', 1, .5], ['ross', '1', 1, .6]]);
  assert.ok(Math.abs(stretches[0].meanMargin - .2) < 1e-12);
});
test('finds a shifted column in a three-column play', () => {
  const rows = [
    'The sailors lift the heavy anchor beside the rocky shore.',
    'The queen hides the silver crown inside the palace chamber.',
    'The herald brings a blood stained sword to the city gate.',
    'The shepherd drives the frightened sheep across the mountain.',
    'The priest lights the sacred fire before the temple door.',
  ];
  const segments = rows.map((text, i) => ({ id: `1:${i}`, column: String(i),
    english: { text: rows[Math.min(i + 1, rows.length - 1)] },
    ross: [{ text }], third: [{ text }] }));
  const result = checkPlay('sample', segments);
  assert.ok(result.flags.some(f => f.column === 'english' && f.index === 1 && f.offset === 1));
  assert.ok(result.stretches.some(s => s.column === 'english' && s.count >= 2));
});
