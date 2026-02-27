const PostgresMatchRepository = {
  create: function(eventStore) {
    return {
      async save(match) {
        const events = await eventStore.getEventsByAggregate(match.id);
        const createdEvent = events.find(function(e) { return e.type === 'MatchCreated'; });
        
        if (createdEvent) {
          await eventStore.append({
            id: 'evt_' + Date.now(),
            aggregateId: match.id,
            type: 'MatchUpdated',
            timestamp: new Date(),
            payload: match
          });
        } else {
          await eventStore.append({
            id: 'evt_' + Date.now(),
            aggregateId: match.id,
            type: 'MatchCreated',
            timestamp: new Date(),
            payload: match
          });
        }
      },

      async getById(id) {
        const events = await eventStore.getEventsByAggregate(id);
        const createdEvent = events.find(function(e) { return e.type === 'MatchCreated'; });
        
        if (!createdEvent) {
          return null;
        }

        return {
          id: id,
          state: createdEvent.payload.state || 'proposed',
          organizerId: createdEvent.payload.organizerId,
          title: createdEvent.payload.title,
          description: createdEvent.payload.description,
          scheduledTime: new Date(createdEvent.payload.scheduledTime),
          durationMinutes: createdEvent.payload.durationMinutes,
          location: createdEvent.payload.location,
          participantIds: createdEvent.payload.participants,
          createdAt: new Date(createdEvent.timestamp),
          updatedAt: new Date(createdEvent.timestamp)
        };
      },

      async getMatchesByActor(actorId) {
        const allEvents = await eventStore.getAllEvents();
        const matchEvents = allEvents.filter(function(e) {
          return e.type === 'MatchCreated' || 
            e.type === 'MatchConfirmed' || 
            e.type === 'MatchCompleted' || 
            e.type === 'MatchCancelled';
        });

        const matchMap = new Map();
        
        for (let i = 0; i < matchEvents.length; i++) {
          const event = matchEvents[i];
          const matchId = event.aggregateId;
          
          if (!matchMap.has(matchId)) {
            matchMap.set(matchId, {
              id: matchId,
              state: 'proposed',
              organizerId: event.payload.organizerId,
              title: event.payload.title,
              description: event.payload.description,
              scheduledTime: new Date(event.payload.scheduledTime),
              durationMinutes: event.payload.durationMinutes,
              location: event.payload.location,
              participantIds: event.payload.participants || [],
              createdAt: new Date(event.timestamp),
              updatedAt: new Date(event.timestamp)
            });
          }

          const match = matchMap.get(matchId);
          
          if (event.type === 'MatchConfirmed') {
            match.state = 'confirmed';
            match.updatedAt = new Date(event.timestamp);
          } else if (event.type === 'MatchCompleted') {
            match.state = 'completed';
            match.completedAt = new Date(event.timestamp);
            match.notes = event.payload.notes;
            match.updatedAt = new Date(event.timestamp);
          } else if (event.type === 'MatchCancelled') {
            match.state = 'cancelled';
            match.cancelledAt = new Date(event.timestamp);
            match.notes = event.payload.reason;
            match.updatedAt = new Date(event.timestamp);
          }
        }

        const result = [];
        const matchValues = matchMap.values();
        for (let match of matchValues) {
          if (match.organizerId === actorId || match.participantIds.includes(actorId)) {
            result.push(match);
          }
        }
        return result;
      },

      async getAll() {
        const allEvents = await eventStore.getAllEvents();
        const matchEvents = allEvents.filter(function(e) {
          return e.type === 'MatchCreated' || 
            e.type === 'MatchConfirmed' || 
            e.type === 'MatchCompleted' || 
            e.type === 'MatchCancelled';
        });

        const matchMap = new Map();
        
        for (let i = 0; i < matchEvents.length; i++) {
          const event = matchEvents[i];
          const matchId = event.aggregateId;
          
          if (!matchMap.has(matchId)) {
            matchMap.set(matchId, {
              id: matchId,
              state: 'proposed',
              organizerId: event.payload.organizerId,
              title: event.payload.title,
              description: event.payload.description,
              scheduledTime: new Date(event.payload.scheduledTime),
              durationMinutes: event.payload.durationMinutes,
              location: event.payload.location,
              participantIds: event.payload.participants || [],
              createdAt: new Date(event.timestamp),
              updatedAt: new Date(event.timestamp)
            });
          }

          const match = matchMap.get(matchId);
          
          if (event.type === 'MatchConfirmed') {
            match.state = 'confirmed';
            match.updatedAt = new Date(event.timestamp);
          } else if (event.type === 'MatchCompleted') {
            match.state = 'completed';
            match.completedAt = new Date(event.timestamp);
            match.notes = event.payload.notes;
            match.updatedAt = new Date(event.timestamp);
          } else if (event.type === 'MatchCancelled') {
            match.state = 'cancelled';
            match.cancelledAt = new Date(event.timestamp);
            match.notes = event.payload.reason;
            match.updatedAt = new Date(event.timestamp);
          }
        }

        const result = [];
        const matchValues = matchMap.values();
        for (let match of matchValues) {
          result.push(match);
        }
        return result;
      }
    };
  }
};

module.exports = PostgresMatchRepository;