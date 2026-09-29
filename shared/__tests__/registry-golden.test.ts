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
    // Regenerated 2026-09-19: publishing Rogers on Lysistrata, Thesmophoriazusae and
    // Wealth adds those three translations to the registry (John's ruling).
    // Regenerated 2026-09-21: Ecclesiazusae's Rogers joins them, its drift fixed.
    // Regenerated 2026-09-22: Hickie's Bohn vol. I joins as `secondary` on
    // Acharnians, Knights, Wasps, Peace and Birds (John's ruling).
    // Regenerated 2026-09-29: edition picker P1-P2 adds greekEditions and each
    // paired translation's `edition` (Smyth, Storr, Murray OCT; John's go).
    // Regenerated 2026-09-29: P3 adds Hall & Geldart's OCT to the 11 comedies.
    expect(hash).toBe('20eec24b12232100bc478faa0b03044041e1da2e83c0c6b6e9fee7a776875916');
  });
});
