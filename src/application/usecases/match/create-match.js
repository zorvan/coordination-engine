const { MatchCreated } = require('../../../domain/events/domain-event');
const { MatchAggregate } = require('../../../domain/aggregates/match-aggregate');
const { generateAggregateId } = require('../../../domain/events/event-utils');

const CreateMatchUseCase = {
  create(matchRepository, eventStore) {
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
      async execute(organizerId, title, description, scheduledTime, durationMinutes, location, participantIds) {
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

module.exports = { CreateMatchUseCase };