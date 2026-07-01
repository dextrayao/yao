// genome + stage (+ optional live stats) -> a self-contained, animated SVG string.
// Aesthetic: a "quantum world" spirit — a luminous probability-cloud core wrapped
// in tilted electron orbits with travelling nodes, on a transparent background so
// it floats in the page's deep space. Cohesive, designed, non-human, alive.

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
  const half = size / 2;

  const moodFactor = opts.stats ? 0.55 + (opts.stats.mood / 100) * 0.45 : 1;
  const glowOpacity = (0.4 + genome.glowIntensity * 0.4) * moodFactor;
  const bodyBlur = 3 + genome.glowIntensity * 5;

  // Probability cloud — soft nested glows.
  const cloud = shapes.auraRadii
    .map((r, i) => {
      const op = (glowOpacity * (0.5 - i * 0.09)).toFixed(3);
      const dur = (5 + i * 1.4).toFixed(1);
      return `<circle class="aura" cx="0" cy="0" r="${fmt(r)}" fill="url(#cloud-${sid})" opacity="${op}" style="animation-duration:${dur}s"/>`;
    })
    .join('');

  // Electron orbits — tilted elliptical rings, each with a travelling node.
  // Outer static group tilts + flattens a circle into an ellipse; an inner
  // group spins so the node orbits. More orbits appear as the pet matures.
  const orbitCount = expr === 'dissolved' ? 0 : Math.min(4, 2 + Math.floor(rank / 2));
  const orbits: string[] = [];
  for (let i = 0; i < orbitCount; i++) {
    const tilt = (150 / orbitCount) * i + 20;
    const rO = R * (1.35 + i * 0.28);
    const dur = (7 + i * 2.4).toFixed(1);
    const dir = i % 2 === 0 ? 'normal' : 'reverse';
    const node = R * 0.06 + 1.5;
    orbits.push(
      `<g transform="rotate(${tilt.toFixed(1)}) scale(1 0.4)">
        <circle cx="0" cy="0" r="${fmt(rO)}" fill="none" stroke="${pal.glow}" stroke-width="1" opacity="0.22"/>
        <g class="orbit-spin" style="animation-duration:${dur}s;animation-direction:${dir}">
          <circle cx="${fmt(rO)}" cy="0" r="${fmt(node)}" fill="${pal.particle}"/>
        </g>
      </g>`,
    );
  }

  // Quantum motes.
  const particles = shapes.particles
    .map(
      (p) =>
        `<circle cx="${fmt(p.x)}" cy="${fmt(p.y)}" r="${fmt(p.r)}" fill="${pal.particle}" class="mote" style="animation-delay:${p.delay.toFixed(2)}s;animation-duration:${genome.particleSpeed}s"/>`,
    )
    .join('');

  const dissolved = expr === 'dissolved';
  const bodyOpacity = dissolved ? 0.55 : 1;
  const face = renderFace(genome, expr, R, pal);

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" role="img" aria-label="quantum spirit creature">
  <defs>
    <radialGradient id="cloud-${sid}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="${pal.glow}" stop-opacity="0.85"/>
      <stop offset="55%" stop-color="${pal.accent}" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="${pal.glow}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="body-${sid}" cx="42%" cy="38%" r="68%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.95"/>
      <stop offset="30%" stop-color="${pal.core}"/>
      <stop offset="100%" stop-color="${pal.coreEdge}"/>
    </radialGradient>
    <filter id="soft-${sid}" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="${bodyBlur.toFixed(1)}" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <style>
    .aura { animation: aura-pulse ease-in-out infinite alternate; transform-origin:center; }
    .mote { animation: mote-drift ease-in-out infinite alternate; transform-origin:center; }
    .orbit-spin { animation: orbit-spin linear infinite; transform-origin:0 0; }
    .body { animation: body-bob ease-in-out infinite alternate; transform-origin:center; }
    .eyes { animation: blink ease-in-out infinite; transform-origin:center; transform-box:fill-box; }
    @keyframes aura-pulse { from { transform: scale(0.94); } to { transform: scale(1.08); } }
    @keyframes mote-drift { from { transform: translateY(${fmt(-genome.particleDrift * 8)}px); opacity:0.25; } to { transform: translateY(${fmt(genome.particleDrift * 8)}px); opacity:0.85; } }
    @keyframes orbit-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes body-bob { from { transform: translateY(-3px) scale(0.99); } to { transform: translateY(3px) scale(1.01); } }
    @keyframes blink { 0%,92%,100% { transform: scaleY(1); } 96% { transform: scaleY(0.12); } }
    @media (prefers-reduced-motion: reduce) { .aura,.mote,.orbit-spin,.body,.eyes { animation: none !important; } }
  </style>
  <g transform="translate(${half} ${half})">
    ${cloud}
    ${particles}
    ${orbits.join('\n    ')}
    <g class="body" style="animation-duration:4s">
      <path d="${shapes.corePath}" fill="url(#body-${sid})" opacity="${bodyOpacity}" filter="url(#soft-${sid})"/>
      ${face}
    </g>
  </g>
</svg>`;
}
