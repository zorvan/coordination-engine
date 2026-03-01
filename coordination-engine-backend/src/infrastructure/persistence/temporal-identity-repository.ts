/**
 * In-memory temporal identity repository for Phase 4
 * 
 * Uses event store as backing storage and builds read model from events
 * 
 * Pattern: Read Model / Projection - derived state from event stream
 * Pattern: Event Sourcing - identity versions as events
 * 
 * @param {Object} eventStore - The event store instance
 * @returns {Object} Temporal identity repository implementation
 */

function createTemporalIdentityRepository(eventStore) {
  return {
    /**
     * Save a temporal identity
     * 
     * @param {Object} identity - Identity aggregate
     * @returns {Promise<void>}
     */
    async save(identity) {
      const events = await eventStore.getEventsByAggregate(identity.identityId);
      const createdEvent = events.find((e) => e.type === 'TemporalIdentityCreated');
      
      if (!createdEvent) {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: identity.identityId,
          type: 'TemporalIdentityCreated',
          timestamp: identity.createdAt,
          payload: {
            identityId: identity.identityId,
            state: identity.state,
            versions: identity.versions,
          },
        });
      }

      for (const version of identity.versions) {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: identity.identityId,
          type: 'TemporalIdentityVersioned',
          timestamp: version.createdAt,
          payload: {
            identityId: identity.identityId,
            version,
            state: identity.state,
          },
        });
      }
    },

    /**
     * Find temporal identity by ID
     * 
     * @param {string} identityId - Identity identifier
     * @returns {Promise<Object|null>} Temporal identity object or null
     */
    async findById(identityId) {
      const events = await eventStore.getEventsByAggregate(identityId);
      const identityEvents = events.filter((e) => e.type === 'TemporalIdentityCreated');
      
      if (identityEvents.length === 0) {
        return null;
      }

      const identity: TemporalIdentityRecord = {
        identityId,
        versions: [],
        currentVersionIndex: -1,
        state: identityEvents[0].payload.state || 'active',
        createdAt: new Date(identityEvents[0].timestamp),
        updatedAt: null,
      };

      for (const event of events) {
        if (event.type === 'TemporalIdentityVersioned') {
          identity.versions.push(event.payload.version);
          identity.currentVersionIndex = identity.versions.length - 1;
          identity.updatedAt = new Date(event.timestamp);
        }
      }

      return identity;
    },

    /**
     * Find temporal identity by actor ID
     * 
     * @param {string} actorId - Actor identifier
     * @returns {Promise<Object|null>} Temporal identity object or null
     */
    async findByActorId(actorId) {
      const events = await eventStore.getAllEvents();
      const identityEvent = events.find(
        (e) => e.type === 'TemporalIdentityCreated' && e.payload.identityId === actorId
      );
      
      if (!identityEvent) {
        return null;
      }

      return this.findById(identityEvent.payload.identityId);
    },
  };
}

export { createTemporalIdentityRepository };
import crypto from 'crypto';

interface TemporalIdentityRecord {
  identityId: string;
  versions: unknown[];
  currentVersionIndex: number;
  state: string;
  createdAt: Date;
  updatedAt: Date | null;
}
