import { MatchCreated } from '../../../domain/events/domain-event';
import { MatchAggregate } from '../../../domain/aggregates/match-aggregate';
import { generateAggregateId } from '../../../domain/events/event-utils';
import { CreateMatchUseCaseLike, EventStoreLike, MatchRepositoryLike } from '../../../types/match';

const CreateMatchUseCase = {
  create(matchRepository: MatchRepositoryLike, eventStore: EventStoreLike): CreateMatchUseCaseLike {
    return {
      /**
       * Create a new match/agenda item
       * 
       * Business logic:
       * - Organizer must be specified
       * - At least one participant is required
       * - Creates an event-sourced match with initial 'proposed' state
       * 
       * @param {string} organizerId - The actor creating the match
       * @param {string} title - Match title
       * @param {string} description - Optional description
       * @param {Date} scheduledTime - When the match is scheduled
       * @param {number} durationMinutes - Duration in minutes
       * @param {string} location - Physical or virtual location
       * @param {string[]} participantIds - Array of participant actor IDs
       * @returns {string} The created match ID
       */
      async execute(
        organizerId: string,
        title: string,
        description: string,
        scheduledTime: Date,
        durationMinutes: number,
        location: string,
        participantIds: string[]
      ): Promise<string> {
        participantIds = participantIds || [];
        
        if (participantIds.length === 0) {
          throw new Error('At least one participant is required');
        }

        const matchId = generateAggregateId();
        
        const match = MatchAggregate.create(
          matchId,
          organizerId,
          title,
          description || '',
          scheduledTime,
          durationMinutes,
          location,
          participantIds
        );

        const event = new MatchCreated(
          matchId,
          organizerId,
          title,
          description,
          scheduledTime,
          durationMinutes,
          location,
          participantIds
        );

        await eventStore.append(event);
        await matchRepository.save(match);
        
        return matchId;
      }
    };
  },
};

export { CreateMatchUseCase };
