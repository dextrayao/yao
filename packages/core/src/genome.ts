// seed -> Genome. The draw ORDER here is part of the contract: never reorder
// these calls, or existing seeds would render as different creatures.

import { makeRng } from './rng.js';
import type { BodyForm, EyeStyle, Genome, MouthStyle } from './types.js';

const BODY_FORMS: readonly BodyForm[] = [
  'orb',
  'crystalline',
  'tendril',
  'feathered',
  'nebula',
];

// Weighted toward round eyes / smiles so creatures read as cute, not uncanny.
const EYE_STYLES: readonly EyeStyle[] = ['round', 'round', 'round', 'sleepy', 'star', 'dot'];
const MOUTH_STYLES: readonly MouthStyle[] = ['smile', 'smile', 'cat', 'dot', 'none'];

const PERSONALITIES: readonly string[] = [
  'serene and contemplative',
  'curious and drifting',
  'shy, hides in its own glow',
  'playful, chases stray light',
  'ancient and knowing',
  'melancholic but gentle',
  'radiant and generous',
  'quiet, speaks in fragments',
];

/**
 * Derive a pet's immutable visual + temperamental DNA from its seed.
 * Pure and deterministic: deriveGenome(s) always returns the same Genome.
 */
export function deriveGenome(seed: string): Genome {
  const rng = makeRng(seed);

  // --- draw order is FROZEN below ---
  const hue = Math.floor(rng.range(0, 360));
  const hueSpread = Math.floor(rng.range(20, 120));
  const saturation = Math.floor(rng.range(45, 85));
  const lightness = Math.floor(rng.range(55, 80));
  const accentHue = (hue + Math.floor(rng.range(120, 240))) % 360;
  const bodyForm = rng.pick(BODY_FORMS);
  const symmetry = rng.int(2, 8);
  const auraLayers = rng.int(1, 4);
  const glowIntensity = Number(rng.range(0.4, 1).toFixed(3));
  const particleCount = rng.int(12, 60);
  const particleSpeed = Number(rng.range(6, 18).toFixed(2));
  const particleDrift = Number(rng.range(0.2, 0.8).toFixed(3));

  const coreShape: number[] = [];
  for (let i = 0; i < symmetry; i++) {
    coreShape.push(Number(rng.range(0.7, 1.3).toFixed(3)));
  }

  const moodBaseline = Math.floor(rng.range(40, 70));
  const personality = rng.pick(PERSONALITIES);

  // --- cute facial DNA appended AFTER the frozen draws above ---
  const eyeStyle = rng.pick(EYE_STYLES);
  const eyeSize = Number(rng.range(0.85, 1.35).toFixed(3));
  const eyeSpacing = Number(rng.range(0.85, 1.25).toFixed(3));
  const mouthStyle = rng.pick(MOUTH_STYLES);
  const cheeks = rng.next() < 0.7;

  return {
    hue,
    hueSpread,
    saturation,
    lightness,
    accentHue,
    bodyForm,
    symmetry,
    auraLayers,
    glowIntensity,
    particleCount,
    particleSpeed,
    particleDrift,
    coreShape,
    moodBaseline,
    personality,
    eyeStyle,
    eyeSize,
    eyeSpacing,
    mouthStyle,
    cheeks,
  };
}
