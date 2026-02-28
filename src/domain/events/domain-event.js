const { generateEventId, DomainEventType } = require('./event-utils');

class DomainEvent {
  constructor(type, payload, timestamp = new Date()) {
    this.type = type;
    this.payload = payload;
    this.timestamp = timestamp;
    this.id = payload.id || generateEventId();
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
  constructor(id, name, email, avatar, circles = []) {
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
  constructor(id, organizerId, title, description, scheduledTime, durationMinutes, location, participantIds) {
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
  constructor(matchId, confirmedBy, confirmedAt) {
    super(DomainEventType.MATCH_CONFIRMED, { matchId, confirmedBy, confirmedAt }, confirmedAt || new Date());
  }
}

class MatchCompleted extends DomainEvent {
  constructor(matchId, completedBy, completedAt) {
    super(DomainEventType.MATCH_COMPLETED, { matchId, completedBy, completedAt }, completedAt || new Date());
  }
}

class MatchCancelled extends DomainEvent {
  constructor(matchId, cancelledBy, reason, cancelledAt) {
    super(DomainEventType.MATCH_CANCELLED, { matchId, cancelledBy, reason, cancelledAt }, cancelledAt || new Date());
  }
}

class TrustUpdated extends DomainEvent {
  constructor(actorId, trustScore, trustLevel, version, computedAt) {
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
  constructor(identityId, version, validFrom, validTo) {
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
  constructor(ruleId, version, ruleContent, timestamp) {
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

module.exports = {
  DomainEvent,
  ActorCreated,
  MatchCreated,
  MatchConfirmed,
  MatchCompleted,
  MatchCancelled,
  TrustUpdated,
  TemporalIdentityVersioned,
  GovernanceRuleVersioned,
};
