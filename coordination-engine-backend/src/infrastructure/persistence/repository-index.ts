import { createInMemoryActorRepository as PostgresActorRepository } from './actor-repository';
import { createTemporalIdentityRepository as PostgresTemporalIdentityRepository } from './temporal-identity-repository';
import { createGovernanceRepository as PostgresGovernanceRepository } from './governance-repository';

export { PostgresActorRepository,
  PostgresTemporalIdentityRepository,
  PostgresGovernanceRepository };
