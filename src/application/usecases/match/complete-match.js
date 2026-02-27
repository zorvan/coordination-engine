const CompleteMatchUseCase = {
  create: function(matchRepository, eventStore, trustProjection) {
    return {
      async execute(matchId, actorId, notes) {
        notes = notes || undefined;
        const events = await eventStore.getEventsByAggregate(matchId);
        const confirmedEvent = events.find(function(e) { return e.type === 'MatchConfirmed'; });
        
        if (!confirmedEvent) {
          throw new Error('Match ' + matchId + ' is not confirmed');
        }

        const event = {
          id: generateEventId(),
          aggregateId: matchId,
          type: 'MatchCompleted',
          timestamp: new Date(),
          payload: {
            completedBy: actorId,
            completedAt: new Date(),
            notes: notes
          }
        };

        await eventStore.append(event);

        const eventsAll = await eventStore.getAllEvents();
        const completedMatches = eventsAll.filter(function(e) {
          return e.type === 'MatchCompleted' && e.payload && e.payload.completedBy === actorId;
        }).length;

        const confirmedMatches = eventsAll.filter(function(e) {
          const payload = e.payload;
          return e.type === 'MatchConfirmed' && 
            (payload && (payload.confirmedBy === actorId || 
             (payload.participants && payload.participants.includes(actorId))));
        }).length;

        const trustScore = computeTrustScore(completedMatches, confirmedMatches);
        const trustLevel = getTrustLevel(trustScore);

        const trustEvent = {
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

        await eventStore.append(trustEvent);
      }
    };
  }
};

module.exports = { CompleteMatchUseCase };