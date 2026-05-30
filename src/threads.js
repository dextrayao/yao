'use strict';

// Threads API 客戶端。
// Threads API 本身沒有「排程」功能，只能立刻發佈，所以發文分兩步驟：
//   1. 建立 media container  -> 取得 creation_id
//   2. 用 creation_id 發佈   -> 取得貼文 id
// 文件：https://developers.facebook.com/docs/threads/posts

const API_BASE = 'https://graph.threads.net/v1.0';

async function callApi(path, params) {
  const url = `${API_BASE}${path}`;
  const body = new URLSearchParams(params);

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = data?.error?.message || res.statusText;
    throw new Error(`Threads API ${res.status}: ${message}`);
  }
  return data;
}

// 步驟 1：建立純文字貼文的 container。
async function createTextContainer({ userId, accessToken, text }) {
  const data = await callApi(`/${userId}/threads`, {
    media_type: 'TEXT',
    text,
    access_token: accessToken,
  });
  if (!data.id) {
    throw new Error('建立 container 失敗：回應沒有 id');
  }
  return data.id; // creation_id
}

// 步驟 2：發佈 container。
async function publishContainer({ userId, accessToken, creationId }) {
  const data = await callApi(`/${userId}/threads_publish`, {
    creation_id: creationId,
    access_token: accessToken,
  });
  if (!data.id) {
    throw new Error('發佈失敗：回應沒有 id');
  }
  return data.id; // 已發佈貼文的 id
}

// 一次完成「建立 + 發佈」一篇純文字貼文。
async function publishText({ userId, accessToken, text }) {
  const creationId = await createTextContainer({ userId, accessToken, text });
  // Threads 官方建議建立 container 後稍等再發佈，讓伺服器完成處理。
  await new Promise((r) => setTimeout(r, 1000));
  return publishContainer({ userId, accessToken, creationId });
}

module.exports = {
  createTextContainer,
  publishContainer,
  publishText,
};
