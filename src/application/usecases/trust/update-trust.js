const { TrustUpdated } = require('../../domain/events/domain-event');
const { computeTrustScore, getTrustLevel } = require('../../domain/services/trust-computation');
const { TrustLevel } = require('../../domain/valuables/trust-value');
const generateEventId = require('../../domain/events/event-utils').generateEventId;
const generateAggregateId = require('../../domain/events/event-utils').generateAggregateId;

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

module.exports = { UpdateTrustUseCase };