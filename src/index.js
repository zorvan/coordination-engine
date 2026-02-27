const express = require('express');
const { createServer } = require('./api/server');
const { Pool } = require('pg');

const PORT = process.env.PORT || 3000;

const startServer = async function() {
  const pool = new Pool({
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'coordination_engine',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres'
  });

  try {
    const app = createServer(pool);
    app.listen(PORT, function() {
      console.log('Server started on port ' + PORT);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
};

startServer();