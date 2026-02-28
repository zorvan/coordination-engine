const { MatchCompleted } = require('../../../domain/events/domain-event');
const { TrustUpdated } = require('../../../domain/events/domain-event');
const { computeTrustScore, getTrustLevel } = require('../../../domain/services/trust-computation');

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

        match.state = 'completed';
        match.notes = notes;
        match.completedAt = new Date();
        match.updatedAt = match.completedAt;

        const completedEvent = new MatchCompleted(
          matchId,
          completedBy,
          match.completedAt
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
        const trustLevel = getTrustLevel(trustScore);

        const trustEvent = new TrustUpdated(
          completedBy,
          trustScore,
          trustLevel,
          1,
          match.completedAt
        );

        await eventStore.append(trustEvent);
        await matchRepository.save(match);
      }
    };
  },
};

module.exports = { CompleteMatchUseCase };
