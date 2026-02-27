/**
 * In-memory match repository implementation
 * 
 * Uses event store as backing storage and builds read model from events
 * 
 * Pattern: Read Model / Projection - derived state from event stream
 * Pattern: Event Sourcing - state is derived from event history
 * 
 * @param {Object} eventStore - The event store instance
 * @returns {Object} Match repository implementation
 */

function createInMemoryMatchRepository(eventStore) {
  return {
    /**
     * Save a match by persisting state change events
     * 
     * @param {Object} match - Match aggregate
     * @returns {Promise<void>}
     */
    async save(match) {
      const events = await eventStore.getEventsByAggregate(match.matchId);
      const createdEvent = events.find((e) => e.type === 'MatchCreated');
      
      if (createdEvent) {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: match.matchId,
          type: 'MatchUpdated',
          timestamp: new Date(),
          payload: match,
        });
      } else {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: match.matchId,
          type: 'MatchCreated',
          timestamp: new Date(),
          payload: match,
        });
      }
    },

    /**
     * Find match by ID
     * 
     * @param {string} id - Match identifier
     * @returns {Promise<Object|null>} Match object or null
     */
    async findById(id) {
      const events = await eventStore.getEventsByAggregate(id);
      const createdEvent = events.find((e) => e.type === 'MatchCreated');
      
      if (!createdEvent) {
        return null;
      }

      let match = {
        matchId: id,
        state: createdEvent.payload.state || 'proposed',
        organizerId: createdEvent.payload.organizerId,
        title: createdEvent.payload.title,
        description: createdEvent.payload.description || '',
        scheduledTime: new Date(createdEvent.payload.scheduledTime),
        durationMinutes: createdEvent.payload.durationMinutes,
        location: createdEvent.payload.location,
        participantIds: createdEvent.payload.participantIds || [],
        createdAt: new Date(createdEvent.timestamp),
        updatedAt: new Date(createdEvent.timestamp),
      };

      for (const event of events) {
        if (event.type === 'MatchConfirmed') {
          match.state = 'confirmed';
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCompleted') {
          match.state = 'completed';
          match.completedAt = new Date(event.timestamp);
          match.notes = event.payload.notes;
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCancelled') {
          match.state = 'cancelled';
          match.cancelledAt = new Date(event.timestamp);
          match.notes = event.payload.reason;
          match.updatedAt = new Date(event.timestamp);
        }
      }

      return match;
    },

    /**
     * Find matches by organizer
     * 
     * @param {string} organizerId - Organizer actor ID
     * @returns {Promise<Object[]>} Array of match objects
     */
    async findByOrganizer(organizerId) {
      const events = await eventStore.getAllEvents();
      const matchEvents = events.filter(
        (e) =>
          e.type === 'MatchCreated' ||
          e.type === 'MatchConfirmed' ||
          e.type === 'MatchCompleted' ||
          e.type === 'MatchCancelled'
      );

      const matchMap = new Map();

      for (const event of matchEvents) {
        const matchId = event.aggregateId;
        
        if (!matchMap.has(matchId)) {
          matchMap.set(matchId, {
            matchId: matchId,
            state: 'proposed',
            organizerId: event.payload.organizerId,
            title: event.payload.title,
            description: event.payload.description || '',
            scheduledTime: new Date(event.payload.scheduledTime),
            durationMinutes: event.payload.durationMinutes,
            location: event.payload.location,
            participantIds: event.payload.participantIds || [],
            createdAt: new Date(event.timestamp),
            updatedAt: new Date(event.timestamp),
          });
        }

        const match = matchMap.get(matchId);
        
        if (event.type === 'MatchConfirmed') {
          match.state = 'confirmed';
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCompleted') {
          match.state = 'completed';
          match.completedAt = new Date(event.timestamp);
          match.notes = event.payload.notes;
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCancelled') {
          match.state = 'cancelled';
          match.cancelledAt = new Date(event.timestamp);
          match.notes = event.payload.reason;
          match.updatedAt = new Date(event.timestamp);
        }
      }

      const result = [];
      for (const match of matchMap.values()) {
        if (match.organizerId === organizerId || match.participantIds.includes(organizerId)) {
          result.push(match);
        }
      }
      return result;
    },

    /**
     * Find all matches
     * 
     * @returns {Promise<Object[]>} Array of all match objects
     */
    async findAll() {
      const events = await eventStore.getAllEvents();
      const matchEvents = events.filter(
        (e) =>
          e.type === 'MatchCreated' ||
          e.type === 'MatchConfirmed' ||
          e.type === 'MatchCompleted' ||
          e.type === 'MatchCancelled'
      );

      const matchMap = new Map();

      for (const event of matchEvents) {
        const matchId = event.aggregateId;
        
        if (!matchMap.has(matchId)) {
          matchMap.set(matchId, {
            matchId: matchId,
            state: 'proposed',
            organizerId: event.payload.organizerId,
            title: event.payload.title,
            description: event.payload.description || '',
            scheduledTime: new Date(event.payload.scheduledTime),
            durationMinutes: event.payload.durationMinutes,
            location: event.payload.location,
            participantIds: event.payload.participantIds || [],
            createdAt: new Date(event.timestamp),
            updatedAt: new Date(event.timestamp),
          });
        }

        const match = matchMap.get(matchId);
        
        if (event.type === 'MatchConfirmed') {
          match.state = 'confirmed';
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCompleted') {
          match.state = 'completed';
          match.completedAt = new Date(event.timestamp);
          match.notes = event.payload.notes;
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCancelled') {
          match.state = 'cancelled';
          match.cancelledAt = new Date(event.timestamp);
          match.notes = event.payload.reason;
          match.updatedAt = new Date(event.timestamp);
        }
      }

      return Array.from(matchMap.values());
    },
  };
}

module.exports = { createInMemoryMatchRepository };