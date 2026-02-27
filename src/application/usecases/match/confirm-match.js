const { MatchAggregate } = require('../../domain/aggregates/match-aggregate');
const { DomainEventType } = require('../../domain/events/event-utils');
const { MatchCreated, MatchConfirmed } = require('../../domain/events/domain-event');

const ConfirmMatchUseCase = {
  create(matchRepository, eventStore) {
    return {
      /**
       * Confirm a match that is in proposed state
       * 
       * Business rule: Only organizer or participants can confirm a match
       * This transitions the match from 'proposed' -> 'confirmed' state
       * 
       * @param {string} matchId - The match to confirm
       * @param {string} actorId - The actor confirming the match
       * @throws {Error} If match not found or actor not authorized
       */
      async execute(matchId, actorId) {
        const match = await matchRepository.findById(matchId);
        
        if (!match) {
          throw new Error(`Match ${matchId} not found`);
        }

        const participantIds = match.participantIds || [];
        const organizerId = match.organizerId;
        
        if (organizerId !== actorId && !participantIds.includes(actorId)) {
          throw new Error('Actor not authorized to confirm this match');
        }

        match.confirm();

        const event = new MatchConfirmed(
          matchId,
          actorId,
          match.updatedAt
        );

        await eventStore.append(event);
        await matchRepository.save(match);
      }
    };
  },
};

module.exports = { ConfirmMatchUseCase };