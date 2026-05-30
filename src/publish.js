'use strict';

// 發出佇列中的下一篇貼文。排程器與 `yao publish-now` 都會呼叫這裡。

const queue = require('./queue');
const threads = require('./threads');

async function publishNext(config, { logger = console } = {}) {
  const posts = queue.load();
  const post = queue.nextPending(posts);

  if (!post) {
    logger.log('[yao] 佇列裡沒有待發的貼文，這次跳過。');
    return { published: false, reason: 'empty' };
  }

  logger.log(`[yao] 準備發佈：${post.id}`);
  try {
    const threadId = await threads.publishText({
      userId: config.userId,
      accessToken: config.accessToken,
      text: post.text,
    });
    queue.markPublished(posts, post.id, threadId);
    queue.save(posts);
    logger.log(`[yao] ✅ 已發佈，貼文 id = ${threadId}`);
    return { published: true, post, threadId };
  } catch (err) {
    queue.markFailed(posts, post.id, err.message);
    queue.save(posts);
    logger.error(`[yao] ❌ 發佈失敗（第 ${post.attempts + 1} 次）：${err.message}`);
    return { published: false, reason: 'error', error: err };
  }
}

module.exports = { publishNext };
