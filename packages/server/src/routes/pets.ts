import type { FastifyInstance } from 'fastify';
import {
  clamp,
  createPet,
  deriveGenome,
  randomSeed,
  renderPetSvg,
  type Pet,
  type Stats,
} from '@yao/core';
import { randomUUID } from 'node:crypto';
import { petsRepo, whispersRepo } from '../repo/pets.js';
import { bus } from '../events.js';
import { advanceAndPersist, fireWhisper } from '../service.js';
import { generateName } from '../llm/whisper.js';

const OWNER = 'local'; // v1 single owner

function decorate(pet: Pet) {
  const genome = deriveGenome(pet.seed);
  return {
    pet,
    genome,
    svg: renderPetSvg(genome, pet.stage, { idSuffix: pet.id.slice(0, 8), stats: pet.stats }),
    whispers: whispersRepo.list(pet.id, 20),
  };
}

export async function petRoutes(app: FastifyInstance): Promise<void> {
  // Create a pet
  app.post('/api/pets', async (req) => {
    const body = (req.body ?? {}) as { name?: string; seed?: string };
    const seed = body.seed?.trim() || randomSeed();
    const name = body.name?.trim() || (await generateName(seed));
    const pet = createPet({ id: randomUUID(), seed, name, now: Date.now(), ownerId: OWNER });
    petsRepo.insert(pet);
    fireWhisper(pet, 'hatch');
    return decorate(pet);
  });

  // List this owner's pets
  app.get('/api/pets', async () => {
    return petsRepo.byOwner(OWNER).map((p) => ({
      pet: p,
      svg: renderPetSvg(deriveGenome(p.seed), p.stage, {
        idSuffix: p.id.slice(0, 8),
        stats: p.stats,
      }),
    }));
  });

  // Get one pet (advanced to now)
  app.get('/api/pets/:id', async (req, reply) => {
    const { id } = req.params as { id: string };
    const stored = petsRepo.get(id);
    if (!stored) return reply.code(404).send({ error: 'not found' });
    return decorate(advanceAndPersist(stored));
  });

  // Interact: feed | soothe | observe | rename
  app.post('/api/pets/:id/interact', async (req, reply) => {
    const { id } = req.params as { id: string };
    const body = (req.body ?? {}) as { action?: string; value?: string };
    const stored = petsRepo.get(id);
    if (!stored) return reply.code(404).send({ error: 'not found' });

    const pet = advanceAndPersist(stored);
    const s: Stats = { ...pet.stats };
    let next: Pet = pet;

    switch (body.action) {
      case 'feed':
        s.hunger = clamp(s.hunger - 35);
        s.mood = clamp(s.mood + 5);
        next = { ...pet, stats: s };
        break;
      case 'soothe':
        s.mood = clamp(s.mood + 12);
        s.energy = clamp(s.energy + 5);
        next = { ...pet, stats: s };
        break;
      case 'rename': {
        const name = body.value?.trim();
        if (!name) return reply.code(400).send({ error: 'value required' });
        next = { ...pet, name: name.slice(0, 24) };
        break;
      }
      case 'observe':
        break; // no stat change; just elicits a whisper
      default:
        return reply.code(400).send({ error: 'unknown action' });
    }

    petsRepo.update(next);
    bus.publish({ kind: 'state', pet: next });
    fireWhisper(next, 'interact');
    return decorate(next);
  });
}
