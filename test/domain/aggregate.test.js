const generateEventId = require('../../src/domain/events/event-utils').generateEventId;
const generateAggregateId = require('../../src/domain/events/event-utils').generateAggregateId;
const createTemporalIdentity = require('../../src/domain/entities/temporal-identity').createTemporalIdentity;
const createActor = require('../../src/domain/entities/actor').createActor;

test('generateEventId creates unique event IDs', () => {
  const id1 = generateEventId();
  const id2 = generateEventId();

  expect(id1).not.toBe(id2);
  expect(id1).toContain('evt_');
  expect(id2).toContain('evt_');
});

test('generateAggregateId creates unique aggregate IDs', () => {
  const id1 = generateAggregateId();
  const id2 = generateAggregateId();

  expect(id1).not.toBe(id2);
  expect(id1).toContain('agg_');
  expect(id2).toContain('agg_');
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
  
  identity.addVersion(version1);
  
  expect(identity.versions).toHaveLength(1);
  expect(identity.getCurrentVersion()).toBe(version1);
});

test('createActor validates email and creates actor', () => {
  expect(() => createActor('actor1', 'John Doe', 'invalid-email')).toThrow();
  
  const actor = createActor('actor1', 'John Doe', 'john@example.com');
  expect(actor.id.value).toBe('actor1');
  expect(actor.attributes.name).toBe('John Doe');
  expect(actor.attributes.email).toBe('john@example.com');
});