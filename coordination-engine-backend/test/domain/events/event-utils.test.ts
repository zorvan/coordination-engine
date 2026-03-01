import { generateEventId as generateEventId } from '../../../src/domain/events/event-utils';
import { generateAggregateId as generateAggregateId } from '../../../src/domain/events/event-utils';

test('generateEventId creates unique event IDs', () => {
  const id1 = generateEventId();
  const id2 = generateEventId();

  expect(id1).not.toBe(id2);
  expect(id1).toMatch(/^[0-9a-f-]{36}$/);
  expect(id2).toMatch(/^[0-9a-f-]{36}$/);
});

test('generateAggregateId creates unique aggregate IDs', () => {
  const id1 = generateAggregateId();
  const id2 = generateAggregateId();

  expect(id1).not.toBe(id2);
  expect(id1).toMatch(/^[0-9a-f-]{36}$/);
  expect(id2).toMatch(/^[0-9a-f-]{36}$/);
});
