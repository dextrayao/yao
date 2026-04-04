module.exports = {
  projects: [
    {
      displayName: 'main',
      testMatch: ['<rootDir>/tests/main/**/*.test.js'],
      testEnvironment: 'node',
      transform: {
        '^.+\\.jsx?$': 'babel-jest',
      },
      transformIgnorePatterns: ['/node_modules/'],
      moduleNameMapper: {
        'better-sqlite3': '<rootDir>/tests/main/__mocks__/better-sqlite3.js',
        electron: '<rootDir>/tests/main/__mocks__/electron.js',
      },
    },
    {
      displayName: 'renderer',
      testMatch: ['<rootDir>/tests/renderer/**/*.test.jsx'],
      testEnvironment: 'jsdom',
      transform: {
        '^.+\\.jsx?$': 'babel-jest',
      },
      transformIgnorePatterns: ['/node_modules/'],
      moduleNameMapper: {
        '\\.css$': '<rootDir>/tests/renderer/__mocks__/styleMock.js',
      },
      setupFilesAfterSetup: ['@testing-library/jest-dom'],
    },
  ],
};
