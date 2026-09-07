import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { AUTHORS } from '../lib/authors';
import { WORKS } from '../lib/works';

describe('generated registry golden value', () => {
  it('keeps the default corpus registry stable', () => {
    const hash = createHash('sha256')
      .update(JSON.stringify(WORKS) + JSON.stringify(AUTHORS))
      .digest('hex');

    // P2 (docs/p2-greek-report.md): the 33 tragedies of Aeschylus, Sophocles
    // and Euripides on the play-line scheme.
    expect(WORKS).toHaveLength(33);
    expect(AUTHORS).toHaveLength(3);
    // After a deliberate registry change, regenerate with this exact command from shared/:
    // node --experimental-strip-types --input-type=module -e "import{createHash}from'node:crypto';import{CORPUS_WORKS as WORKS,CORPUS_AUTHORS as AUTHORS}from'./lib/registry.generated.ts';console.log(createHash('sha256').update(JSON.stringify(WORKS)+JSON.stringify(AUTHORS)).digest('hex'))"
    expect(hash).toBe('5d805148b8c10f0c5f1ccc4b93445ff7d9eadcab02ca1be4703d203cacac760d');
  });
});
