// SQLite connection + schema. Synchronous (better-sqlite3) so DB writes inside
// the tick loop never interleave with HTTP handlers.

import fs from 'node:fs';
import path from 'node:path';
import Database from 'better-sqlite3';
import { config } from './config.js';

fs.mkdirSync(path.dirname(config.dbPath), { recursive: true });

export const db = new Database(config.dbPath);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
  CREATE TABLE IF NOT EXISTS pets (
    id            TEXT PRIMARY KEY,
    owner_id      TEXT NOT NULL,
    dimension_id  TEXT NOT NULL,
    data          TEXT NOT NULL,          -- full Pet JSON
    updated_at    INTEGER NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_pets_owner ON pets(owner_id);
  CREATE INDEX IF NOT EXISTS idx_pets_dimension ON pets(dimension_id);

  CREATE TABLE IF NOT EXISTS whispers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id      TEXT NOT NULL,
    text        TEXT NOT NULL,
    source      TEXT NOT NULL,            -- 'llm' | 'template'
    created_at  INTEGER NOT NULL,
    FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE
  );
  CREATE INDEX IF NOT EXISTS idx_whispers_pet ON whispers(pet_id, created_at);
`);
