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

/**
 * Relational Graph interface for tracking actor relationships
 * 
 * This enables soft social logic:
 * - "If X attends, I attend" (positive constraint)
 * - "If X attends, I prefer not" (negative constraint)
 * - Confidence weighting for each constraint
 * 
 * Pattern: Graph Database interface - edges represent relationships
 */
const RelationalGraphInterface = {
  /**
   * Add a relational edge between actors
   * 
   * @param {string} sourceId - Source actor ID (the one making the constraint)
   * @param {string} targetId - Target actor ID (the one being referenced)
   * @param {string} constraintType - 'positive' or 'negative' constraint
   * @param {number} confidence - Confidence level (0-100)
   * @returns {Promise<void>}
   */
  addEdge: async function(sourceId, targetId, constraintType, confidence) {},

  /**
   * Get all edges for an actor
   * 
   * @param {string} actorId - Actor identifier
   * @returns {Promise<Object[]>} Array of edges with source, target, type, confidence
   */
  getEdgesForActor: async function(actorId) {},

  /**
   * Get reciprocal edges (where actor is the target)
   * 
   * @param {string} actorId - Actor identifier
   * @returns {Promise<Object[]>} Array of edges where actor is target
   */
  getReciprocalEdges: async function(actorId) {},

  /**
   * Check if a relationship exists
   * 
   * @param {string} sourceId - Source actor ID
   * @param {string} targetId - Target actor ID
   * @returns {Promise<boolean>} True if relationship exists
   */
  hasEdge: async function(sourceId, targetId) {},

  /**
   * Remove an edge
   * 
   * @param {string} sourceId - Source actor ID
   * @param {string} targetId - Target actor ID
   * @returns {Promise<void>}
   */
  removeEdge: async function(sourceId, targetId) {},
};

/**
 * Fairness Ledger interface for tracking match fairness metrics
 * 
 * This ensures the system biases toward social stability:
 * - Prevents one enthusiastic minority dominating
 * - Ensures majority mild dissatisfaction isn't ignored
 * - Provides metrics for transparency in ranking
 */
const FairnessLedgerInterface = {
  /**
   * Compute fairness metrics for a match
   * 
   * @param {string} matchId - Match identifier
   * @returns {Promise<Object>} Fairness metrics including:
   *   - totalRegret: Sum of all regret points
   *   - enthusiastCount: Count of Strong Yes votes
   *   - participationRate: Percentage of members who voted
   *   - fairnessScore: 0-1 fairness rating
   */
  computeFairnessMetrics: async function(matchId) {},

  /**
   * Get all fairness metrics for a set of matches
   * 
   * @param {string[]} matchIds - Match identifiers
   * @returns {Promise<Object[]>} Array of fairness metrics objects
   */
  getAllFairnessMetrics: async function(matchIds) {},

  /**
   * Rebuild fairness ledger from event history
   * 
   * @param {Object} eventStore - The event store instance
   * @returns {Promise<void>}
   */
  rebuildFromEvents: async function(eventStore) {},
};

const AgentRepositoryInterface = {
  /**
   * Find an agent by ID
   * @param {string} id - Agent identifier
   * @returns {Promise<Object|null>} Agent object or null
   */
  findById: async function(id) {},

  /**
   * Save an agent to storage
   * @param {Object} agent - Agent to persist
   * @returns {Promise<void>}
   */
  save: async function(agent) {},

  /**
   * Find all agents
   * @returns {Promise<Object[]>} Array of all agent objects
   */
  findAll: async function() {},
};

const AgentNegotiationRepositoryInterface = {
  /**
   * Find agent negotiation by ID
   * @param {string} negotiationId - Negotiation identifier
   * @returns {Promise<Object|null>} Agent negotiation object or null
   */
  findById: async function(negotiationId) {},

  /**
   * Save an agent negotiation
   * @param {Object} negotiation - Agent negotiation aggregate
   * @returns {Promise<void>}
   */
  save: async function(negotiation) {},

  /**
   * Find negotiations by match ID
   * @param {string} matchId - Match identifier
   * @returns {Promise<Object[]>} Array of negotiation objects
   */
  findByMatchId: async function(matchId) {},

  /**
   * Find all negotiations
   * @returns {Promise<Object[]>} Array of all negotiation objects
   */
  findAll: async function() {},
};

module.exports = {
  MatchRepositoryInterface,
  EventStoreInterface,
  ActorRepositoryInterface,
  TemporalIdentityRepositoryInterface,
  GovernanceRepositoryInterface,
  RelationalGraphInterface,
  FairnessLedgerInterface,
  AgentRepositoryInterface,
  AgentNegotiationRepositoryInterface,
};