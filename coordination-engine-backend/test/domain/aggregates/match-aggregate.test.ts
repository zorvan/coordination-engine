import { MatchAggregate } from '../../../src/domain/aggregates/match-aggregate';
import { MatchState } from '../../../src/domain/valuables/match-state';

describe('MatchAggregate', () => {
  let match;

  beforeEach(() => {
    match = MatchAggregate.create(
      'match-123',
      'organizer-1',
      'Game Night',
      'Join us for board games',
      new Date('2026-03-01'),
      120,
      'Room 101',
      ['player-1', 'player-2', 'player-3']
    );
  });

  test('creates match in proposed state', () => {
    expect(match.matchId).toBe('match-123');
    expect(match.state).toBe(MatchState.PROPOSED);
    expect(match.organizerId).toBe('organizer-1');
    expect(match.title).toBe('Game Night');
    expect(match.description).toBe('Join us for board games');
    expect(match.scheduledTime).toBeInstanceOf(Date);
    expect(match.durationMinutes).toBe(120);
    expect(match.location).toBe('Room 101');
    expect(match.participantIds).toEqual(['player-1', 'player-2', 'player-3']);
    expect(match.createdAt).toBeInstanceOf(Date);
    expect(match.updatedAt).toBeInstanceOf(Date);
    expect(match.version).toBe(0);
  });

  test('confirms match and transitions state', () => {
    match.confirm();
    expect(match.state).toBe(MatchState.CONFIRMED);
    expect(match.version).toBe(1);
  });

  test('completed match and transitions state', () => {
    match.confirm();
    match.complete('Great game!');

    expect(match.state).toBe(MatchState.COMPLETED);
    expect(match.version).toBe(2);
    expect(match.notes).toBe('Great game!');
    expect(match.completedAt).toBeInstanceOf(Date);
  });

  test('cancels match and transitions state', () => {
    match.cancel('Too few participants');

    expect(match.state).toBe(MatchState.CANCELLED);
    expect(match.version).toBe(1);
    expect(match.notes).toBe('Too few participants');
    expect(match.cancelledAt).toBeInstanceOf(Date);
  });

  test('throws error for invalid state transitions', () => {
    expect(() => {
      match.complete('Complete without confirming');
    }).toThrow('Invalid transition from proposed to completed');
  });

  test('isValidTransition checks state machine', () => {
    expect(match.isValidTransition(MatchState.CONFIRMED)).toBe(true);
    expect(match.isValidTransition(MatchState.CANCELLED)).toBe(true);
    expect(match.isValidTransition(MatchState.COMPLETED)).toBe(false);
  });

  test('has valid transitions from proposed state', () => {
    expect(match.isValidTransition(MatchState.CONFIRMED)).toBe(true);
    expect(match.isValidTransition(MatchState.CANCELLED)).toBe(true);
  });

  test('has valid transitions from confirmed state', () => {
    match.confirm();
    expect(match.isValidTransition(MatchState.COMPLETED)).toBe(true);
    expect(match.isValidTransition(MatchState.CANCELLED)).toBe(true);
  });

  test('has no valid transitions from completed state', () => {
    match.confirm();
    match.complete('Done');
    expect(match.isValidTransition(MatchState.CONFIRMED)).toBe(false);
    expect(match.isValidTransition(MatchState.COMPLETED)).toBe(false);
  });

  test('has no valid transitions from cancelled state', () => {
    match.cancel('Cancelled');
    expect(match.isValidTransition(MatchState.CONFIRMED)).toBe(false);
    expect(match.isValidTransition(MatchState.COMPLETED)).toBe(false);
  });
});
