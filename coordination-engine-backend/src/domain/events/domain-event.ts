import { generateEventId, DomainEventType } from './event-utils';

type DomainEventTypeValue = (typeof DomainEventType)[keyof typeof DomainEventType];

type DomainPayload = {
  id?: string;
  aggregateId?: string;
  matchId?: string;
  actorId?: string;
  identityId?: string;
  ruleId?: string;
  [key: string]: unknown;
};

class DomainEvent {
  type: DomainEventTypeValue;
  payload: DomainPayload;
  timestamp: Date;
  id: string;
  aggregateId: string | null;

  constructor(type: DomainEventTypeValue, payload: DomainPayload, timestamp: Date = new Date()) {
    this.type = type;
    this.payload = payload;
    this.timestamp = timestamp;
    this.id = typeof payload.id === 'string' ? payload.id : generateEventId();
    this.aggregateId =
      payload.aggregateId ||
      payload.matchId ||
      payload.actorId ||
      payload.identityId ||
      payload.ruleId ||
      payload.id ||
      null;
  }
}

class ActorCreated extends DomainEvent {
  constructor(id: string, name: string, email: string, avatar: string, circles: string[] = []) {
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
    );
  }
}

class MatchCreated extends DomainEvent {
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
    );
  }
}

class MatchConfirmed extends DomainEvent {
  constructor(matchId: string, confirmedBy: string, confirmedAt: Date) {
    super(DomainEventType.MATCH_CONFIRMED, { matchId, confirmedBy, confirmedAt }, confirmedAt || new Date());
  }
}

class MatchCompleted extends DomainEvent {
  constructor(matchId: string, completedBy: string, completedAt: Date) {
    super(DomainEventType.MATCH_COMPLETED, { matchId, completedBy, completedAt }, completedAt || new Date());
  }
}

class MatchCancelled extends DomainEvent {
  constructor(matchId: string, cancelledBy: string, reason: string, cancelledAt: Date) {
    super(DomainEventType.MATCH_CANCELLED, { matchId, cancelledBy, reason, cancelledAt }, cancelledAt || new Date());
  }
}

class TrustUpdated extends DomainEvent {
  constructor(actorId: string, trustScore: number, trustLevel: string, version: number, computedAt: Date) {
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
    );
  }
}

class TemporalIdentityVersioned extends DomainEvent {
  constructor(identityId: string, version: number, validFrom: Date, validTo: Date | null) {
    super(
      DomainEventType.TEMPORAL_IDENTITY_VERSIONED,
      {
        identityId,
        version,
        validFrom,
        validTo,
      },
      validFrom || new Date()
    );
  }
}

class GovernanceRuleVersioned extends DomainEvent {
  constructor(ruleId: string, version: number, ruleContent: string, timestamp: Date) {
    super(
      DomainEventType.GOVERNANCE_RULE_VERSIONED,
      {
        ruleId,
        version,
        ruleContent,
        timestamp,
      },
      timestamp || new Date()
    );
  }
}

export { DomainEvent,
  ActorCreated,
  MatchCreated,
  MatchConfirmed,
  MatchCompleted,
  MatchCancelled,
  TrustUpdated,
  TemporalIdentityVersioned,
  GovernanceRuleVersioned, };
