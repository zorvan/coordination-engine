/**
 * Role entity for temporal identity management
 * 
 * Represents a role that can be assigned to actors
 * with temporal validity (half-life mechanism)
 */

const RoleType = {
  ORGANIZER: 'organizer',
  PARTICIPANT: 'participant',
  MODERATOR: 'moderator',
  OBSERVER: 'observer',
} as const;

const RoleHalfLife = {
  DAY: 24 * 60 * 60 * 1000,
  WEEK: 7 * 24 * 60 * 60 * 1000,
  MONTH: 30 * 24 * 60 * 60 * 1000,
  YEAR: 365 * 24 * 60 * 60 * 1000,
} as const;

type RoleTypeValue = (typeof RoleType)[keyof typeof RoleType];

interface Role {
  id: string;
  name: string;
  type: RoleTypeValue;
  validFrom: Date;
  validTo: Date | null;
  isExpired: boolean;
  createdAt: Date;
}

/**
 * Create a new role
 * 
 * @param {string} id - Unique role identifier
 * @param {string} name - Role name
 * @param {string} type - Role type (organizer, participant, moderator, observer)
 * @param {Date} validFrom - When the role becomes active
 * @param {Date} validTo - When the role expires (optional)
 * @returns {Object} Role entity
 */
function createRole(id: string, name: string, type: RoleTypeValue, validFrom: Date, validTo: Date | null = null): Role {
  if (!Object.values(RoleType).includes(type)) {
    throw new Error(`Invalid role type: ${type}`);
  }

  // Check if role is expired
  const now = new Date();
  const isExpired = !!validTo && now > validTo;

  return {
    id,
    name,
    type,
    validFrom,
    validTo,
    isExpired,
    createdAt: new Date(),
  };
}

/**
 * Check if a role is currently valid
 * 
 * @param {Object} role - Role entity
 * @param {Date} atDate - Date to check validity at (default: now)
 * @returns {boolean} True if role is valid
 */
function isRoleValid(role: Role, atDate: Date = new Date()): boolean {
  if (role.isExpired) return false;
  if (atDate < role.validFrom) return false;
  if (role.validTo && atDate > role.validTo) return false;
  return true;
}

/**
 * Check if a role will expire within a given time frame
 * 
 * @param {Object} role - Role entity
 * @param {number} timeFrameMs - Time frame in milliseconds
 * @returns {boolean} True if role will expire within time frame
 */
function willExpire(role: Role, timeFrameMs: number): boolean {
  if (!role.validTo) return false;
  
  const now = new Date();
  const expirationTime = role.validTo.getTime();
  const currentTime = now.getTime();
  
  return (expirationTime - currentTime) <= timeFrameMs;
}

export { RoleType,
  RoleHalfLife,
  createRole,
  isRoleValid,
  willExpire, };
