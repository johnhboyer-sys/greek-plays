// The site is static files (wrangler.jsonc `assets`); this Worker runs only
// for /api/* (run_worker_first) and serves one route: the feedback form,
// which it emails to John (John, 2026-10-24: "a form on the site that
// e-mails me rather than opening the user's email client"; free: Email
// Routing sends to a verified address at no cost).
const MAX_MESSAGE = 5000;
const EMAIL_RE = /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/;

function reply(status, body) {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

async function feedback(request, env) {
  if (request.method !== 'POST') return reply(405, { error: 'Use POST.' });
  // Same-origin form posts only.
  const origin = request.headers.get('origin');
  if (origin && new URL(origin).host !== new URL(request.url).host) return reply(403, { error: 'Wrong origin.' });
  let data;
  try { data = await request.json(); } catch { return reply(400, { error: 'The form could not be read.' }); }
  // A filled hidden field is a bot: report success and send nothing.
  if (data.website) return reply(200, { ok: true });
  const message = String(data.message ?? '').trim();
  const type = data.type === 'bug' ? 'bug' : 'feature';
  const from = String(data.email ?? '').trim();
  const page = String(data.page ?? '').slice(0, 300);
  if (!message) return reply(400, { error: 'Write a message first.' });
  if (message.length > MAX_MESSAGE) return reply(400, { error: `Keep it under ${MAX_MESSAGE} characters.` });
  if (from && (!EMAIL_RE.test(from) || from.length > 200)) return reply(400, { error: 'That email address does not look right.' });
  const ip = request.headers.get('cf-connecting-ip') ?? 'unknown';
  if (env.FEEDBACK_LIMIT) {
    const { success } = await env.FEEDBACK_LIMIT.limit({ key: ip });
    if (!success) return reply(429, { error: 'Too many messages just now. Try again in a minute.' });
  }
  const subject = type === 'bug' ? 'The Greek Drama Reader: Bug Report' : 'The Greek Drama Reader: Feature Request';
  const text = [message, '', '—', `Type: ${type === 'bug' ? 'Bug / error report' : 'Feature request'}`, `Page: ${page || 'unknown'}`, `Reply to: ${from || 'not given'}`].join('\n');
  try {
    await env.FEEDBACK.send({
      to: 'johnhboyer@gmail.com',
      from: { email: 'feedback@johnhboyer.com', name: 'Greek Drama Reader' },
      ...(from ? { replyTo: from } : {}),
      subject,
      text,
    });
  } catch (e) {
    console.error('feedback send failed', e && e.message);
    return reply(502, { error: 'The message did not send. Try again later.' });
  }
  return reply(200, { ok: true });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/api/feedback') return feedback(request, env);
    return env.ASSETS.fetch(request);
  },
};
