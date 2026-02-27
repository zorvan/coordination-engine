/**
 * Repository interfaces define the contract between application and infrastructure layers
 * 
 * These are abstract interfaces that infrastructure implementations must satisfy
 * 
 * Pattern: Dependency Inversion - application depends on abstractions, not concretions
 * Pattern: Repository - encapsulates data access logic
 * 
 * Design decisions:
 * - All methods are async for flexibility (can be in-memory or DB)
 * - Interface methods return promises
 * - No implementation details in this layer
 */

const MatchRepositoryInterface = {
  /**
   * Find a match by ID
   * @param {string} id - Match identifier
   * @returns {Promise<Object|null>} Match object or null
   */
  findById: async function(id) {},

  /**
   * Save a match to storage
   * @param {Object} match - Match aggregate to persist
   * @returns {Promise<void>}
   */
  save: async function(match) {},

  /**
   * Find matches by organizer
   * @param {string} organizerId - Organizer actor ID
   * @returns {Promise<Object[]>} Array of match objects
   */
  findByOrganizer: async function(organizerId) {},

  /**
   * Find all matches
   * @returns {Promise<Object[]>} Array of all match objects
   */
  findAll: async function() {},
};

const EventStoreInterface = {
  /**
   * Append an event to the store
   * @param {Object} event - Event to append
   * @returns {Promise<void>}
   */
  append: async function(event) {},

  /**
   * Get all events for an aggregate
   * @param {string} aggregateId - Aggregate identifier
   * @returns {Promise<Object[]>} Array of events
   */
  getEventsByAggregate: async function(aggregateId) {},

  /**
   * Get all events of a specific type
   * @param {string} eventType - Event type name
   * @returns {Promise<Object[]>} Array of events
   */
  getEventsByType: async function(eventType) {},

  /**
   * Get all events in the store
   * @returns {Promise<Object[]>} Array of all events
   */
  getAllEvents: async function() {},

  /**
   * Get events since a specific timestamp
   * @param {Date} since - Start timestamp
   * @returns {Promise<Object[]>} Array of events
   */
  getEventsSince: async function(since) {},
};

const ActorRepositoryInterface = {
  /**
   * Find an actor by ID
   * @param {string} id - Actor identifier
   * @returns {Promise<Object|null>} Actor object or null
   */
  findById: async function(id) {},

  /**
   * Save an actor to storage
   * @param {Object} actor - Actor aggregate to persist
   * @returns {Promise<void>}
   */
  save: async function(actor) {},

  /**
   * Find actor by email
   * @param {string} email - Actor email
   * @returns {Promise<Object|null>} Actor object or null
   */
  findByEmail: async function(email) {},

  /**
   * Find all actors
   * @returns {Promise<Object[]>} Array of all actor objects
   */
  findAll: async function() {},
};

const TemporalIdentityRepositoryInterface = {
  /**
   * Find a temporal identity by ID
   * @param {string} identityId - Identity identifier
   * @returns {Promise<Object|null>} Temporal identity object or null
   */
  findById: async function(identityId) {},

  /**
   * Save a temporal identity to storage
   * @param {Object} identity - Identity to persist
   * @returns {Promise<void>}
   */
  save: async function(identity) {},
};

const GovernanceRepositoryInterface = {
  /**
   * Save a governance rule version
   * @param {Object} rule - Governance rule object
   * @returns {Promise<void>}
   */
  saveRuleVersion: async function(rule) {},

  /**
   * Get current version of a rule
   * @param {string} ruleId - Rule identifier
   * @returns {Promise<Object|null>} Current rule version
   */
  getCurrentVersion: async function(ruleId) {},

  /**
   * Get all versions of a rule
   * @param {string} ruleId - Rule identifier
   * @returns {Promise<Object[]>} Array of rule versions
   */
  getAllVersions: async function(ruleId) {},
};

module.exports = {
  MatchRepositoryInterface,
  EventStoreInterface,
  ActorRepositoryInterface,
  TemporalIdentityRepositoryInterface,
  GovernanceRepositoryInterface,
};