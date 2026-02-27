# Deterministic Coordination Engine

A multi-layered coordination infrastructure built with Clean Architecture principles.

## Architecture

This project follows Clean Architecture with the following layers:

- **domain**: Core business logic, entities, value objects, domain events, and aggregates
- **application**: Use cases, services, and application-level orchestration
- **infrastructure**: External concerns like database, messaging, AI services
- **api**: REST API endpoints and transport layer

## Phases

### Phase 1: Deterministic Core
- Event sourcing with immutable event store
- Actor and Match aggregates
- Trust projection computation
- State machine enforcement

### Phase 2: Relational Graph + Fairness Ledger
- Relational edge projections
- Fairness computation
- Projection rebuild tooling

### Phase 3: Agent Negotiation Layer
- AI advisory services integration
- Proposal validation pipeline

### Phase 4: Temporal Identity + Governance
- Identity versioning
- Role half-life mechanism
- Governance event versioning

## Tech Stack

- Language: TypeScript
- Database: PostgreSQL (event store)
- Testing: Jest
- Build: ts-node, tsc