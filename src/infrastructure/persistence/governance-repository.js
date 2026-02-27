const PostgresGovernanceRepository = {
  create: function(eventStore, tableName) {
    const _tableName = tableName || 'governance_rules';

    return {
      async saveRuleVersion(ruleType, version, activatedAt) {
        let client = null;
        try {
          if (eventStore && eventStore['_pool']) {
            client = await eventStore['_pool'].connect();
          }
          if (client) {
            await client.query(
              'INSERT INTO ' + _tableName + ' (rule_type, version, activated_at) VALUES ($1, $2, $3)',
              [ruleType, version, activatedAt]
            );
          }
        } finally {
          if (client) {
            client.release();
          }
        }
      },

      async getCurrentVersion(ruleType) {
        let client = null;
        let result = null;
        try {
          if (eventStore && eventStore['_pool']) {
            client = await eventStore['_pool'].connect();
          }
          if (client) {
            result = await client.query(
              'SELECT version FROM ' + _tableName + ' WHERE rule_type = $1 ORDER BY activated_at DESC LIMIT 1',
              [ruleType]
            );
          }
        } finally {
          if (client) {
            client.release();
          }
        }
        return result && result.rows && result.rows.length > 0 ? result.rows[0].version : null;
      },

      async getAllVersions(ruleType) {
        let client = null;
        let result = null;
        try {
          if (eventStore && eventStore['_pool']) {
            client = await eventStore['_pool'].connect();
          }
          if (client) {
            result = await client.query(
              'SELECT * FROM ' + _tableName + ' WHERE rule_type = $1 ORDER BY activated_at',
              [ruleType]
            );
          }
        } finally {
          if (client) {
            client.release();
          }
        }
        return result ? result.rows : [];
      }
    };
  }
};

module.exports = PostgresGovernanceRepository;