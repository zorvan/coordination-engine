import express from 'express';
import { Pool } from 'pg';
import { PostgresEventStore } from '../infrastructure/persistence/event-store';
import { createInMemoryMatchRepository } from '../infrastructure/persistence/match-repository';
import { createInMemoryActorRepository } from '../infrastructure/persistence/actor-repository';
import { CreateMatchUseCase } from '../application/usecases/match/create-match';
import { ConfirmMatchUseCase } from '../application/usecases/match/confirm-match';
import { CompleteMatchUseCase } from '../application/usecases/match/complete-match';
import { CancelMatchUseCase } from '../application/usecases/match/cancel-match';
import { createRoutes } from './routes';
import { MatchRepositoryLike } from '../types/match';
import { logger } from '../infrastructure/logging/logger';

/**
 * Build and return an Express application configured with
 * all of the domain routes.
 *
 * @param {Pool} pool - A pg Pool instance used by the PostgreSQL event store.
 * @returns {import('express').Express} An express application instance.
 */
const createServer = async function(pool: Pool): Promise<express.Express> {
  const app: express.Express = express();

  app.use(function(req, res, next) {
    const start = Date.now();
    res.on('finish', function() {
      const durationMs = Date.now() - start;
      logger.info('HTTP request handled', {
        method: req.method,
        path: req.path,
        statusCode: res.statusCode,
        durationMs
      });
    });
    next();
  });

  app.use(function(req, res, next) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

    if (req.method === 'OPTIONS') {
      res.sendStatus(204);
      return;
    }

    next();
  });

  // enable JSON body parsing for all routes
  app.use(express.json());

  const eventStore = await PostgresEventStore.create(pool);
  logger.info('Persistence initialized', { store: 'postgres_event_store' });
  const matchRepository: MatchRepositoryLike = createInMemoryMatchRepository(eventStore);
  const actorRepository = createInMemoryActorRepository(eventStore);
  
  const createMatchUseCase = CreateMatchUseCase.create(matchRepository, eventStore);
  const confirmMatchUseCase = ConfirmMatchUseCase.create(matchRepository, eventStore);
  const completeMatchUseCase = CompleteMatchUseCase.create(matchRepository, actorRepository, eventStore);
  const cancelMatchUseCase = CancelMatchUseCase.create(matchRepository, eventStore);
  
  const matchRoutes = createRoutes(
    matchRepository,
    createMatchUseCase,
    confirmMatchUseCase,
    completeMatchUseCase,
    cancelMatchUseCase,
    eventStore,
    actorRepository
  );

  // register the route definitions on the express app
  // `routes` is now an array of method/path entries, so just walk it.
  for (const r of matchRoutes.routes) {
    if (r.method === 'get') {
      app.get(r.path, r.handler);
      
      logger.debug('GET', {
       method: r.method,
       path: r.path
     });
    } else if (r.method === 'post') {
      app.post(r.path, r.handler);
      
      logger.debug('POST', {
       method: r.method,
       path: r.path
     });
    } else if (r.method === 'put') {
      app.put(r.path, r.handler);
      
      logger.debug('PUT', {
       method: r.method,
       path: r.path
     });
    }
  }

  app.use(function(req, res) {
    logger.warn('Failed to load resource: the server responded with a status of 404 (Not Found)', {
      method: req.method,
      path: req.path
    });
    res.status(404).json({
      error: 'not_found',
      message: 'Resource not found'
    });
  });

  return app;
};

export { createServer };
