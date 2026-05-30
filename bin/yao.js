#!/usr/bin/env node
'use strict';

// 命令列工具：
//   yao auth url    --app-id … --redirect-uri …                       產生 Threads 授權連結
//   yao auth token  --app-id … --app-secret … --redirect-uri … --code …  用授權碼換出長期 token
//   yao add "要發的內容"        把一篇貼文加進佇列
//   yao generate <檔案> [篇數]  用 AI 把素材檔自動改寫成多篇貼文並加進佇列
//   yao import <檔案.json>      把一個 JSON 字串陣列（現成貼文）整批加進佇列
//   yao list                    列出佇列狀態
//   yao publish-now             立刻發出下一篇（給測試，或用系統 cron / GitHub Actions 呼叫）

require('dotenv').config();
const fs = require('fs');
const queue = require('../src/queue');

function cmdAdd(args) {
  const text = args.join(' ').trim();
  if (!text) {
    console.error('用法：yao add "你要發的內容"');
    process.exit(1);
  }
  const post = queue.add(text);
  console.log(`已加入佇列：${post.id}`);
  console.log(`內容：${post.text}`);
}

function cmdList() {
  const posts = queue.load();
  if (posts.length === 0) {
    console.log('佇列是空的。用 `yao add "內容"` 新增貼文。');
    return;
  }
  const icon = { pending: '🕒', published: '✅', failed: '❌' };
  for (const p of posts) {
    const preview = p.text.length > 30 ? p.text.slice(0, 30) + '…' : p.text;
    console.log(`${icon[p.status] || '?'} [${p.status}] ${preview}`);
  }
  const pending = posts.filter((p) => p.status === 'pending').length;
  console.log(`\n共 ${posts.length} 篇，待發 ${pending} 篇。`);
}

// 把 --key value 解析成物件。
function parseFlags(args) {
  const flags = {};
  for (let i = 0; i < args.length; i += 1) {
    if (args[i].startsWith('--')) {
      const key = args[i].slice(2);
      flags[key] = args[i + 1];
      i += 1;
    }
  }
  return flags;
}

async function cmdAuth(args) {
  const [sub, ...rest] = args;
  const flags = parseFlags(rest);
  const auth = require('../src/auth');

  if (sub === 'url') {
    if (!flags['app-id'] || !flags['redirect-uri']) {
      console.error('用法：yao auth url --app-id <APP_ID> --redirect-uri <REDIRECT_URI>');
      process.exit(1);
    }
    const url = auth.buildAuthorizeUrl({
      appId: flags['app-id'],
      redirectUri: flags['redirect-uri'],
    });
    console.log('在瀏覽器打開這個連結並同意授權：\n');
    console.log(url);
    console.log('\n授權後會跳轉到你的 redirect URI，網址會帶 ?code=...，把那個 code 複製下來。');
    console.log('接著執行：yao auth token --app-id … --app-secret … --redirect-uri … --code <剛剛的code>');
    return;
  }

  if (sub === 'token') {
    const required = ['app-id', 'app-secret', 'redirect-uri', 'code'];
    const missing = required.filter((k) => !flags[k]);
    if (missing.length) {
      console.error(`缺少參數：${missing.map((k) => '--' + k).join(', ')}`);
      console.error('用法：yao auth token --app-id … --app-secret … --redirect-uri … --code …');
      process.exit(1);
    }
    console.log('正在換取長期 token…');
    const { userId, longToken, expiresIn } = await auth.getLongLivedCredentials({
      appId: flags['app-id'],
      appSecret: flags['app-secret'],
      redirectUri: flags['redirect-uri'],
      code: flags['code'],
    });
    const days = expiresIn ? Math.round(expiresIn / 86400) : 60;
    console.log('\n✅ 成功！把以下兩行填進你的 .env：\n');
    console.log(`THREADS_USER_ID=${userId}`);
    console.log(`THREADS_ACCESS_TOKEN=${longToken}`);
    console.log(`\n（此 token 約 ${days} 天後過期，快過期時再重新授權即可。）`);
    return;
  }

  console.log('用法：');
  console.log('  yao auth url   --app-id … --redirect-uri …');
  console.log('  yao auth token --app-id … --app-secret … --redirect-uri … --code …');
  process.exit(sub ? 1 : 0);
}

function cmdImport(args) {
  const [file] = args;
  if (!file) {
    console.error('用法：yao import <檔案.json>（內容須為字串陣列）');
    process.exit(1);
  }
  if (!fs.existsSync(file)) {
    console.error(`找不到檔案：${file}`);
    process.exit(1);
  }

  let items;
  try {
    items = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    console.error('檔案不是有效的 JSON');
    process.exit(1);
  }
  if (!Array.isArray(items)) {
    console.error('JSON 內容必須是一個字串陣列');
    process.exit(1);
  }

  let added = 0;
  for (const text of items) {
    try {
      queue.add(text);
      added += 1;
      const preview = String(text).replace(/\n/g, ' ').slice(0, 30);
      console.log(`  ✅ ${preview}…`);
    } catch (err) {
      console.error(`  ⚠️ 跳過一篇：${err.message}`);
    }
  }
  console.log(`\n完成，已加入 ${added} 篇到佇列。用 \`yao list\` 檢視。`);
}

async function cmdGenerate(args) {
  const [file, countArg] = args;
  if (!file) {
    console.error('用法：yao generate <素材檔案> [要產生的篇數，預設 10]');
    process.exit(1);
  }
  if (!fs.existsSync(file)) {
    console.error(`找不到檔案：${file}`);
    process.exit(1);
  }

  const count = Number(countArg) || 10;
  const source = fs.readFileSync(file, 'utf8');

  const { generatePosts } = require('../src/generate');
  console.log(`正在用 AI 依素材產生 ${count} 篇貼文…`);
  const posts = await generatePosts({ source, count });

  let added = 0;
  for (const text of posts) {
    try {
      queue.add(text);
      added += 1;
      const preview = text.length > 40 ? text.slice(0, 40) + '…' : text;
      console.log(`  ✅ ${preview}`);
    } catch (err) {
      console.error(`  ⚠️ 跳過一篇：${err.message}`);
    }
  }
  console.log(`\n完成，已加入 ${added} 篇到佇列。用 \`yao list\` 檢視。`);
}

async function cmdPublishNow() {
  const config = require('../src/config').load();
  const { publishNext } = require('../src/publish');
  const result = await publishNext(config);
  process.exit(result.published ? 0 : 1);
}

async function main() {
  const [command, ...args] = process.argv.slice(2);
  switch (command) {
    case 'auth':
      return cmdAuth(args);
    case 'add':
      return cmdAdd(args);
    case 'generate':
      return cmdGenerate(args);
    case 'import':
      return cmdImport(args);
    case 'list':
      return cmdList();
    case 'publish-now':
      return cmdPublishNow();
    default:
      console.log('用法：');
      console.log('  yao auth url|token …        取得 Threads 授權與長期 token');
      console.log('  yao add "內容"             把一篇貼文加進佇列');
      console.log('  yao generate <檔案> [篇數]  用 AI 把素材自動改寫成多篇貼文');
      console.log('  yao import <檔案.json>      把現成貼文（JSON 陣列）整批加進佇列');
      console.log('  yao list                   列出佇列狀態');
      console.log('  yao publish-now            立刻發出下一篇');
      process.exit(command ? 1 : 0);
  }
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
