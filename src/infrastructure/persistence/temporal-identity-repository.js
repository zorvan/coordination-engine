const PostgresTemporalIdentityRepository = {
  create: function(eventStore) {
    return {
      async save(identity) {
        await eventStore.append({
          id: `evt_${Date.now()}`,
          aggregateId: identity.identityId,
          type: 'IdentityVersioned',
          timestamp: new Date(),
          payload: identity
        });
      },

      async getById(identityId) {
        const events = await eventStore.getEventsByAggregate(identityId);
        const identityEvents = events.filter(e => e.type === 'IdentityVersioned');
        
        if (identityEvents.length === 0) {
          return null;
        }

        // Return the latest version
        return identityEvents[identityEvents.length - 1].payload;
      }
    };
  }
};

module.exports = PostgresTemporalIdentityRepository;