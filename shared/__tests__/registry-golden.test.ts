import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { AUTHORS } from '../lib/authors';
import { WORKS } from '../lib/works';

describe('generated registry golden value', () => {
  it('keeps the default corpus registry stable', () => {
    const hash = createHash('sha256')
      .update(JSON.stringify(WORKS) + JSON.stringify(AUTHORS))
      .digest('hex');

    // P2+P3: the 44 plays of Aeschylus, Sophocles, Euripides and Aristophanes
    // on the play-line scheme.
    expect(WORKS).toHaveLength(44);
    expect(AUTHORS).toHaveLength(4);
    // After a deliberate registry change, regenerate with this exact command from shared/:
    // node --experimental-strip-types --input-type=module -e "import{createHash}from'node:crypto';import{CORPUS_WORKS as WORKS,CORPUS_AUTHORS as AUTHORS}from'./lib/registry.generated.ts';console.log(createHash('sha256').update(JSON.stringify(WORKS)+JSON.stringify(AUTHORS)).digest('hex'))"
    expect(hash).toBe('e4a740b374fdda5948fee4c7643b9e5aeee90a6d6193e949fb0f7d615d4e73bf');
  });
});
