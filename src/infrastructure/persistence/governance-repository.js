/**
 * Governance repository for Phase 4
 * 
 * Manages governance rule versioning with temporal validity
 * 
 * Pattern: Event Sourcing - governance changes as events
 */

const crypto = require('crypto');

/**
 * Governance repository implementation
 * 
 * @param {Object} eventStore - The event store instance
 * @returns {Object} Governance repository implementation
 */
function createGovernanceRepository(eventStore) {
  return {
    /**
     * Save a governance rule version
     * 
     * @param {Object} rule - Governance rule entity
     * @returns {Promise<void>}
     */
    async saveRuleVersion(rule) {
      await eventStore.append({
        id: crypto.randomUUID(),
        aggregateId: rule.ruleId,
        type: 'GovernanceRuleVersioned',
        timestamp: rule.createdAt,
        payload: {
          ruleId: rule.ruleId,
          name: rule.name,
          type: rule.type,
          content: rule.content,
          activatedAt: rule.activatedAt,
          expiresAt: rule.expiresAt,
          isActive: rule.isActive,
        },
      });
    },

    /**
     * Get current version of a rule
     * 
     * @param {string} ruleId - Rule identifier
     * @param {Date} atDate - Date to check validity (default: now)
     * @returns {Promise<Object|null>} Current rule version or null
     */
    async getCurrentVersion(ruleId, atDate = new Date()) {
      const events = await eventStore.getEventsByAggregate(ruleId);
      
      if (events.length === 0) {
        return null;
      }

      // Find the latest active version
      let latestValidVersion = null;
      
      for (const event of events) {
        if (event.type === 'GovernanceRuleVersioned') {
          const payload = event.payload;
          
          // Check if rule is active at the given date
          if (payload.activatedAt <= atDate) {
            if (!payload.expiresAt || payload.expiresAt >= atDate) {
              latestValidVersion = payload;
            }
          }
        }
      }

      return latestValidVersion;
    },

    /**
     * Get all versions of a rule
     * 
     * @param {string} ruleId - Rule identifier
     * @returns {Promise<Object[]>} Array of rule versions
     */
    async getAllVersions(ruleId) {
      const events = await eventStore.getEventsByAggregate(ruleId);
      
      return events
        .filter((e) => e.type === 'GovernanceRuleVersioned')
        .map((e) => e.payload);
    },

    /**
     * Check if a rule is active at a specific date
     * 
     * @param {string} ruleId - Rule identifier
     * @param {Date} atDate - Date to check (default: now)
     * @returns {Promise<boolean>} True if rule is active
     */
    async isRuleActive(ruleId, atDate = new Date()) {
      const version = await this.getCurrentVersion(ruleId, atDate);
      return version !== null;
    },
  };
}

module.exports = { createGovernanceRepository };