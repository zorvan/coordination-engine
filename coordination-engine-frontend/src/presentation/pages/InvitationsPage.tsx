/**
 * Invitations page component.
 */

import { useCallback, useEffect, useState } from 'react'
import { Button, Card, CardHeader, CardBody, EmptyState, Form, FormGroup, Input, Loading, Modal } from '@presentation/components'
import { confirmMatch, getAvailability, listMatches, submitAvailability, type AvailabilityPriority } from '@infrastructure/api/match-service'

interface InvitationItem {
  id: string
  title: string
  organizerId: string
  when: Date
  location: string
  description?: string
}

export function InvitationsPage() {
  const actorId = typeof window !== 'undefined' ? sessionStorage.getItem('ce-auth-user') || '' : ''
  const [invitations, setInvitations] = useState<InvitationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [acceptingId, setAcceptingId] = useState<string | null>(null)
  const [selectedInvitation, setSelectedInvitation] = useState<InvitationItem | null>(null)
  const [saveLoading, setSaveLoading] = useState(false)
  const [priority, setPriority] = useState<AvailabilityPriority>('medium')
  const [availabilityStart, setAvailabilityStart] = useState('')
  const [availabilityEnd, setAvailabilityEnd] = useState('')
  const [commitments, setCommitments] = useState('')
  const [error, setError] = useState('')

  const loadInvitations = useCallback(async () => {
    if (!actorId) {
      setInvitations([])
      setLoading(false)
      return
    }
    try {
      const matches = await listMatches(actorId)
      const incoming = matches
        .filter(
          (match) =>
            match.organizerId !== actorId &&
            match.participantIds.includes(actorId) &&
            match.state === 'proposed'
        )
        .map((match) => ({
          id: match.matchId,
          title: match.title,
          organizerId: match.organizerId,
          when: new Date(match.scheduledTime),
          location: match.location,
          description: match.description,
        }))
      setInvitations(incoming)
    } finally {
      setLoading(false)
    }
  }, [actorId])

  useEffect(() => {
    void loadInvitations()
  }, [loadInvitations])

  async function handleAccept(invite: InvitationItem) {
    if (!actorId) {
      return
    }
    setAcceptingId(invite.id)
    try {
      await confirmMatch(invite.id, actorId)
      await loadInvitations()
    } finally {
      setAcceptingId(null)
    }
  }

  async function openAvailabilityModal(invite: InvitationItem) {
    setSelectedInvitation(invite)
    setError('')
    if (!actorId) {
      return
    }
    const existing = await getAvailability(invite.id, actorId)
    if (existing) {
      setPriority(existing.priority)
      setAvailabilityStart(existing.availabilityStart)
      setAvailabilityEnd(existing.availabilityEnd)
      setCommitments(existing.commitments || '')
      return
    }
    setPriority('medium')
    setAvailabilityStart('')
    setAvailabilityEnd('')
    setCommitments('')
  }

  async function handleSaveAvailability(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedInvitation || !actorId) {
      return
    }
    if (!availabilityStart || !availabilityEnd) {
      setError('Availability start and end are required.')
      return
    }

    setSaveLoading(true)
    setError('')
    try {
      await submitAvailability({
        matchId: selectedInvitation.id,
        actorId,
        priority,
        availabilityStart,
        availabilityEnd,
        commitments,
      })
      setSelectedInvitation(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save availability')
    } finally {
      setSaveLoading(false)
    }
  }

  if (loading) {
    return <Loading message="Loading invitations..." />
  }

  if (invitations.length === 0) {
    return (
      <EmptyState
        title="No pending invitations"
        message="You don't have any pending invitations at the moment."
        icon="📭"
      />
    )
  }

  return (
    <div className="panel">
      <div className="section-head">
        <h2>Invitations</h2>
        <span className="subtle">{invitations.length} pending</span>
      </div>

      <div className="invite-list">
        {invitations.map((invite) => (
          <Card key={invite.id} className="invite-card">
            <CardHeader
              title={invite.title}
              subtitle={`Invited by ${invite.organizerId}`}
            />
            <CardBody className="invite-details">
              <div className="detail-row">
                <span className="label">📅</span>
                <span>{invite.when.toLocaleString()}</span>
              </div>
              <div className="detail-row">
                <span className="label">📍</span>
                <span>{invite.location}</span>
              </div>
              {invite.description && (
                <p className="description">{invite.description}</p>
              )}
            </CardBody>
            <div className="inline-actions">
              <Button
                variant="primary"
                loading={acceptingId === invite.id}
                disabled={acceptingId !== null}
                onClick={() => void handleAccept(invite)}
              >
                Accept
              </Button>
              <Button variant="primary" onClick={() => void openAvailabilityModal(invite)}>
                Set Availability
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <Modal open={Boolean(selectedInvitation)} title="Availability Preferences" onClose={() => setSelectedInvitation(null)}>
        <Form onSubmit={handleSaveAvailability}>
          <FormGroup label="Priority">
            <select className="input" value={priority} onChange={(e) => setPriority(e.target.value as AvailabilityPriority)}>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </FormGroup>

          <FormGroup label="Available From">
            <Input type="datetime-local" value={availabilityStart} onChange={(e) => setAvailabilityStart(e.target.value)} required />
          </FormGroup>

          <FormGroup label="Available Until">
            <Input type="datetime-local" value={availabilityEnd} onChange={(e) => setAvailabilityEnd(e.target.value)} required />
          </FormGroup>

          <FormGroup label="Commitments">
            <textarea
              className="input"
              rows={3}
              value={commitments}
              onChange={(e) => setCommitments(e.target.value)}
              placeholder="Conflicts, constraints, or non-negotiable commitments"
            />
          </FormGroup>

          {error ? <p className="auth-error">{error}</p> : null}

          <div className="inline-actions">
            <Button type="button" variant="ghost" onClick={() => setSelectedInvitation(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={saveLoading} disabled={saveLoading}>
              Save
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  )
}
