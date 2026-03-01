/**
 * In-memory event store implementation.
 * 
 * This is a simple implementation for frontend use, storing events in memory.
 * For production, this would be replaced with a server-backed implementation.
 * 
 * Design decisions:
 * - Events stored in memory (not persisted across reloads)
 * - Events indexed by aggregate ID for fast retrieval
 * - Simple event type filtering
 * - Clear API for event store operations
 */

import { DomainEvent } from '@domain/events/domain-event'
import { generateEventId } from '@domain/events/event-utils'

/**
 * In-memory event store.
 * 
 * This class provides event storage for the frontend application.
 * Since the frontend doesn't have a persistent database, this store
 * is cleared on page reload.
 * 
 * @remarks
 * For production use with persistence, this should be replaced with
 * a backend service or localStorage implementation.
 */
export class InMemoryEventStore {
  /**
   * Storage for all events.
   */
  private events: Map<string, DomainEvent> = new Map()
  
  /**
   * Index by aggregate ID for fast lookup.
   */
  private aggregateIndex: Map<string, Set<string>> = new Map()
  
  /**
   * Index by event type for filtering.
   */
  private typeIndex: Map<string, Set<string>> = new Map()
  
  /**
   * All events in insertion order.
   */
  private allEvents: DomainEvent[] = []
  
  /**
   * Append an event to the store.
   * 
   * @param event - Event to append
   */
  async append(event: DomainEvent): Promise<void> {
    const eventId = event.id || generateEventId()
    event.id = eventId

    this.events.set(eventId, event)
    this.allEvents.push(event)

    const aggregateId = event.aggregateId
    if (aggregateId) {
      if (!this.aggregateIndex.has(aggregateId)) {
        this.aggregateIndex.set(aggregateId, new Set())
      }
      this.aggregateIndex.get(aggregateId)?.add(eventId)
    }

    const eventType = event.type
    if (eventType) {
      if (!this.typeIndex.has(eventType)) {
        this.typeIndex.set(eventType, new Set())
      }
      this.typeIndex.get(eventType)?.add(eventId)
    }
  }
  
  /**
   * Get all events for a specific aggregate.
   * 
   * @param aggregateId - Aggregate identifier
   * @returns Array of events for the aggregate
   */
  async getEventsByAggregate(aggregateId: string): Promise<DomainEvent[]> {
    const eventIds = this.aggregateIndex.get(aggregateId)
    if (!eventIds) {
      return []
    }
    
    const events: DomainEvent[] = []
    for (const eventId of eventIds) {
      const event = this.events.get(eventId)
      if (event) {
        events.push(event)
      }
    }
    
    return events
  }
  
  /**
   * Get all events of a specific type.
   * 
   * @param eventType - Event type name
   * @returns Array of events
   */
  async getEventsByType(eventType: string): Promise<DomainEvent[]> {
    const eventIds = this.typeIndex.get(eventType)
    if (!eventIds) {
      return []
    }
    
    const events: DomainEvent[] = []
    for (const eventId of eventIds) {
      const event = this.events.get(eventId)
      if (event) {
        events.push(event)
      }
    }
    
    return events
  }
  
  /**
   * Get all events in the store.
   * 
   * @returns Array of all events
   */
  async getAllEvents(): Promise<DomainEvent[]> {
    return [...this.allEvents]
  }
  
  /**
   * Get events since a specific timestamp.
   * 
   * @param since - Start timestamp
   * @returns Array of events
   */
  async getEventsSince(since: Date): Promise<DomainEvent[]> {
    return this.allEvents.filter((e) => e.timestamp >= since)
  }
  
  /**
   * Get event by ID.
   * 
   * @param eventId - Event identifier
   * @returns Event object or null
   */
  async getEventById(eventId: string): Promise<DomainEvent | null> {
    return this.events.get(eventId) || null
  }
  
  /**
   * Get count of events.
   * 
   * @returns Number of events
   */
  async getEventCount(): Promise<number> {
    return this.allEvents.length
  }
  
  /**
   * Clear all events (useful for testing).
   */
  async clear(): Promise<void> {
    this.events.clear()
    this.aggregateIndex.clear()
    this.typeIndex.clear()
    this.allEvents = []
  }
}
