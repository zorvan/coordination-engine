const {
  DomainEventType,
  generateEventId,
  generateEventStreamId,
  generateAggregateId,
} = require('../../../src/domain/events/event-utils');

describe('event-utils', () => {
  test('DomainEventType constants are defined', () => {
    expect(DomainEventType.ACTOR_CREATED).toBe('ActorCreated');
    expect(DomainEventType.MATCH_CREATED).toBe('MatchCreated');
    expect(DomainEventType.MATCH_CONFIRMED).toBe('MatchConfirmed');
    expect(DomainEventType.MATCH_COMPLETED).toBe('MatchCompleted');
    expect(DomainEventType.MATCH_CANCELLED).toBe('MatchCancelled');
    expect(DomainEventType.TRUST_UPDATED).toBe('TrustUpdated');
    expect(DomainEventType.TEMPORAL_IDENTITY_VERSIONED).toBe('TemporalIdentityVersioned');
    expect(DomainEventType.GOVERNANCE_RULE_VERSIONED).toBe('GovernanceRuleVersioned');
  });

  test('generateEventId returns valid UUID v4', () => {
    const eventId = generateEventId();
    expect(eventId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  });

  test('generateEventId generates unique IDs', () => {
    const id1 = generateEventId();
    const id2 = generateEventId();
    expect(id1).not.toBe(id2);
  });

  test('generateEventStreamId creates proper format', () => {
    const streamId = generateEventStreamId('Match', 'match-123');
    expect(streamId).toBe('Match:match-123');
  });

  test('generateEventStreamId works with multiple aggregate types', () => {
    expect(generateEventStreamId('Actor', 'actor-1')).toBe('Actor:actor-1');
    expect(generateEventStreamId('Match', 'match-2')).toBe('Match:match-2');
    expect(generateEventStreamId('TemporalIdentity', 'identity-3')).toBe('TemporalIdentity:identity-3');
  });

  test('generateAggregateId returns valid UUID v4', () => {
    const aggregateId = generateAggregateId();
    expect(aggregateId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  });

  test('generateAggregateId generates unique IDs', () => {
    const id1 = generateAggregateId();
    const id2 = generateAggregateId();
    expect(id1).not.toBe(id2);
  });
});
