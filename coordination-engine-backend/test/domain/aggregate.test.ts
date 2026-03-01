import { generateEventId as generateEventId } from '../../src/domain/events/event-utils';
import { generateAggregateId as generateAggregateId } from '../../src/domain/events/event-utils';
import { createTemporalIdentity as createTemporalIdentity } from '../../src/domain/entities/temporal-identity';
import { createActor } from '../../src/domain/entities/actor';

test('generateEventId creates unique event IDs', () => {
  const id1 = generateEventId();
  const id2 = generateEventId();

  expect(id1).not.toBe(id2);
});

test('generateAggregateId creates unique aggregate IDs', () => {
  const id1 = generateAggregateId();
  const id2 = generateAggregateId();

  expect(id1).not.toBe(id2);
});

test('createTemporalIdentity creates identity with versions', () => {
  const identity = createTemporalIdentity('identity1');
  
  expect(identity.identityId).toBe('identity1');
  expect(identity.versions).toEqual([]);
  expect(identity.currentVersionIndex).toBe(-1);
});

test('createTemporalIdentity adds and gets versions', () => {
  const identity = createTemporalIdentity('identity1');
  
  const version1 = {
    state: 'active',
    trustLevel: 'untrusted',
    trustScore: 0,
    validFrom: new Date('2024-01-01')
  };
  
  identity.addVersion(1, version1.validFrom);
  
  expect(identity.versions).toHaveLength(1);
  expect(identity.getCurrentVersion().version).toBe(1);
});

test('createActor validates email and creates actor', () => {
  expect(() => createActor('actor1', 'John Doe', 'invalid-email')).toThrow();
  
  const actor = createActor('actor1', 'John Doe', 'john@example.com');
  expect(actor.id).toBe('actor1');
  expect(actor.name).toBe('John Doe');
  expect(actor.email).toBe('john@example.com');
});