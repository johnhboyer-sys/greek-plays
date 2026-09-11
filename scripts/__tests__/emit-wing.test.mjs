import { test } from 'node:test';
import assert from 'node:assert/strict';

import { buildWing } from '../emit-wing.mjs';

function argumentManifests(byId) {
  return (id) => {
    const argument = byId[id];
    if (argument === undefined) throw new Error(`unexpected read of ${id}`);
    return { registry: { argument } };
  };
}

// Astra lane B, F5: a zero-work public build must still emit a valid snapshot.
test('emits a valid empty snapshot when membership is empty', () => {
  const wing = buildWing([{ id: 'aeschylus', works: [] }], () => {
    throw new Error('unexpected read');
  });
  assert.deepEqual(wing.memberships, []);
  assert.deepEqual(wing.featured, []);
  assert.ok(!wing.paths || wing.paths.length === 0);
});

test('includes a featured work only when it is a member', () => {
  const wing = buildWing(
    [{ id: 'sophocles', works: ['oedipus-tyrannus'] }],
    argumentManifests({ 'oedipus-tyrannus': 'OT blurb' }),
  );
  assert.deepEqual(
    wing.featured.map((item) => item.work),
    ['oedipus-tyrannus'],
  );
  assert.ok(!wing.paths || wing.paths.length === 0);
});

test('includes Oresteia stops only for member plays', () => {
  const wing = buildWing(
    [{ id: 'aeschylus', works: ['agamemnon', 'eumenides'] }],
    argumentManifests({ agamemnon: 'Ag blurb', eumenides: 'Eu blurb' }),
  );
  assert.equal(wing.paths.length, 1);
  assert.deepEqual(
    wing.paths[0].stops.map((stop) => stop.work),
    ['agamemnon', 'eumenides'],
  );
});
