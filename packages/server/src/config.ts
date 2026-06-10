// Runtime configuration, loaded from environment (.env at repo root).

import { fileURLToPath } from 'node:url';
import path from 'node:path';
import dotenv from 'dotenv';

// repo root = packages/server/src -> ../../../
const REPO_ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../../',
);

dotenv.config({ path: path.join(REPO_ROOT, '.env') });

function resolvePath(p: string): string {
  return path.isAbsolute(p) ? p : path.resolve(REPO_ROOT, p);
}

export const config = {
  repoRoot: REPO_ROOT,
  port: Number(process.env.PORT ?? 4711),
  host: process.env.HOST ?? '0.0.0.0',
  dbPath: resolvePath(process.env.DB_PATH ?? './data/ethereal.db'),
  authToken: process.env.AUTH_TOKEN ?? '',
  ollamaUrl: process.env.OLLAMA_URL ?? 'http://localhost:11434',
  ollamaModel: process.env.OLLAMA_MODEL ?? 'qwen2.5',
  whisperEnabled: (process.env.WHISPER_ENABLED ?? '1') !== '0',
  /** Directory of built web assets to serve (packages/web/dist). */
  webDist: path.join(REPO_ROOT, 'packages/web/dist'),
} as const;
