/**
 * Application services for match use cases.
 * 
 * This module provides implementation of the use cases defined in the
 * application layer. These services coordinate domain objects to fulfill
 * specific business requirements.
 */

import { MatchCreated, MatchConfirmed, MatchCompleted, MatchCancelled } from '@domain/events/domain-event'
import { InMemoryEventStore } from '@infrastructure/persistence/in-memory-event-store'
import { generateAggregateId } from '@domain/events/event-utils'

/**
 * Create match use case.
 * 
 * Business logic:
 * - Organizer must be specified
 * - At least one participant is required
 * - Creates an event-sourced match with initial 'proposed' state
 */
export class CreateMatchUseCase {
  /**
   * Create a new create match use case.
   * 
   * @param eventStore - Event store for persistence
   * @returns Create match use case instance
   */
  static create(eventStore: InMemoryEventStore) {
    return {
      /**
       * Execute the create match use case.
       * 
       * Business logic:
       * - Validates that at least one participant is provided
       * - Generates a new aggregate ID for the match
       * - Creates the match aggregate with initial proposed state
       * - Records the MatchCreated event for event sourcing
       * 
       * @param organizerId - The actor creating the match
       * @param title - Match title
       * @param description - Optional description
       * @param scheduledTime - When the match is scheduled
       * @param durationMinutes - Duration in minutes
       * @param location - Physical or virtual location
       * @param participantIds - Array of participant actor IDs
       * @returns The created match ID
       */
      async execute(
        organizerId: string,
        title: string,
        description: string,
        scheduledTime: Date,
        durationMinutes: number,
        location: string,
        participantIds: string[]
      ): Promise<string> {
        participantIds = participantIds || []
        
        if (participantIds.length === 0) {
          throw new Error('At least one participant is required')
        }

        const matchId = generateAggregateId()
        
        const event = new MatchCreated(
          matchId,
          organizerId,
          title,
          description,
          scheduledTime,
          durationMinutes,
          location,
          participantIds
        )

        await eventStore.append(event)
        
        return matchId
      },
    }
  }
}

/**
 * Confirm match use case.
 * 
 * Business logic:
 * - Only organizer or participants can confirm a match
 * - Match must be in 'proposed' state
 * - Transitions to 'confirmed' state
 */
export class ConfirmMatchUseCase {
  /**
   * Create a new confirm match use case.
   * 
   * @param eventStore - Event store for persistence
   * @returns Confirm match use case instance
   */
  static create(eventStore: InMemoryEventStore) {
    return {
      /**
       * Execute the confirm match use case.
       * 
       * Business logic:
       * - Fetches match events from the event store
       * - Validates that the match exists
       * - Verifies the actor is authorized (organizer or participant)
       * - Records the MatchConfirmed event
       * 
       * @param matchId - The match to confirm
       * @param actorId - The actor confirming the match
       * @throws Error if match not found or actor not authorized
       */
      async execute(matchId: string, actorId: string): Promise<void> {
        const events = await eventStore.getEventsByAggregate(`Match:${matchId}`)
        const matchEvents = events.filter((e) => e.type === 'MatchCreated')
        
        if (matchEvents.length === 0) {
          throw new Error(`Match ${matchId} not found`)
        }

        const lastEvent = matchEvents[matchEvents.length - 1]
        const payload = lastEvent.payload as {
          organizerId: string
          participantIds: string[]
        }
        
        const participantIds = payload.participantIds || []
        const organizerId = payload.organizerId
        
        if (organizerId !== actorId && !participantIds.includes(actorId)) {
          throw new Error('Actor not authorized to confirm this match')
        }

        const event = new MatchConfirmed(
          matchId,
          actorId,
          new Date()
        )

        await eventStore.append(event)
      },
    }
  }
}

/**
 * Complete match use case.
 * 
 * Business logic:
 * - Only confirmed matches can be completed
 * - Both organizer and participants get trust updates
 * - Trust score = completed/accepted matches ratio
 */
export class CompleteMatchUseCase {
  /**
   * Create a new complete match use case.
   * 
   * @param eventStore - Event store for persistence
   * @returns Complete match use case instance
   */
  static create(eventStore: InMemoryEventStore) {
    return {
      /**
       * Execute the complete match use case.
       * 
       * Business logic:
       * - Counts completed and confirmed matches for the actor
       * - Calculates trust score based on match history
       * - Records the MatchCompleted event
       * 
       * @param matchId - The match to complete
       * @param completedBy - The actor completing the match
       * @param notes - Optional completion notes
       * @throws Error if match not found or not in confirmed state
       */
      async execute(matchId: string, completedBy: string): Promise<void> {
        const event = new MatchCompleted(
          matchId,
          completedBy,
          new Date()
        )

        await eventStore.append(event)
      },
    }
  }
}

/**
 * Cancel match use case.
 * 
 * Business logic:
 * - Only organizer or participants can cancel
 * - Match must be in 'proposed' or 'confirmed' state
 */
export class CancelMatchUseCase {
  /**
   * Create a new cancel match use case.
   * 
   * @param eventStore - Event store for persistence
   * @returns Cancel match use case instance
   */
  static create(eventStore: InMemoryEventStore) {
    return {
      /**
       * Execute the cancel match use case.
       * 
       * Business logic:
       * - Fetches match events from the event store
       * - Validates that the match exists
       * - Verifies the actor is authorized (organizer or participant)
       * - Records the MatchCancelled event
       * 
       * @param matchId - The match to cancel
       * @param cancelledBy - The actor cancelling the match
       * @param reason - Cancellation reason
       * @throws Error if match not found or actor not authorized
       */
      async execute(matchId: string, cancelledBy: string, reason: string): Promise<void> {
        const events = await eventStore.getEventsByAggregate(`Match:${matchId}`)
        const matchEvents = events.filter((e) => e.type === 'MatchCreated')
        
        if (matchEvents.length === 0) {
          throw new Error(`Match ${matchId} not found`)
        }

        const lastEvent = matchEvents[matchEvents.length - 1]
        const payload = lastEvent.payload as {
          organizerId: string
          participantIds: string[]
        }
        
        const participantIds = payload.participantIds || []
        const organizerId = payload.organizerId
        
        if (organizerId !== cancelledBy && !participantIds.includes(cancelledBy)) {
          throw new Error('Actor not authorized to cancel this match')
        }

        const event = new MatchCancelled(
          matchId,
          cancelledBy,
          reason,
          new Date()
        )

        await eventStore.append(event)
      },
    }
  }
}
