'use strict';

// 協助完成 Threads 的 OAuth，換出可以發文用的長期存取權杖。
// 流程：產生授權連結 → 你在瀏覽器同意 → 拿到 code → 換短期 token → 換 60 天長期 token。
// 文件：https://developers.facebook.com/docs/threads/get-started

const SCOPES = 'threads_basic,threads_content_publish';

// 第 0 步：產生要在瀏覽器打開的授權連結。
function buildAuthorizeUrl({ appId, redirectUri }) {
  const params = new URLSearchParams({
    client_id: appId,
    redirect_uri: redirectUri,
    scope: SCOPES,
    response_type: 'code',
  });
  return `https://threads.net/oauth/authorize?${params.toString()}`;
}

// 第 1 步：用授權碼換短期 token（同時拿到 user_id）。
async function exchangeCodeForToken({ appId, appSecret, redirectUri, code }) {
  const body = new URLSearchParams({
    client_id: appId,
    client_secret: appSecret,
    grant_type: 'authorization_code',
    redirect_uri: redirectUri,
    code,
  });

  const res = await fetch('https://graph.threads.net/oauth/access_token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.access_token) {
    throw new Error(`換短期 token 失敗：${data?.error_message || data?.error?.message || res.statusText}`);
  }
  return { shortToken: data.access_token, userId: String(data.user_id) };
}

// 第 2 步：把短期 token 換成 60 天長期 token。
async function exchangeForLongLived({ appSecret, shortToken }) {
  const params = new URLSearchParams({
    grant_type: 'th_exchange_token',
    client_secret: appSecret,
    access_token: shortToken,
  });

  const res = await fetch(`https://graph.threads.net/access_token?${params.toString()}`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.access_token) {
    throw new Error(`換長期 token 失敗：${data?.error_message || data?.error?.message || res.statusText}`);
  }
  return { longToken: data.access_token, expiresIn: data.expires_in };
}

// 一次跑完 1+2，回傳 user_id 與長期 token。
async function getLongLivedCredentials({ appId, appSecret, redirectUri, code }) {
  const { shortToken, userId } = await exchangeCodeForToken({ appId, appSecret, redirectUri, code });
  const { longToken, expiresIn } = await exchangeForLongLived({ appSecret, shortToken });
  return { userId, longToken, expiresIn };
}

module.exports = {
  SCOPES,
  buildAuthorizeUrl,
  exchangeCodeForToken,
  exchangeForLongLived,
  getLongLivedCredentials,
};
