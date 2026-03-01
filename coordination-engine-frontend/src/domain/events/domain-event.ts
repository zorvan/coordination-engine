/**
 * Base domain event class.
 * 
 * All domain events extend this class, providing a consistent structure
 * for event sourcing and audit trails.
 * 
 * Design decisions:
 * - Base class with common properties (id, type, payload, timestamp)
 * - Automatic event ID generation if not provided
 * - Flexible aggregate ID extraction from payload
 */

/**
 * Base domain event class for event sourcing.
 * 
 * This class provides the foundational structure for all domain events,
 * ensuring consistency across the event-sourced system.
 */

import { generateEventId, DomainEventType } from './event-utils'
export { DomainEventType } from './event-utils'

export class DomainEvent {
  /**
   * Create a new domain event.
   * 
   * @param type - Event type (e.g., 'MatchCreated')
   * @param payload - Event payload with aggregate-specific data
   * @param timestamp - Event timestamp (default: now)
   */
  constructor(
    public type: string,
    public payload: Record<string, unknown>,
    public timestamp: Date = new Date()
  ) {
    const payloadId = typeof payload.id === 'string' ? payload.id : undefined
    this.id = payloadId ?? generateEventId()
    this.aggregateId = this.extractAggregateId(payload)
  }

  /**
   * Unique event identifier.
   */
  id: string

  /**
   * ID of the aggregate this event belongs to.
   */
  aggregateId: string | null

  /**
   * Extract aggregate ID from payload.
   * 
   * This method tries multiple common payload field names to find
   * the aggregate ID, making the class flexible for different event types.
   * 
   * @param payload - Event payload
   * @returns Aggregate ID or null if not found
   */
  private extractAggregateId(payload: Record<string, unknown>): string | null {
    const candidateKeys = ['aggregateId', 'matchId', 'actorId', 'identityId', 'ruleId', 'id'] as const
    for (const key of candidateKeys) {
      const value = payload[key]
      if (typeof value === 'string') {
        return value
      }
    }
    return (
      null
    ) as string | null
  }
}

/**
 * Actor created event.
 * 
 * Fired when a new actor is registered in the system.
 */
export class ActorCreated extends DomainEvent {
  /**
   * Create an actor created event.
   * 
   * @param id - Actor ID
   * @param name - Actor name
   * @param email - Actor email
   * @param avatar - Actor avatar URL
   * @param circles - Circles the actor belongs to
   */
  constructor(
    id: string,
    name: string,
    email: string,
    avatar: string,
    circles: string[] = []
  ) {
    super(
      DomainEventType.ACTOR_CREATED,
      {
        id,
        name,
        email,
        avatar,
        circles,
      },
      new Date()
    )
  }
}

/**
 * Match created event.
 * 
 * Fired when a new match is created.
 */
export class MatchCreated extends DomainEvent {
  /**
   * Create a match created event.
   * 
   * @param id - Match ID
   * @param organizerId - Organizer actor ID
   * @param title - Match title
   * @param description - Match description
   * @param scheduledTime - When the match is scheduled
   * @param durationMinutes - Duration in minutes
   * @param location - Physical or virtual location
   * @param participantIds - Array of participant actor IDs
   */
  constructor(
    id: string,
    organizerId: string,
    title: string,
    description: string,
    scheduledTime: Date,
    durationMinutes: number,
    location: string,
    participantIds: string[]
  ) {
    super(
      DomainEventType.MATCH_CREATED,
      {
        id,
        organizerId,
        title,
        description,
        scheduledTime,
        durationMinutes,
        location,
        participantIds,
      },
      new Date()
    )
  }
}

/**
 * Match confirmed event.
 * 
 * Fired when a match is confirmed by organizer or participant.
 */
export class MatchConfirmed extends DomainEvent {
  /**
   * Create a match confirmed event.
   * 
   * @param matchId - Match ID
   * @param confirmedBy - Actor ID confirming the match
   * @param confirmedAt - Timestamp of confirmation
   */
  constructor(matchId: string, confirmedBy: string, confirmedAt: Date) {
    super(
      DomainEventType.MATCH_CONFIRMED,
      { matchId, confirmedBy, confirmedAt },
      confirmedAt || new Date()
    )
  }
}

/**
 * Match completed event.
 * 
 * Fired when a match is completed.
 */
export class MatchCompleted extends DomainEvent {
  /**
   * Create a match completed event.
   * 
   * @param matchId - Match ID
   * @param completedBy - Actor ID completing the match
   * @param completedAt - Timestamp of completion
   */
  constructor(matchId: string, completedBy: string, completedAt: Date) {
    super(
      DomainEventType.MATCH_COMPLETED,
      { matchId, completedBy, completedAt },
      completedAt || new Date()
    )
  }
}

/**
 * Match cancelled event.
 * 
 * Fired when a match is cancelled.
 */
export class MatchCancelled extends DomainEvent {
  /**
   * Create a match cancelled event.
   * 
   * @param matchId - Match ID
   * @param cancelledBy - Actor ID cancelling the match
   * @param reason - Cancellation reason
   * @param cancelledAt - Timestamp of cancellation
   */
  constructor(
    matchId: string,
    cancelledBy: string,
    reason: string,
    cancelledAt: Date
  ) {
    super(
      DomainEventType.MATCH_CANCELLED,
      { matchId, cancelledBy, reason, cancelledAt },
      cancelledAt || new Date()
    )
  }
}

/**
 * Trust updated event.
 * 
 * Fired when an actor's trust score or level changes.
 */
export class TrustUpdated extends DomainEvent {
  /**
   * Create a trust updated event.
   * 
   * @param actorId - Actor ID
   * @param trustScore - New trust score
   * @param trustLevel - New trust level
   * @param version - Version number
   * @param computedAt - Timestamp of computation
   */
  constructor(
    actorId: string,
    trustScore: number,
    trustLevel: string,
    version: number,
    computedAt: Date
  ) {
    super(
      DomainEventType.TRUST_UPDATED,
      {
        actorId,
        trustScore,
        trustLevel,
        version,
        computedAt,
      },
      computedAt || new Date()
    )
  }
}

/**
 * Temporal identity versioned event.
 * 
 * Fired when an actor's temporal identity is versioned.
 */
export class TemporalIdentityVersioned extends DomainEvent {
  /**
   * Create a temporal identity versioned event.
   * 
   * @param identityId - Identity ID
   * @param version - Version number
   * @param validFrom - When version becomes active
   * @param validTo - When version expires
   */
  constructor(identityId: string, version: number, validFrom: Date, validTo?: Date) {
    super(
      DomainEventType.TEMPORAL_IDENTITY_VERSIONED,
      {
        identityId,
        version,
        validFrom,
        validTo,
      },
      validFrom || new Date()
    )
  }
}

/**
 * Governance rule versioned event.
 * 
 * Fired when a governance rule is versioned.
 */
export class GovernanceRuleVersioned extends DomainEvent {
  /**
   * Create a governance rule versioned event.
   * 
   * @param ruleId - Rule ID
   * @param version - Version number
   * @param ruleContent - Rule configuration
   * @param timestamp - Timestamp
   */
  constructor(
    ruleId: string,
    version: number,
    ruleContent: Record<string, unknown>,
    timestamp: Date
  ) {
    super(
      DomainEventType.GOVERNANCE_RULE_VERSIONED,
      {
        ruleId,
        version,
        ruleContent,
        timestamp,
      },
      timestamp || new Date()
    )
  }
}
