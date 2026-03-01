/**
 * Temporal identity use case
 * 
 * Handles temporal identity management with role half-life mechanism
 * 
 * Pattern: Use Case - coordinates domain entities for specific business goals
 */

import crypto from 'crypto';

const TemporalIdentityUseCase = {
  /**
   * Create temporal identity use case
   * 
   * @param {Object} eventStore - Event store for audit trail
   * @returns {Object} Use case with methods
   */
  create(eventStore) {
    return {
      /**
       * Create a new temporal identity for an actor
       * 
       * @param {string} identityId - Identity identifier
       * @param {string} state - Initial state (active, suspended, expired)
       * @returns {Promise<string>} Identity ID
       */
      async createIdentity(identityId, state = 'active') {
        const now = new Date();
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: identityId,
          type: 'TemporalIdentityCreated',
          timestamp: now,
          payload: {
            identityId,
            state,
          },
        });

        return identityId;
      },

      /**
       * Add a version to an identity
       * 
       * @param {string} identityId - Identity identifier
       * @param {number} version - Version number
       * @param {Date} validFrom - When version becomes active
       * @param {Date} validTo - When version expires (optional)
       * @returns {Promise<void>}
       */
      async addVersion(identityId, version, validFrom, validTo) {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: identityId,
          type: 'TemporalIdentityVersioned',
          timestamp: validFrom,
          payload: {
            identityId,
            version,
            validFrom,
            validTo,
          },
        });
      },

      /**
       * Suspend an identity
       * 
       * @param {string} identityId - Identity identifier
       * @param {Date} suspendedAt - Timestamp of suspension
       * @returns {Promise<void>}
       */
      async suspendIdentity(identityId, suspendedAt) {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: identityId,
          type: 'TemporalIdentitySuspended',
          timestamp: suspendedAt || new Date(),
          payload: {
            identityId,
            suspendedAt: suspendedAt || new Date(),
          },
        });
      },

      /**
       * Expire an identity
       * 
       * @param {string} identityId - Identity identifier
       * @param {Date} expiredAt - Timestamp of expiration
       * @returns {Promise<void>}
       */
      async expireIdentity(identityId, expiredAt) {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: identityId,
          type: 'TemporalIdentityExpired',
          timestamp: expiredAt || new Date(),
          payload: {
            identityId,
            expiredAt: expiredAt || new Date(),
          },
        });
      },

      /**
       * Get current version of an identity
       * 
       * @param {string} identityId - Identity identifier
       * @param {Date} atDate - Date to check (default: now)
       * @returns {Promise<Object|null>} Current version or null
       */
      async getCurrentVersion(identityId, atDate = new Date()) {
        const events = await eventStore.getEventsByAggregate(identityId);
        
        let currentVersion = null;
        
        for (const event of events) {
          if (event.type === 'TemporalIdentityVersioned') {
            const version = event.payload;
            if (version.validFrom <= atDate) {
              if (!version.validTo || version.validTo >= atDate) {
                currentVersion = version;
              }
            }
          }
        }

        return currentVersion;
      },

      /**
       * Get all versions of an identity
       * 
       * @param {string} identityId - Identity identifier
       * @returns {Promise<Object[]>} Array of versions
       */
      async getVersions(identityId) {
        const events = await eventStore.getEventsByAggregate(identityId);
        
        return events
          .filter((e) => e.type === 'TemporalIdentityVersioned')
          .map((e) => e.payload);
      },

      /**
       * Check if identity has a role at a specific date
       * 
       * @param {string} identityId - Identity identifier
       * @param {string} role - Role to check
       * @param {Date} atDate - Date to check at (default: now)
       * @returns {Promise<boolean>} True if identity has role
       */
      async hasRole(identityId, role, atDate = new Date()) {
        const version = await this.getCurrentVersion(identityId, atDate);
        return version !== null;
      },
    };
  },
};

export { TemporalIdentityUseCase };