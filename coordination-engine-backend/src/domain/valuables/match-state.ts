import { MatchStateValue } from '../../types/match';

const MatchState = {
  PROPOSED: 'proposed',
  CONFIRMED: 'confirmed',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
} as const;

const MatchStateMachine: Record<MatchStateValue, MatchStateValue[]> = {
  proposed: ['confirmed', 'cancelled'],
  confirmed: ['completed', 'cancelled'],
  completed: [],
  cancelled: [],
};

function isValidTransition(fromState: MatchStateValue, toState: MatchStateValue): boolean {
  const validTransitions = MatchStateMachine[fromState];
  return validTransitions ? validTransitions.includes(toState) : false;
}

function canTransitionTo(fromState: MatchStateValue, toState: MatchStateValue): boolean {
  return isValidTransition(fromState, toState);
}

function getValidTransitions(currentState: MatchStateValue): MatchStateValue[] {
  return MatchStateMachine[currentState] || [];
}

export { MatchState,
  MatchStateMachine,
  isValidTransition,
  canTransitionTo,
  getValidTransitions, };
