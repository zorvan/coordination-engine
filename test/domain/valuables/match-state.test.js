const { MATCH_STATE_MACHINE, isValidTransition, canTransitionTo, getValidTransitions } = require('../../src/domain/valuables/match-state');

test('MATCH_STATE_MACHINE defines valid transitions', () => {
  expect(MATCH_STATE_MACHINE.proposed).toContain('confirmed');
  expect(MATCH_STATE_MACHINE.proposed).toContain('cancelled');
  expect(MATCH_STATE_MACHINE.confirmed).toContain('completed');
  expect(MATCH_STATE_MACHINE.confirmed).toContain('cancelled');
  expect(MATCH_STATE_MACHINE.completed).toEqual([]);
  expect(MATCH_STATE_MACHINE.cancelled).toEqual([]);
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