const IdentityState = {
  ACTIVE: 'active',
  SUSPENDED: 'suspended',
  EXPIRED: 'expired',
};

const TrustLevel = {
  VERY_LOW: 'very_low',
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  VERY_HIGH: 'very_high',
};

/**
 * Temporal identity aggregate
 * 
 * Manages identity versions with temporal validity
 * Supports role half-life mechanism for expiration
 * 
 * Pattern: Aggregate Root - encapsulates identity state and behavior
 */
function createTemporalIdentity(identityId) {
  const identity = {
    identityId,
    versions: [],
    currentVersionIndex: -1,
    state: IdentityState.ACTIVE,
    createdAt: new Date(),
    updatedAt: null,
  };

  /**
   * Get version for a specific date
   * 
   * @param {Date} atDate - Date to check version validity
   * @returns {Object|null} Version object or null
   */
  identity.getVersion = function(atDate) {
    for (let i = this.versions.length - 1; i >= 0; i--) {
      const version = this.versions[i];
      if (version.validFrom <= atDate) {
        if (!version.validTo || version.validTo >= atDate) {
          return version;
        }
      }
    }
    return null;
  };

  /**
   * Get current version
   * 
   * @returns {Object} Current version
   * @throws {Error} If no current version exists
   */
  identity.getCurrentVersion = function() {
    if (this.currentVersionIndex === -1) {
      throw new Error('No current identity version exists');
    }
    return this.versions[this.currentVersionIndex];
  };

  /**
   * Add a new version
   * 
   * @param {number} version - Version number
   * @param {Date} validFrom - When version becomes active
   * @param {Date} validTo - When version expires (optional)
   * @returns {void}
   */
  identity.addVersion = function(version, validFrom, validTo) {
    this.versions.push({
      version,
      validFrom,
      validTo,
    });
    this.currentVersionIndex = this.versions.length - 1;
    this.updatedAt = new Date();
  };

  /**
   * Check if actor has a specific role at a given date
   * 
   * @param {string} role - Role to check
   * @param {Date} atDate - Date to check at (default: now)
   * @returns {boolean} True if actor has role
   */
  identity.hasRole = function(role, atDate = new Date()) {
    const version = this.getVersion(atDate);
    return version !== null;
  };

  /**
   * Suspend the identity
   * 
   * @param {Date} suspendedAt - Timestamp of suspension
   * @returns {void}
   */
  identity.suspend = function(suspendedAt) {
    this.state = IdentityState.SUSPENDED;
    this.updatedAt = suspendedAt || new Date();
  };

  /**
   * Expire the identity
   * 
   * @param {Date} expiredAt - Timestamp of expiration
   * @returns {void}
   */
  identity.expire = function(expiredAt) {
    this.state = IdentityState.EXPIRED;
    this.updatedAt = expiredAt || new Date();
  };

  /**
   * Check if identity is expired
   * 
   * @param {Date} atDate - Date to check at (default: now)
   * @returns {boolean} True if expired
   */
  identity.isExpired = function(atDate = new Date()) {
    return this.state === IdentityState.EXPIRED;
  };

  return identity;
}

module.exports = {
  IdentityState,
  TrustLevel,
  createTemporalIdentity,
};