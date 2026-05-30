'use strict';

// 常駐排程器：依 SCHEDULE_TIMES 設定的時間，每天定時各發一篇。
// 啟動方式：node src/index.js  （或 npm start）

require('dotenv').config();
const cron = require('node-cron');
const config = require('./config').load();
const { publishNext } = require('./publish');

console.log('[yao] 排程器啟動');
console.log(`[yao] 時區：${config.timezone}`);
console.log(
  `[yao] 每天發文時間：${config.times.map((t) => t.time).join(', ')}（共 ${config.times.length} 篇/天）`
);

for (const slot of config.times) {
  cron.schedule(
    slot.cron,
    () => {
      console.log(`[yao] ⏰ ${slot.time} 觸發`);
      publishNext(config).catch((err) => console.error('[yao] 未預期錯誤：', err));
    },
    { timezone: config.timezone }
  );
}

console.log('[yao] 已排程，等待中…（按 Ctrl+C 結束）');
