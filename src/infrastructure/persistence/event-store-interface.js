/**
 * Event Store interface for PostgreSQL-based implementations
 * 
 * This defines the contract that infrastructure implementations must satisfy
 * 
 * Design decisions:
 * - All methods async for database flexibility
 * - Timestamp-based ordering for event sourcing
 * - Aggregate-based event retrieval for projection building
 */

const PostgresEventStoreInterface = {
  /**
   * Append an event to the event store
   * @param {Object} event - Event object with id, type, payload, timestamp
   * @returns {Promise<void>}
   */
  append: async function(event) {},

  /**
   * Get all events for a specific aggregate
   * @param {string} aggregateId - Aggregate identifier
   * @returns {Promise<Object[]>} Array of events
   */
  getEventsByAggregate: async function(aggregateId) {},

  /**
   * Get all events in the store
   * @returns {Promise<Object[]>} Array of all events
   */
  getAllEvents: async function() {},

  /**
   * Get events since a specific timestamp
   * @param {Date} timestamp - Start timestamp
   * @returns {Promise<Object[]>} Array of events
   */
  getEventsSince: async function(timestamp) {},
};

module.exports = {
  PostgresEventStoreInterface,
};