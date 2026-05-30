'use strict';

// 從環境變數讀取設定，並把 "HH:MM" 的發文時間轉成 cron 表達式。

function parseTimes(raw) {
  const times = String(raw || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

  if (times.length === 0) {
    throw new Error('SCHEDULE_TIMES 未設定，請至少給一個時間，例如 09:00,21:00');
  }

  return times.map((t) => {
    const match = /^(\d{1,2}):(\d{2})$/.exec(t);
    if (!match) {
      throw new Error(`時間格式錯誤："${t}"，正確格式為 HH:MM（24 小時制）`);
    }
    const hour = Number(match[1]);
    const minute = Number(match[2]);
    if (hour > 23 || minute > 59) {
      throw new Error(`時間超出範圍："${t}"`);
    }
    return { time: t, hour, minute, cron: `${minute} ${hour} * * *` };
  });
}

function load(env = process.env) {
  const config = {
    userId: env.THREADS_USER_ID,
    accessToken: env.THREADS_ACCESS_TOKEN,
    timezone: env.TIMEZONE || 'Asia/Taipei',
    times: parseTimes(env.SCHEDULE_TIMES || '09:00,21:00'),
  };

  const missing = [];
  if (!config.userId) missing.push('THREADS_USER_ID');
  if (!config.accessToken) missing.push('THREADS_ACCESS_TOKEN');
  if (missing.length > 0) {
    throw new Error(`缺少必要的環境變數：${missing.join(', ')}（請參考 .env.example）`);
  }

  return config;
}

module.exports = { load, parseTimes };
