// Server-Sent Events: pushes state / event / whisper messages for one pet.
// EventSource can't send headers, so the token arrives as ?token= (see auth.ts).

import type { FastifyInstance } from 'fastify';
import { petsRepo } from '../repo/pets.js';
import { bus, type ServerMessage } from '../events.js';

export async function streamRoutes(app: FastifyInstance): Promise<void> {
  app.get('/api/stream/:id', (req, reply) => {
    const { id } = req.params as { id: string };
    const pet = petsRepo.get(id);
    if (!pet) {
      reply.code(404).send({ error: 'not found' });
      return;
    }

    reply.raw.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    });
    reply.hijack(); // we own the socket now

    const send = (msg: ServerMessage) => {
      reply.raw.write(`data: ${JSON.stringify(msg)}\n\n`);
    };

    // Initial snapshot so the client renders immediately.
    send({ kind: 'state', pet });

    const unsubscribe = bus.subscribePet(id, send);
    const heartbeat = setInterval(() => reply.raw.write(': ping\n\n'), 25_000);

    const cleanup = () => {
      clearInterval(heartbeat);
      unsubscribe();
      reply.raw.end();
    };
    req.raw.on('close', cleanup);
    req.raw.on('error', cleanup);
  });
}
