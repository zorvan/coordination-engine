// @ts-ignore: node types not available in test environment
import crypto from 'crypto';
import { createInMemoryActorRepository } from '../../src/infrastructure/persistence/actor-repository';
import { createActor } from '../../src/domain/entities/actor';

type StoredEvent = {
  id: string;
  aggregateId: string;
  type: string;
  payload: any;
  timestamp: Date;
};

// a tiny in-memory event store implementation for tests
function makeEventStore() {
  const events: StoredEvent[] = [];
  return {
    append: async (event: Partial<StoredEvent> & Pick<StoredEvent, 'type'>) => {
      const toSave: StoredEvent = {
        id: event.id || crypto.randomUUID(),
        aggregateId: event.aggregateId || '',
        type: event.type,
        payload: event.payload ?? {},
        timestamp: event.timestamp instanceof Date ? event.timestamp : new Date(),
      };
      events.push(toSave);
    },
    getEventsByAggregate: async (aggregateId: string) => {
      return events.filter((e) => e.aggregateId === aggregateId);
    },
    getAllEvents: async () => [...events],
  } as any;
}

// jest globals (describe, test, expect, beforeEach) are available at runtime.
// declare them here so the TypeScript compiler doesn't complain.
declare const describe: any;
declare const test: any;
declare const beforeEach: any;
declare const expect: any;

describe('actor repository and update semantics', () => {
  let repo: ReturnType<typeof createInMemoryActorRepository>;
  let store: ReturnType<typeof makeEventStore>;

  beforeEach(() => {
    store = makeEventStore();
    repo = createInMemoryActorRepository(store);
  });

  test('patching a single field preserves others', async () => {
    const actor = createActor('actor1', 'Alice', 'alice@example.com', '');
    await repo.save(actor);

    // first update: add phone + location
    await repo.update({ id: actor.id, phone: '555-1234', location: 'Here' });
    let saved = await repo.findById(actor.id);
    expect(saved).not.toBeNull();
    expect(saved?.phone).toBe('555-1234');
    expect(saved?.location).toBe('Here');

    // second update: change only name, simulate server merge bug by
    // pretending we merged with an "existing" state that didn't have phone
    // (represents a stale read).  if the route blindly saved that object,
    // the phone would be lost.
    const staleExisting = { id: actor.id, name: 'Alice', email: 'alice@example.com' };
    const bugPayload = { ...staleExisting, name: 'Alice Smith' };
    await repo.update(bugPayload as any);

    const after = await repo.findById(actor.id);
    expect(after).not.toBeNull();

    // under correct (patch) behaviour, the phone should still be present
    expect(after?.phone).toBe('555-1234');
    expect(after?.name).toBe('Alice Smith');
  });

  test('onboardingCompletedAt is persisted and detectable', async () => {
    const actor = createActor('actor2', 'Bob', 'bob@example.com', '');
    await repo.save(actor);

    // simulate onboarding update
    const now = new Date().toISOString();
    await repo.update({ id: actor.id, phone: '123', location: 'Town', bio: 'Hi', onboardingCompletedAt: now });

    const saved = await repo.findById(actor.id);
    expect(saved).not.toBeNull();
    expect(saved?.onboardingCompletedAt).toBe(now);
    // boolean check as frontend uses
    const completed = Boolean(
      saved?.onboardingCompletedAt ||
      (saved?.phone && saved?.location && saved?.bio)
    );
    expect(completed).toBe(true);
  });
});
