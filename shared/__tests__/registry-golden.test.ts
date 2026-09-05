import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { AUTHORS } from '../lib/authors';
import { WORKS } from '../lib/works';

describe('generated registry golden value', () => {
  it('keeps the default corpus registry stable', () => {
    const hash = createHash('sha256')
      .update(JSON.stringify(WORKS) + JSON.stringify(AUTHORS))
      .digest('hex');

    // Zero-works registry (drama fork P0, docs/plan.md §1): the CPR corpus
    // was stripped along with its manifests, leaving an empty registry until
    // the first play manifest lands (P1+).
    expect(WORKS).toHaveLength(0);
    expect(AUTHORS).toHaveLength(0);
    // After a deliberate registry change, regenerate with this exact command from shared/:
    // node --experimental-strip-types --input-type=module -e "import{createHash}from'node:crypto';import{CORPUS_WORKS as WORKS,CORPUS_AUTHORS as AUTHORS}from'./lib/registry.generated.ts';console.log(createHash('sha256').update(JSON.stringify(WORKS)+JSON.stringify(AUTHORS)).digest('hex'))"
    expect(hash).toBe('821bf06b4dcb406ea508a4a992eadc22f29850cd208ba24aea7c29148de8ccf1');
  });
});
