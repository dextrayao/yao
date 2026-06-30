// The cute face: big eyes, expression driven by live stats, blush, mouth.
// Pure SVG-string output, sized relative to the body radius R.
//
// The 圓 (yuan) apex returns 'dissolved' — the face fades to pure light,
// embodying 《空靈經》卷七: 「筆下無人，而畫自畫」.

import type { Genome, Stage, Stats } from '../types.js';
import { derivePalette, type Palette } from './palette.js';

export type Expression =
  | 'sleeping' // unhatched egg
  | 'sleepy' // low energy
  | 'happy' // high mood
  | 'content' // default
  | 'sad' // low mood
  | 'dissolved'; // 圓 — face returns to emptiness

/** Pure: choose an expression from stage + live stats. */
export function expressionFor(stage: Stage, stats?: Stats): Expression {
  if (stage === 'egg') return 'sleeping';
  if (stage === 'yuan') return 'dissolved';
  if (!stats) return 'content';
  if (stats.energy < 30) return 'sleepy';
  if (stats.mood > 65) return 'happy';
  if (stats.mood < 30) return 'sad';
  return 'content';
}

const f = (n: number): string => Number(n.toFixed(2)).toString();
const EYE_INK = '#0c0c16';

function openEye(
  cx: number,
  ey: number,
  er: number,
  style: Genome['eyeStyle'],
  lowered: boolean,
): string {
  const hi = `<circle cx="${f(cx - er * 0.3)}" cy="${f(ey - er * 0.32 + (lowered ? er * 0.2 : 0))}" r="${f(er * 0.32)}" fill="#fff" opacity="0.95"/>` +
    `<circle cx="${f(cx + er * 0.22)}" cy="${f(ey + er * 0.18)}" r="${f(er * 0.13)}" fill="#fff" opacity="0.75"/>`;
  switch (style) {
    case 'dot':
      return `<circle cx="${f(cx)}" cy="${f(ey)}" r="${f(er * 0.6)}" fill="${EYE_INK}"/>${hi}`;
    case 'star': {
      // simple 4-point sparkle
      const s = er * 1.05;
      const d = `M ${f(cx)} ${f(ey - s)} L ${f(cx + s * 0.28)} ${f(ey - s * 0.28)} L ${f(cx + s)} ${f(ey)} L ${f(cx + s * 0.28)} ${f(ey + s * 0.28)} L ${f(cx)} ${f(ey + s)} L ${f(cx - s * 0.28)} ${f(ey + s * 0.28)} L ${f(cx - s)} ${f(ey)} L ${f(cx - s * 0.28)} ${f(ey - s * 0.28)} Z`;
      return `<path d="${d}" fill="${EYE_INK}"/><circle cx="${f(cx - er * 0.25)}" cy="${f(ey - er * 0.25)}" r="${f(er * 0.22)}" fill="#fff" opacity="0.9"/>`;
    }
    case 'round':
    case 'sleepy':
    default:
      return `<circle cx="${f(cx)}" cy="${f(ey)}" r="${f(er)}" fill="${EYE_INK}"/>${hi}`;
  }
}

/** Render the face group (eyes + cheeks + mouth) for a body of radius R. */
export function renderFace(
  genome: Genome,
  expression: Expression,
  R: number,
  pal: Palette = derivePalette(genome),
): string {
  if (expression === 'dissolved') return ''; // 圓: no face — pure light

  const ey = -R * 0.12;
  const ex = R * 0.42 * genome.eyeSpacing;
  const er = R * 0.19 * genome.eyeSize;
  const ink = EYE_INK;
  const stroke = (d: string, w: number) =>
    `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(w)}" stroke-linecap="round"/>`;

  // --- eyes ---
  let eyes: string;
  let openEyes = false;
  if (expression === 'happy') {
    // closed joyful arcs  ∩ ∩
    const arc = (cx: number) =>
      stroke(`M ${f(cx - er)} ${f(ey + er * 0.2)} Q ${f(cx)} ${f(ey - er * 0.9)} ${f(cx + er)} ${f(ey + er * 0.2)}`, er * 0.32);
    eyes = arc(-ex) + arc(ex);
  } else if (expression === 'sleeping' || expression === 'sleepy') {
    // gentle closed ∪ ∪
    const arc = (cx: number) =>
      stroke(`M ${f(cx - er)} ${f(ey)} Q ${f(cx)} ${f(ey + er * 0.55)} ${f(cx + er)} ${f(ey)}`, er * 0.28);
    eyes = arc(-ex) + arc(ex);
  } else {
    // open eyes (content / sad)
    const lowered = expression === 'sad';
    eyes = openEye(-ex, ey, er, genome.eyeStyle, lowered) + openEye(ex, ey, er, genome.eyeStyle, lowered);
    openEyes = true;
    if (expression === 'sad') {
      // worried inner brows
      eyes =
        stroke(`M ${f(-ex - er * 0.8)} ${f(ey - er * 1.4)} L ${f(-ex + er * 0.2)} ${f(ey - er * 0.9)}`, er * 0.16) +
        stroke(`M ${f(ex + er * 0.8)} ${f(ey - er * 1.4)} L ${f(ex - er * 0.2)} ${f(ey - er * 0.9)}`, er * 0.16) +
        eyes;
    }
  }

  // --- cheeks (cute blush) ---
  let cheeks = '';
  if (genome.cheeks && (expression === 'happy' || expression === 'content')) {
    const cy = R * 0.14;
    const cx = R * 0.52;
    const blush = (x: number) =>
      `<ellipse cx="${f(x)}" cy="${f(cy)}" rx="${f(R * 0.14)}" ry="${f(R * 0.09)}" fill="${pal.accent}" opacity="0.45"/>`;
    cheeks = blush(-cx) + blush(cx);
  }

  // --- mouth ---
  let mouth = '';
  const my = R * 0.32;
  if (expression === 'happy') {
    mouth = stroke(`M ${f(-R * 0.18)} ${f(my - R * 0.02)} Q ${f(0)} ${f(my + R * 0.16)} ${f(R * 0.18)} ${f(my - R * 0.02)}`, R * 0.035);
  } else if (expression === 'sad') {
    mouth = stroke(`M ${f(-R * 0.13)} ${f(my + R * 0.04)} Q ${f(0)} ${f(my - R * 0.08)} ${f(R * 0.13)} ${f(my + R * 0.04)}`, R * 0.03);
  } else if (expression === 'content') {
    switch (genome.mouthStyle) {
      case 'smile':
        mouth = stroke(`M ${f(-R * 0.11)} ${f(my)} Q ${f(0)} ${f(my + R * 0.09)} ${f(R * 0.11)} ${f(my)}`, R * 0.03);
        break;
      case 'cat':
        mouth =
          stroke(`M ${f(-R * 0.12)} ${f(my)} Q ${f(-R * 0.06)} ${f(my + R * 0.07)} ${f(0)} ${f(my)}`, R * 0.028) +
          stroke(`M ${f(0)} ${f(my)} Q ${f(R * 0.06)} ${f(my + R * 0.07)} ${f(R * 0.12)} ${f(my)}`, R * 0.028);
        break;
      case 'dot':
        mouth = `<circle cx="0" cy="${f(my)}" r="${f(R * 0.035)}" fill="${ink}"/>`;
        break;
      case 'none':
      default:
        mouth = '';
    }
  }
  // sleeping/sleepy: no mouth (peaceful)

  const blinkClass = openEyes ? ' class="eyes"' : '';
  return `<g class="face"><g${blinkClass}>${eyes}</g>${cheeks}${mouth}</g>`;
}
