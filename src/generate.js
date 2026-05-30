'use strict';

// 用 Claude 把一整批素材自動改寫成多篇 Threads 貼文。
// 產出的每篇都符合 Threads 的 500 字上限，可直接進佇列排程發出。

const Anthropic = require('@anthropic-ai/sdk');

const MODEL = 'claude-opus-4-8';

const SYSTEM_PROMPT = [
  '你是一位專業的社群小編，負責經營 Threads 帳號。',
  '使用者會提供一整批素材（草稿、筆記、想法、文章片段等）。',
  '你的工作是依照素材的內容與語氣，創作出多篇可以直接發佈的 Threads 貼文。',
  '',
  '規則：',
  '- 每篇貼文必須是繁體中文，且不超過 500 字（含標點與表情符號）。',
  '- 忠於素材的觀點與資訊，不要捏造事實。',
  '- 每篇聚焦一個重點，語氣自然、口語、適合社群閱讀。',
  '- 可適度使用換行與少量表情符號，但不要塞滿 hashtag。',
  '- 每篇都能獨立閱讀，不要寫成「上一篇／下一篇」這種連載口吻。',
].join('\n');

// 回傳格式：物件包一個字串陣列，方便用結構化輸出驗證。
const OUTPUT_SCHEMA = {
  type: 'object',
  properties: {
    posts: {
      type: 'array',
      items: { type: 'string' },
    },
  },
  required: ['posts'],
  additionalProperties: false,
};

// 依素材產生 count 篇貼文，回傳字串陣列。
async function generatePosts({ source, count, apiKey = process.env.ANTHROPIC_API_KEY }) {
  const material = String(source || '').trim();
  if (!material) {
    throw new Error('素材內容是空的，沒有東西可以改寫');
  }
  if (!apiKey) {
    throw new Error('缺少 ANTHROPIC_API_KEY，請在 .env 填入（參考 .env.example）');
  }

  const client = new Anthropic({ apiKey });

  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 8000,
    thinking: { type: 'adaptive' },
    system: [
      { type: 'text', text: SYSTEM_PROMPT, cache_control: { type: 'ephemeral' } },
    ],
    output_config: { format: { type: 'json_schema', schema: OUTPUT_SCHEMA } },
    messages: [
      {
        role: 'user',
        content: `請依照以下素材，創作 ${count} 篇 Threads 貼文：\n\n${material}`,
      },
    ],
  });

  const textBlock = response.content.find((b) => b.type === 'text');
  if (!textBlock) {
    throw new Error('Claude 沒有回傳文字內容');
  }

  let parsed;
  try {
    parsed = JSON.parse(textBlock.text);
  } catch {
    throw new Error('無法解析 Claude 回傳的內容');
  }

  const posts = Array.isArray(parsed.posts) ? parsed.posts : [];
  return posts.map((p) => String(p).trim()).filter(Boolean);
}

module.exports = { generatePosts, MODEL };
