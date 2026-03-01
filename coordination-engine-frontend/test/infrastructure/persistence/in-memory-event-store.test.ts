/**
 * In-memory event store tests.
 * 
 * These tests verify the event store functionality including append,
 * retrieval by aggregate and type, and filtering.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { InMemoryEventStore } from '@infrastructure/persistence/in-memory-event-store'
import { DomainEvent, MatchCreated } from '@domain/events/domain-event'

/**
 * Tests for the InMemoryEventStore.
 */
describe('InMemoryEventStore', () => {
  let eventStore: InMemoryEventStore
  const testAggregateId = 'test-aggregate-123'

  /**
   * Setup before each test.
   */
  beforeEach(() => {
    eventStore = new InMemoryEventStore()
  })

  /**
   * Tests appending an event to the store.
   */
  it('should append an event', async () => {
    const event = new MatchCreated(
      testAggregateId,
      'organizer1',
      'Test Match',
      'Test description',
      new Date(),
      60,
      'Location',
      ['participant1']
    )

    // The aggregateId is extracted from the payload - MatchCreated uses 'id' field
    expect(event.aggregateId).toBe(testAggregateId)

    await eventStore.append(event)

    // The key in aggregateIndex is the aggregateId without prefix
    const events = await eventStore.getEventsByAggregate(testAggregateId)
    expect(events.length).toBe(1)
    expect(events[0].id).toBe(event.id)
    expect(events[0].type).toBe('MatchCreated')
  })
})