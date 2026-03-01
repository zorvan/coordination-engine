import express from 'express';
import { createServer } from './api/server';
import { Pool } from 'pg';
import { logger } from './infrastructure/logging/logger';

const PORT = process.env.PORT || 3000;

const startServer = async function() {
  logger.info('Server bootstrap starting', {
    port: PORT,
    dbHost: process.env.DB_HOST || 'localhost',
    dbPort: process.env.DB_PORT || '5432',
    dbName: process.env.DB_NAME || 'coordination_engine'
  });

  const pool = new Pool({
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'coordination_engine',
    user: process.env.DB_USER || 'cedbuser',
    password: process.env.DB_PASSWORD || 'cedbpasswd'
  });

  try {
    const app = await createServer(pool);
    app.listen(PORT, function() {
      logger.info('Server started', { port: PORT });
    });
  } catch (error) {
    logger.error('Failed to start server', {
      error: error instanceof Error ? error.message : 'Unknown error'
    });
    process.exit(1);
  }
};

process.on('uncaughtException', function(error) {
  logger.error('Uncaught exception', { error: error.message, stack: error.stack });
});

process.on('unhandledRejection', function(reason) {
  logger.error('Unhandled rejection', {
    reason: reason instanceof Error ? reason.message : String(reason)
  });
});

startServer();
