const { computeTrustScore, getTrustLevel } = require('../../domain/services/trust-computation');

const PostgresTrustProjection = {
  create: function(eventStore) {
    return {
      async computeTrustScore(actorId) {
        const events = await eventStore.getAllEvents();
        
        const completedMatches = events.filter(e => 
          e.type === 'MatchCompleted' && e.payload?.completedBy === actorId
        ).length;

        const confirmedMatches = events.filter(e => 
          e.type === 'MatchConfirmed' && 
          (e.payload?.confirmedBy === actorId || 
           (e.payload?.participants && e.payload.participants.includes(actorId)))
        ).length;

        return computeTrustScore(completedMatches, confirmedMatches);
      },

      async updateTrustScore(actorId, completedMatches, acceptedMatches) {
        const score = computeTrustScore(completedMatches, acceptedMatches);
        const level = getTrustLevel(score);

        const trustEvent = {
          id: `evt_trust_${Date.now()}`,
          aggregateId: actorId,
          type: 'TrustScoreUpdated',
          timestamp: new Date(),
          payload: {
            actorId,
            score,
            level,
            version: '1.0'
          }
        };

        await eventStore.append(trustEvent);
      }
    };
  }
};

module.exports = PostgresTrustProjection;