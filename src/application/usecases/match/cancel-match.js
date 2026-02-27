const CancelMatchUseCase = {
  create: function(matchRepository, eventStore) {
    return {
      async execute(matchId, actorId, reason) {
        reason = reason || undefined;
        const events = await eventStore.getEventsByAggregate(matchId);
        const confirmedEvent = events.find(function(e) { return e.type === 'MatchConfirmed'; });
        
        if (!confirmedEvent) {
          throw new Error('Match ' + matchId + ' is not confirmed');
        }

        const event = {
          id: generateEventId(),
          aggregateId: matchId,
          type: 'MatchCancelled',
          timestamp: new Date(),
          payload: {
            cancelledBy: actorId,
            cancelledAt: new Date(),
            reason: reason
          }
        };

        await eventStore.append(event);
      }
    };
  }
};

module.exports = { CancelMatchUseCase };