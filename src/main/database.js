const path = require('path');
const Database = require('better-sqlite3');
const { app } = require('electron');

let db;

function getDbPath() {
  const userDataPath = app.getPath('userData').replace(/[^/]+$/, 'noted');
  return path.join(userDataPath, 'noted.db');
}

function ensureDir(dirPath) {
  const fs = require('fs');
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function initDatabase() {
  const dbPath = getDbPath();
  ensureDir(path.dirname(dbPath));

  db = new Database(dbPath);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  db.exec(`
    CREATE TABLE IF NOT EXISTS notes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      content TEXT NOT NULL,
      summary TEXT DEFAULT '',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tags (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS note_tags (
      note_id INTEGER NOT NULL,
      tag_id INTEGER NOT NULL,
      PRIMARY KEY (note_id, tag_id),
      FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
      FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
      content,
      summary,
      content_rowid='id'
    );

    -- Triggers to keep FTS in sync
    CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
      INSERT INTO notes_fts(rowid, content, summary)
      VALUES (new.id, new.content, new.summary);
    END;

    CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
      UPDATE notes_fts SET content = new.content, summary = new.summary
      WHERE rowid = new.id;
    END;

    CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
      DELETE FROM notes_fts WHERE rowid = old.id;
    END;
  `);

  return db;
}

function getDb() {
  if (!db) throw new Error('Database not initialized');
  return db;
}

// --- Notes ---

function createNote(content) {
  const db = getDb();
  const stmt = db.prepare('INSERT INTO notes (content) VALUES (?)');
  const result = stmt.run(content);
  return result.lastInsertRowid;
}

function updateNoteSummary(noteId, summary) {
  const db = getDb();
  db.prepare('UPDATE notes SET summary = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?')
    .run(summary, noteId);
}

function getAllNotes() {
  const db = getDb();
  const notes = db.prepare(`
    SELECT n.*, GROUP_CONCAT(t.name) as tags
    FROM notes n
    LEFT JOIN note_tags nt ON n.id = nt.note_id
    LEFT JOIN tags t ON nt.tag_id = t.id
    GROUP BY n.id
    ORDER BY n.created_at DESC
  `).all();
  return notes.map(n => ({ ...n, tags: n.tags ? n.tags.split(',') : [] }));
}

function getNotesByTag(tagName) {
  const db = getDb();
  const notes = db.prepare(`
    SELECT n.*, GROUP_CONCAT(t2.name) as tags
    FROM notes n
    JOIN note_tags nt ON n.id = nt.note_id
    JOIN tags t ON nt.tag_id = t.id
    LEFT JOIN note_tags nt2 ON n.id = nt2.note_id
    LEFT JOIN tags t2 ON nt2.tag_id = t2.id
    WHERE t.name = ?
    GROUP BY n.id
    ORDER BY n.created_at DESC
  `).all(tagName);
  return notes.map(n => ({ ...n, tags: n.tags ? n.tags.split(',') : [] }));
}

function searchNotes(query) {
  const db = getDb();
  const notes = db.prepare(`
    SELECT n.*, GROUP_CONCAT(t.name) as tags
    FROM notes n
    JOIN notes_fts fts ON n.id = fts.rowid
    LEFT JOIN note_tags nt ON n.id = nt.note_id
    LEFT JOIN tags t ON nt.tag_id = t.id
    WHERE notes_fts MATCH ?
    GROUP BY n.id
    ORDER BY rank
  `).all(query);
  return notes.map(n => ({ ...n, tags: n.tags ? n.tags.split(',') : [] }));
}

function deleteNote(noteId) {
  const db = getDb();
  db.prepare('DELETE FROM notes WHERE id = ?').run(noteId);
}

// --- Tags ---

function addTagToNote(noteId, tagName) {
  const db = getDb();
  const tag = db.prepare('INSERT OR IGNORE INTO tags (name) VALUES (?)').run(tagName);
  const tagRow = db.prepare('SELECT id FROM tags WHERE name = ?').get(tagName);
  db.prepare('INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)')
    .run(noteId, tagRow.id);
}

function setNoteTags(noteId, tagNames) {
  const db = getDb();
  db.prepare('DELETE FROM note_tags WHERE note_id = ?').run(noteId);
  for (const name of tagNames) {
    addTagToNote(noteId, name);
  }
}

function getAllTags() {
  const db = getDb();
  return db.prepare(`
    SELECT t.name, COUNT(nt.note_id) as count
    FROM tags t
    JOIN note_tags nt ON t.id = nt.tag_id
    GROUP BY t.id
    ORDER BY count DESC
  `).all();
}

// --- Settings ---

function getSetting(key) {
  const db = getDb();
  const row = db.prepare('SELECT value FROM settings WHERE key = ?').get(key);
  return row ? row.value : null;
}

function setSetting(key, value) {
  const db = getDb();
  db.prepare('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)').run(key, value);
}

module.exports = {
  initDatabase,
  getDb,
  createNote,
  updateNoteSummary,
  getAllNotes,
  getNotesByTag,
  searchNotes,
  deleteNote,
  addTagToNote,
  setNoteTags,
  getAllTags,
  getSetting,
  setSetting,
};
