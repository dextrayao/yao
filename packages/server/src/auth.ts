// Minimal access control: loopback requests pass freely (local dev on the Mac);
// anything else (phone over Tailscale/LAN) needs the bearer token. SSE clients
// (EventSource can't set headers) may pass the token as ?token=.
//
// This single-token check is also the seed of the multiplayer ownership model:
// today the token maps to the one owner "local".

import type { FastifyReply, FastifyRequest } from 'fastify';
import { config } from './config.js';

function isLoopback(ip: string): boolean {
  return (
    ip === '127.0.0.1' ||
    ip === '::1' ||
    ip === '::ffff:127.0.0.1' ||
    ip.startsWith('127.')
  );
}

function presentedToken(req: FastifyRequest): string | null {
  const header = req.headers.authorization;
  if (header?.startsWith('Bearer ')) return header.slice(7).trim();
  const q = (req.query as Record<string, unknown> | undefined)?.['token'];
  return typeof q === 'string' ? q : null;
}

/** Fastify preHandler guarding /api routes. */
export function requireAuth(req: FastifyRequest, reply: FastifyReply, done: () => void): void {
  if (isLoopback(req.ip)) return done();

  if (!config.authToken) {
    reply.code(503).send({ error: 'AUTH_TOKEN not configured; remote access disabled' });
    return;
  }
  if (presentedToken(req) === config.authToken) return done();

  reply.code(401).send({ error: 'unauthorized' });
}
