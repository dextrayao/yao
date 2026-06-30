// genome + stage (+ optional live stats) -> a self-contained, animated SVG string.
// Composition: void → aura → particles → rotating petal halo (behind) → upright
// bobbing body + cute face (front). Runs identically on server and browser.

import { derivePalette } from './palette.js';
import { deriveShapes } from './shapes.js';
import { expressionFor, renderFace } from './face.js';
import { stageRank } from '../evolution.js';
import type { Genome, Stage, Stats } from '../types.js';

export interface RenderOptions {
  size?: number;
  /** Suffix to keep SVG element ids unique when several render on one page. */
  idSuffix?: string;
  /** Live stats drive the facial expression + glow; omit for a neutral portrait. */
  stats?: Stats;
}

const fmt = (n: number): string => n.toFixed(2);

export function renderPetSvg(
  genome: Genome,
  stage: Stage,
  opts: RenderOptions = {},
): string {
  const size = opts.size ?? 320;
  const sid = opts.idSuffix ?? 'p';
  const pal = derivePalette(genome);
  const shapes = deriveShapes(genome, stage, size);
  const rank = stageRank(stage);
  const R = shapes.baseRadius;
  const expr = expressionFor(stage, opts.stats);

  const moodFactor = opts.stats ? 0.5 + (opts.stats.mood / 100) * 0.5 : 1;
  const glowOpacity = (0.35 + genome.glowIntensity * 0.5) * moodFactor;
  const blur = 6 + genome.glowIntensity * 14 + rank * 1.2;
  const half = size / 2;

  const auras = shapes.auraRadii
    .map((r, i) => {
      const op = (glowOpacity * (0.5 - i * 0.08)).toFixed(3);
      const dur = (5 + i * 1.3).toFixed(1);
      return `<circle class="aura" cx="0" cy="0" r="${fmt(r)}" fill="url(#glow-${sid})" opacity="${op}" style="animation-duration:${dur}s"/>`;
    })
    .join('');

  // Rotating petal halo behind the body: the genome's radial symmetry, now a
  // slowly-turning ring of soft petals rather than a spinning mandala.
  const petals: string[] = [];
  const petalR = R * 1.15;
  const petalOp = (0.1 + shapes.expression * 0.16).toFixed(3);
  for (let i = 0; i < genome.symmetry; i++) {
    const angle = (360 / genome.symmetry) * i;
    petals.push(
      `<g transform="rotate(${angle.toFixed(1)}) translate(0 ${fmt(-petalR)})"><path d="${shapes.corePath}" transform="scale(0.42)" fill="url(#glow-${sid})" opacity="${petalOp}"/></g>`,
    );
  }
  const haloDur = (50 - rank * 4).toFixed(0);

  const particles = shapes.particles
    .map(
      (p) =>
        `<circle cx="${fmt(p.x)}" cy="${fmt(p.y)}" r="${fmt(p.r)}" fill="${pal.particle}" class="mote" style="animation-delay:${p.delay.toFixed(2)}s;animation-duration:${genome.particleSpeed}s"/>`,
    )
    .join('');

  // Upright body. 圓 (dissolved) softens toward pure light: 「筆下無人」.
  const dissolved = expr === 'dissolved';
  const bodyOpacity = dissolved ? 0.5 : 0.95;
  const face = renderFace(genome, expr, R, pal);

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" role="img" aria-label="ethereal spirit creature">
  <defs>
    <radialGradient id="void-${sid}" cx="50%" cy="48%" r="65%">
      <stop offset="0%" stop-color="${pal.accent}" stop-opacity="0.18"/>
      <stop offset="60%" stop-color="${pal.void}" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="${pal.void}"/>
    </radialGradient>
    <radialGradient id="glow-${sid}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="${pal.glow}" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="${pal.glow}" stop-opacity="0"/>
    </radialGradient>
    <filter id="bloom-${sid}" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="${blur.toFixed(1)}" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <style>
    .aura { animation: aura-pulse ease-in-out infinite alternate; transform-origin:center; }
    .mote { animation: mote-drift ease-in-out infinite alternate; transform-origin:center; }
    .halo { animation: halo-spin linear infinite; transform-origin:center; }
    .body { animation: body-bob ease-in-out infinite alternate; transform-origin:center; }
    .eyes { animation: blink ease-in-out infinite; transform-origin:center; transform-box:fill-box; }
    @keyframes aura-pulse { from { transform: scale(0.95); } to { transform: scale(1.06); } }
    @keyframes mote-drift { from { transform: translateY(${fmt(-genome.particleDrift * 10)}px); opacity:0.3; } to { transform: translateY(${fmt(genome.particleDrift * 10)}px); opacity:0.9; } }
    @keyframes halo-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes body-bob { from { transform: translateY(-2.5px); } to { transform: translateY(2.5px); } }
    @keyframes blink { 0%,92%,100% { transform: scaleY(1); } 96% { transform: scaleY(0.1); } }
    @media (prefers-reduced-motion: reduce) { .aura,.mote,.halo,.body,.eyes { animation: none !important; } }
  </style>
  <rect x="0" y="0" width="${size}" height="${size}" fill="url(#void-${sid})"/>
  <g transform="translate(${half} ${half})">
    ${auras}
    ${particles}
    <g class="halo" style="animation-duration:${haloDur}s">
      ${petals.join('\n      ')}
    </g>
    <g class="body" style="animation-duration:4s">
      <path d="${shapes.corePath}" fill="${pal.core}" opacity="${bodyOpacity}" filter="url(#bloom-${sid})"/>
      ${face}
    </g>
  </g>
</svg>`;
}
