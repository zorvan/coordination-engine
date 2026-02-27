const PostgresActorRepository = require('./actor-repository');
const PostgresTemporalIdentityRepository = require('./temporal-identity-repository');
const PostgresGovernanceRepository = require('./governance-repository');

module.exports = {
  PostgresActorRepository,
  PostgresTemporalIdentityRepository,
  PostgresGovernanceRepository
};