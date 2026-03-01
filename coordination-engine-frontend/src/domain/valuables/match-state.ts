/**
 * Match value object.
 * 
 * This value object represents the state of a match in the coordination engine.
 * 
 * Design decisions:
 * - Using immutable value object pattern
 * - State transitions are validated through this value object
 * - Provides clear state constants for match lifecycle
 */

export const MatchState = {
  PROPOSED: 'proposed',
  CONFIRMED: 'confirmed',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
} as const

export type MatchStateValue = (typeof MatchState)[keyof typeof MatchState]

/**
 * Match state machine defines valid transitions between states.
 * 
 * Design decisions:
 * - Explicit state machine for match lifecycle
 * - Prevents invalid state transitions at the value object level
 * - Clear, readable transition rules
 */
export const MatchStateMachine = {
  [MatchState.PROPOSED]: [MatchState.CONFIRMED, MatchState.CANCELLED],
  [MatchState.CONFIRMED]: [MatchState.COMPLETED, MatchState.CANCELLED],
  [MatchState.COMPLETED]: [],
  [MatchState.CANCELLED]: [],
} as const satisfies Record<MatchStateValue, readonly MatchStateValue[]>

/**
 * Check if a state transition is valid according to the state machine.
 * 
 * @param fromState - Current state
 * @param toState - Target state
 * @returns True if transition is valid
 */
export function isValidTransition(fromState: MatchStateValue, toState: MatchStateValue): boolean {
  const validTransitions = MatchStateMachine[fromState] as readonly MatchStateValue[]
  return validTransitions ? validTransitions.includes(toState) : false
}

/**
 * Check if a state can transition to another state.
 * 
 * @param fromState - Current state
 * @param toState - Target state
 * @returns True if transition is possible
 */
export function canTransitionTo(fromState: MatchStateValue, toState: MatchStateValue): boolean {
  return isValidTransition(fromState, toState)
}

/**
 * Get all valid transitions from the current state.
 * 
 * @param currentState - Current state
 * @returns Array of valid target states
 */
export function getValidTransitions(currentState: MatchStateValue): MatchStateValue[] {
  return [...MatchStateMachine[currentState]]
}
