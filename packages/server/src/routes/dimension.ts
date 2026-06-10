// Multiplayer-reserved endpoints. v1 implements only the single default
// dimension; the shapes exist now so going multiplayer is data, not a rewrite.

import type { FastifyInstance } from 'fastify';
import { deriveGenome, renderPetSvg } from '@yao/core';
import { petsRepo } from '../repo/pets.js';

export async function dimensionRoutes(app: FastifyInstance): Promise<void> {
  app.get('/api/dimensions/:dimId', async (req) => {
    const { dimId } = req.params as { dimId: string };
    return { id: dimId, name: '空靈次元', mode: 'single-player' };
  });

  app.get('/api/dimensions/:dimId/pets', async (req) => {
    const { dimId } = req.params as { dimId: string };
    return petsRepo.byDimension(dimId).map((p) => ({
      pet: p,
      svg: renderPetSvg(deriveGenome(p.seed), p.stage, {
        idSuffix: p.id.slice(0, 8),
        stats: p.stats,
      }),
    }));
  });

  // Reserved, not yet implemented in v1.
  app.post('/api/pets/:id/co-raise', async (_req, reply) =>
    reply.code(501).send({ error: 'co-raise not implemented in v1' }),
  );

  app.post('/api/dimensions/:dimId/pets/:id/gesture', async () => ({ ok: true, noop: true }));
}
