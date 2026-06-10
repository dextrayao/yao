// genome -> color ramp. Ethereal default: luminous, cool-leaning, soft.

import type { Genome } from '../types.js';

export interface Palette {
  void: string; // deep dimension background
  core: string; // body fill
  glow: string; // halo / bloom
  accent: string; // secondary light
  particle: string; // drifting motes
}

const hsl = (h: number, s: number, l: number, a = 1): string =>
  a >= 1 ? `hsl(${h}, ${s}%, ${l}%)` : `hsla(${h}, ${s}%, ${l}%, ${a})`;

export function derivePalette(genome: Genome): Palette {
  const { hue, hueSpread, saturation, lightness, accentHue } = genome;
  return {
    void: hsl((hue + 200) % 360, Math.min(40, saturation * 0.4), 8),
    core: hsl(hue, saturation, lightness),
    glow: hsl((hue + hueSpread / 2) % 360, saturation, Math.min(92, lightness + 15)),
    accent: hsl(accentHue, saturation, Math.min(85, lightness + 8)),
    particle: hsl((hue + hueSpread) % 360, Math.min(70, saturation), 90),
  };
}
