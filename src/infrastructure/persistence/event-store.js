const PostgresEventStore = {
  create: function(pool, tableName) {
    const _pool = pool;
    const _tableName = tableName || 'event_store';

    return {
      async append(event) {
        const client = await _pool.connect();
        try {
          await client.query(
            `INSERT INTO ${_tableName} (id, aggregate_id, type, timestamp, payload)
             VALUES ($1, $2, $3, $4, $5)`,
            [event.id, event.aggregateId, event.type, event.timestamp, JSON.stringify(event.payload)]
          );
        } finally {
          client.release();
        }
      },

      async getEventsByAggregate(aggregateId) {
        const client = await _pool.connect();
        try {
          const result = await client.query(
            `SELECT * FROM ${_tableName} WHERE aggregate_id = $1 ORDER BY timestamp`,
            [aggregateId]
          );
          return result.rows.map(row => ({
            id: row.id,
            aggregateId: row.aggregate_id,
            type: row.type,
            timestamp: row.timestamp,
            payload: row.payload
          }));
        } finally {
          client.release();
        }
      },

      async getAllEvents() {
        const client = await _pool.connect();
        try {
          const result = await client.query(
            `SELECT * FROM ${_tableName} ORDER BY timestamp`
          );
          return result.rows.map(row => ({
            id: row.id,
            aggregateId: row.aggregate_id,
            type: row.type,
            timestamp: row.timestamp,
            payload: row.payload
          }));
        } finally {
          client.release();
        }
      },

      async getEventsSince(timestamp) {
        const client = await _pool.connect();
        try {
          const result = await client.query(
            `SELECT * FROM ${_tableName} WHERE timestamp >= $1 ORDER BY timestamp`,
            [timestamp]
          );
          return result.rows.map(row => ({
            id: row.id,
            aggregateId: row.aggregate_id,
            type: row.type,
            timestamp: row.timestamp,
            payload: row.payload
          }));
        } finally {
          client.release();
        }
      }
    };
  }
};

module.exports = { PostgresEventStore };