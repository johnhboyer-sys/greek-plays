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
    expect(hash).toBe('2e5b8cc00bfa05ec88ea4caacb08cf3c24a1fde5c87b9f103fb559dbb5f4766e');
  });
});
