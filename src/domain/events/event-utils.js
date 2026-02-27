const crypto = require('crypto');

/**
 * Event utilities for event-sourced domain
 * 
 * Design decisions:
 * - Use crypto.randomUUID() for proper UUID v4 generation
 * - DomainEventType: Centralized event type constants for consistency
 * - generateEventStreamId: Format for event sourcing aggregate streams
 * - All functions are pure and testable
 */

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

/**
 * Generate a unique event ID using UUID v4
 * 
 * @returns {string} UUID v4 formatted event ID
 */
const generateEventId = () => crypto.randomUUID();

/**
 * Generate an event stream ID for an aggregate
 * 
 * Format: {aggregateType}:{aggregateId}
 * Example: Match:123e4567-e89b-12d3-a456-426614174000
 * 
 * @param {string} aggregateType - Type of aggregate (e.g., 'Match', 'Actor')
 * @param {string} aggregateId - Unique aggregate identifier
 * @returns {string} Event stream ID
 */
const generateEventStreamId = (aggregateType, aggregateId) => {
  return `${aggregateType}:${aggregateId}`;
};

/**
 * Generate a unique aggregate ID using UUID v4
 * 
 * @returns {string} UUID v4 formatted aggregate ID
 */
const generateAggregateId = () => crypto.randomUUID();

module.exports = {
  DomainEventType,
  generateEventId,
  generateEventStreamId,
  generateAggregateId,
};