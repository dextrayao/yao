'use strict';

// 貼文佇列：你把要發的內容寫進 data/queue.json，排程器每次取出最前面一篇「pending」發出去。
// 這個模組刻意不依賴任何第三方套件，方便單獨測試。

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DATA_DIR = path.join(__dirname, '..', 'data');
const QUEUE_PATH = path.join(DATA_DIR, 'queue.json');

const MAX_ATTEMPTS = 3;

function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
}

function load(filePath = QUEUE_PATH) {
  if (!fs.existsSync(filePath)) {
    return [];
  }
  const raw = fs.readFileSync(filePath, 'utf8').trim();
  if (!raw) {
    return [];
  }
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed)) {
    throw new Error(`${filePath} 必須是一個 JSON 陣列`);
  }
  return parsed;
}

function save(posts, filePath = QUEUE_PATH) {
  ensureDataDir();
  fs.writeFileSync(filePath, JSON.stringify(posts, null, 2) + '\n', 'utf8');
}

// 在佇列尾端新增一篇待發貼文。
function add(text, filePath = QUEUE_PATH) {
  const trimmed = String(text || '').trim();
  if (!trimmed) {
    throw new Error('貼文內容不可為空');
  }
  if (trimmed.length > 500) {
    throw new Error(`貼文超過 Threads 上限 500 字（目前 ${trimmed.length} 字）`);
  }
  const posts = load(filePath);
  const post = {
    id: crypto.randomUUID(),
    text: trimmed,
    status: 'pending',
    attempts: 0,
    createdAt: new Date().toISOString(),
  };
  posts.push(post);
  save(posts, filePath);
  return post;
}

// 取得下一篇要發的貼文（最前面、狀態為 pending 的那一篇），沒有則回傳 null。
function nextPending(posts) {
  return posts.find((p) => p.status === 'pending') || null;
}

// 標記某篇貼文已成功發佈。
function markPublished(posts, id, threadId) {
  const post = posts.find((p) => p.id === id);
  if (!post) return posts;
  post.status = 'published';
  post.threadId = threadId;
  post.publishedAt = new Date().toISOString();
  return posts;
}

// 標記某篇貼文發佈失敗；累積到上限後標為 failed，否則維持 pending 等下次重試。
function markFailed(posts, id, errorMessage) {
  const post = posts.find((p) => p.id === id);
  if (!post) return posts;
  post.attempts = (post.attempts || 0) + 1;
  post.lastError = errorMessage;
  post.status = post.attempts >= MAX_ATTEMPTS ? 'failed' : 'pending';
  return posts;
}

module.exports = {
  QUEUE_PATH,
  MAX_ATTEMPTS,
  load,
  save,
  add,
  nextPending,
  markPublished,
  markFailed,
};
