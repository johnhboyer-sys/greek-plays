// Where the feedback form may post, or null to show no form. The form posts
// to the Worker's /api/feedback (app/worker/index.js), which only the
// Cloudflare deploy runs. That deploy also serves this marker file from
// app/public; the mirror bundle leaves it out (scripts/make-bundle.mjs), so on
// a plain static host (a mirror, the Docker image, a restore) the marker is
// missing and the form stays hidden (HANDOFF-PORTABILITY.md, phase 2). The
// marker is a static file, so asking for it never wakes the Worker.
export const FEEDBACK_MARKER = 'feedback-endpoint.json';

export async function feedbackEndpoint(
  base: string,
  fetchFn: (url: string) => Promise<Response> = (url) => fetch(url),
): Promise<string | null> {
  try {
    const r = await fetchFn(`${base}/${FEEDBACK_MARKER}`);
    if (!r.ok) return null;
    const body = await r.json();
    const post = body?.post;
    // A path on this host only: never another origin, never "//host".
    return typeof post === 'string' && post.startsWith('/') && !post.startsWith('//') ? post : null;
  } catch {
    return null;
  }
}
