const { MatchStateMachine, isValidTransition, canTransitionTo, getValidTransitions } = require('../../src/domain/valuables/match-state');

test('MatchStateMachine defines valid transitions', () => {
  expect(MatchStateMachine.proposed).toContain('confirmed');
  expect(MatchStateMachine.proposed).toContain('cancelled');
  expect(MatchStateMachine.confirmed).toContain('completed');
  expect(MatchStateMachine.confirmed).toContain('cancelled');
  expect(MatchStateMachine.completed).toEqual([]);
  expect(MatchStateMachine.cancelled).toEqual([]);
});

test('isValidTransition returns true for valid transitions', () => {
  expect(isValidTransition('proposed', 'confirmed')).toBe(true);
  expect(isValidTransition('proposed', 'cancelled')).toBe(true);
  expect(isValidTransition('confirmed', 'completed')).toBe(true);
  expect(isValidTransition('confirmed', 'cancelled')).toBe(true);
});

test('isValidTransition returns false for invalid transitions', () => {
  expect(isValidTransition('proposed', 'completed')).toBe(false);
  expect(isValidTransition('confirmed', 'proposed')).toBe(false);
  expect(isValidTransition('completed', 'confirmed')).toBe(false);
  expect(isValidTransition('cancelled', 'confirmed')).toBe(false);
});

test('canTransitionTo is an alias for isValidTransition', () => {
  expect(canTransitionTo('proposed', 'confirmed')).toBe(true);
  expect(canTransitionTo('proposed', 'completed')).toBe(false);
});

test('getValidTransitions returns correct transitions', () => {
  expect(getValidTransitions('proposed')).toEqual(['confirmed', 'cancelled']);
  expect(getValidTransitions('confirmed')).toEqual(['completed', 'cancelled']);
  expect(getValidTransitions('completed')).toEqual([]);
  expect(getValidTransitions('cancelled')).toEqual([]);
  expect(getValidTransitions('unknown')).toEqual([]);
});