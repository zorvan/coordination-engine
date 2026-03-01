import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMatchCommands, useMatchData } from '../hooks/useMatch'
import { Button, Loading } from '@presentation/components'
import { getSessionUserId } from '@presentation/auth/session-storage'

export function MatchPage() {
  const { matchId } = useParams<{ matchId: string }>()
  const navigate = useNavigate()
  const { match, loading, error, refresh } = useMatchData(matchId || '')
  const { cancelMatch, completeMatch, confirmMatch } = useMatchCommands()
  const [busy, setBusy] = useState(false)
  const actorId = getSessionUserId()

  async function handleConfirm() {
    if (!matchId || !actorId) return
    setBusy(true)
    try {
      await confirmMatch(matchId, actorId)
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  async function handleComplete() {
    if (!matchId || !actorId) return
    setBusy(true)
    try {
      await completeMatch(matchId, actorId)
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  async function handleCancel() {
    if (!matchId || !actorId) return
    setBusy(true)
    try {
      await cancelMatch(matchId, actorId, 'Cancelled from UI')
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return <Loading message="Loading match..." />
  }

  if (error) {
    return (
      <div className="panel">
        <h2>Error loading match</h2>
        <p>{error}</p>
      </div>
    )
  }

  if (!match) {
    return (
      <div className="panel">
        <h2>Match not found</h2>
        <p>The match you&apos;re looking for doesn&apos;t exist.</p>
      </div>
    )
  }

  return (
    <div className="panel">
      <div className="section-head">
        <h2>{match.title}</h2>
        <span className={`state ${match.state}`}>{match.state}</span>
      </div>
      {match.description ? <p className="subtle">{match.description}</p> : null}
      <div className="match-details">
        <div className="detail-item"><span className="label">Organizer:</span><span className="value">{match.organizerId}</span></div>
        <div className="detail-item"><span className="label">Scheduled:</span><span className="value">{match.scheduledTime.toLocaleString()}</span></div>
        <div className="detail-item"><span className="label">Duration:</span><span className="value">{match.durationMinutes} minutes</span></div>
        <div className="detail-item"><span className="label">Location:</span><span className="value">{match.location}</span></div>
      </div>

      <div className="inline-actions" style={{ marginTop: '1rem' }}>
        {match.state === 'proposed' ? (
          <Button variant="primary" onClick={() => void handleConfirm()} disabled={busy}>Confirm</Button>
        ) : null}
        {match.state === 'confirmed' ? (
          <Button variant="primary" onClick={() => void handleComplete()} disabled={busy}>Complete</Button>
        ) : null}
        {(match.state === 'proposed' || match.state === 'confirmed') ? (
          <Button variant="ghost" onClick={() => void handleCancel()} disabled={busy}>Cancel</Button>
        ) : null}
        <Button variant="ghost" onClick={() => navigate('/')}>Back</Button>
      </div>
    </div>
  )
}
