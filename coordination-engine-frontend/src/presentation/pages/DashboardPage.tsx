import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMatchCommands, useMatchesData } from '@presentation/hooks/useMatch'
import { Button } from '@presentation/components'
import { getSessionUserId } from '@presentation/auth/session-storage'

export function DashboardPage() {
  const navigate = useNavigate()
  const { matches, loading, error, refresh } = useMatchesData()
  const { createMatch, confirmMatch } = useMatchCommands()
  const actorId = getSessionUserId()

  const invitations = useMemo(
    () =>
      matches.filter(
        (match) =>
          actorId &&
          match.organizerId !== actorId &&
          match.participantIds.includes(actorId) &&
          match.state === 'proposed'
      ),
    [actorId, matches]
  )

  const pendingCount = invitations.length
  const upcoming = useMemo(
    () =>
      matches
        .filter(
          (match) =>
            actorId &&
            (match.organizerId === actorId || match.participantIds.includes(actorId)) &&
            match.state !== 'cancelled'
        )
        .sort((a, b) => a.scheduledTime.getTime() - b.scheduledTime.getTime())
        .slice(0, 6),
    [actorId, matches]
  )

  async function handleCreateGathering() {
    if (!actorId) {
      return
    }

    const now = new Date()
    const createdId = await createMatch({
      organizerId: actorId,
      title: `New Gathering ${now.toLocaleTimeString()}`,
      description: 'Created from dashboard CTA',
      scheduledTime: new Date(now.getTime() + 1000 * 60 * 60 * 24),
      durationMinutes: 90,
      location: 'Online',
      participantIds: [actorId],
    })

    if (!createdId) {
      return
    }

    await refresh()
    navigate(`/matches/${createdId}`)
  }

  async function handleInviteAccept(matchId: string) {
    if (!actorId) {
      return
    }
    await confirmMatch(matchId, actorId)
    await refresh()
  }

  return (
    <>
      <section className="panel">
        <div className="section-head">
          <h2>Upcoming Gatherings</h2>
          <Button variant="primary" onClick={() => void handleCreateGathering()}>+ Create Gathering</Button>
        </div>

        {loading ? <p className="subtle">Loading gatherings...</p> : null}
        {error ? <p className="subtle">{error}</p> : null}

        <div className="card-grid">
          {upcoming.map((g) => (
            <article key={g.matchId} className="card">
              <div className="card-head">
                <span className="type">Match</span>
                <span className={`state ${g.state}`}>{g.state}</span>
              </div>
              <h3>{g.title}</h3>
              <p>{g.scheduledTime.toLocaleString()}</p>
              <div className="meta">
                <span>{g.participantIds.length} members</span>
                <Button variant="ghost" onClick={() => navigate(`/matches/${g.matchId}`)}>View</Button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>Invitations</h2>
          <span className="subtle">{pendingCount} pending</span>
        </div>
        <div className="invite-list">
          {invitations.map((invite) => (
            <div key={invite.matchId} className="invite">
              <div>
                <strong>{invite.title}</strong>
                <p>{invite.scheduledTime.toLocaleString()}</p>
              </div>
              <div className="inline-actions">
                <Button variant="ghost" onClick={() => navigate('/invitations')}>Decline</Button>
                <Button variant="primary" onClick={() => void handleInviteAccept(invite.matchId)}>Accept</Button>
              </div>
            </div>
          ))}
          {invitations.length === 0 ? <p className="subtle">No pending invitations.</p> : null}
        </div>
      </section>
    </>
  )
}
