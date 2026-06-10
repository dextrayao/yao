// In-process pub/sub bridging the simulation to SSE clients. Keyed by pet (and
// dimension) so the same bus serves single-pet streams now and dimension-wide
// streams when multiplayer arrives.

import { EventEmitter } from 'node:events';
import type { DimensionEvent, Pet } from '@yao/core';

export type ServerMessage =
  | { kind: 'state'; pet: Pet }
  | { kind: 'event'; event: DimensionEvent }
  | { kind: 'whisper'; petId: string; text: string; source: string; at: number };

class Bus {
  private emitter = new EventEmitter();

  constructor() {
    // Many concurrent SSE subscribers are expected.
    this.emitter.setMaxListeners(0);
  }

  publish(msg: ServerMessage): void {
    const petId = msg.kind === 'state' ? msg.pet.id : msg.kind === 'event' ? msg.event.petId : msg.petId;
    this.emitter.emit(`pet:${petId}`, msg);
    this.emitter.emit('all', msg);
  }

  subscribePet(petId: string, listener: (msg: ServerMessage) => void): () => void {
    const channel = `pet:${petId}`;
    this.emitter.on(channel, listener);
    return () => this.emitter.off(channel, listener);
  }
}

export const bus = new Bus();
