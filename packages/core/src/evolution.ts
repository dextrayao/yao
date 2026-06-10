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

/** Ordered low -> high. */
export const STAGE_GATES: readonly StageGate[] = [
  { stage: 'egg', growth: 0, minAgeMs: 0 },
  { stage: 'wisp', growth: 15, minAgeMs: 2 * HOUR },
  { stage: 'sprite', growth: 35, minAgeMs: 12 * HOUR },
  { stage: 'spirit', growth: 55, minAgeMs: 2 * DAY },
  { stage: 'ethereal', growth: 78, minAgeMs: 5 * DAY },
  { stage: 'transcendent', growth: 95, minAgeMs: 10 * DAY },
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

/** Numeric rank of a stage (egg=0 .. transcendent=5). */
export function stageRank(stage: Stage): number {
  return STAGE_ORDER.indexOf(stage);
}
