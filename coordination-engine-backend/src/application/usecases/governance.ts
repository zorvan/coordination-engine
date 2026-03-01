/**
 * Governance use case
 * 
 * Handles governance rule management with versioning
 * 
 * Pattern: Use Case - coordinates domain entities for specific business goals
 */

import crypto from 'crypto';

const GovernanceUseCase = {
  /**
   * Create governance use case
   * 
   * @param {Object} governanceRepository - Repository for rule storage
   * @param {Object} eventStore - Event store for audit trail
   * @returns {Object} Use case with methods
   */
  create(governanceRepository, eventStore) {
    return {
      /**
       * Create a new governance rule
       * 
       * @param {string} ruleId - Rule identifier
       * @param {string} name - Rule name
       * @param {string} type - Rule type (validation, restriction, preference, confidence)
       * @param {Object} content - Rule content/configuration
       * @param {Date} activatedAt - When rule becomes active
       * @param {Date} expiresAt - When rule expires (optional)
       * @returns {Promise<string>} Rule ID
       */
      async createRule(ruleId, name, type, content, activatedAt, expiresAt) {
        const now = new Date();
        const isActive = activatedAt <= now && (!expiresAt || expiresAt >= now);
        
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: ruleId,
          type: 'GovernanceRuleVersioned',
          timestamp: now,
          payload: {
            ruleId,
            name,
            type,
            content,
            activatedAt,
            expiresAt,
            isActive,
            version: 1,
            createdAt: now,
          },
        });

        return ruleId;
      },

      /**
       * Get current active rule version
       * 
       * @param {string} ruleId - Rule identifier
       * @param {Date} atDate - Date to check validity (default: now)
       * @returns {Promise<Object|null>} Current rule version or null
       */
      async getCurrentRuleVersion(ruleId, atDate = new Date()) {
        const events = await eventStore.getEventsByAggregate(ruleId);
        
        let latestValidVersion = null;
        
        for (const event of events) {
          if (event.type === 'GovernanceRuleVersioned') {
            const payload = event.payload;
            
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
       * Check if a rule is active at a specific date
       * 
       * @param {string} ruleId - Rule identifier
       * @param {Date} atDate - Date to check (default: now)
       * @returns {Promise<boolean>} True if rule is active
       */
      async isRuleActive(ruleId, atDate = new Date()) {
        const version = await this.getCurrentRuleVersion(ruleId, atDate);
        return version !== null;
      },

      /**
       * Get all versions of a rule
       * 
       * @param {string} ruleId - Rule identifier
       * @returns {Promise<Object[]>} Array of rule versions
       */
      async getRuleVersions(ruleId) {
        const events = await eventStore.getEventsByAggregate(ruleId);
        
        return events
          .filter((e) => e.type === 'GovernanceRuleVersioned')
          .map((e) => e.payload);
      },
    };
  },
};

export { GovernanceUseCase };