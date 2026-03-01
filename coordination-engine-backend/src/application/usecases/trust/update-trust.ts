import { TrustUpdated } from '../../../domain/events/domain-event';
import { computeTrustScore, getTrustLevel } from '../../../domain/services/trust-computation';
import { generateEventId as generateEventId } from '../../../domain/events/event-utils';
import { generateAggregateId as generateAggregateId } from '../../../domain/events/event-utils';

const UpdateTrustUseCase = {
  create(actorRepository, eventStore) {
    return {
      /**
       * Update an actor's trust score based on match completion history
       * 
       * Business logic:
       * - Trust score = completed matches / accepted matches
       * - 5-tier trust levels: Very Low, Low, Medium, High, Very High
       * - Updates are event-sourced for auditability
       * 
       * @param {string} actorId - The actor to update
       * @param {number} completedMatches - Number of matches completed
       * @param {number} acceptedMatches - Number of matches accepted/confirmed
       * @returns {Object} The updated trust value object
       */
      async execute(actorId, completedMatches, acceptedMatches) {
        const actor = await actorRepository.findById(actorId);
        
        if (!actor) {
          throw new Error(`Actor ${actorId} not found`);
        }

        const trustScore = computeTrustScore(completedMatches, acceptedMatches);
        const trustLevel = getTrustLevel(trustScore);

        actor.applyTrustUpdate(trustScore, trustLevel, 1, new Date());

        const event = new TrustUpdated(
          actorId,
          trustScore,
          trustLevel,
          1,
          actor.updatedAt
        );

        await eventStore.append(event);
        await actorRepository.save(actor);

        return {
          actorId,
          trustScore,
          trustLevel,
        };
      }
    };
  },
};

export { UpdateTrustUseCase };
