const generateEventId = require('../../domain/events/event-utils').generateEventId;
const { getTrustFormulaVersion } = require('../../domain/services/trust-computation');
const { MatchConfirmedEvent } = require('../../domain/events/match-events');

const ConfirmMatchUseCase = {
  create: function(matchRepository, eventStore) {
    return {
      async execute(matchId, actorId) {
        const events = await eventStore.getEventsByAggregate(matchId);
        const matchEvent = events.find(function(e) { return e.type === 'MatchCreated'; });
        
        if (!matchEvent) {
          throw new Error('Match ' + matchId + ' not found');
        }

        const participantIds = matchEvent.payload.participants || [];
        const organizerId = matchEvent.payload.organizerId;
        
        if (organizerId !== actorId && !participantIds.includes(actorId)) {
          throw new Error('Actor not authorized to confirm this match');
        }

        const event = MatchConfirmedEvent(
          generateEventId(),
          matchId,
          new Date(),
          {
            confirmedBy: actorId,
            confirmedAt: new Date()
          }
        );

        await eventStore.append(event);
      }
    };
  }
};

module.exports = { ConfirmMatchUseCase };