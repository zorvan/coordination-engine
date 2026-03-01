/**
 * Domain event utilities for event-sourced domain.
 * 
 * Design decisions:
 * - Using Web Crypto API for UUID generation (browser-compatible)
 * - DomainEventType: Centralized event type constants for consistency
 * - generateEventStreamId: Format for event sourcing aggregate streams
 * - All functions are pure and testable
 */

/**
 * Domain event type constants for consistency across the application.
 * 
 * Design decisions:
 * - Centralized event type definitions
 * - TypeScript const assertion for type safety
 */
export const DomainEventType = {
  ACTOR_CREATED: 'ActorCreated',
  MATCH_CREATED: 'MatchCreated',
  MATCH_CONFIRMED: 'MatchConfirmed',
  MATCH_COMPLETED: 'MatchCompleted',
  MATCH_CANCELLED: 'MatchCancelled',
  TRUST_UPDATED: 'TrustUpdated',
  TEMPORAL_IDENTITY_VERSIONED: 'TemporalIdentityVersioned',
  GOVERNANCE_RULE_VERSIONED: 'GovernanceRuleVersioned',
} as const

/**
 * Generate a unique event ID using UUID v4.
 * 
 * This uses the Web Crypto API which is available in modern browsers.
 * 
 * @returns UUID v4 formatted event ID
 */
export function generateEventId(): string {
  return crypto.randomUUID()
}

/**
 * Generate an event stream ID for an aggregate.
 * 
 * Format: {aggregateType}:{aggregateId}
 * Example: Match:123e4567-e89b-12d3-a456-426614174000
 * 
 * @param aggregateType - Type of aggregate (e.g., 'Match', 'Actor')
 * @param aggregateId - Unique aggregate identifier
 * @returns Event stream ID
 */
export function generateEventStreamId(aggregateType: string, aggregateId: string): string {
  return `${aggregateType}:${aggregateId}`
}

/**
 * Generate a unique aggregate ID using UUID v4.
 * 
 * @returns UUID v4 formatted aggregate ID
 */
export function generateAggregateId(): string {
  return crypto.randomUUID()
}

// Re-export DomainEventType for backward compatibility (internal use only)
// This is a duplicate export, removed for TypeScript strictness