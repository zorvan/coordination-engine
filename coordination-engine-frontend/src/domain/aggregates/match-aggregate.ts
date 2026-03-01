/**
 * Match aggregate with state machine.
 * 
 * This aggregate root manages the lifecycle and state transitions of a match.
 * It enforces the state machine rules and maintains consistency.
 * 
 * Business logic:
 * - States: proposed, confirmed, completed, cancelled
 * - Valid transitions: proposed→confirmed/cancelled, confirmed→completed/cancelled
 * - Cannot transition from completed or cancelled states
 * - Tracks timestamps for creation, completion, and cancellation
 */

import { MatchState, isValidTransition, getValidTransitions, type MatchStateValue } from '../valuables/match-state'

/**
 * Match aggregate interface.
 */
export interface MatchAggregate {
  /**
   * Unique match identifier.
   */
  matchId: string
  
  /**
   * Current state of the match.
   */
  state: MatchStateValue
  
  /**
   * Actor ID of the match organizer.
   */
  organizerId: string
  
  /**
   * Match title.
   */
  title: string
  
  /**
   * Optional match description.
   */
  description: string
  
  /**
   * When the match is scheduled.
   */
  scheduledTime: Date
  
  /**
   * Duration in minutes.
   */
  durationMinutes: number
  
  /**
   * Physical or virtual location.
   */
  location: string
  
  /**
   * Array of participant actor IDs.
   */
  participantIds: string[]
  
  /**
   * When the match was created.
   */
  createdAt: Date
  
  /**
   * When the match state was last updated.
   */
  updatedAt: Date
  
  /**
   * When the match was completed (if applicable).
   */
  completedAt: Date | null
  
  /**
   * When the match was cancelled (if applicable).
   */
  cancelledAt: Date | null
  
  /**
   * Notes or reason for the current state.
   */
  notes: string | null
  
  /**
   * Version number for optimistic concurrency control.
   */
  version: number
  
  /**
   * Transition to a new state.
   * 
   * @param newState - Target state
   * @throws Error if transition is invalid
   */
  transitionTo(newState: MatchStateValue): void
  
  /**
   * Confirm the match (proposed → confirmed).
   */
  confirm(): void
  
  /**
   * Complete the match (confirmed → completed).
   * 
   * @param notes - Optional completion notes
   */
  complete(notes: string): void
  
  /**
   * Cancel the match (proposed/confirmed → cancelled).
   * 
   * @param reason - Cancellation reason
   */
  cancel(reason: string): void
  
  /**
   * Check if a state transition is valid.
   * 
   * @param targetState - Target state
   * @returns True if transition is valid
   */
  isValidTransition(targetState: MatchStateValue): boolean
}

/**
 * Create a new match aggregate.
 * 
 * @param id - Unique match identifier
 * @param organizerId - Organizing actor ID
 * @param title - Match title
 * @param description - Optional description
 * @param scheduledTime - When the match is scheduled
 * @param durationMinutes - Duration in minutes
 * @param location - Physical or virtual location
 * @param participantIds - Array of participant actor IDs
 * @returns Match aggregate with state machine
 */
export function createMatchAggregate(
  id: string,
  organizerId: string,
  title: string,
  description: string,
  scheduledTime: Date,
  durationMinutes: number,
  location: string,
  participantIds: string[]
): MatchAggregate {
  const aggregate: MatchAggregate = {
    matchId: id,
    state: MatchState.PROPOSED,
    organizerId,
    title,
    description,
    scheduledTime,
    durationMinutes,
    location,
    participantIds,
    createdAt: new Date(),
    updatedAt: new Date(),
    completedAt: null,
    cancelledAt: null,
    notes: null,
    version: 0,

    /**
     * Transition to a new state.
     * 
     * Business logic:
     * - Validates transition using the state machine
     * - Updates timestamp and version
     * - Sets completion/cancellation timestamps when appropriate
     * 
     * @param newState - Target state
     * @throws Error if transition is invalid
     */
    transitionTo(newState: MatchStateValue): void {
      if (!isValidTransition(aggregate.state, newState)) {
        throw new Error(`Invalid transition from ${aggregate.state} to ${newState}`)
      }
      aggregate.state = newState
      aggregate.updatedAt = new Date()
      aggregate.version++
      
      if (newState === MatchState.COMPLETED) {
        aggregate.completedAt = new Date()
      }
      if (newState === MatchState.CANCELLED) {
        aggregate.cancelledAt = new Date()
      }
    },

    /**
     * Confirm the match (proposed → confirmed).
     * 
     * Business rule: Only proposed matches can be confirmed.
     * This transitions the match to confirmed state for planning purposes.
     */
    confirm(): void {
      aggregate.transitionTo(MatchState.CONFIRMED)
    },

    /**
     * Complete the match (confirmed → completed).
     * 
     * Business rule: Only confirmed matches can be completed.
     * Records completion notes and updates timestamp.
     * 
     * @param notes - Optional completion notes
     */
    complete(notes: string): void {
      aggregate.transitionTo(MatchState.COMPLETED)
      aggregate.notes = notes
    },

    /**
     * Cancel the match (proposed/confirmed → cancelled).
     * 
     * Business rule: Only proposed or confirmed matches can be cancelled.
     * Once cancelled, the match cannot be recovered.
     * 
     * @param reason - Cancellation reason
     */
    cancel(reason: string): void {
      aggregate.transitionTo(MatchState.CANCELLED)
      aggregate.notes = reason
    },

    /**
     * Check if a state transition is valid.
     * 
     * @param targetState - Target state
     * @returns True if transition is valid
     */
    isValidTransition(targetState: MatchStateValue): boolean {
      return isValidTransition(aggregate.state, targetState)
    },
  }

  return aggregate
}

/**
 * Get valid transitions from a given state.
 * 
 * @param state - Current state
 * @returns Array of valid target states
 */
export function getMatchValidTransitions(state: MatchStateValue): MatchStateValue[] {
  return getValidTransitions(state)
}
