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

function createTemporalIdentity(identityId) {
  const identity = {
    identityId,
    versions: [],
    currentVersionIndex: -1,
    createdAt: new Date(),
    updatedAt: null,
  };

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

  identity.getCurrentVersion = function() {
    if (this.currentVersionIndex === -1) {
      throw new Error('No current identity version exists');
    }
    return this.versions[this.currentVersionIndex];
  };

  identity.addVersion = function(version, validFrom, validTo) {
    this.versions.push({
      version,
      validFrom,
      validTo,
    });
    this.currentVersionIndex = this.versions.length - 1;
    this.updatedAt = new Date();
  };

  identity.hasRole = function(role, atDate) {
    const version = this.getVersion(atDate);
    return version !== null;
  };

  return identity;
}

module.exports = {
  IdentityState,
  TrustLevel,
  createTemporalIdentity,
};