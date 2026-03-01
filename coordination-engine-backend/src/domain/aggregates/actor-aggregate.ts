import { TrustValue as TrustLevel } from '../valuables/trust-value';
import { computeTrustScore as computeTrustScore } from '../valuables/trust-value';

interface TemporalIdentitySnapshot {
  state: string;
  trustLevel: string;
  validFrom: Date;
  validTo: Date | null;
}

interface ActorAggregateEntity {
  actorId: string;
  name: string;
  email: string;
  avatar: string;
  circles: string[];
  temporalIdentity: TemporalIdentitySnapshot | null;
  trustScore: number;
  trustLevel: string;
  acceptedMatches: number;
  completedMatches: number;
  createdAt: Date;
  updatedAt: Date;
  updateTemporalIdentity(state: string, trustLevel: string, validFrom: Date, validTo: Date | null): void;
  incrementAcceptedMatches(): void;
  incrementCompletedMatches(): void;
  computeTrustScore(): number;
  applyTrustUpdate(score: number, level: string, version: number, computedAt: Date): void;
}

const ActorAggregate = {
  create(id: string, name: string, email: string, avatar: string, circles: string[] = []): ActorAggregateEntity {
    const actor: ActorAggregateEntity = {
      actorId: id,
      name,
      email,
      avatar,
      circles,
      temporalIdentity: null,
      trustScore: 0,
      trustLevel: TrustLevel.VERY_LOW,
      acceptedMatches: 0,
      completedMatches: 0,
      createdAt: new Date(),
      updatedAt: new Date(),
      updateTemporalIdentity(state: string, trustLevel: string, validFrom: Date, validTo: Date | null) {
        this.temporalIdentity = {
          state,
          trustLevel,
          validFrom,
          validTo,
        };
        this.updatedAt = new Date();
      },
      incrementAcceptedMatches() {
        this.acceptedMatches++;
        this.updatedAt = new Date();
      },
      incrementCompletedMatches() {
        this.completedMatches++;
        this.updatedAt = new Date();
      },
      computeTrustScore() {
        return computeTrustScore(this.completedMatches, this.acceptedMatches);
      },
      applyTrustUpdate(score: number, level: string, _version: number, computedAt: Date) {
        this.trustScore = score;
        this.trustLevel = level;
        this.updatedAt = computedAt;
      },
    };

    return actor;
  },
};

export { ActorAggregate };
