const crypto = require('crypto');

/**
 * In-memory event store implementation
 * 
 * This is a simple implementation suitable for development and testing
 * Production should use PostgreSQL event store (see event-store-postgres.js)
 * 
 * Design decisions:
 * - Events stored in memory (append-only)
 * - Events indexed by aggregate ID for fast retrieval
 * - Simple event type filtering
 * - No persistence across restarts (for dev environment)
 */

class EventStore {
  constructor() {
    /**
     * Events storage
     * Format: Map<eventId, Event>
     */
    this.events = new Map();
    
    /**
     * Aggregate index
     * Format: Map<aggregateId, Set<eventId>>
     */
    this.aggregateIndex = new Map();
    
    /**
     * Event type index
     * Format: Map<eventType, Set<eventId>>
     */
    this.typeIndex = new Map();
    
    /**
     * All events in insertion order
     * @type {Array}
     */
    this.allEvents = [];
  }

  /**
   * Append an event to the store
   * 
   * @param {Object} event - Event object with id, type, payload, timestamp
   * @returns {Promise<void>}
   */
  async append(event) {
    const eventId = event.id || crypto.randomUUID();
    const eventWithId = { ...event, id: eventId };
    
    this.events.set(eventId, eventWithId);
    this.allEvents.push(eventWithId);
    
    const aggregateId = eventWithId.aggregateId;
    if (aggregateId) {
      if (!this.aggregateIndex.has(aggregateId)) {
        this.aggregateIndex.set(aggregateId, new Set());
      }
      this.aggregateIndex.get(aggregateId).add(eventId);
    }
    
    const eventType = eventWithId.type;
    if (eventType) {
      if (!this.typeIndex.has(eventType)) {
        this.typeIndex.set(eventType, new Set());
      }
      this.typeIndex.get(eventType).add(eventId);
    }
  }

  /**
   * Get all events for a specific aggregate
   * 
   * @param {string} aggregateId - Aggregate identifier
   * @returns {Promise<Object[]>} Array of events for the aggregate
   */
  async getEventsByAggregate(aggregateId) {
    const eventIds = this.aggregateIndex.get(aggregateId);
    if (!eventIds) {
      return [];
    }
    
    const events = [];
    for (const eventId of eventIds) {
      const event = this.events.get(eventId);
      if (event) {
        events.push(event);
      }
    }
    
    return events;
  }

  /**
   * Get all events of a specific type
   * 
   * @param {string} eventType - Event type name
   * @returns {Promise<Object[]>} Array of events
   */
  async getEventsByType(eventType) {
    const eventIds = this.typeIndex.get(eventType);
    if (!eventIds) {
      return [];
    }
    
    const events = [];
    for (const eventId of eventIds) {
      const event = this.events.get(eventId);
      if (event) {
        events.push(event);
      }
    }
    
    return events;
  }

  /**
   * Get all events in the store
   * 
   * @returns {Promise<Object[]>} Array of all events
   */
  async getAllEvents() {
    return [...this.allEvents];
  }

  /**
   * Get events since a specific timestamp
   * 
   * @param {Date} since - Start timestamp
   * @returns {Promise<Object[]>} Array of events
   */
  async getEventsSince(since) {
    return this.allEvents.filter((e) => e.timestamp >= since);
  }

  /**
   * Get event by ID
   * 
   * @param {string} eventId - Event identifier
   * @returns {Promise<Object|null>} Event object or null
   */
  async getEventById(eventId) {
    return this.events.get(eventId) || null;
  }

  /**
   * Get count of events
   * 
   * @returns {Promise<number>} Number of events
   */
  async getEventCount() {
    return this.allEvents.length;
  }

  /**
   * Clear all events (useful for testing)
   * 
   * @returns {Promise<void>}
   */
  async clear() {
    this.events.clear();
    this.aggregateIndex.clear();
    this.typeIndex.clear();
    this.allEvents = [];
  }
}

module.exports = { EventStore };