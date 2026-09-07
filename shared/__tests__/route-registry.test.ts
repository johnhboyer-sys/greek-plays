import { describe, expect, it } from 'vitest';
// @ts-expect-error The production generator is a plain .mjs module.
import * as routeRegistry from '../../scripts/build-route-registry.mjs';
import {
  CORPUS_AUTHORS,
  CORPUS_WORKS,
  WORK_CORPUS_DATA,
} from '../lib/registry.generated';

const {
  checkCaseInsensitiveWorkIds,
  checkDuplicateRoutes,
  checkReservedSegments,
  checkRouteRegistry,
  scanReservedSegments,
} = routeRegistry;

describe('route registry collision gates', () => {
  it('reports an injected duplicate route', () => {
    const problems = checkDuplicateRoutes([
      { route: '/author/work', corpus: 'one', work: 'first' },
      { route: '/author/work', corpus: 'two', work: 'second' },
    ]);

    expect(problems).toHaveLength(1);
    expect(problems[0]).toContain("duplicate route '/author/work'");
  });

  it("reports a reserved author id of 'search'", () => {
    const problems = checkReservedSegments([{ id: 'search' }], [], ['search']);

    expect(problems).toHaveLength(1);
    expect(problems[0]).toContain("author id 'search'");
  });

  it("reports a case-insensitive work-id collision for 'en' and 'EN'", () => {
    const problems = checkCaseInsensitiveWorkIds([{ id: 'en' }, { id: 'EN' }]);

    expect(problems).toHaveLength(1);
    expect(problems[0]).toContain("'en', 'EN'");
  });

  it('accepts the P2 registry (44 plays, no collisions)', () => {
    const result = checkRouteRegistry({
      works: CORPUS_WORKS,
      authors: CORPUS_AUTHORS,
      workCorpus: WORK_CORPUS_DATA,
      reservedSegments: scanReservedSegments(),
    });

    expect(result.routes).toHaveLength(44); // P2: 44 plays, author-scoped routes
    expect(result.problems).toEqual([]);
  });
});
