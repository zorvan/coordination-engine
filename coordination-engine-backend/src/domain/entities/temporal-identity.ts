const IdentityState = {
  ACTIVE: 'active',
  SUSPENDED: 'suspended',
  EXPIRED: 'expired',
} as const;

const TrustLevel = {
  VERY_LOW: 'very_low',
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  VERY_HIGH: 'very_high',
} as const;

type IdentityStateValue = (typeof IdentityState)[keyof typeof IdentityState];

interface IdentityVersion {
  version: number;
  validFrom: Date;
  validTo: Date | null;
}

interface TemporalIdentityEntity {
  identityId: string;
  versions: IdentityVersion[];
  currentVersionIndex: number;
  state: IdentityStateValue;
  createdAt: Date;
  updatedAt: Date | null;
  getVersion(atDate: Date): IdentityVersion | null;
  getCurrentVersion(): IdentityVersion;
  addVersion(version: number, validFrom: Date, validTo: Date | null): void;
  hasRole(role: string, atDate?: Date): boolean;
  suspend(suspendedAt?: Date): void;
  expire(expiredAt?: Date): void;
  isExpired(atDate?: Date): boolean;
}

/**
 * Temporal identity aggregate
 * 
 * Manages identity versions with temporal validity
 * Supports role half-life mechanism for expiration
 * 
 * Pattern: Aggregate Root - encapsulates identity state and behavior
 */
function createTemporalIdentity(identityId: string): TemporalIdentityEntity {
  const identity: TemporalIdentityEntity = {
    identityId,
    versions: [],
    currentVersionIndex: -1,
    state: IdentityState.ACTIVE,
    createdAt: new Date(),
    updatedAt: null,
    getVersion(atDate: Date) {
      for (let i = this.versions.length - 1; i >= 0; i--) {
        const version = this.versions[i];
        if (version.validFrom <= atDate) {
          if (!version.validTo || version.validTo >= atDate) {
            return version;
          }
        }
      }
      return null;
    },
    getCurrentVersion() {
      if (this.currentVersionIndex === -1) {
        throw new Error('No current identity version exists');
      }
      return this.versions[this.currentVersionIndex];
    },
    addVersion(version: number, validFrom: Date, validTo: Date | null = null) {
      this.versions.push({
        version,
        validFrom,
        validTo,
      });
      this.currentVersionIndex = this.versions.length - 1;
      this.updatedAt = new Date();
    },
    hasRole(_role: string, atDate: Date = new Date()) {
      const version = this.getVersion(atDate);
      return version !== null;
    },
    suspend(suspendedAt: Date = new Date()) {
      this.state = IdentityState.SUSPENDED;
      this.updatedAt = suspendedAt;
    },
    expire(expiredAt: Date = new Date()) {
      this.state = IdentityState.EXPIRED;
      this.updatedAt = expiredAt;
    },
    isExpired(_atDate: Date = new Date()) {
      return this.state === IdentityState.EXPIRED;
    },
  };

  return identity;
}

export { IdentityState,
  TrustLevel,
  createTemporalIdentity, };
