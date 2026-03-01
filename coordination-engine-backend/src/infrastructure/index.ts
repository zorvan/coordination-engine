/**
 * Infrastructure layer exports for Phase 4
 * 
 * This module provides implementations for all infrastructure concerns:
 * - Event sourcing (PostgreSQL event store)
 * - Data persistence (PostgreSQL repositories)
 * - Projections (Trust, Relational Graph, Fairness Ledger)
 * - Temporal identity and governance
 * - Agent negotiation
 * 
 * Pattern: Dependency Injection - use cases depend on infrastructure abstractions
 * Pattern: Adapter - infrastructure implementations adapt database to domain interfaces
 */

import { EventStore } from './persistence/event-store';
import { createInMemoryMatchRepository } from './persistence/match-repository';
import { createInMemoryActorRepository } from './persistence/actor-repository';
import { createTemporalIdentityRepository } from './persistence/temporal-identity-repository';
import { createGovernanceRepository } from './persistence/governance-repository';
import { createRelationalGraphRepository } from './persistence/relational-graph-repository';
import { createFairnessLedger } from './persistence/fairness-ledger';
import { createAgentRepository } from './persistence/agent-repository';
import { createAgentNegotiationRepository } from './persistence/agent-negotiation-repository';
import { computeTrustProjection } from './projections/trust-projection';

export { EventStore,
  createInMemoryMatchRepository,
  createInMemoryActorRepository,
  createTemporalIdentityRepository,
  createGovernanceRepository,
  createRelationalGraphRepository,
  createFairnessLedger,
  createAgentRepository,
  createAgentNegotiationRepository,
  computeTrustProjection, };