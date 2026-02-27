/**
 * Infrastructure layer exports
 * 
 * This module provides implementations for all infrastructure concerns:
 * - Event sourcing (PostgreSQL event store)
 * - Data persistence (PostgreSQL repositories)
 * - Projections (Trust, Relational Graph, Fairness Ledger)
 * 
 * Pattern: Dependency Injection - use cases depend on infrastructure abstractions
 * Pattern: Adapter - infrastructure implementations adapt database to domain interfaces
 */

const { EventStore } = require('./persistence/event-store');
const { createInMemoryMatchRepository } = require('./persistence/match-repository');
const { createInMemoryActorRepository } = require('./persistence/actor-repository');
const { createInMemoryTemporalIdentityRepository } = require('./persistence/temporal-identity-repository');
const { createInMemoryGovernanceRepository } = require('./persistence/governance-repository');
const { computeTrustProjection } = require('./projections/trust-projection');

module.exports = {
  EventStore,
  createInMemoryMatchRepository,
  createInMemoryActorRepository,
  createInMemoryTemporalIdentityRepository,
  createInMemoryGovernanceRepository,
  computeTrustProjection,
};