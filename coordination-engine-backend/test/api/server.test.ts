import { createServer } from '../../src/api/server';
import * as eventStoreModule from '../../src/infrastructure/persistence/event-store';

/**
 * Basic smoke tests for the HTTP server implementation.  The primary goal of
 * this suite is to make sure that the helper in `src/api/server.js` actually
 * returns an Express application and that at least one route defined in
 * `src/api/routes.js` is wired up correctly.  This keeps the "listen"
 * behaviour working and guards against regressions as the API evolves.
 *
 * These assertions avoid needing to start a real HTTP server so they can run
 * without additional dependencies such as supertest.
 */

describe('API server', () => {
  let app;

  beforeAll(async () => {
    // intercept creation of the PostgresEventStore so we don't need a real
    // database. return a minimal in-memory implementation used elsewhere.
    jest.spyOn(eventStoreModule.PostgresEventStore, 'create').mockImplementation(async (_pool: any) => {
      return {
        append: async () => {},
        getEventsByAggregate: async () => [],
        getAllEvents: async () => [],
        getEventsByType: async () => [],
        getEventsSince: async () => [],
        getEventById: async () => null,
        getEventCount: async () => 0,
        clear: async () => {},
      } as any;
    });

    app = await createServer({} as any);
  });

  test('returns an Express app with listen/get/post methods', () => {
    expect(app).toBeDefined();
    expect(typeof app.listen).toBe('function');
    expect(typeof app.get).toBe('function');
    expect(typeof app.post).toBe('function');
  });

  test('router contains a GET handler for /matches/:matchId', () => {
    // Express 4 uses app._router, Express 5 exposes app.router.
    const routes =
      (app._router && app._router.stack) ||
      (app.router && app.router.stack) ||
      [];
    const hasMatchRoute = routes.some((layer) => {
      return layer.route && layer.route.path === '/matches/:matchId' &&
             layer.route.methods && layer.route.methods.get;
    });
    expect(hasMatchRoute).toBe(true);
  });
});
