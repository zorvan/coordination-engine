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

const { EventStore } = require('./persistence/event-store');
const { createInMemoryMatchRepository } = require('./persistence/match-repository');
const { createInMemoryActorRepository } = require('./persistence/actor-repository');
const { createTemporalIdentityRepository } = require('./persistence/temporal-identity-repository');
const { createGovernanceRepository } = require('./persistence/governance-repository');
const { createRelationalGraphRepository } = require('./persistence/relational-graph-repository');
const { createFairnessLedger } = require('./persistence/fairness-ledger');
const { createAgentRepository } = require('./persistence/agent-repository');
const { createAgentNegotiationRepository } = require('./persistence/agent-negotiation-repository');
const { computeTrustProjection } = require('./projections/trust-projection');

module.exports = {
  EventStore,
  createInMemoryMatchRepository,
  createInMemoryActorRepository,
  createTemporalIdentityRepository,
  createGovernanceRepository,
  createRelationalGraphRepository,
  createFairnessLedger,
  createAgentRepository,
  createAgentNegotiationRepository,
  computeTrustProjection,
};