/**
 * MatchState tests.
 * 
 * These tests verify the match state machine logic.
 */

import { describe, it, expect } from 'vitest'
import { MatchState, MatchStateMachine, isValidTransition, canTransitionTo, getValidTransitions } from '@domain/valuables/match-state'

/**
 * Tests for MatchState constants.
 */
describe('MatchState', () => {
  /**
   * Tests all states are defined.
   */
  it('should define all states', () => {
    expect(MatchState.PROPOSED).toBe('proposed')
    expect(MatchState.CONFIRMED).toBe('confirmed')
    expect(MatchState.COMPLETED).toBe('completed')
    expect(MatchState.CANCELLED).toBe('cancelled')
  })
})

/**
 * Tests for MatchStateMachine.
 */
describe('MatchStateMachine', () => {
  /**
   * Tests proposed state transitions.
   */
  it('should allow proposed to transition to confirmed or cancelled', () => {
    expect(MatchStateMachine['proposed']).toContain('confirmed')
    expect(MatchStateMachine['proposed']).toContain('cancelled')
  })

  /**
   * Tests confirmed state transitions.
   */
  it('should allow confirmed to transition to completed or cancelled', () => {
    expect(MatchStateMachine['confirmed']).toContain('completed')
    expect(MatchStateMachine['confirmed']).toContain('cancelled')
  })

  /**
   * Tests completed state has no transitions.
   */
  it('should not allow completed to transition', () => {
    expect(MatchStateMachine['completed']).toEqual([])
  })

  /**
   * Tests cancelled state has no transitions.
   */
  it('should not allow cancelled to transition', () => {
    expect(MatchStateMachine['cancelled']).toEqual([])
  })
})

/**
 * Tests for isValidTransition function.
 */
describe('isValidTransition', () => {
  /**
   * Tests valid transitions.
   */
  it('should validate valid transitions', () => {
    expect(isValidTransition('proposed', 'confirmed')).toBe(true)
    expect(isValidTransition('proposed', 'cancelled')).toBe(true)
    expect(isValidTransition('confirmed', 'completed')).toBe(true)
    expect(isValidTransition('confirmed', 'cancelled')).toBe(true)
  })

  /**
   * Tests invalid transitions.
   */
  it('should reject invalid transitions', () => {
    expect(isValidTransition('proposed', 'completed')).toBe(false)
    expect(isValidTransition('confirmed', 'proposed')).toBe(false)
    expect(isValidTransition('completed', 'proposed')).toBe(false)
    expect(isValidTransition('cancelled', 'confirmed')).toBe(false)
  })

  /**
   * Tests unknown state.
   */
  it('should return false for unknown state', () => {
    expect(isValidTransition('unknown' as any, 'confirmed')).toBe(false)
  })
})

/**
 * Tests for canTransitionTo function.
 */
describe('canTransitionTo', () => {
  /**
   * Tests that canTransitionTo is same as isValidTransition.
   */
  it('should be an alias for isValidTransition', () => {
    expect(canTransitionTo('proposed', 'confirmed')).toBe(true)
    expect(canTransitionTo('confirmed', 'proposed')).toBe(false)
  })
})

/**
 * Tests for getValidTransitions function.
 */
describe('getValidTransitions', () => {
  /**
   * Tests proposed state transitions.
   */
  it('should return valid transitions for proposed state', () => {
    const transitions = getValidTransitions('proposed')
    expect(transitions).toEqual(['confirmed', 'cancelled'])
  })

  /**
   * Tests confirmed state transitions.
   */
  it('should return valid transitions for confirmed state', () => {
    const transitions = getValidTransitions('confirmed')
    expect(transitions).toEqual(['completed', 'cancelled'])
  })

  /**
   * Tests completed state has no transitions.
   */
  it('should return empty array for completed state', () => {
    const transitions = getValidTransitions('completed')
    expect(transitions).toEqual([])
  })

  /**
   * Tests cancelled state has no transitions.
   */
  it('should return empty array for cancelled state', () => {
    const transitions = getValidTransitions('cancelled')
    expect(transitions).toEqual([])
  })
})