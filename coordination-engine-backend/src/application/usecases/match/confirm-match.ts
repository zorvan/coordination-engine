import { MatchConfirmed } from '../../../domain/events/domain-event';
import { ConfirmMatchUseCaseLike, EventStoreLike, MatchRepositoryLike } from '../../../types/match';

const ConfirmMatchUseCase = {
  create(matchRepository: MatchRepositoryLike, eventStore: EventStoreLike): ConfirmMatchUseCaseLike {
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
      async execute(matchId: string, actorId: string): Promise<void> {
        const match = await matchRepository.findById(matchId);
        
        if (!match) {
          throw new Error(`Match ${matchId} not found`);
        }

        const participantIds = match.participantIds || [];
        const organizerId = match.organizerId;
        
        if (organizerId !== actorId && !participantIds.includes(actorId)) {
          throw new Error('Actor not authorized to confirm this match');
        }

        if (match.state !== 'proposed') {
          throw new Error('Only proposed matches can be confirmed');
        }
        match.state = 'confirmed';
        match.updatedAt = new Date();

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

export { ConfirmMatchUseCase };
