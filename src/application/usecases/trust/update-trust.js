const updateTrustUseCase = {
  create: function(eventStore, trustProjection) {
    return {
      async execute(actorId) {
        const events = await eventStore.getAllEvents();
        
        const completedMatches = events.filter(function(e) {
          return e.type === 'MatchCompleted' && e.payload && e.payload.completedBy === actorId;
        }).length;

        const confirmedMatches = events.filter(function(e) {
          const payload = e.payload;
          return e.type === 'MatchConfirmed' && 
            (payload && (payload.confirmedBy === actorId || 
             (payload.participants && payload.participants.includes(actorId))));
        }).length;

        const trustScore = computeTrustScore(completedMatches, confirmedMatches);
        const trustLevel = getTrustLevel(trustScore);

        const event = {
          id: generateEventId(),
          aggregateId: actorId,
          type: 'TrustScoreUpdated',
          timestamp: new Date(),
          payload: {
            actorId: actorId,
            score: trustScore,
            level: trustLevel,
            version: getTrustFormulaVersion()
          }
        };

        await eventStore.append(event);
      }
    };
  }
};

module.exports = { UpdateActorTrustUseCase };