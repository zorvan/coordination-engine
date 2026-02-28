const express = require('express');
//const PostgresEventStore = require('../infrastructure/persistence/event-store').PostgresEventStore;
const EventStore = require('../infrastructure/persistence/event-store').EventStore;
const { createInMemoryMatchRepository } = require('../infrastructure/persistence/match-repository');
const { createInMemoryActorRepository } = require('../infrastructure/persistence/actor-repository');
const { CreateMatchUseCase } = require('../application/usecases/match/create-match');
const { ConfirmMatchUseCase } = require('../application/usecases/match/confirm-match');
const { CompleteMatchUseCase } = require('../application/usecases/match/complete-match');
const { CancelMatchUseCase } = require('../application/usecases/match/cancel-match');
const { createRoutes } = require('./routes');

/**
 * Build and return an Express application configured with
 * all of the domain routes.
 *
 * @param {Pool} pool - A pg Pool instance (currently unused but kept for
 *                      backwards compatibility and future persistence wiring).
 * @returns {import('express').Express} An express application instance.
 */
const createServer = function(pool) {
  const app = express();

  // enable JSON body parsing for all routes
  app.use(express.json());

  //const eventStore = PostgresEventStore.create(pool);
  const eventStore = new EventStore();
  const matchRepository = createInMemoryMatchRepository(eventStore);
  const actorRepository = createInMemoryActorRepository(eventStore);
  
  const createMatchUseCase = CreateMatchUseCase.create(matchRepository, eventStore);
  const confirmMatchUseCase = ConfirmMatchUseCase.create(matchRepository, eventStore);
  const completeMatchUseCase = CompleteMatchUseCase.create(matchRepository, actorRepository, eventStore);
  const cancelMatchUseCase = CancelMatchUseCase.create(matchRepository, eventStore);
  
  const matchRoutes = createRoutes(
    createMatchUseCase,
    confirmMatchUseCase,
    completeMatchUseCase,
    cancelMatchUseCase,
    eventStore
  );

  // register the route definitions on the express app
  Object.keys(matchRoutes.routes).forEach((path) => {
    const r = matchRoutes.routes[path];
    if (r.method === 'get') {
      app.get(path, r.handler);
    } else if (r.method === 'post') {
      app.post(path, r.handler);
    }
  });

  return app;
};

module.exports = { createServer };
