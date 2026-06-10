// Pure stat math. One fixed micro-step at a time so the simulation composes
// exactly: N steps of STEP_MS == one advance over N*STEP_MS.

import type { Genome, Stats } from './types.js';

export const clamp = (v: number, lo = 0, hi = 100): number =>
  v < lo ? lo : v > hi ? hi : v;

/** Linear approach toward target, capped so a single step never overshoots. */
function approach(
  value: number,
  target: number,
  dtHours: number,
  ratePerHour: number,
): number {
  const f = Math.min(1, ratePerHour * dtHours);
  return value + (target - value) * f;
}

// --- tuned rates (per real hour) ---
const HUNGER_PER_HOUR = 6;
/** Baseline growth: the pet matures on its own even if neglected (free growth). */
const GROWTH_BASE_PER_HOUR = 0.5;
/** Extra growth while thriving — care accelerates, never gates, evolution. */
const GROWTH_BONUS_PER_HOUR = 0.9;
const MOOD_RATE = 0.8;
const ENERGY_RATE = 1.2;
const VITALITY_RATE = 0.5;

/** Circadian energy target: low at night (~20), high at midday (~80). */
export function circadianEnergyTarget(atMs: number): number {
  const d = new Date(atMs);
  const dayFraction = (d.getHours() + d.getMinutes() / 60) / 24;
  return 50 + 30 * Math.sin(2 * Math.PI * (dayFraction - 0.25));
}

/** Advance stats by one micro-step. Pure: returns a new Stats object. */
export function stepStats(
  stats: Stats,
  genome: Genome,
  stepMs: number,
  atMs: number,
): Stats {
  const dtH = stepMs / 3_600_000;

  const hunger = clamp(stats.hunger + HUNGER_PER_HOUR * dtH);

  const energyTarget = circadianEnergyTarget(atMs);
  const energy = clamp(approach(stats.energy, energyTarget, dtH, ENERGY_RATE));

  const hungerPenalty = hunger > 60 ? (hunger - 60) * 0.6 : 0;
  const moodTarget = clamp(genome.moodBaseline - hungerPenalty);
  const mood = clamp(approach(stats.mood, moodTarget, dtH, MOOD_RATE));

  const healthy = hunger < 75 && mood > 30;
  const vitalityTarget = healthy ? 100 : 15;
  const vitality = clamp(
    approach(stats.vitality, vitalityTarget, dtH, VITALITY_RATE),
  );

  // Growth is monotonic: a baseline trickle always accrues (autonomous "free
  // growth"), and thriving adds a bonus. Never regresses.
  const thriving = vitality > 50 && mood > 45;
  const growthRate = GROWTH_BASE_PER_HOUR + (thriving ? GROWTH_BONUS_PER_HOUR : 0);
  const growth = clamp(stats.growth + growthRate * dtH);

  return { hunger, mood, energy, vitality, growth };
}

/** Starting stats for a freshly hatched egg. */
export function initialStats(genome: Genome): Stats {
  return {
    hunger: 20,
    mood: genome.moodBaseline,
    energy: 60,
    vitality: 80,
    growth: 0,
  };
}
