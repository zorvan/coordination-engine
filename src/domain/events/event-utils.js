const crypto = require('crypto');

const DomainEventType = {
  ACTOR_CREATED: 'ActorCreated',
  MATCH_CREATED: 'MatchCreated',
  MATCH_CONFIRMED: 'MatchConfirmed',
  MATCH_COMPLETED: 'MatchCompleted',
  MATCH_CANCELLED: 'MatchCancelled',
  TRUST_UPDATED: 'TrustUpdated',
  TEMPORAL_IDENTITY_VERSIONED: 'TemporalIdentityVersioned',
  GOVERNANCE_RULE_VERSIONED: 'GovernanceRuleVersioned',
};

const generateEventId = () => crypto.randomUUID();

const generateEventStreamId = (aggregateType, aggregateId) => {
  return `${aggregateType}:${aggregateId}`;
};

const generateAggregateId = () => crypto.randomUUID();

module.exports = {
  DomainEventType,
  generateEventId,
  generateEventStreamId,
  generateAggregateId,
};