// Fastify bootstrap: one process serving the API, SSE, the static PWA, and the
// 24/7 ticker. Binds 0.0.0.0 so the phone (LAN / Tailscale) can reach it.

import fs from 'node:fs';
import Fastify from 'fastify';
import fastifyStatic from '@fastify/static';
import { config } from './config.js';
import { db } from './db.js';
import { requireAuth } from './auth.js';
import { petRoutes } from './routes/pets.js';
import { streamRoutes } from './routes/stream.js';
import { dimensionRoutes } from './routes/dimension.js';
import { startTicker, stopTicker } from './ticker.js';
import { tickAll } from './service.js';
import { whisperProvider } from './llm/whisper.js';

const app = Fastify({ logger: { level: 'info' }, trustProxy: true });

// Guard every /api route. Static assets (the PWA shell) need no token.
app.addHook('onRequest', (req, reply, done) => {
  if (req.url.startsWith('/api/')) return requireAuth(req, reply, done);
  done();
});

await app.register(petRoutes);
await app.register(streamRoutes);
await app.register(dimensionRoutes);

app.get('/api/health', async () => ({
  ok: true,
  llm: { provider: whisperProvider.name, available: await whisperProvider.available() },
}));

// Serve the built PWA if present; otherwise a friendly placeholder.
if (fs.existsSync(config.webDist)) {
  await app.register(fastifyStatic, { root: config.webDist });
  app.setNotFoundHandler((req, reply) => {
    if (req.url.startsWith('/api/')) return reply.code(404).send({ error: 'not found' });
    return reply.sendFile('index.html'); // SPA fallback
  });
} else {
  app.get('/', async (_req, reply) => {
    reply.type('text/html').send(
      `<!doctype html><meta charset=utf8><title>空靈次元</title>
       <body style="font-family:system-ui;background:#0a0a12;color:#cdd;padding:2rem">
       <h1>空靈次元</h1>
       <p>Backend is running. Build the web app: <code>npm run build</code>, then reload.</p>
       <p>API health: <a style="color:#9df" href="/api/health">/api/health</a></p>`,
    );
  });
}

async function shutdown(signal: string): Promise<void> {
  app.log.info(`${signal} received — shutting down`);
  stopTicker();
  try {
    tickAll(); // final catch-up so lastTickAt is current
  } catch (err) {
    app.log.error(err);
  }
  await app.close();
  db.close();
  process.exit(0);
}
process.on('SIGINT', () => void shutdown('SIGINT'));
process.on('SIGTERM', () => void shutdown('SIGTERM'));

try {
  await app.listen({ port: config.port, host: config.host });
  startTicker();
  app.log.info(`空靈次元 listening on http://${config.host}:${config.port}`);
} catch (err) {
  app.log.error(err);
  process.exit(1);
}
