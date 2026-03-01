import { API_BASE_URL } from './client'

export type ActorRecord = Record<string, unknown>

export type OnboardingProfilePayload = {
  name: string
  phone: string
  location: string
  website: string
  bio: string
  onboardingCompletedAt: string
}

export function isOnboardingCompleteFromActor(actor: ActorRecord): boolean {
  return Boolean(
    actor.onboardingCompletedAt ||
    (typeof actor.phone === 'string' && actor.phone.trim()) &&
    (typeof actor.location === 'string' && actor.location.trim()) &&
    (typeof actor.bio === 'string' && actor.bio.trim())
  )
}

export async function fetchActorProfile(userId: string): Promise<ActorRecord | null> {
  const response = await fetch(`${API_BASE_URL}/actors/${encodeURIComponent(userId)}`)
  if (!response.ok) {
    return null
  }

  const data = await response.json() as { actor?: ActorRecord }
  return data.actor || {}
}

export async function updateActorProfile(
  userId: string,
  payload: OnboardingProfilePayload
): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/actors/${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  return response.ok
}
