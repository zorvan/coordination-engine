# Coordination Engine

A multi-layered coordination infrastructure built with Clean Architecture principles.

## Overview

Transform informal "When are you free?" chaos into structured, transparent, socially reasonable group convergence.

## Features

- **Event Sourcing**: Full audit trail of all state changes
- **Trust Scoring**: Contextual reputation based on match history
- **State Machine**: Enforced match lifecycle (proposed -> confirmed -> completed)
- **Clean Architecture**: Separated domain, application, infrastructure, and API layers

## Architecture

```
┌─────────────────────────────────────┐
│           API Layer (REST)          │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│        Application Layer            │
│         (Use Cases)                 │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│          Domain Layer               │
│     (Core Business Logic)           │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│       Infrastructure Layer          │
│   (Persistence, External Services)  │
└─────────────────────────────────────┘
```

## Phases

### Phase 1: Deterministic Core (COMPLETE)
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

## Quick Start

```bash
# Install dependencies
npm install

# Run tests
npm test

# Start server
npm start
```

## Project Structure

```
src/
├── domain/           # Core business logic
├── application/      # Use cases and orchestration
├── infrastructure/   # External concerns
└── api/              # REST API endpoints
```

## Test Results

```
Test Suites: 5 passed, 5 total
Tests:       34 passed, 34 total
```

## License

MIT