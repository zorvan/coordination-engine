import { useCallback, useEffect, useState } from 'react'
import { cancelMatch, completeMatch, confirmMatch, createMatch, getMatch, listMatches, type Match } from '@infrastructure/api/match-service'

type MatchState = 'proposed' | 'confirmed' | 'completed' | 'cancelled'

export type MatchView = {
  matchId: string
  state: MatchState
  title: string
  description: string
  scheduledTime: Date
  durationMinutes: number
  location: string
  participantIds: string[]
  createdAt: Date
  updatedAt: Date
  organizerId: string
  notes?: string
}

function toMatchView(match: Match): MatchView {
  return {
    matchId: match.matchId,
    state: match.state,
    title: match.title,
    description: match.description ?? '',
    scheduledTime: new Date(match.scheduledTime),
    durationMinutes: match.durationMinutes,
    location: match.location,
    participantIds: match.participantIds ?? [],
    organizerId: match.organizerId,
    createdAt: match.createdAt ? new Date(match.createdAt) : new Date(),
    updatedAt: match.updatedAt ? new Date(match.updatedAt) : new Date(),
    notes: match.notes,
  }
}

export function useMatchesData() {
  const [matches, setMatches] = useState<MatchView[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | undefined>(undefined)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const items = await listMatches()
      setMatches(items.map(toMatchView))
      setError(undefined)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { matches, loading, error, refresh }
}

export function useMatchData(matchId: string) {
  const [match, setMatch] = useState<MatchView | undefined>(undefined)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | undefined>(undefined)

  const refresh = useCallback(async () => {
    if (!matchId) {
      setMatch(undefined)
      setLoading(false)
      return
    }

    setLoading(true)
    try {
      const item = await getMatch(matchId)
      setMatch(toMatchView(item))
      setError(undefined)
    } catch (err) {
      setMatch(undefined)
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [matchId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { match, loading, error, refresh }
}

export function useMatchCommands() {
  const createMatchCommand = useCallback(
    async (input: {
      organizerId: string
      title: string
      description: string
      scheduledTime: Date
      durationMinutes: number
      location: string
      participantIds: string[]
    }) => {
      return createMatch({
        organizerId: input.organizerId,
        title: input.title,
        description: input.description,
        scheduledTime: input.scheduledTime.toISOString(),
        durationMinutes: input.durationMinutes,
        location: input.location,
        participantIds: input.participantIds,
      })
    },
    []
  )

  const confirmMatchCommand = useCallback(
    async (matchId: string, actorId: string) => {
      await confirmMatch(matchId, actorId)
    },
    []
  )

  const completeMatchCommand = useCallback(
    async (matchId: string, actorId: string) => {
      await completeMatch(matchId, actorId)
    },
    []
  )

  const cancelMatchCommand = useCallback(
    async (matchId: string, actorId: string, reason: string) => {
      await cancelMatch(matchId, actorId, reason)
    },
    []
  )

  return {
    createMatch: createMatchCommand,
    confirmMatch: confirmMatchCommand,
    completeMatch: completeMatchCommand,
    cancelMatch: cancelMatchCommand,
  }
}
