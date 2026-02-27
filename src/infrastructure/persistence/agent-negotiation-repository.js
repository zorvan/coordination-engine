const crypto = require('crypto');

/**
 * Agent negotiation repository
 * 
 * Stores agent negotiations using event sourcing
 * 
 * Pattern: Read Model / Projection - derived state from event stream
 * 
 * @param {Object} eventStore - The event store instance
 * @returns {Object} Agent negotiation repository implementation
 */

function createAgentNegotiationRepository(eventStore) {
  return {
    /**
     * Save an agent negotiation
     * 
     * @param {Object} negotiation - Negotiation aggregate
     * @returns {Promise<void>}
     */
    async save(negotiation) {
      const events = await eventStore.getEventsByAggregate(negotiation.negotiationId);
      const initiatedEvent = events.find((e) => e.type === 'AgentNegotiationInitiated');
      
      if (!initiatedEvent) {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: negotiation.negotiationId,
          type: 'AgentNegotiationInitiated',
          timestamp: negotiation.createdAt,
          payload: {
            negotiationId: negotiation.negotiationId,
            matchId: negotiation.matchId,
            organizerId: negotiation.organizerId,
            status: negotiation.status,
          },
        });
      }

      await eventStore.append({
        id: crypto.randomUUID(),
        aggregateId: negotiation.negotiationId,
        type: 'AgentNegotiationUpdated',
        timestamp: negotiation.completedAt || new Date(),
        payload: {
          negotiationId: negotiation.negotiationId,
          status: negotiation.status,
          completedAt: negotiation.completedAt || null,
        },
      });
    },

    /**
     * Find agent negotiation by ID
     * 
     * @param {string} negotiationId - Negotiation identifier
     * @returns {Promise<Object|null>} Agent negotiation object or null
     */
    async findById(negotiationId) {
      const events = await eventStore.getEventsByAggregate(negotiationId);
      
      if (events.length === 0) {
        return null;
      }

      let negotiation = {
        negotiationId,
        matchId: null,
        organizerId: null,
        agents: [],
        proposals: [],
        status: 'initiated',
        createdAt: null,
        completedAt: null,
      };

      for (const event of events) {
        if (event.type === 'AgentNegotiationInitiated') {
          negotiation.matchId = event.payload.matchId;
          negotiation.organizerId = event.payload.organizerId;
          negotiation.createdAt = new Date(event.timestamp);
        } else if (event.type === 'AgentNegotiationUpdated') {
          negotiation.status = event.payload.status;
          negotiation.completedAt = event.payload.completedAt
            ? new Date(event.payload.completedAt)
            : null;
        }
      }

      return negotiation;
    },

    /**
     * Find negotiations by match ID
     * 
     * @param {string} matchId - Match identifier
     * @returns {Promise<Object[]>} Array of negotiation objects
     */
    async findByMatchId(matchId) {
      const allEvents = await eventStore.getAllEvents();
      const negotiationEvents = allEvents.filter(
        (e) => e.type === 'AgentNegotiationInitiated'
      );

      const negotiations = [];

      for (const event of negotiationEvents) {
        if (event.payload.matchId === matchId) {
          const negotiation = await this.findById(event.payload.negotiationId);
          if (negotiation) {
            negotiations.push(negotiation);
          }
        }
      }

      return negotiations;
    },

    /**
     * Find all negotiations
     * 
     * @returns {Promise<Object[]>} Array of all negotiation objects
     */
    async findAll() {
      const allEvents = await eventStore.getAllEvents();
      const negotiationEvents = allEvents.filter(
        (e) => e.type === 'AgentNegotiationInitiated'
      );

      const negotiations = [];

      for (const event of negotiationEvents) {
        const negotiation = await this.findById(event.payload.negotiationId);
        if (negotiation) {
          negotiations.push(negotiation);
        }
      }

      return negotiations;
    },
  };
}

module.exports = { createAgentNegotiationRepository };