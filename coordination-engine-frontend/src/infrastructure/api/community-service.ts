import { API_BASE_URL } from './client'
import type { AvailabilitySlot, Friend, Group } from '@presentation/components'

export type CommunitySnapshot = {
  calendarSlots: AvailabilitySlot[]
  friends: Friend[]
  groups: Group[]
  updatedAt?: string
}

export async function fetchCommunitySnapshot(userId: string): Promise<CommunitySnapshot | null> {
  const response = await fetch(`${API_BASE_URL}/actors/${encodeURIComponent(userId)}/community`)
  if (!response.ok) {
    return null
  }
  const data = await response.json() as { community?: CommunitySnapshot }
  return data.community || null
}

export async function saveCommunitySnapshot(
  userId: string,
  payload: Partial<CommunitySnapshot>
): Promise<CommunitySnapshot | null> {
  const response = await fetch(`${API_BASE_URL}/actors/${encodeURIComponent(userId)}/community`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    return null
  }
  const data = await response.json() as { community?: CommunitySnapshot }
  return data.community || null
}
