const CreateMatchUseCase = {
  create: function(matchRepository, eventStore) {
    return {
      async execute(organizerId, title, description, scheduledTime, durationMinutes, location, participantIds) {
        participantIds = participantIds || [];
        const matchId = generateEventId();
        
        const event = {
          id: generateEventId(),
          aggregateId: matchId,
          type: 'MatchCreated',
          timestamp: new Date(),
          payload: {
            organizerId: organizerId,
            title: title,
            description: description,
            scheduledTime: scheduledTime,
            durationMinutes: durationMinutes,
            location: location,
            participants: participantIds
          }
        };

        await eventStore.append(event);
        
        return matchId;
      }
    };
  }
};

module.exports = { CreateMatchUseCase };