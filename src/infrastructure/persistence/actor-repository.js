const crypto = require('crypto');

/**
 * In-memory actor repository for development
 * 
 * Uses event store as backing storage and builds read model from events
 * 
 * Pattern: Read Model / Projection - derived state from event stream
 * Pattern: Repository - encapsulates data access logic
 * 
 * @param {Object} eventStore - The event store instance
 * @returns {Object} Actor repository implementation
 */

function createInMemoryActorRepository(eventStore) {
  return {
    /**
     * Save an actor by persisting a ActorCreated event
     * 
     * @param {Object} actor - Actor aggregate
     * @returns {Promise<void>}
     */
    async save(actor) {
      const events = await eventStore.getEventsByAggregate(actor.id);
      const createdEvent = events.find((e) => e.type === 'ActorCreated');
      
      if (!createdEvent) {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: actor.id,
          type: 'ActorCreated',
          timestamp: new Date(),
          payload: actor,
        });
      }
    },

    /**
     * Find actor by ID
     * 
     * @param {string} id - Actor identifier
     * @returns {Promise<Object|null>} Actor object or null
     */
    async findById(id) {
      const events = await eventStore.getEventsByAggregate(id);
      const createdEvent = events.find((e) => e.type === 'ActorCreated');
      
      if (!createdEvent) {
        return null;
      }

      return {
        id: createdEvent.payload.id,
        name: createdEvent.payload.name,
        email: createdEvent.payload.email,
        avatar: createdEvent.payload.avatar,
        circles: createdEvent.payload.circles || [],
        temporalIdentity: createdEvent.payload.temporalIdentity,
        trustScore: createdEvent.payload.trustScore || 0,
        trustLevel: createdEvent.payload.trustLevel || 'very_low',
        acceptedMatches: createdEvent.payload.acceptedMatches || 0,
        completedMatches: createdEvent.payload.completedMatches || 0,
        createdAt: new Date(createdEvent.timestamp),
        updatedAt: new Date(createdEvent.timestamp),
      };
    },

    /**
     * Find actor by email
     * 
     * @param {string} email - Actor email
     * @returns {Promise<Object|null>} Actor object or null
     */
    async findByEmail(email) {
      const events = await eventStore.getAllEvents();
      const createdEvent = events.find(
        (e) => e.type === 'ActorCreated' && e.payload.email === email
      );
      
      if (!createdEvent) {
        return null;
      }

      const id = createdEvent.payload.id;
      return this.findById(id);
    },

    /**
     * Find all actors
     * 
     * @returns {Promise<Object[]>} Array of all actor objects
     */
    async findAll() {
      const events = await eventStore.getAllEvents();
      const actorEvents = events.filter((e) => e.type === 'ActorCreated');
      
      return actorEvents.map((event) => ({
        id: event.payload.id,
        name: event.payload.name,
        email: event.payload.email,
        avatar: event.payload.avatar,
        circles: event.payload.circles || [],
        temporalIdentity: event.payload.temporalIdentity,
        trustScore: event.payload.trustScore || 0,
        trustLevel: event.payload.trustLevel || 'very_low',
        acceptedMatches: event.payload.acceptedMatches || 0,
        completedMatches: event.payload.completedMatches || 0,
        createdAt: new Date(event.timestamp),
        updatedAt: new Date(event.timestamp),
      }));
    },
  };
}

module.exports = { createInMemoryActorRepository };