// Glue between the pure core and the stateful world: advance pets, persist,
// publish to SSE, and fire whispers. Used by both the ticker and HTTP routes.

import { advance, type DimensionEventType, type Pet } from '@yao/core';
import { petsRepo, whispersRepo } from './repo/pets.js';
import { bus } from './events.js';
import { maybeWhisper } from './llm/whisper.js';

/** Generate + persist + broadcast a whisper. Fire-and-forget; never throws. */
export function fireWhisper(pet: Pet, event: DimensionEventType): void {
  void (async () => {
    try {
      const w = await maybeWhisper(pet, event);
      if (!w) return;
      const row = whispersRepo.add(pet.id, w.text, w.source);
      bus.publish({
        kind: 'whisper',
        petId: pet.id,
        text: row.text,
        source: row.source,
        at: row.createdAt,
      });
    } catch {
      /* whispers are decorative — swallow errors */
    }
  })();
}

/** Advance a single pet to now, persist if it moved, broadcast state + events. */
export function advanceAndPersist(pet: Pet, now = Date.now()): Pet {
  const { pet: next, events } = advance(pet, now);
  if (next === pet && events.length === 0) return pet;

  petsRepo.update(next);
  bus.publish({ kind: 'state', pet: next });
  for (const event of events) {
    bus.publish({ kind: 'event', event });
    if (event.type === 'evolve') fireWhisper(next, 'evolve');
  }
  return next;
}

/** Advance every pet (the ticker's per-cycle work). */
export function tickAll(now = Date.now()): void {
  const pets = petsRepo.all();
  const changed: Pet[] = [];
  for (const pet of pets) {
    const { pet: next, events } = advance(pet, now);
    if (next === pet && events.length === 0) continue;
    changed.push(next);
    bus.publish({ kind: 'state', pet: next });
    for (const event of events) {
      bus.publish({ kind: 'event', event });
      if (event.type === 'evolve') fireWhisper(next, 'evolve');
    }
  }
  if (changed.length > 0) petsRepo.updateMany(changed);
}
