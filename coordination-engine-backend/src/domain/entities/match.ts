const MatchState = {
  proposed: 'proposed',
  confirmed: 'confirmed',
  completed: 'completed',
  cancelled: 'cancelled',
};

const MatchStateMachine = {
  proposed: ['confirmed', 'cancelled'],
  confirmed: ['completed', 'cancelled'],
  completed: [],
  cancelled: [],
};

function createMatch(
  id,
  organizerId,
  title,
  description,
  scheduledTime,
  durationMinutes,
  location,
  participantIds = []
) {
  return {
    id,
    state: 'proposed',
    organizerId,
    title,
    description,
    scheduledTime,
    durationMinutes,
    location,
    participantIds,
    createdAt: new Date(),
    updatedAt: new Date(),
  };
}

function canTransitionTo(currentState, targetState) {
  const transitions = MatchStateMachine[currentState];
  return transitions ? transitions.includes(targetState) : false;
}

export { MatchState, MatchStateMachine, createMatch, canTransitionTo };
