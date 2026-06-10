// The 24/7 simulation loop. Self-rescheduling setTimeout chain (not setInterval)
// so a slow tick never stacks. Runs once immediately on boot to catch up any
// offline time, then every STEP_MS.

import { STEP_MS } from '@yao/core';
import { tickAll } from './service.js';

let timer: NodeJS.Timeout | null = null;

function loop(): void {
  try {
    tickAll();
  } catch (err) {
    console.error('[ticker] tick failed:', err);
  }
  timer = setTimeout(loop, STEP_MS);
}

export function startTicker(): void {
  if (timer) return;
  loop(); // immediate catch-up tick on boot
  console.log(`[ticker] started — ticking every ${STEP_MS / 1000}s`);
}

export function stopTicker(): void {
  if (timer) clearTimeout(timer);
  timer = null;
}
