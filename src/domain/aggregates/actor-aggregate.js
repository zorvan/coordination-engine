const TrustLevel = require('../valuables/trust-value').TrustValue;
const computeTrustScore = require('../valuables/trust-value').computeTrustScore;

const ActorAggregate = {
  create(id, name, email, avatar, circles = []) {
    const actor = {
      actorId: id,
      name,
      email,
      avatar,
      circles,
      temporalIdentity: null,
      trustScore: 0,
      trustLevel: TrustLevel.VERY_LOW,
      acceptedMatches: 0,
      completedMatches: 0,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    actor.updateTemporalIdentity = function(state, trustLevel, validFrom, validTo) {
      this.temporalIdentity = {
        state,
        trustLevel,
        validFrom,
        validTo,
      };
      this.updatedAt = new Date();
    };

    actor.incrementAcceptedMatches = function() {
      this.acceptedMatches++;
      this.updatedAt = new Date();
    };

    actor.incrementCompletedMatches = function() {
      this.completedMatches++;
      this.updatedAt = new Date();
    };

    actor.computeTrustScore = function() {
      return computeTrustScore(this.completedMatches, this.acceptedMatches);
    };

    actor.applyTrustUpdate = function(score, level, version, computedAt) {
      this.trustScore = score;
      this.trustLevel = level;
      this.updatedAt = computedAt;
    };

    return actor;
  },
};

module.exports = { ActorAggregate };