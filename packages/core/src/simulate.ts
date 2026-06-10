// The deterministic heart. advance(pet, now) re-derives the pet's state purely
// from elapsed wall-clock time, stepping in fixed 60s increments. Because every
// step is identical in size, advancing 6h in one call equals 360 one-minute
// calls — which is exactly what makes offline catch-up and restart-safety work.

import { deriveGenome } from './genome.js';
import { stageFor, stageRank } from './evolution.js';
import { stepStats } from './stats.js';
import type { DimensionEvent, Pet } from './types.js';

/** Simulation micro-step size. */
export const STEP_MS = 60_000;

/** Cap how much offline time we replay after a long outage. */
export const MAX_OFFLINE_MS = 3 * 24 * 3_600_000;

export interface AdvanceResult {
  pet: Pet;
  events: DimensionEvent[];
}

/**
 * Advance a pet to `now`. Returns a new pet (input is not mutated) plus any
 * events (e.g. stage transitions) that occurred during the elapsed window.
 */
export function advance(pet: Pet, now: number): AdvanceResult {
  const rawElapsed = now - pet.lastTickAt;
  if (rawElapsed < STEP_MS) {
    return { pet, events: [] };
  }

  const capped = rawElapsed > MAX_OFFLINE_MS;
  const elapsed = capped ? MAX_OFFLINE_MS : rawElapsed;
  const steps = Math.floor(elapsed / STEP_MS);

  const genome = deriveGenome(pet.seed);
  let stats = pet.stats;
  for (let i = 0; i < steps; i++) {
    const atMs = pet.lastTickAt + (i + 1) * STEP_MS;
    stats = stepStats(stats, genome, STEP_MS, atMs);
  }

  // When capped we skip the excess outright rather than re-process it later.
  const newLastTickAt = capped ? now : pet.lastTickAt + steps * STEP_MS;

  const newStage = stageFor(stats.growth, now - pet.bornAt);
  const events: DimensionEvent[] = [];
  const mutationLog = pet.mutationLog;
  let nextLog = mutationLog;

  if (stageRank(newStage) > stageRank(pet.stage)) {
    const mutation = { at: now, from: pet.stage, to: newStage };
    nextLog = [...mutationLog, mutation];
    events.push({
      type: 'evolve',
      petId: pet.id,
      dimensionId: pet.dimensionId,
      at: now,
      data: { from: pet.stage, to: newStage },
    });
  }

  const next: Pet = {
    ...pet,
    stats,
    stage: newStage,
    lastTickAt: newLastTickAt,
    mutationLog: nextLog,
  };

  return { pet: next, events };
}
