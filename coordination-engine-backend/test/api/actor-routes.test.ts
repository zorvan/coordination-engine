// this integration-style test exercises the express routes without needing a real
// PostgreSQL instance. we wire up the in-memory actor repository and stub event
// store used by the production code.

// @ts-ignore: types not included in this repo's test setup
import express from 'express';
// @ts-ignore: types not installed for supertest
import request from 'supertest';
// @ts-ignore
import crypto from 'crypto';
import { createRoutes } from '../../src/api/routes';
import { createInMemoryActorRepository } from '../../src/infrastructure/persistence/actor-repository';
import { createActor } from '../../src/domain/entities/actor';

type StoredEvent = {
  id: string;
  aggregateId: string;
  type: string;
  payload: any;
  timestamp: Date;
};

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
    getEventsByAggregate: async (aggregateId: string) => events.filter((e) => e.aggregateId === aggregateId),
    getAllEvents: async () => [...events],
  } as any;
}

// declare jest globals to keep ts happy
declare const describe: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;

describe('actor HTTP routes', () => {
  let app: express.Application;
  let eventStore: any;
  let actorRepo: any;

  beforeEach(() => {
    app = express();
    app.use(express.json());
    eventStore = makeEventStore();
    actorRepo = createInMemoryActorRepository(eventStore);

    // the router doesn't care about the match use case dependencies for these
    // tests, so we pass null for the unused arguments.
    const routes = createRoutes(null as any, null as any, null as any, null as any, null as any, eventStore, actorRepo);
    // dump the registered paths/methods for sanity
    // @ts-ignore
    console.log('routes defined:', routes.routes.map((r) => `${r.method} ${r.path}`));

    for (const r of routes.routes as any[]) {
      if (r.method === 'get') app.get(r.path, r.handler);
      if (r.method === 'post') app.post(r.path, r.handler);
      if (r.method === 'put') app.put(r.path, r.handler);
    }
  });

  it('PATCH semantics: updating name should not erase phone', async () => {
    const actor = createActor('actorA', 'Original', 'orig@example.com', '');
    await actorRepo.save(actor);

    // patch phone
    await request(app)
      .put(`/actors/${encodeURIComponent(actor.id)}`)
      .send({ phone: '999' })
      .expect(200);

    let res = await request(app)
      .get(`/actors/${encodeURIComponent(actor.id)}`)
      .expect(200);
    expect(res.body.actor.phone).toBe('999');

    // update name only
    await request(app)
      .put(`/actors/${encodeURIComponent(actor.id)}`)
      .send({ name: 'NewName' })
      .expect(200);

    res = await request(app)
      .get(`/actors/${encodeURIComponent(actor.id)}`)
      .expect(200);
    expect(res.body.actor.phone).toBe('999');
    expect(res.body.actor.name).toBe('NewName');
  });

  it('calling login twice for a new email does not create two ActorCreated events', async () => {
    const id = 'email:test@example.com';

    await request(app).post('/auth/email/login').send({ email: 'test@example.com', password: 'abc123' });
    console.log('events after first login:', await eventStore.getEventsByAggregate(id));
    await request(app).post('/auth/email/login').send({ email: 'test@example.com', password: 'abc123' });
    console.log('events after second login:', await eventStore.getEventsByAggregate(id));

    const events = await eventStore.getEventsByAggregate(id);
    const created = events.filter((e: any) => e.type === 'ActorCreated');
    expect(created.length).toBe(1);
  });
});
