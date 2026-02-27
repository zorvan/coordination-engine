/**
 * Temporal identity use case
 * 
 * Handles temporal identity management with role half-life mechanism
 * 
 * Pattern: Use Case - coordinates domain entities for specific business goals
 */

const { createTemporalIdentity } = require('../../domain/entities/temporal-identity');
const { createVersion, RoleHalfLife } = require('../../domain/services/temporal-identity');
const { createTemporalIdentityRepository } = require('../../infrastructure/persistence/temporal-identity-repository');

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
        const identity = createTemporalIdentity(identityId);
        identity.state = state;
        identity.createdAt = new Date();

        const repository = createTemporalIdentityRepository(eventStore);
        await repository.save(identity);

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
        const repository = createTemporalIdentityRepository(eventStore);
        const identity = await repository.findById(identityId);
        
        if (!identity) {
          throw new Error(`Identity ${identityId} not found`);
        }

        const versionObj = createVersion(version, validFrom, validTo);
        identity.addVersion(versionObj, validFrom, validTo);
        
        await repository.save(identity);
      },

      /**
       * Suspend an identity
       * 
       * @param {string} identityId - Identity identifier
       * @param {Date} suspendedAt - Timestamp of suspension
       * @returns {Promise<void>}
       */
      async suspendIdentity(identityId, suspendedAt) {
        const repository = createTemporalIdentityRepository(eventStore);
        const identity = await repository.findById(identityId);
        
        if (!identity) {
          throw new Error(`Identity ${identityId} not found`);
        }

        identity.suspend(suspendedAt);
        await repository.save(identity);
      },

      /**
       * Expire an identity
       * 
       * @param {string} identityId - Identity identifier
       * @param {Date} expiredAt - Timestamp of expiration
       * @returns {Promise<void>}
       */
      async expireIdentity(identityId, expiredAt) {
        const repository = createTemporalIdentityRepository(eventStore);
        const identity = await repository.findById(identityId);
        
        if (!identity) {
          throw new Error(`Identity ${identityId} not found`);
        }

        identity.expire(expiredAt);
        await repository.save(identity);
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
        const repository = createTemporalIdentityRepository(eventStore);
        const identity = await repository.findById(identityId);
        
        if (!identity) {
          throw new Error(`Identity ${identityId} not found`);
        }

        return identity.hasRole(role, atDate);
      },
    };
  },
};

module.exports = { TemporalIdentityUseCase };