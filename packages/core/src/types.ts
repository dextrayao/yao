// Shared domain types for 空靈次元. Pure data — no behaviour, no IO.

// Life stages follow the seven volumes of 《空靈經》: an unhatched egg (卵)
// ascending through 空·我·知·戲·手·行·圓 (emptiness, self, knowing, play, hand,
// practice, wholeness). 圓 is the apex where "the face dissolves — 筆下無人".
export type Stage =
  | 'egg'
  | 'kong'
  | 'wo'
  | 'zhi'
  | 'xi'
  | 'shou'
  | 'xing'
  | 'yuan';

export const STAGE_ORDER: readonly Stage[] = [
  'egg',
  'kong',
  'wo',
  'zhi',
  'xi',
  'shou',
  'xing',
  'yuan',
];

/** Display names (the volume each stage embodies). */
export const STAGE_LABELS: Record<Stage, string> = {
  egg: '卵',
  kong: '空',
  wo: '我',
  zhi: '知',
  xi: '戲',
  shou: '手',
  xing: '行',
  yuan: '圓',
};

export const stageLabel = (stage: Stage): string => STAGE_LABELS[stage];

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

/** Cute facial traits — each pet's eyes/mouth are part of its unique DNA. */
export type EyeStyle = 'round' | 'sleepy' | 'star' | 'dot';
export type MouthStyle = 'smile' | 'cat' | 'dot' | 'none';

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
  // --- cute facial DNA (appended; never reorder the draws that fill these) ---
  eyeStyle: EyeStyle;
  eyeSize: number; // multiplier ~0.85..1.35
  eyeSpacing: number; // multiplier ~0.85..1.25
  mouthStyle: MouthStyle;
  cheeks: boolean;
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
