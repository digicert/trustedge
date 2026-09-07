/**
 * ai-proxy-worker.js
 * ──────────────────
 * Cloudflare Worker that proxies "Ask AI" requests from the TrustEdge
 * compatibility page to GitHub Models API (free with GitHub Copilot).
 *
 * DEPLOY (free, ~2 minutes):
 *   1. npm install -g wrangler
 *   2. wrangler login
 *   3. wrangler deploy scripts/ai-proxy-worker.js --name trustedge-ai-proxy
 *   4. In Cloudflare dashboard → Workers → trustedge-ai-proxy → Settings → Variables
 *      Add secret:  GITHUB_TOKEN = <your PAT with models:read scope>
 *   5. Note your worker URL:  https://trustedge-ai-proxy.<your-subdomain>.workers.dev
 *   6. In docs/index.html, add before </body>:
 *        <script>window.AI_PROXY_URL = "https://trustedge-ai-proxy.<subdomain>.workers.dev";</script>
 *
 * CODESPACE ALTERNATIVE:
 *   Run locally in a Codespace and expose port 8787 publicly:
 *     GITHUB_TOKEN=<token> wrangler dev scripts/ai-proxy-worker.js --port 8787
 *   Then set:  window.AI_PROXY_URL = "https://<codespace-name>-8787.app.github.dev"
 */

const GITHUB_MODELS_URL = 'https://models.inference.ai.azure.com/chat/completions';
const MODEL = 'openai/gpt-4o-mini';   // cheapest / fastest; change to gpt-4o or claude if needed

const SYSTEM_PROMPT = `You are a helpful assistant for DigiCert TrustEdge, an IoT security agent.
Answer questions with exact, copy-pasteable shell commands. Be concise — 3-10 lines max.
Commands must match the TrustEdge version and platform in the context.
Never invent flags not documented in the TrustEdge docs at https://dev.digicert.com/en/trustedge.html.`;

export default {
  async fetch(request, env) {

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders() });
    }

    if (request.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405 });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response('Bad Request', { status: 400 });
    }

    const { context, question, commands_version } = body;
    if (!question) return new Response('Missing question', { status: 400 });

    const userMessage = [
      `Platform context: ${context || 'unknown'}`,
      commands_version ? `TrustEdge commands.json version: ${commands_version}` : '',
      '',
      `Question: ${question}`,
    ].filter(Boolean).join('\n');

    // Call GitHub Models API
    const ghRes = await fetch(GITHUB_MODELS_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: MODEL,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user',   content: userMessage },
        ],
        temperature: 0.2,
        max_tokens: 512,
      }),
    });

    if (!ghRes.ok) {
      const err = await ghRes.text();
      return new Response(JSON.stringify({ error: err }), {
        status: ghRes.status,
        headers: { 'Content-Type': 'application/json', ...corsHeaders() },
      });
    }

    const data = await ghRes.json();
    const answer = data.choices?.[0]?.message?.content || 'No response';

    return new Response(JSON.stringify({ answer }), {
      headers: { 'Content-Type': 'application/json', ...corsHeaders() },
    });
  },
};

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}
