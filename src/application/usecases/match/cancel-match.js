const { MatchCancelled } = require('../../../domain/events/domain-event');

const CancelMatchUseCase = {
  create(matchRepository, eventStore) {
    return {
      /**
       * Cancel a match (proposed or confirmed state)
       * 
       * Business logic:
       * - Only organizer or participants can cancel
       * - Once cancelled, match cannot be recovered
       * 
       * @param {string} matchId - The match to cancel
       * @param {string} cancelledBy - The actor cancelling the match
       * @param {string} reason - Cancellation reason
       * @throws {Error} If match not found or actor not authorized
       */
      async execute(matchId, cancelledBy, reason) {
        const match = await matchRepository.findById(matchId);
        
        if (!match) {
          throw new Error(`Match ${matchId} not found`);
        }

        const participantIds = match.participantIds || [];
        const organizerId = match.organizerId;
        
        if (organizerId !== cancelledBy && !participantIds.includes(cancelledBy)) {
          throw new Error('Actor not authorized to cancel this match');
        }

        if (match.state !== 'proposed' && match.state !== 'confirmed') {
          throw new Error('Only proposed or confirmed matches can be cancelled');
        }
        match.state = 'cancelled';
        match.notes = reason;
        match.cancelledAt = new Date();
        match.updatedAt = match.cancelledAt;

        const event = new MatchCancelled(
          matchId,
          cancelledBy,
          reason,
          match.cancelledAt
        );

        await eventStore.append(event);
        await matchRepository.save(match);
      }
    };
  },
};

module.exports = { CancelMatchUseCase };
