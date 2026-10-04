import '@testing-library/jest-dom/vitest';

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

class IntersectionObserverMock {
  readonly root = null;
  readonly rootMargin = '';
  readonly thresholds = [];

  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() { return []; }
}

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: ResizeObserverMock,
});

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: IntersectionObserverMock,
});

Element.prototype.scrollIntoView = vi.fn();

// happy-dom does not implement the Web Animations API; components that call
// `element.animate(...)` (e.g. WordPopup) would throw. Stub a minimal
// Animation-like object so those code paths run under test.
Element.prototype.animate = vi.fn(() => ({
  finished: Promise.resolve(),
  cancel() {},
  finish() {},
  play() {},
  pause() {},
  onfinish: null,
  addEventListener() {},
  removeEventListener() {},
})) as unknown as Element['animate'];

// happy-dom's page origin is http://localhost:3000, where nothing listens:
// components that mount in these tests fetch /data/... for files no test
// mocks, and each attempt printed an ECONNREFUSED AggregateError that reads
// like a failure. Fail same-origin fetches at once with the TypeError a dead
// network gives, so components take the same path as before (a rejection,
// which data.ts evicts from its caches; a 404 would cache [] or {} instead).
// Tests that spy on or stub fetch replace this as before.
{
  const realFetch = globalThis.fetch;
  globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
    const raw = input instanceof Request ? input.url : String(input);
    // Some tests leave location.href unparseable as a base, so test a
    // relative URL by its missing scheme rather than by resolving it.
    const relative = !/^[a-z][a-z\d+.-]*:/i.test(raw);
    if (relative || new URL(raw).origin === window.location.origin) {
      return Promise.reject(new TypeError(`fetch failed: no test server for ${raw}`));
    }
    return realFetch(input, init);
  }) as typeof fetch;
}
