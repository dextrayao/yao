// genome + stage -> geometry. Deterministic: same inputs, same shapes.

import { makeRng } from '../rng.js';
import { stageRank } from '../evolution.js';
import type { Genome, Stage } from '../types.js';

export interface Particle {
  x: number;
  y: number;
  r: number;
  delay: number; // animation offset (s)
}

export interface ShapeData {
  /** SVG path "d" for the core blob, centered at (0,0). */
  corePath: string;
  /** Aura ring radii. */
  auraRadii: number[];
  particles: Particle[];
  /** 0..1 — how fully the form is "expressed" at this stage. */
  expression: number;
  /** Core blob radius — used to place the face. */
  baseRadius: number;
}

/** Smooth closed blob path through points sampled around the center. */
function blobPath(radii: number[], baseRadius: number): string {
  const n = radii.length;
  if (n < 3) {
    // too few points to form a blob — fall back to a circle-ish square path
    const r = baseRadius;
    return `M ${-r} 0 A ${r} ${r} 0 1 0 ${r} 0 A ${r} ${r} 0 1 0 ${-r} 0 Z`;
  }
  const pts = radii.map((mult, i) => {
    const a = (i / n) * Math.PI * 2 - Math.PI / 2;
    const r = baseRadius * mult;
    return [Math.cos(a) * r, Math.sin(a) * r] as const;
  });
  // Catmull-Rom -> cubic Bézier for an organic closed curve.
  let d = `M ${pts[0]![0].toFixed(2)} ${pts[0]![1].toFixed(2)}`;
  for (let i = 0; i < n; i++) {
    const p0 = pts[(i - 1 + n) % n]!;
    const p1 = pts[i]!;
    const p2 = pts[(i + 1) % n]!;
    const p3 = pts[(i + 2) % n]!;
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C ${c1x.toFixed(2)} ${c1y.toFixed(2)}, ${c2x.toFixed(2)} ${c2y.toFixed(2)}, ${p2[0].toFixed(2)} ${p2[1].toFixed(2)}`;
  }
  return d + ' Z';
}

export function deriveShapes(genome: Genome, stage: Stage, viewSize = 320): ShapeData {
  const rank = stageRank(stage); // 0..5
  const expression = 0.35 + (rank / 7) * 0.65; // 卵 small, 圓 full
  const baseRadius = (viewSize * 0.16) * (0.7 + expression * 0.6);

  const corePath = blobPath(genome.coreShape, baseRadius);

  const auraRadii: number[] = [];
  for (let i = 0; i < genome.auraLayers; i++) {
    auraRadii.push(baseRadius * (1.4 + i * 0.55) * (0.8 + expression * 0.4));
  }

  // Particles appear from the 'wisp' stage onward, scaling with expression.
  const rng = makeRng(genome.coreShape.join(',') + ':particles');
  const count = rank === 0 ? 0 : Math.round(genome.particleCount * expression);
  const particles: Particle[] = [];
  const field = viewSize * 0.42;
  for (let i = 0; i < count; i++) {
    const a = rng.range(0, Math.PI * 2);
    const dist = Math.sqrt(rng.next()) * field;
    particles.push({
      x: Math.cos(a) * dist,
      y: Math.sin(a) * dist,
      r: rng.range(0.6, 2.4),
      delay: rng.range(0, genome.particleSpeed),
    });
  }

  return { corePath, auraRadii, particles, expression, baseRadius };
}
