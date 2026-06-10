// Deterministic, seedable PRNG. Same seed string => same sequence, forever.
// Used to derive a pet's genome so a seed always renders the identical creature.

/** Hash a string into four 32-bit seeds (cyrb128). */
export function cyrb128(str: string): [number, number, number, number] {
  let h1 = 1779033703;
  let h2 = 3144134277;
  let h3 = 1013904242;
  let h4 = 2773480762;
  for (let i = 0; i < str.length; i++) {
    const k = str.charCodeAt(i);
    h1 = h2 ^ Math.imul(h1 ^ k, 597399067);
    h2 = h3 ^ Math.imul(h2 ^ k, 2869860233);
    h3 = h4 ^ Math.imul(h3 ^ k, 951274213);
    h4 = h1 ^ Math.imul(h4 ^ k, 2716044179);
  }
  h1 = Math.imul(h3 ^ (h1 >>> 18), 597399067);
  h2 = Math.imul(h4 ^ (h2 >>> 22), 2869860233);
  h3 = Math.imul(h1 ^ (h3 >>> 17), 951274213);
  h4 = Math.imul(h2 ^ (h4 >>> 19), 2716044179);
  return [
    (h1 ^ h2 ^ h3 ^ h4) >>> 0,
    (h2 ^ h1) >>> 0,
    (h3 ^ h1) >>> 0,
    (h4 ^ h1) >>> 0,
  ];
}

/** mulberry32 — small, fast 32-bit PRNG returning floats in [0, 1). */
export function mulberry32(a: number): () => number {
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface Rng {
  /** Next float in [0, 1). */
  next(): number;
  /** Float in [min, max). */
  range(min: number, max: number): number;
  /** Integer in [min, max] inclusive. */
  int(min: number, max: number): number;
  /** Pick one element from a non-empty array. */
  pick<T>(items: readonly T[]): T;
}

/** Build a deterministic Rng from a seed string. */
export function makeRng(seed: string): Rng {
  const [s] = cyrb128(seed);
  const rand = mulberry32(s);
  return {
    next: rand,
    range: (min, max) => min + rand() * (max - min),
    int: (min, max) => min + Math.floor(rand() * (max - min + 1)),
    pick: (items) => {
      if (items.length === 0) throw new Error('pick() on empty array');
      return items[Math.floor(rand() * items.length)] as (typeof items)[number];
    },
  };
}

/** Generate a random 128-bit hex seed string (uses Math.random; for creation only). */
export function randomSeed(): string {
  let out = '';
  for (let i = 0; i < 32; i++) {
    out += Math.floor(Math.random() * 16).toString(16);
  }
  return out;
}
