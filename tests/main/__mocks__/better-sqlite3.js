// Mock better-sqlite3 for unit tests
class MockStatement {
  constructor() {
    this.rows = [];
  }
  run(...args) {
    return { changes: 1, lastInsertRowid: 1 };
  }
  get(...args) {
    return this.rows[0] || null;
  }
  all(...args) {
    return this.rows;
  }
}

class MockDatabase {
  constructor() {
    this.statements = {};
    this.execCalls = [];
  }
  pragma() {}
  exec(sql) {
    this.execCalls.push(sql);
  }
  prepare(sql) {
    const stmt = new MockStatement();
    this.statements[sql] = stmt;
    return stmt;
  }
}

module.exports = function(path) {
  return new MockDatabase();
};
module.exports.MockDatabase = MockDatabase;
module.exports.MockStatement = MockStatement;
