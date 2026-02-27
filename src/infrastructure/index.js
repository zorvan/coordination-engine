const PostgresEventStore = require('./event-store').PostgresEventStore;
const PostgresMatchRepository = require('./persistence/match-repository');
const PostgresActorRepository = require('./persistence/actor-repository');
const PostgresTemporalIdentityRepository = require('./persistence/temporal-identity-repository');
const PostgresGovernanceRepository = require('./persistence/governance-repository');
const PostgresTrustProjection = require('./projections/trust-projection');
const PostgresRelationalGraph = require('./projections/relational-graph');
const PostgresFairnessLedger = require('./projections/fairness-ledger');

module.exports = {
  PostgresEventStore,
  PostgresMatchRepository,
  PostgresActorRepository,
  PostgresTemporalIdentityRepository,
  PostgresGovernanceRepository,
  PostgresTrustProjection,
  PostgresRelationalGraph,
  PostgresFairnessLedger
};