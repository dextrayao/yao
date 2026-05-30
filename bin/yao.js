#!/usr/bin/env node
'use strict';

// 命令列工具：
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
