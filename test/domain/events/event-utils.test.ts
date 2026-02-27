const generateEventId = require('../../src/domain/events/event-utils').generateEventId;
const generateAggregateId = require('../../src/domain/events/event-utils').generateAggregateId;

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