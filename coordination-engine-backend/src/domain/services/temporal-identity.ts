import { RoleType, RoleHalfLife } from '../entities/role';

/**
 * TemporalIdentity Version
 * 
 * Represents a version of an actor's temporal identity with roles
 * and half-life expiration
 */

interface TemporalVersion {
  version: number;
  validFrom: Date;
  validTo: Date | null;
  createdAt: Date;
  expired?: boolean;
  expiredAt?: Date | null;
}

function createVersion(version: number, validFrom: Date, validTo: Date | null = null): TemporalVersion {
  return {
    version,
    validFrom,
    validTo,
    createdAt: new Date(),
  };
}

/**
 * Apply role half-life expiration check
 * 
 * @param {Object} version - Version object
 * @param {Date} now - Current date
 * @returns {Object} Updated version with expiration status
 */
function applyRoleHalfLife(version: TemporalVersion, now: Date = new Date()): TemporalVersion {
  if (version.validTo && now > version.validTo) {
    return {
      ...version,
      expired: true,
      expiredAt: now,
    };
  }
  
  return {
    ...version,
    expired: false,
    expiredAt: null,
  };
}

/**
 * Calculate remaining validity period
 * 
 * @param {Object} version - Version object
 * @param {Date} now - Current date
 * @returns {number} Remaining milliseconds (0 if expired)
 */
function getRemainingValidity(version: TemporalVersion, now: Date = new Date()): number {
  if (version.expired) return 0;
  if (!version.validTo) return Infinity;
  
  const remaining = version.validTo.getTime() - now.getTime();
  return Math.max(0, remaining);
}

export { createVersion,
  applyRoleHalfLife,
  getRemainingValidity,
  RoleType,
  RoleHalfLife, };
