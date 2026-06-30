import { describe, it, expect } from 'vitest';
import {
  advance,
  createPet,
  deriveGenome,
  expressionFor,
  renderPetSvg,
  stageFor,
  STEP_MS,
  type Pet,
  type Stats,
} from '../src/index.js';

const T0 = 1_700_000_000_000; // fixed epoch for reproducible tests

function freshPet(seed = 'seed-alpha'): Pet {
  return createPet({ id: 'pet1', seed, name: 'Test', now: T0 });
}

describe('genome', () => {
  it('is deterministic for a given seed', () => {
    expect(deriveGenome('abc')).toEqual(deriveGenome('abc'));
  });

  it('differs across seeds', () => {
    expect(deriveGenome('abc')).not.toEqual(deriveGenome('xyz'));
  });
});

describe('simulate composition (offline catch-up == stepwise)', () => {
  it('advancing 6h in one call equals 360 one-minute calls', () => {
    const sixHours = 360 * STEP_MS;

    const single = advance(freshPet(), T0 + sixHours).pet;

    let stepwise = freshPet();
    for (let i = 0; i < 360; i++) {
      stepwise = advance(stepwise, stepwise.lastTickAt + STEP_MS).pet;
    }

    expect(single.lastTickAt).toBe(stepwise.lastTickAt);
    expect(single.stats).toEqual(stepwise.stats);
    expect(single.stage).toBe(stepwise.stage);
  });

  it('does not advance for sub-step elapsed', () => {
    const r = advance(freshPet(), T0 + STEP_MS - 1);
    expect(r.events).toHaveLength(0);
    expect(r.pet.lastTickAt).toBe(T0);
  });

  it('leaves sub-minute remainder on lastTickAt', () => {
    const r = advance(freshPet(), T0 + STEP_MS + 5_000);
    expect(r.pet.lastTickAt).toBe(T0 + STEP_MS);
  });
});

describe('evolution', () => {
  it('gates stages on both growth and age (seven volumes)', () => {
    const DAY = 24 * 3_600_000;
    expect(stageFor(0, 0)).toBe('egg');
    expect(stageFor(20, 60_000)).toBe('egg'); // growth ok, too young
    expect(stageFor(20, 3 * 3_600_000)).toBe('kong'); // 空
    expect(stageFor(100, 13 * DAY)).toBe('yuan'); // 圓 apex
    expect(stageFor(100, 11 * DAY)).toBe('xing'); // 圓 needs 12d; gated at 行
    expect(stageFor(50, 11 * DAY)).toBe('xi'); // 戲 — age ok, growth gates
  });

  it('emits an evolve event when a pet ages enough to grow', () => {
    // Fast-forward well past the wisp gate; a cared-for pet should evolve.
    const r = advance(freshPet(), T0 + 20 * 3_600_000);
    expect(r.pet.stage).not.toBe('egg');
    expect(r.events.some((e) => e.type === 'evolve')).toBe(true);
    expect(r.pet.mutationLog.length).toBeGreaterThan(0);
  });
});

describe('render', () => {
  it('produces a self-contained svg string', () => {
    const svg = renderPetSvg(deriveGenome('seed-alpha'), 'shou');
    expect(svg.startsWith('<svg')).toBe(true);
    expect(svg).toContain('</svg>');
    expect(svg).toContain('<path');
  });

  it('draws a face for non-egg stages, none at 圓 (dissolved)', () => {
    const g = deriveGenome('seed-alpha');
    expect(renderPetSvg(g, 'xi', { stats: { hunger: 10, mood: 80, energy: 70, vitality: 90, growth: 50 } })).toContain('class="face"');
    expect(renderPetSvg(g, 'yuan')).not.toContain('class="face"'); // 筆下無人
  });
});

describe('expressionFor', () => {
  const s = (mood: number, energy: number): Stats => ({ hunger: 0, mood, energy, vitality: 90, growth: 50 });
  it('maps stage + stats to a cute expression', () => {
    expect(expressionFor('egg')).toBe('sleeping');
    expect(expressionFor('yuan')).toBe('dissolved');
    expect(expressionFor('wo', s(80, 70))).toBe('happy');
    expect(expressionFor('wo', s(50, 20))).toBe('sleepy');
    expect(expressionFor('wo', s(20, 70))).toBe('sad');
    expect(expressionFor('wo', s(50, 70))).toBe('content');
  });
});
