const Anthropic = require('@anthropic-ai/sdk');
const { getSetting } = require('./database');

function getClient() {
  const apiKey = getSetting('anthropic_api_key');
  if (!apiKey) return null;
  return new Anthropic({ apiKey });
}

async function generateSummaryAndTags(content) {
  const client = getClient();
  if (!client) return null;

  const response = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 300,
    messages: [
      {
        role: 'user',
        content: `Analyze this note and return a JSON object with:
1. "summary": a one-sentence summary (max 100 chars)
2. "tags": an array of 1-5 relevant short tags (lowercase, no #)

Note content:
${content}

Respond ONLY with valid JSON, no other text.`,
      },
    ],
  });

  try {
    const text = response.content[0].text.trim();
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function askQuestion(question, context) {
  const client = getClient();
  if (!client) throw new Error('API key not configured');

  const systemPrompt = context.length > 0
    ? `You are a helpful assistant. Answer questions based on the user's notes. Here are relevant notes:\n\n${context.map((n, i) => `[Note ${i + 1}] ${n.content}${n.summary ? ' (Summary: ' + n.summary + ')' : ''}`).join('\n\n')}`
    : 'You are a helpful assistant. The user has no notes matching their question. Answer based on your general knowledge and let them know no matching notes were found.';

  const response = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 1024,
    system: systemPrompt,
    messages: [{ role: 'user', content: question }],
  });

  return response.content[0].text;
}

module.exports = { generateSummaryAndTags, askQuestion };
