'use strict';

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const queue = require('../src/queue');

function tmpFile() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'yao-')), 'queue.json');
}

test('add 會把貼文加進佇列並標為 pending', () => {
  const file = tmpFile();
  const post = queue.add('哈囉 Threads', file);
  assert.equal(post.status, 'pending');
  assert.equal(post.attempts, 0);

  const posts = queue.load(file);
  assert.equal(posts.length, 1);
  assert.equal(posts[0].text, '哈囉 Threads');
});

test('add 會拒絕空白內容', () => {
  const file = tmpFile();
  assert.throws(() => queue.add('   ', file), /不可為空/);
});

test('add 會拒絕超過 500 字', () => {
  const file = tmpFile();
  assert.throws(() => queue.add('字'.repeat(501), file), /上限/);
});

test('nextPending 回傳最前面的 pending 貼文', () => {
  const posts = [
    { id: 'a', status: 'published' },
    { id: 'b', status: 'pending' },
    { id: 'c', status: 'pending' },
  ];
  assert.equal(queue.nextPending(posts).id, 'b');
});

test('nextPending 在沒有 pending 時回傳 null', () => {
  assert.equal(queue.nextPending([{ id: 'a', status: 'published' }]), null);
});

test('markPublished 更新狀態與 threadId', () => {
  const posts = [{ id: 'a', status: 'pending', attempts: 0 }];
  queue.markPublished(posts, 'a', 'thread-123');
  assert.equal(posts[0].status, 'published');
  assert.equal(posts[0].threadId, 'thread-123');
  assert.ok(posts[0].publishedAt);
});

test('markFailed 在達到上限前維持 pending', () => {
  const posts = [{ id: 'a', status: 'pending', attempts: 0 }];
  queue.markFailed(posts, 'a', 'boom');
  assert.equal(posts[0].status, 'pending');
  assert.equal(posts[0].attempts, 1);
  assert.equal(posts[0].lastError, 'boom');
});

test('markFailed 達到上限後標為 failed', () => {
  const posts = [{ id: 'a', status: 'pending', attempts: queue.MAX_ATTEMPTS - 1 }];
  queue.markFailed(posts, 'a', 'boom');
  assert.equal(posts[0].status, 'failed');
});
