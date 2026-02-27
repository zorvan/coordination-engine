const crypto = require('crypto');

/**
 * In-memory governance repository for development
 * 
 * Uses event store as backing storage and builds read model from events
 * 
 * Pattern: Read Model / Projection - derived state from event stream
 * 
 * @param {Object} eventStore - The event store instance
 * @returns {Object} Governance repository implementation
 */

function createInMemoryGovernanceRepository(eventStore) {
  return {
    /**
     * Save a governance rule version
     * 
     * @param {Object} rule - Governance rule object with type, version, content
     * @returns {Promise<void>}
     */
    async saveRuleVersion(rule) {
      await eventStore.append({
        id: crypto.randomUUID(),
        aggregateId: rule.ruleId,
        type: 'GovernanceRuleVersioned',
        timestamp: new Date(),
        payload: rule,
      });
    },

    /**
     * Get current version of a rule
     * 
     * @param {string} ruleId - Rule identifier
     * @returns {Promise<Object|null>} Current rule version or null
     */
    async getCurrentVersion(ruleId) {
      const events = await eventStore.getEventsByAggregate(ruleId);
      const ruleEvents = events.filter((e) => e.type === 'GovernanceRuleVersioned');
      
      if (ruleEvents.length === 0) {
        return null;
      }

      // Return the latest version
      return ruleEvents[ruleEvents.length - 1].payload;
    },

    /**
     * Get all versions of a rule
     * 
     * @param {string} ruleId - Rule identifier
     * @returns {Promise<Object[]>} Array of rule versions
     */
    async getAllVersions(ruleId) {
      const events = await eventStore.getEventsByAggregate(ruleId);
      return events.filter((e) => e.type === 'GovernanceRuleVersioned');
    },
  };
}

module.exports = { createInMemoryGovernanceRepository };