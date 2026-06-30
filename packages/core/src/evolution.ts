// Stage derivation. A pet reaches a stage only when BOTH its growth and its
// age clear the thresholds — so evolution is earned over real time, not grindable.

import type { Stage } from './types.js';
import { STAGE_ORDER } from './types.js';

const HOUR = 3_600_000;
const DAY = 24 * HOUR;

interface StageGate {
  stage: Stage;
  growth: number; // minimum growth (0..100)
  minAgeMs: number; // minimum age since birth
}

// Ordered low -> high. Early volumes are growth-gated (felt within hours of
// care); later volumes are age-gated (圓 takes ~12 days), so the apex is earned.
export const STAGE_GATES: readonly StageGate[] = [
  { stage: 'egg', growth: 0, minAgeMs: 0 },
  { stage: 'kong', growth: 6, minAgeMs: 1 * HOUR },
  { stage: 'wo', growth: 16, minAgeMs: 5 * HOUR },
  { stage: 'zhi', growth: 30, minAgeMs: 14 * HOUR },
  { stage: 'xi', growth: 46, minAgeMs: 1.5 * DAY },
  { stage: 'shou', growth: 64, minAgeMs: 3 * DAY },
  { stage: 'xing', growth: 82, minAgeMs: 6 * DAY },
  { stage: 'yuan', growth: 96, minAgeMs: 12 * DAY },
];

/** Highest stage whose growth + age gates are both satisfied. */
export function stageFor(growth: number, ageMs: number): Stage {
  let result: Stage = 'egg';
  for (const gate of STAGE_GATES) {
    if (growth >= gate.growth && ageMs >= gate.minAgeMs) {
      result = gate.stage;
    }
  }
  return result;
}

/** Numeric rank of a stage (egg=0 .. yuan=7). */
export function stageRank(stage: Stage): number {
  return STAGE_ORDER.indexOf(stage);
}
