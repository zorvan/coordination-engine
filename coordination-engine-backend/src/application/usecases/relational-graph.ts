import { RelationalEdge } from '../../domain/entities/relational-edge';
import { RelationalGraph } from '../../domain/aggregates/relational-graph';
import { generateAggregateId } from '../../domain/events/event-utils';

/**
 * Relational Graph Use Cases
 * 
 * This module handles soft social logic:
 * - "If X attends, I attend" (positive constraint)
 * - "If X attends, I prefer not" (negative constraint)
 * - Confidence weighting for each constraint
 */

const RelationalGraphUseCase = {
  /**
   * Create a new relational graph for a context (e.g., gathering)
   * 
   * @param {Object} relationalGraphRepository - Repository for edge storage
   * @param {Object} eventStore - Event store for audit trail
   * @returns {Object} Use case with methods
   */
  create(relationalGraphRepository, eventStore) {
    return {
      /**
       * Add a positive constraint ("If X attends, I attend")
       * 
       * @param {string} sourceId - Source actor ID (the one making the constraint)
       * @param {string} targetId - Target actor ID (the one being referenced)
       * @param {number} confidence - Confidence level (0-100)
       * @returns {Promise<string>} The edge ID
       */
      async addPositiveConstraint(sourceId, targetId, confidence) {
        const edge = RelationalEdge.createPositive(sourceId, targetId, confidence);
        
        await relationalGraphRepository.save(edge);
        
        return edge.id;
      },

      /**
       * Add a negative constraint ("If X attends, I prefer not")
       * 
       * @param {string} sourceId - Source actor ID
       * @param {string} targetId - Target actor ID
       * @param {number} confidence - Confidence level (0-100)
       * @returns {Promise<string>} The edge ID
       */
      async addNegativeConstraint(sourceId, targetId, confidence) {
        const edge = RelationalEdge.createNegative(sourceId, targetId, confidence);
        
        await relationalGraphRepository.save(edge);
        
        return edge.id;
      },

      /**
       * Get all constraints for an actor
       * 
       * @param {string} actorId - Actor identifier
       * @returns {Promise<Object[]>} Array of constraint objects
       */
      async getConstraintsForActor(actorId) {
        return relationalGraphRepository.getEdgesForActor(actorId);
      },

      /**
       * Check if a constraint exists between two actors
       * 
       * @param {string} sourceId - Source actor ID
       * @param {string} targetId - Target actor ID
       * @returns {Promise<boolean>} True if constraint exists
       */
      async hasConstraint(sourceId, targetId) {
        return relationalGraphRepository.hasEdge(sourceId, targetId);
      },

      /**
       * Check for constraint loops (mutual exclusions)
       * 
       * @param {string} contextId - Context identifier (e.g., gathering ID)
       * @returns {Promise<boolean>} True if any loops detected
       */
      async hasLoops(contextId) {
        return relationalGraphRepository.hasLoops(contextId);
      },

      /**
       * Remove a constraint
       * 
       * @param {string} sourceId - Source actor ID
       * @param {string} targetId - Target actor ID
       * @returns {Promise<void>}
       */
      async removeConstraint(sourceId, targetId) {
        await relationalGraphRepository.removeEdge(sourceId, targetId);
      },

      /**
       * Get constraint weights for an actor
       * 
       * @param {string} actorId - Actor identifier
       * @returns {Promise<Object>} Weights for positive and negative constraints
       */
      async getConstraintWeights(actorId) {
        return relationalGraphRepository.getConstraintWeights(actorId);
      },
    };
  },
};

export { RelationalGraphUseCase };