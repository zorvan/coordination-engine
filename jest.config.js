module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/test/**/*.test.js', '**/?(*.)+(spec|test).js'],
  transform: {
    '^.+\\.ts$': 'ts-jest'
  },
  moduleFileExtensions: ['ts', 'js', 'json'],
  collectCoverageFrom: ['src/**/*.ts', 'src/**/*.js'],
  coverageDirectory: 'coverage',
  testPathIgnorePatterns: ['/node_modules/', '/dist/']
};