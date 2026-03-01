import crypto from 'crypto';
import { EventStoreLike, Match, MatchRepositoryLike, MatchStateValue, StoredEvent } from '../../types/match';

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

function createInMemoryMatchRepository(eventStore: EventStoreLike): MatchRepositoryLike {
  return {
    /**
     * Save a match by persisting state change events
     * 
     * @param {Object} match - Match aggregate
     * @returns {Promise<void>}
     */
    async save(match: Match): Promise<void> {
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
    async findById(id: string): Promise<Match | null> {
      const events = await eventStore.getEventsByAggregate(id);
      const createdEvent = events.find((e) => e.type === 'MatchCreated');
      
      if (!createdEvent) {
        return null;
      }

      let match: Match = {
        matchId: id,
        state: ((createdEvent.payload as Partial<Match>).state || 'proposed') as MatchStateValue,
        organizerId: (createdEvent.payload as Partial<Match>).organizerId || '',
        title: (createdEvent.payload as Partial<Match>).title || '',
        description: (createdEvent.payload as Partial<Match>).description || '',
        scheduledTime: new Date((createdEvent.payload as Partial<Match>).scheduledTime || createdEvent.timestamp),
        durationMinutes: (createdEvent.payload as Partial<Match>).durationMinutes || 0,
        location: (createdEvent.payload as Partial<Match>).location || '',
        participantIds: (createdEvent.payload as Partial<Match>).participantIds || [],
        createdAt: new Date(createdEvent.timestamp),
        updatedAt: new Date(createdEvent.timestamp),
        completedAt: null,
        cancelledAt: null,
        notes: null,
        version: 0,
      };

      for (const event of events) {
        if (event.type === 'MatchConfirmed') {
          match.state = 'confirmed';
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCompleted') {
          match.state = 'completed';
          match.completedAt = new Date(event.timestamp);
          match.notes = (event.payload as { notes?: string }).notes || null;
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCancelled') {
          match.state = 'cancelled';
          match.cancelledAt = new Date(event.timestamp);
          match.notes = (event.payload as { reason?: string }).reason || null;
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
    async findByOrganizer(organizerId: string): Promise<Match[]> {
      const events = await eventStore.getAllEvents();
      const matchEvents = events.filter(
        (e) =>
          e.type === 'MatchCreated' ||
          e.type === 'MatchConfirmed' ||
          e.type === 'MatchCompleted' ||
          e.type === 'MatchCancelled'
      );

      const matchMap = new Map<string, Match>();

      for (const event of matchEvents) {
        const matchId = event.aggregateId;
        
        if (!matchMap.has(matchId)) {
          matchMap.set(matchId, {
            matchId: matchId,
            state: 'proposed',
            organizerId: (event.payload as Partial<Match>).organizerId || '',
            title: (event.payload as Partial<Match>).title || '',
            description: (event.payload as Partial<Match>).description || '',
            scheduledTime: new Date((event.payload as Partial<Match>).scheduledTime || event.timestamp),
            durationMinutes: (event.payload as Partial<Match>).durationMinutes || 0,
            location: (event.payload as Partial<Match>).location || '',
            participantIds: (event.payload as Partial<Match>).participantIds || [],
            createdAt: new Date(event.timestamp),
            updatedAt: new Date(event.timestamp),
            completedAt: null,
            cancelledAt: null,
            notes: null,
            version: 0,
          });
        }

        const match = matchMap.get(matchId);
        if (!match) {
          continue;
        }
        
        if (event.type === 'MatchConfirmed') {
          match.state = 'confirmed';
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCompleted') {
          match.state = 'completed';
          match.completedAt = new Date(event.timestamp);
          match.notes = (event.payload as { notes?: string }).notes || null;
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCancelled') {
          match.state = 'cancelled';
          match.cancelledAt = new Date(event.timestamp);
          match.notes = (event.payload as { reason?: string }).reason || null;
          match.updatedAt = new Date(event.timestamp);
        }
      }

      const result: Match[] = [];
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
    async findAll(): Promise<Match[]> {
      const events = await eventStore.getAllEvents();
      const matchEvents = events.filter(
        (e) =>
          e.type === 'MatchCreated' ||
          e.type === 'MatchConfirmed' ||
          e.type === 'MatchCompleted' ||
          e.type === 'MatchCancelled'
      );

      const matchMap = new Map<string, Match>();

      for (const event of matchEvents) {
        const matchId = event.aggregateId;
        
        if (!matchMap.has(matchId)) {
          matchMap.set(matchId, {
            matchId: matchId,
            state: 'proposed',
            organizerId: (event.payload as Partial<Match>).organizerId || '',
            title: (event.payload as Partial<Match>).title || '',
            description: (event.payload as Partial<Match>).description || '',
            scheduledTime: new Date((event.payload as Partial<Match>).scheduledTime || event.timestamp),
            durationMinutes: (event.payload as Partial<Match>).durationMinutes || 0,
            location: (event.payload as Partial<Match>).location || '',
            participantIds: (event.payload as Partial<Match>).participantIds || [],
            createdAt: new Date(event.timestamp),
            updatedAt: new Date(event.timestamp),
            completedAt: null,
            cancelledAt: null,
            notes: null,
            version: 0,
          });
        }

        const match = matchMap.get(matchId);
        if (!match) {
          continue;
        }
        
        if (event.type === 'MatchConfirmed') {
          match.state = 'confirmed';
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCompleted') {
          match.state = 'completed';
          match.completedAt = new Date(event.timestamp);
          match.notes = (event.payload as { notes?: string }).notes || null;
          match.updatedAt = new Date(event.timestamp);
        } else if (event.type === 'MatchCancelled') {
          match.state = 'cancelled';
          match.cancelledAt = new Date(event.timestamp);
          match.notes = (event.payload as { reason?: string }).reason || null;
          match.updatedAt = new Date(event.timestamp);
        }
      }

      return Array.from(matchMap.values());
    },
  };
}

export { createInMemoryMatchRepository };
