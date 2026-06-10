// Shared domain types for 空靈次元. Pure data — no behaviour, no IO.

/** Life stages, ordered from birth (egg) to apex (transcendent). */
export type Stage =
  | 'egg'
  | 'wisp'
  | 'sprite'
  | 'spirit'
  | 'ethereal'
  | 'transcendent';

export const STAGE_ORDER: readonly Stage[] = [
  'egg',
  'wisp',
  'sprite',
  'spirit',
  'ethereal',
  'transcendent',
];

/** All stats live on a 0..100 scale. */
export interface Stats {
  /** 0 = sated, 100 = starving. Rises with time. */
  hunger: number;
  /** Emotional state. */
  mood: number;
  /** Follows a day/night circadian rhythm. */
  energy: number;
  /** Survival floor. Low vitality => dormant/slumbering, never permadeath. */
  vitality: number;
  /** Monotonic progress that drives evolution. */
  growth: number;
}

export type BodyForm =
  | 'orb'
  | 'crystalline'
  | 'tendril'
  | 'feathered'
  | 'nebula';

/** Deterministic visual DNA derived from a seed. Never changes over a pet's life. */
export interface Genome {
  hue: number; // 0..360
  hueSpread: number; // palette width in degrees
  saturation: number; // 0..100
  lightness: number; // 0..100
  accentHue: number; // 0..360
  bodyForm: BodyForm;
  symmetry: number; // 2..8 radial copies
  auraLayers: number; // 1..4
  glowIntensity: number; // 0..1
  particleCount: number;
  particleSpeed: number; // seconds per drift cycle
  particleDrift: number; // 0..1 drift amplitude
  /** Radii multipliers for the deterministic core blob (one per symmetry point). */
  coreShape: number[];
  /** Baseline mood the pet drifts toward when content. */
  moodBaseline: number; // 0..100
  /** One-line personality descriptor fed to the LLM. */
  personality: string;
}

export interface MutationEvent {
  at: number; // epoch ms
  from: Stage;
  to: Stage;
}

export interface Pet {
  id: string;
  ownerId: string; // "local" in v1; reserved for multiplayer
  dimensionId: string; // "default" in v1; reserved
  name: string;
  seed: string; // immutable hex DNA
  bornAt: number; // epoch ms
  lastTickAt: number; // epoch ms; advances each tick
  stats: Stats;
  stage: Stage;
  mutationLog: MutationEvent[];
  personalityHint: string;
}

export type DimensionEventType =
  | 'hatch'
  | 'evolve'
  | 'mood_drift'
  | 'interact';

export interface DimensionEvent {
  type: DimensionEventType;
  petId: string;
  dimensionId: string;
  at: number;
  data?: Record<string, unknown>;
}
