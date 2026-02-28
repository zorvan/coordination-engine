const { Pool } = require('pg');
const { PostgresEventStore } = require('../../src/infrastructure/persistence/event-store');

// These tests require a running Postgres instance. The connection parameters
// can be changed via environment variables (same as the application). If the
// pool cannot connect, tests will be skipped automatically.

describe('PostgresEventStore', () => {
  let pool;
  let store;

  beforeAll(async () => {
    // "postgresql://cedbuser:cedbpasswd@localhost:5432/coordination_engine_test?"
    try {
      pool = new Pool({
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_TEST_NAME || process.env.DB_NAME || 'coordination_engine_test',
        user: process.env.DB_USER || 'cedbuser',
        password: process.env.DB_PASSWORD || 'cedbpasswd',
      });
      // simple query to verify connection
      await pool.query('SELECT 1');
      store = PostgresEventStore.create(pool);
      // ensure table clean
      await pool.query('DROP TABLE IF EXISTS events');
      await store._ensureTable();
    } catch (err) {
      console.warn('Postgres not available, skipping PostgresEventStore tests:', err.message);
      pool = null;
    }
  });

  afterAll(async () => {
    if (pool) {
      await pool.end();
    }
  });

  beforeEach(async () => {
    if (!pool) return;
    await pool.query('DELETE FROM events');
  });

  test('append and retrieve by aggregate', async () => {
    if (!pool) return;
    const evt = {
      id: 'evt-1',
      aggregateId: 'agg-1',
      type: 'TestEvent',
      payload: { foo: 'bar' },
      timestamp: new Date(),
    };
    await store.append(evt);
    const events = await store.getEventsByAggregate('agg-1');
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({
      id: 'evt-1',
      type: 'TestEvent',
      payload: { foo: 'bar' },
    });
  });

  test('getAllEvents and since', async () => {
    if (!pool) return;
    const now = new Date();
    await store.append({ id: 'e1', type: 'A', timestamp: now });
    await store.append({ id: 'e2', type: 'B', timestamp: new Date(now.getTime() + 1000) });

    const all = await store.getAllEvents();
    expect(all.length).toBe(2);

    const later = await store.getEventsSince(new Date(now.getTime() + 500));
    expect(later.length).toBe(1);
    expect(later[0].id).toBe('e2');
  });
});
