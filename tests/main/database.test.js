const path = require('path');

// database.js requires electron's app.getPath, so we mock it
jest.mock('electron');
jest.mock('better-sqlite3');

const db = require('../../src/main/database');

describe('Database module', () => {
  beforeAll(() => {
    db.initDatabase();
  });

  describe('initDatabase', () => {
    it('should initialize without throwing', () => {
      expect(() => db.initDatabase()).not.toThrow();
    });

    it('should return a database instance', () => {
      const result = db.initDatabase();
      expect(result).toBeDefined();
    });
  });

  describe('getDb', () => {
    it('should return the database after init', () => {
      expect(() => db.getDb()).not.toThrow();
      expect(db.getDb()).toBeDefined();
    });
  });

  describe('createNote', () => {
    it('should create a note and return an id', () => {
      const id = db.createNote('Test note content');
      expect(id).toBeDefined();
    });

    it('should handle empty string gracefully', () => {
      // The DB itself allows empty strings (NOT NULL doesn't prevent '')
      expect(() => db.createNote('')).not.toThrow();
    });
  });

  describe('updateNoteSummary', () => {
    it('should update without throwing', () => {
      expect(() => db.updateNoteSummary(1, 'Test summary')).not.toThrow();
    });
  });

  describe('getAllNotes', () => {
    it('should return an array', () => {
      const notes = db.getAllNotes();
      expect(Array.isArray(notes)).toBe(true);
    });
  });

  describe('getNotesByTag', () => {
    it('should return an array', () => {
      const notes = db.getNotesByTag('test');
      expect(Array.isArray(notes)).toBe(true);
    });
  });

  describe('searchNotes', () => {
    it('should return an array', () => {
      const notes = db.searchNotes('test');
      expect(Array.isArray(notes)).toBe(true);
    });
  });

  describe('deleteNote', () => {
    it('should delete without throwing', () => {
      expect(() => db.deleteNote(1)).not.toThrow();
    });
  });

  describe('Tags', () => {
    it('addTagToNote should not throw', () => {
      expect(() => db.addTagToNote(1, 'test-tag')).not.toThrow();
    });

    it('setNoteTags should not throw', () => {
      expect(() => db.setNoteTags(1, ['tag1', 'tag2'])).not.toThrow();
    });

    it('getAllTags should return an array', () => {
      const tags = db.getAllTags();
      expect(Array.isArray(tags)).toBe(true);
    });
  });

  describe('Settings', () => {
    it('setSetting should not throw', () => {
      expect(() => db.setSetting('test_key', 'test_value')).not.toThrow();
    });

    it('getSetting should return null for missing key', () => {
      const result = db.getSetting('nonexistent');
      expect(result).toBeNull();
    });
  });
});
