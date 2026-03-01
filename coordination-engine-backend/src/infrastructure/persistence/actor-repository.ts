import crypto from 'crypto';

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
       * Update actor by appending an ActorUpdated event.
       * This method accepts a *partial* actor object – callers should only include
       * the properties that have changed.  The projection logic in `findById`
       * will merge each event payload on top of the previous state, so patches
       * are safe even if the caller doesn't know the full actor.
       * The repository projections will merge ActorCreated + ActorUpdated payloads
       */
      async update(actor) {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: actor.id,
          type: 'ActorUpdated',
          timestamp: new Date(),
          payload: actor,
        });
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
      if (!createdEvent) return null;

      // apply any ActorUpdated events on top of the original
      const updates = events.filter((e) => e.type === 'ActorUpdated').sort((a, b) => +new Date(a.timestamp) - +new Date(b.timestamp));
      let base = { ...createdEvent.payload };
      for (const u of updates) {
        base = { ...base, ...u.payload };
      }

      return {
        id: base.id,
        name: base.name,
        email: base.email,
        avatar: base.avatar,
        phone: base.phone || '',
        bio: base.bio || '',
        location: base.location || '',
        website: base.website || '',
        onboardingCompletedAt: base.onboardingCompletedAt || null,
        circles: base.circles || [],
        temporalIdentity: base.temporalIdentity,
        trustScore: base.trustScore || 0,
        trustLevel: base.trustLevel || 'very_low',
        acceptedMatches: base.acceptedMatches || 0,
        completedMatches: base.completedMatches || 0,
        createdAt: new Date(createdEvent.timestamp),
        updatedAt: updates.length > 0 ? new Date(updates[updates.length - 1].timestamp) : new Date(createdEvent.timestamp),
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
      const actorCreated = events.filter((e) => e.type === 'ActorCreated');
      // fold updates onto created events for each actor
      return Promise.all(actorCreated.map(async (event) => {
        return this.findById(event.payload.id);
      }));
    },
  };
}

export { createInMemoryActorRepository };
