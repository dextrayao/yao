// One-tap self-update: pull the latest code from GitHub and rebuild the web app,
// so the keeper never needs a terminal again after the first pull. Auth-gated
// (same bearer token as the rest of /api). Rebuilds the FRONTEND (served from
// dist) live; server-logic changes still need a process restart.

import { exec } from 'node:child_process';
import { promisify } from 'node:util';
import type { FastifyInstance } from 'fastify';
import { config } from '../config.js';

const run = promisify(exec);

async function sh(cmd: string, timeoutMs: number): Promise<string> {
  const { stdout, stderr } = await run(cmd, { cwd: config.repoRoot, timeout: timeoutMs });
  return (stdout + stderr).trim();
}

export async function adminRoutes(app: FastifyInstance): Promise<void> {
  app.post('/api/update', async (_req, reply) => {
    try {
      app.log.info('[update] git pull…');
      const pull = await sh('git pull --ff-only', 90_000);
      const already = /Already up to date|Already up-to-date/i.test(pull);
      app.log.info('[update] npm run build…');
      await sh('npm run build', 300_000);
      return { ok: true, updated: !already, pull: pull.slice(-400) };
    } catch (err) {
      app.log.error(err);
      return reply.code(500).send({ ok: false, error: String(err).slice(-600) });
    }
  });
}
