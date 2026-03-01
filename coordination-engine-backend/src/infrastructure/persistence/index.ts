import { PostgresEventStore } from './event-store';
import { createInMemoryMatchRepository as PostgresMatchRepository } from './match-repository';
import { createInMemoryActorRepository as PostgresActorRepository } from './actor-repository';
import { createTemporalIdentityRepository as PostgresTemporalIdentityRepository } from './temporal-identity-repository';
import { createGovernanceRepository as PostgresGovernanceRepository } from './governance-repository';

export { PostgresEventStore,
  PostgresMatchRepository,
  PostgresActorRepository,
  PostgresTemporalIdentityRepository,
  PostgresGovernanceRepository };
