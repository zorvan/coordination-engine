const { PostgresEventStore } = require('./event-store');
const PostgresMatchRepository = require('./match-repository');
const PostgresActorRepository = require('./actor-repository');
const PostgresTemporalIdentityRepository = require('./temporal-identity-repository');
const PostgresGovernanceRepository = require('./governance-repository');

module.exports = {
  PostgresEventStore,
  PostgresMatchRepository,
  PostgresActorRepository,
  PostgresTemporalIdentityRepository,
  PostgresGovernanceRepository
};