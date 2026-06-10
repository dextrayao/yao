// Pet creation. Pure factory — given a seed and identity, returns a fresh egg.

import { deriveGenome } from './genome.js';
import { initialStats } from './stats.js';
import type { Pet } from './types.js';

export interface CreatePetInput {
  id: string;
  seed: string;
  name: string;
  now: number;
  ownerId?: string;
  dimensionId?: string;
}

export function createPet(input: CreatePetInput): Pet {
  const genome = deriveGenome(input.seed);
  return {
    id: input.id,
    ownerId: input.ownerId ?? 'local',
    dimensionId: input.dimensionId ?? 'default',
    name: input.name,
    seed: input.seed,
    bornAt: input.now,
    lastTickAt: input.now,
    stats: initialStats(genome),
    stage: 'egg',
    mutationLog: [],
    personalityHint: genome.personality,
  };
}
