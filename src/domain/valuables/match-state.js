const MatchState = {
  PROPOSED: 'proposed',
  CONFIRMED: 'confirmed',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
};

const MatchStateMachine = {
  proposed: ['confirmed', 'cancelled'],
  confirmed: ['completed', 'cancelled'],
  completed: [],
  cancelled: [],
};

function isValidTransition(fromState, toState) {
  const validTransitions = MatchStateMachine[fromState];
  return validTransitions ? validTransitions.includes(toState) : false;
}

function canTransitionTo(fromState, toState) {
  return isValidTransition(fromState, toState);
}

function getValidTransitions(currentState) {
  return MatchStateMachine[currentState] || [];
}

module.exports = {
  MatchState,
  MatchStateMachine,
  isValidTransition,
  canTransitionTo,
  getValidTransitions,
};