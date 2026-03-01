# Coordination Engine Frontend

A modern React frontend for the coordination-engine backend, following Clean Architecture principles.

## Architecture

```
src/
├── domain/           # Core business logic (entities, valuables, services)
├── application/      # Use cases and orchestration
├── infrastructure/   # External concerns (API, persistence)
└── presentation/     # UI components and pages
```

## Features

- **Event Sourcing**: View match lifecycle events
- **Trust Scoring**: Monitor actor trust levels
- **State Machine**: Visualize match state transitions
- **Clean Architecture**: Separated concerns with clear boundaries

## Tech Stack

- **Framework**: React 18 with Vite
- **State Management**: Zustand
- **Testing**: Vitest + React Testing Library
- **Language**: TypeScript 5

## Development

```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Run tests
npm test

# Run with coverage
npm run test:coverage

# Type check
npm run typecheck

# Lint
npm run lint
```

## Project Structure

### Domain Layer
- **Entities**: Match, Actor, Agent
- **Value Objects**: MatchState, TrustValue
- **Services**: Trust computation, Fairness ledger

### Application Layer
- **Use Cases**: CreateMatch, ConfirmMatch, CompleteMatch, CancelMatch
- **Services**: Business logic orchestration

### Infrastructure Layer
- **API**: REST client for backend
- **Persistence**: Local storage, cache

### Presentation Layer
- **Components**: Reusable UI components
- **Pages**: Route-level components
- **Contexts**: React contexts for state

## Branch Strategy

- `main`: Production-ready code
- `feature/phase*`: Feature development branches
- `hotfix/*`: Urgent fixes

## License

MIT