jest.mock('electron');
jest.mock('better-sqlite3');
jest.mock('@anthropic-ai/sdk', () => {
  return jest.fn().mockImplementation(() => ({
    messages: {
      create: jest.fn().mockResolvedValue({
        content: [{ text: '{"summary": "Test summary", "tags": ["test"]}' }],
      }),
    },
  }));
});

const db = require('../../src/main/database');
const claude = require('../../src/main/claude');

describe('Claude module', () => {
  beforeAll(() => {
    db.initDatabase();
  });

  describe('generateSummaryAndTags', () => {
    it('should return null when no API key is set', async () => {
      const result = await claude.generateSummaryAndTags('test content');
      expect(result).toBeNull();
    });
  });

  describe('askQuestion', () => {
    it('should throw when no API key is set', async () => {
      await expect(claude.askQuestion('test?', [])).rejects.toThrow(
        'API key not configured'
      );
    });
  });
});
