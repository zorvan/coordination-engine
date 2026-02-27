const ActorRepositoryInterface = require('../../domain/repositories').ActorRepositoryInterface;

const PostgresActorRepository = {
  create: function(eventStore) {
    return {
      async save(actor) {
        const events = await eventStore.getEventsByAggregate(actor.id.value);
        const createdEvent = events.find(e => e.type === 'ActorCreated');
        
        if (!createdEvent) {
          await eventStore.append({
            id: `evt_${Date.now()}`,
            aggregateId: actor.id.value,
            type: 'ActorCreated',
            timestamp: new Date(),
            payload: actor
          });
        }
      },

      async getById(id) {
        const events = await eventStore.getEventsByAggregate(id);
        const createdEvent = events.find(e => e.type === 'ActorCreated');
        
        if (!createdEvent) {
          return null;
        }

        return {
          id: { value: createdEvent.payload.id.value },
          attributes: createdEvent.payload.attributes,
          temporalIdentity: createdEvent.payload.temporalIdentity,
          createdAt: new Date(createdEvent.timestamp),
          updatedAt: new Date(createdEvent.timestamp)
        };
      },

      async getAll() {
        const allEvents = await eventStore.getAllEvents();
        const actorEvents = allEvents.filter(e => e.type === 'ActorCreated');
        
        return actorEvents.map(event => ({
          id: { value: event.payload.id.value },
          attributes: event.payload.attributes,
          temporalIdentity: event.payload.temporalIdentity,
          createdAt: new Date(event.timestamp),
          updatedAt: new Date(event.timestamp)
        }));
      }
    };
  }
};

module.exports = PostgresActorRepository;