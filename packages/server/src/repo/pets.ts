// Pet + whisper persistence. Pets are stored as JSON blobs with indexed
// owner/dimension columns, so going multiplayer later is a query change.

import type { Pet } from '@yao/core';
import { db } from '../db.js';

const insertStmt = db.prepare(
  `INSERT INTO pets (id, owner_id, dimension_id, data, updated_at)
   VALUES (@id, @ownerId, @dimensionId, @data, @updatedAt)`,
);
const updateStmt = db.prepare(
  `UPDATE pets SET owner_id=@ownerId, dimension_id=@dimensionId, data=@data, updated_at=@updatedAt WHERE id=@id`,
);
const getStmt = db.prepare(`SELECT data FROM pets WHERE id = ?`);
const byOwnerStmt = db.prepare(
  `SELECT data FROM pets WHERE owner_id = ? ORDER BY updated_at DESC`,
);
const byDimensionStmt = db.prepare(
  `SELECT data FROM pets WHERE dimension_id = ? ORDER BY updated_at DESC`,
);
const allStmt = db.prepare(`SELECT data FROM pets`);

const parse = (row: { data: string } | undefined): Pet | null =>
  row ? (JSON.parse(row.data) as Pet) : null;

function rowFor(pet: Pet) {
  return {
    id: pet.id,
    ownerId: pet.ownerId,
    dimensionId: pet.dimensionId,
    data: JSON.stringify(pet),
    updatedAt: Date.now(),
  };
}

export const petsRepo = {
  insert(pet: Pet): void {
    insertStmt.run(rowFor(pet));
  },
  update(pet: Pet): void {
    updateStmt.run(rowFor(pet));
  },
  get(id: string): Pet | null {
    return parse(getStmt.get(id) as { data: string } | undefined);
  },
  byOwner(ownerId: string): Pet[] {
    return (byOwnerStmt.all(ownerId) as { data: string }[]).map(
      (r) => JSON.parse(r.data) as Pet,
    );
  },
  byDimension(dimensionId: string): Pet[] {
    return (byDimensionStmt.all(dimensionId) as { data: string }[]).map(
      (r) => JSON.parse(r.data) as Pet,
    );
  },
  all(): Pet[] {
    return (allStmt.all() as { data: string }[]).map(
      (r) => JSON.parse(r.data) as Pet,
    );
  },
  /** Persist many pets in one transaction (used by the ticker). */
  updateMany: db.transaction((pets: Pet[]) => {
    for (const pet of pets) updateStmt.run(rowFor(pet));
  }),
};

export interface WhisperRow {
  id: number;
  petId: string;
  text: string;
  source: string;
  createdAt: number;
}

const insertWhisper = db.prepare(
  `INSERT INTO whispers (pet_id, text, source, created_at) VALUES (?, ?, ?, ?)`,
);
const listWhispers = db.prepare(
  `SELECT id, pet_id as petId, text, source, created_at as createdAt
   FROM whispers WHERE pet_id = ? ORDER BY created_at DESC LIMIT ?`,
);
const trimWhispers = db.prepare(
  `DELETE FROM whispers WHERE pet_id = ? AND id NOT IN (
     SELECT id FROM whispers WHERE pet_id = ? ORDER BY created_at DESC LIMIT ?
   )`,
);

const WHISPER_KEEP = 50;

export const whispersRepo = {
  add(petId: string, text: string, source: string): WhisperRow {
    const at = Date.now();
    const info = insertWhisper.run(petId, text, source, at);
    trimWhispers.run(petId, petId, WHISPER_KEEP);
    return { id: Number(info.lastInsertRowid), petId, text, source, createdAt: at };
  },
  list(petId: string, limit = 20): WhisperRow[] {
    return listWhispers.all(petId, limit) as WhisperRow[];
  },
};
