import { CreateMatchUseCase } from '@application/usecases/match'
import { InMemoryEventStore } from '@infrastructure/persistence/in-memory-event-store'
import { DomainEventType } from '@domain/events/event-utils'

export async function seedDemoData(eventStore: InMemoryEventStore): Promise<void> {
  const existing = await eventStore.getEventsByType(DomainEventType.MATCH_CREATED)
  if (existing.length > 0) {
    return
  }

  const createMatch = CreateMatchUseCase.create(eventStore)
  const now = new Date()

  await createMatch.execute(
    'organizer-1',
    'Saturday Basketball',
    'Weekly pickup match at the neighborhood court',
    new Date(now.getTime() + 1000 * 60 * 60 * 24),
    90,
    'City Court',
    ['organizer-1', 'mert', 'aylin', 'deniz']
  )

  await createMatch.execute(
    'organizer-1',
    'Board Games Night',
    'Open invitation for strategy games',
    new Date(now.getTime() + 1000 * 60 * 60 * 36),
    120,
    'Community Hall',
    ['organizer-1', 'selin', 'omer']
  )

  await createMatch.execute(
    'organizer-1',
    'Product Sprint Sync',
    'Cross-team planning session',
    new Date(now.getTime() + 1000 * 60 * 60 * 48),
    60,
    'Online',
    ['organizer-1', 'team-a', 'team-b']
  )
}
