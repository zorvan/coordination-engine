const crypto = require('crypto');

/**
 * Relational graph repository
 * 
 * Stores and retrieves relational edges (soft social constraints)
 * between actors.
 * 
 * Pattern: Read Model / Projection - derived state from event stream
 * 
 * @param {Object} eventStore - The event store instance
 * @returns {Object} Relational graph repository implementation
 */

function createRelationalGraphRepository(eventStore) {
  return {
    /**
     * Save a relational edge
     * 
     * @param {Object} edge - Edge entity to persist
     * @returns {Promise<void>}
     */
    async save(edge) {
      // Check for loops before saving
      const existingEdges = await this.getEdgesForActor(edge.sourceId);
      for (const existingEdge of existingEdges) {
        if (
          existingEdge.targetId === edge.targetId &&
          existingEdge.constraintType !== edge.constraintType
        ) {
          throw new Error(
            `Loop detected: ${edge.sourceId} and ${edge.targetId} have conflicting constraints`
          );
        }
      }

      await eventStore.append({
        id: crypto.randomUUID(),
        aggregateId: edge.id,
        type: 'RelationalEdgeCreated',
        timestamp: edge.createdAt,
        payload: edge,
      });
    },

    /**
     * Get all edges for an actor
     * 
     * @param {string} actorId - Actor identifier
     * @returns {Promise<Object[]>} Array of edge objects
     */
    async getEdgesForActor(actorId) {
      const events = await eventStore.getAllEvents();
      const edgeEvents = events.filter(
        (e) => e.type === 'RelationalEdgeCreated'
      );

      return edgeEvents
        .filter((e) => e.payload.sourceId === actorId)
        .map((e) => ({
          id: e.payload.id,
          sourceId: e.payload.sourceId,
          targetId: e.payload.targetId,
          constraintType: e.payload.constraintType,
          confidence: e.payload.confidence,
          createdAt: new Date(e.payload.createdAt),
          updatedAt: new Date(e.payload.updatedAt),
        }));
    },

    /**
     * Get reciprocal edges (where actor is the target)
     * 
     * @param {string} actorId - Actor identifier
     * @returns {Promise<Object[]>} Array of edge objects
     */
    async getReciprocalEdges(actorId) {
      const events = await eventStore.getAllEvents();
      const edgeEvents = events.filter(
        (e) => e.type === 'RelationalEdgeCreated'
      );

      return edgeEvents
        .filter((e) => e.payload.targetId === actorId)
        .map((e) => ({
          id: e.payload.id,
          sourceId: e.payload.sourceId,
          targetId: e.payload.targetId,
          constraintType: e.payload.constraintType,
          confidence: e.payload.confidence,
          createdAt: new Date(e.payload.createdAt),
          updatedAt: new Date(e.payload.updatedAt),
        }));
    },

    /**
     * Check if a relationship exists
     * 
     * @param {string} sourceId - Source actor ID
     * @param {string} targetId - Target actor ID
     * @returns {Promise<boolean>} True if relationship exists
     */
    async hasEdge(sourceId, targetId) {
      const edges = await this.getEdgesForActor(sourceId);
      return edges.some((e) => e.targetId === targetId);
    },

    /**
     * Remove a relational edge
     * 
     * @param {string} sourceId - Source actor ID
     * @param {string} targetId - Target actor ID
     * @returns {Promise<void>}
     */
    async removeEdge(sourceId, targetId) {
      // Delete all edges between source and target
      const events = await eventStore.getAllEvents();
      const edgeEvents = events.filter(
        (e) => e.type === 'RelationalEdgeCreated'
      );

      for (const event of edgeEvents) {
        const edge = event.payload;
        if (
          edge.sourceId === sourceId &&
          edge.targetId === targetId
        ) {
          await eventStore.append({
            id: crypto.randomUUID(),
            aggregateId: edge.id,
            type: 'RelationalEdgeRemoved',
            timestamp: new Date(),
            payload: {
              edgeId: edge.id,
              sourceId,
              targetId,
              removedAt: new Date(),
            },
          });
        }
      }
    },

    /**
     * Check for loops (mutual exclusion constraints)
     * 
     * @param {string} contextId - Context identifier (e.g., gathering ID)
     * @returns {Promise<boolean>} True if any loops detected
     */
    async hasLoops(contextId) {
      const events = await eventStore.getAllEvents();
      const edgeEvents = events.filter(
        (e) => e.type === 'RelationalEdgeCreated'
      );

      const edges = edgeEvents.map((e) => ({
        sourceId: e.payload.sourceId,
        targetId: e.payload.targetId,
        constraintType: e.payload.constraintType,
      }));

      for (const edge of edges) {
        const reciprocal = edges.find(
          (e) => e.sourceId === edge.targetId && e.targetId === edge.sourceId
        );

        if (reciprocal && edge.constraintType !== reciprocal.constraintType) {
          return true;
        }
      }

      return false;
    },

    /**
     * Get constraint weights for an actor
     * 
     * @param {string} actorId - Actor identifier
     * @returns {Promise<Object>} Weights for positive and negative constraints
     */
    async getConstraintWeights(actorId) {
      const edges = await this.getEdgesForActor(actorId);

      const positiveEdges = edges.filter(
        (e) => e.constraintType === 'positive'
      );

      const negativeEdges = edges.filter(
        (e) => e.constraintType === 'negative'
      );

      const positiveWeight = positiveEdges.reduce(
        (sum, e) => sum + e.confidence / 100,
        0
      );

      const negativeWeight = negativeEdges.reduce(
        (sum, e) => sum + e.confidence / 100,
        0
      );

      return { positiveWeight, negativeWeight };
    },
  };
}

module.exports = { createRelationalGraphRepository };