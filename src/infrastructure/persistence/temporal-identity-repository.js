const crypto = require('crypto');

/**
 * In-memory temporal identity repository for development
 * 
 * Uses event store as backing storage and builds read model from events
 * 
 * Pattern: Read Model / Projection - derived state from event stream
 * Pattern: Event Sourcing - state is derived from event history
 * 
 * @param {Object} eventStore - The event store instance
 * @returns {Object} Temporal identity repository implementation
 */

function createInMemoryTemporalIdentityRepository(eventStore) {
  return {
    /**
     * Save a temporal identity by persisting version events
     * 
     * @param {Object} identity - Temporal identity aggregate
     * @returns {Promise<void>}
     */
    async save(identity) {
      await eventStore.append({
        id: crypto.randomUUID(),
        aggregateId: identity.identityId,
        type: 'TemporalIdentityVersioned',
        timestamp: new Date(),
        payload: identity,
      });
    },

    /**
     * Find temporal identity by ID
     * 
     * @param {string} identityId - Identity identifier
     * @returns {Promise<Object|null>} Temporal identity object or null
     */
    async findById(identityId) {
      const events = await eventStore.getEventsByAggregate(identityId);
      const identityEvents = events.filter((e) => e.type === 'TemporalIdentityVersioned');
      
      if (identityEvents.length === 0) {
        return null;
      }

      // Return the latest version
      return identityEvents[identityEvents.length - 1].payload;
    },
  };
}

module.exports = { createInMemoryTemporalIdentityRepository };