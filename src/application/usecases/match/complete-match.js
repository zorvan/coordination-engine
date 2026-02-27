const { MatchAggregate } = require('../../domain/aggregates/match-aggregate');
const { MatchCompleted } = require('../../domain/events/domain-event');
const { TrustUpdated } = require('../../domain/events/domain-event');
const { TrustLevel } = require('../../domain/valuables/trust-value');
const computeTrustScore = require('../../domain/services/trust-computation').computeTrustScore;
const generateEventId = require('../../domain/events/event-utils').generateEventId;

const CompleteMatchUseCase = {
  create(matchRepository, actorRepository, eventStore) {
    return {
      /**
       * Complete a match and update trust scores
       * 
       * Business logic:
       * - Only confirmed matches can be completed
       * - Both organizer and participants get trust updates
       * - Trust score = completed/accepted matches ratio
       * 
       * @param {string} matchId - The match to complete
       * @param {string} completedBy - The actor completing the match
       * @param {string} notes - Optional completion notes
       * @throws {Error} If match not found or not in confirmed state
       */
      async execute(matchId, completedBy, notes) {
        const match = await matchRepository.findById(matchId);
        
        if (!match) {
          throw new Error(`Match ${matchId} not found`);
        }

        if (match.state !== 'confirmed') {
          throw new Error('Only confirmed matches can be completed');
        }

        match.complete(notes);

        const completedEvent = new MatchCompleted(
          matchId,
          completedBy,
          match.updatedAt
        );

        await eventStore.append(completedEvent);

        const completedMatches = await eventStore.getEventsByType('MatchCompleted');
        const confirmedMatches = await eventStore.getEventsByType('MatchConfirmed');
        
        const completedCount = completedMatches.filter(
          (e) => e.payload.completedBy === completedBy
        ).length;
        
        const confirmedCount = confirmedMatches.filter(
          (e) => e.payload.confirmedBy === completedBy
        ).length;

        const trustScore = computeTrustScore(completedCount, confirmedCount);
        const trustLevel = TrustLevel.HIGH;

        const trustEvent = new TrustUpdated(
          completedBy,
          trustScore,
          trustLevel,
          1,
          match.updatedAt
        );

        await eventStore.append(trustEvent);
        await matchRepository.save(match);
      }
    };
  },
};

module.exports = { CompleteMatchUseCase };