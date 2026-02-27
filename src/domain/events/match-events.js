const TRUST_FORMULA_VERSION = '1.0';

const MatchCreatedEvent = function(eventId, aggregateId, timestamp, payload) {
  return {
    id: eventId,
    aggregateId: aggregateId,
    type: 'MatchCreated',
    timestamp: timestamp,
    payload: payload
  };
};

const MatchConfirmedEvent = function(eventId, aggregateId, timestamp, payload) {
  return {
    id: eventId,
    aggregateId: aggregateId,
    type: 'MatchConfirmed',
    timestamp: timestamp,
    payload: payload
  };
};

const MatchCompletedEvent = function(eventId, aggregateId, timestamp, payload) {
  return {
    id: eventId,
    aggregateId: aggregateId,
    type: 'MatchCompleted',
    timestamp: timestamp,
    payload: payload
  };
};

const MatchCancelledEvent = function(eventId, aggregateId, timestamp, payload) {
  return {
    id: eventId,
    aggregateId: aggregateId,
    type: 'MatchCancelled',
    timestamp: timestamp,
    payload: payload
  };
};

const TrustScoreUpdatedEvent = function(eventId, aggregateId, timestamp, payload) {
  return {
    id: eventId,
    aggregateId: aggregateId,
    type: 'TrustScoreUpdated',
    timestamp: timestamp,
    payload: payload
  };
};

const RelationalEdgeCreatedEvent = function(eventId, aggregateId, timestamp, payload) {
  return {
    id: eventId,
    aggregateId: aggregateId,
    type: 'RelationalEdgeCreated',
    timestamp: timestamp,
    payload: payload
  };
};

const IdentityVersionedEvent = function(eventId, aggregateId, timestamp, payload) {
  return {
    id: eventId,
    aggregateId: aggregateId,
    type: 'IdentityVersioned',
    timestamp: timestamp,
    payload: payload
  };
};

const RoleHalfLifeEvent = function(eventId, aggregateId, timestamp, payload) {
  return {
    id: eventId,
    aggregateId: aggregateId,
    type: 'RoleHalfLife',
    timestamp: timestamp,
    payload: payload
  };
};

const GovernanceRuleVersionedEvent = function(eventId, aggregateId, timestamp, payload) {
  return {
    id: eventId,
    aggregateId: aggregateId,
    type: 'GovernanceRuleVersioned',
    timestamp: timestamp,
    payload: payload
  };
};

module.exports = {
  TRUST_FORMULA_VERSION,
  MatchCreatedEvent,
  MatchConfirmedEvent,
  MatchCompletedEvent,
  MatchCancelledEvent,
  TrustScoreUpdatedEvent,
  RelationalEdgeCreatedEvent,
  IdentityVersionedEvent,
  RoleHalfLifeEvent,
  GovernanceRuleVersionedEvent
};