// genome -> a cohesive, luminous colour ramp. Everything stays in the creature's
// own hue family (only gently shifted) so nothing turns muddy — 空靈 = clean,
// cool, glowing, never a clashing complementary brown.

import type { Genome } from '../types.js';

export interface Palette {
  void: string; // deep dimension background (used only for soft fades)
  core: string; // body fill (center)
  coreEdge: string; // body fill (edge) — gives depth
  glow: string; // halo / bloom
  accent: string; // subtle secondary light
  particle: string; // drifting motes
}

const hsl = (h: number, s: number, l: number, a = 1): string =>
  a >= 1 ? `hsl(${h}, ${s}%, ${l}%)` : `hsla(${h}, ${s}%, ${l}%, ${a})`;

export function derivePalette(genome: Genome): Palette {
  const { lightness, saturation } = genome;
  // Remap the seed's hue into a cohesive cool-electric "quantum" band
  // (cyan → blue → indigo → violet). Every creature still differs, but the
  // family reads as designed — never acid-green or muddy brown.
  const norm = (((genome.hue % 360) + 360) % 360) / 360;
  const hue = 186 + norm * 116; // 186..302
  const s = Math.min(78, Math.max(52, saturation + 6)); // vivid but elegant
  const l = Math.max(60, lightness);

  return {
    void: hsl(hue, 30, 7),
    core: hsl(hue, s, Math.min(74, l + 4)),
    coreEdge: hsl((hue + 14) % 360, Math.min(85, s + 8), Math.max(46, l - 16)),
    glow: hsl((hue + 6) % 360, Math.min(88, s + 10), Math.min(90, l + 22)),
    accent: hsl((hue + 30) % 360, s, Math.min(84, l + 12)),
    particle: hsl((hue + 16) % 360, 48, 94),
  };
}
