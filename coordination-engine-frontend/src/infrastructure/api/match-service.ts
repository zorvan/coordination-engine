/**
 * Match API service.
 * 
 * This module provides service functions for interacting with the match API endpoints.
 */

import { post, get } from './client'

/**
 * Match data interface for API responses.
 */
export interface Match {
  matchId: string
  state: 'proposed' | 'confirmed' | 'completed' | 'cancelled'
  title: string
  description?: string
  scheduledTime: string
  durationMinutes: number
  location: string
  participantIds: string[]
  organizerId: string
  createdAt?: string
  updatedAt?: string
  notes?: string
}

export type AvailabilityPriority = 'high' | 'medium' | 'low'

export interface AvailabilityPreference {
  actorId: string
  priority: AvailabilityPriority
  availabilityStart: string
  availabilityEnd: string
  commitments: string
  submittedAt?: string
}

function unwrapData<T>(response: { data?: T } & Record<string, unknown>): T | undefined {
  if (response.data !== undefined) {
    return response.data
  }
  return response as unknown as T
}

export async function listMatches(actorId?: string): Promise<Match[]> {
  const suffix = actorId ? `?actorId=${encodeURIComponent(actorId)}` : ''
  const response = await get<{ matches: Match[] }>(`/matches${suffix}`)

  if (response.status === 'error') {
    throw new Error(response.message || 'Failed to fetch matches')
  }

  const payload = unwrapData<{ matches: Match[] }>(response)
  return payload?.matches || []
}

export async function submitAvailability(input: {
  matchId: string
  actorId: string
  priority: AvailabilityPriority
  availabilityStart: string
  availabilityEnd: string
  commitments: string
}): Promise<void> {
  const response = await post<{ status: string }>('/matches/availability', input)
  if (response.status === 'error') {
    throw new Error(response.message || 'Failed to save availability')
  }
}

export async function getAvailability(matchId: string, actorId: string): Promise<AvailabilityPreference | null> {
  const response = await get<{ availability: AvailabilityPreference }>(`/matches/${encodeURIComponent(matchId)}/availability/${encodeURIComponent(actorId)}`)
  if (response.status === 'error') {
    return null
  }
  const payload = unwrapData<{ availability: AvailabilityPreference }>(response)
  return payload?.availability || null
}

/**
 * Create a new match.
 * 
 * @param input - Match creation parameters
 * @returns The created match ID
 */
export async function createMatch(input: {
  organizerId: string
  title: string
  description: string
  scheduledTime: string
  durationMinutes: number
  location: string
  participantIds: string[]
}): Promise<string> {
  const response = await post<{ matchId: string }>('/matches', input)
  
  if (response.status === 'error') {
    throw new Error(response.message || 'Failed to create match')
  }

  const payload = unwrapData<{ matchId: string }>(response)
  return payload?.matchId || ''
}

/**
 * Confirm a match.
 * 
 * @param matchId - ID of the match to confirm
 * @param actorId - ID of the actor confirming
 */
export async function confirmMatch(matchId: string, actorId: string): Promise<void> {
  const response = await post<{ status: string }>('/matches/confirm', {
    matchId,
    actorId,
  })
  
  if (response.status === 'error') {
    throw new Error(response.message || 'Failed to confirm match')
  }
}

/**
 * Complete a match.
 * 
 * @param matchId - ID of the match to complete
 * @param actorId - ID of the actor completing
 * @param notes - Optional completion notes
 */
export async function completeMatch(
  matchId: string,
  actorId: string,
  notes?: string
): Promise<void> {
  const response = await post<{ status: string }>('/matches/complete', {
    matchId,
    actorId,
    notes,
  })
  
  if (response.status === 'error') {
    throw new Error(response.message || 'Failed to complete match')
  }
}

/**
 * Cancel a match.
 * 
 * @param matchId - ID of the match to cancel
 * @param actorId - ID of the actor cancelling
 * @param reason - Reason for cancellation
 */
export async function cancelMatch(
  matchId: string,
  actorId: string,
  reason: string
): Promise<void> {
  const response = await post<{ status: string }>('/matches/cancel', {
    matchId,
    actorId,
    reason,
  })
  
  if (response.status === 'error') {
    throw new Error(response.message || 'Failed to cancel match')
  }
}

/**
 * Get match details by ID.
 * 
 * @param matchId - ID of the match to fetch
 * @returns The match details
 */
export async function getMatch(matchId: string): Promise<Match> {
  const response = await get<Match>(`/matches/${matchId}`)
  
  if (response.status === 'error') {
    throw new Error(response.message || 'Failed to fetch match')
  }
  
  const payload = unwrapData<Match>(response)
  return payload || ({ matchId, state: 'proposed' } as Match)
}
