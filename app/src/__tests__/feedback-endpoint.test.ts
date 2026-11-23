import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { feedbackEndpoint, FEEDBACK_MARKER } from '../lib/feedback-endpoint';

// The feedback form posts to the Worker's /api/feedback (app/worker/index.js).
// A plain static host (a mirror, the Docker image, a restore) has no /api, so
// the form shows only where the host serves the marker file the Cloudflare
// deploy ships and the mirror bundle leaves out (HANDOFF-PORTABILITY.md,
// phase 2). The failing cases come first.
const res = (status: number, body: string, type = 'application/json') =>
  new Response(body, { status, headers: { 'content-type': type } });

describe('feedbackEndpoint', () => {
  it.each([
    ['a 404', () => res(404, 'not found', 'text/html')],
    ['a host that answers every path with its home page', () => res(200, '<!doctype html><p>home</p>', 'text/html')],
    ['a marker that is not JSON', () => res(200, 'post=/api/feedback')],
    ['a marker with no address', () => res(200, '{}')],
    ['an address on another host', () => res(200, '{"post":"https://evil.example/api"}')],
    ['a protocol-relative address', () => res(200, '{"post":"//evil.example/api"}')],
    ['an address that is not a string', () => res(200, '{"post":["/api/feedback"]}')],
    ['a server error', () => res(500, '{"post":"/api/feedback"}')],
    // Grok's read of #18: a browser reads "/\\host" as "//host"
    ['a backslash address', () => res(200, '{"post":"/\\\\evil.example/collect"}')],
    ['an address with a scheme inside', () => res(200, '{"post":"/x:evil"}')],
    ['an address with a query', () => res(200, '{"post":"/api/feedback?to=x"}')],
  ])('shows no form for %s', async (_name, answer) => {
    expect(await feedbackEndpoint('', async () => answer())).toBeNull();
  });

  it('shows no form when the marker came by way of a redirect', async () => {
    // Grok's read of #18: a host that redirects the marker elsewhere
    const redirected = { ok: true, redirected: true, json: async () => ({ post: '/api/feedback' }) } as unknown as Response;
    expect(await feedbackEndpoint('', async () => redirected)).toBeNull();
  });

  it('shows no form when the request itself fails (offline, refused)', async () => {
    expect(await feedbackEndpoint('', async () => { throw new TypeError('Failed to fetch'); })).toBeNull();
  });

  it('asks for the marker under the site base, and takes its same-origin address', async () => {
    const asked: string[] = [];
    const got = await feedbackEndpoint('/plays', async (url) => { asked.push(String(url)); return res(200, '{"post":"/api/feedback"}'); });
    expect(asked).toEqual([`/plays/${FEEDBACK_MARKER}`]);
    expect(got).toBe('/api/feedback');
  });

  it('the marker ships in app/public with the Worker\'s address', () => {
    const marker = JSON.parse(readFileSync(join(process.cwd(), 'public', FEEDBACK_MARKER), 'utf8'));
    expect(marker).toEqual({ post: '/api/feedback' });
    expect(readFileSync(join(process.cwd(), 'worker', 'index.js'), 'utf8')).toContain("url.pathname === '/api/feedback'");
  });

  it('the foot hides the button until the marker says where to post, and posts there', () => {
    const foot = readFileSync(join(process.cwd(), 'src', 'components', 'SiteFoot.astro'), 'utf8');
    expect(foot).toMatch(/<button type="button" class="feedback-btn" hidden>/);
    expect(foot).toMatch(/feedbackEndpoint\(/);
    expect(foot).not.toMatch(/fetch\('\/api\/feedback'/);
  });
});
