import crypto from 'crypto';
import { Pool, QueryResultRow } from 'pg';
import { StoredEvent } from '../../types/match';
import { logger } from '../logging/logger';

/**
 * In-memory event store implementation
 * 
 * This is a simple implementation suitable for development and testing
 * Production should use PostgreSQL event store (see PostgresEventStore below)
 * 
 * Design decisions:
 * - Events stored in memory (append-only)
 * - Events indexed by aggregate ID for fast retrieval
 * - Simple event type filtering
 * - No persistence across restarts (for dev environment)
 */

class EventStore {
  events: Map<string, StoredEvent>;
  aggregateIndex: Map<string, Set<string>>;
  typeIndex: Map<string, Set<string>>;
  allEvents: StoredEvent[];

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
  async append(event: Partial<StoredEvent> & Pick<StoredEvent, 'type'>): Promise<void> {
    const eventId = event.id || crypto.randomUUID();
    const eventWithId: StoredEvent = {
      id: eventId,
      aggregateId: event.aggregateId || '',
      type: event.type,
      payload: event.payload ?? {},
      timestamp: event.timestamp instanceof Date ? event.timestamp : new Date(),
    };
    
    this.events.set(eventId, eventWithId);
    this.allEvents.push(eventWithId);
    logger.debug('In-memory event appended', {
      eventId,
      aggregateId: eventWithId.aggregateId,
      type: eventWithId.type
    });
    
    const aggregateId = eventWithId.aggregateId;
    if (aggregateId) {
      if (!this.aggregateIndex.has(aggregateId)) {
        this.aggregateIndex.set(aggregateId, new Set());
      }
      this.aggregateIndex.get(aggregateId)!.add(eventId);
    }
    
    const eventType = eventWithId.type;
    if (eventType) {
      if (!this.typeIndex.has(eventType)) {
        this.typeIndex.set(eventType, new Set());
      }
      this.typeIndex.get(eventType)!.add(eventId);
    }
  }

  /**
   * Get all events for a specific aggregate
   * 
   * @param {string} aggregateId - Aggregate identifier
   * @returns {Promise<Object[]>} Array of events for the aggregate
   */
  async getEventsByAggregate(aggregateId: string): Promise<StoredEvent[]> {
    const eventIds = this.aggregateIndex.get(aggregateId);
    if (!eventIds) {
      return [];
    }
    
    const events: StoredEvent[] = [];
    for (const eventId of eventIds) {
      const event = this.events.get(eventId);
      if (event) {
        events.push(event);
      }
    }
    
    logger.debug('In-memory events fetched by aggregate', { aggregateId, count: events.length });
    return events;
  }

  /**
   * Get all events of a specific type
   * 
   * @param {string} eventType - Event type name
   * @returns {Promise<Object[]>} Array of events
   */
  async getEventsByType(eventType: string): Promise<StoredEvent[]> {
    const eventIds = this.typeIndex.get(eventType);
    if (!eventIds) {
      return [];
    }
    
    const events: StoredEvent[] = [];
    for (const eventId of eventIds) {
      const event = this.events.get(eventId);
      if (event) {
        events.push(event);
      }
    }
    
    logger.debug('In-memory events fetched by type', { eventType, count: events.length });
    return events;
  }

  /**
   * Get all events in the store
   * 
   * @returns {Promise<Object[]>} Array of all events
   */
  async getAllEvents(): Promise<StoredEvent[]> {
    logger.debug('In-memory all events fetched', { count: this.allEvents.length });
    return [...this.allEvents];
  }

  /**
   * Get events since a specific timestamp
   * 
   * @param {Date} since - Start timestamp
   * @returns {Promise<Object[]>} Array of events
   */
  async getEventsSince(since: Date): Promise<StoredEvent[]> {
    return this.allEvents.filter((e) => e.timestamp >= since);
  }

  /**
   * Get event by ID
   * 
   * @param {string} eventId - Event identifier
   * @returns {Promise<Object|null>} Event object or null
   */
  async getEventById(eventId: string): Promise<StoredEvent | null> {
    return this.events.get(eventId) || null;
  }

  /**
   * Get count of events
   * 
   * @returns {Promise<number>} Number of events
   */
  async getEventCount(): Promise<number> {
    return this.allEvents.length;
  }

  /**
   * Clear all events (useful for testing)
   * 
   * @returns {Promise<void>}
   */
  async clear(): Promise<void> {
    this.events.clear();
    this.aggregateIndex.clear();
    this.typeIndex.clear();
    this.allEvents = [];
  }
}

// PostgreSQL-backed implementation -------------------------------------------

class PostgresEventStore {
  pool: Pool;
  /**
   * Create a PostgreSQL-based event store.
   * Guarantees the events table exists.
   *
   * @param {import('pg').Pool} pool
   * @returns {Promise<PostgresEventStore>}
   */
  static async create(pool: Pool): Promise<PostgresEventStore> {
    if (!pool) throw new Error('Postgres pool must be provided');
    const store = new PostgresEventStore(pool);
    await store._ensureTable();
    return store;
  }

  constructor(pool: Pool) {
    this.pool = pool;
  }

  async _ensureTable(): Promise<void> {
    const sql = `
      CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        aggregate_id TEXT,
        type TEXT NOT NULL,
        payload JSONB,
        timestamp TIMESTAMP NOT NULL
      );
    `;
    await this.pool.query(sql);
  }

  async append(event: Partial<StoredEvent> & Pick<StoredEvent, 'type'>): Promise<void> {
    const eventId = event.id || crypto.randomUUID();
    const sql = `
      INSERT INTO events(id, aggregate_id, type, payload, timestamp)
      VALUES($1,$2,$3,$4,$5)
    `;
    await this.pool.query(sql, [
      eventId,
      event.aggregateId || null,
      event.type,
      event.payload == null ? null : JSON.stringify(event.payload),
      event.timestamp instanceof Date ? event.timestamp : event.timestamp ? new Date(event.timestamp) : new Date()
    ]);
    logger.debug('Postgres event appended', {
      eventId,
      aggregateId: event.aggregateId || null,
      type: event.type
    });
  }

  _rowToEvent(row: QueryResultRow): StoredEvent {
    return {
      id: row.id,
      aggregateId: row.aggregate_id,
      type: row.type,
      payload: row.payload,
      timestamp: row.timestamp,
    };
  }

  async getEventsByAggregate(aggregateId: string): Promise<StoredEvent[]> {
    const res = await this.pool.query(
      `SELECT * FROM events WHERE aggregate_id = $1 ORDER BY timestamp ASC`,
      [aggregateId]
    );
    logger.debug('Postgres events fetched by aggregate', { aggregateId, count: res.rowCount || 0 });
    return res.rows.map((r) => this._rowToEvent(r));
  }

  async getAllEvents(): Promise<StoredEvent[]> {
    const res = await this.pool.query(`SELECT * FROM events ORDER BY timestamp ASC`);
    logger.debug('Postgres all events fetched', { count: res.rowCount || 0 });
    return res.rows.map((r) => this._rowToEvent(r));
  }

  async getEventsByType(eventType: string): Promise<StoredEvent[]> {
    const res = await this.pool.query(
      `SELECT * FROM events WHERE type = $1 ORDER BY timestamp ASC`,
      [eventType]
    );
    logger.debug('Postgres events fetched by type', { eventType, count: res.rowCount || 0 });
    return res.rows.map((r) => this._rowToEvent(r));
  }

  async getEventsSince(since: Date): Promise<StoredEvent[]> {
    const ts = since instanceof Date ? since : new Date(since);
    const res = await this.pool.query(
      `SELECT * FROM events WHERE timestamp >= $1 ORDER BY timestamp ASC`,
      [ts]
    );
    logger.debug('Postgres events fetched since', { since: ts.toISOString(), count: res.rowCount || 0 });
    return res.rows.map((r) => this._rowToEvent(r));
  }
}

export { EventStore, PostgresEventStore };
