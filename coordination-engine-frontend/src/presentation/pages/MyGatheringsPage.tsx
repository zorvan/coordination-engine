/**
 * My Gatherings page component.
 */

import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card, CardHeader, CardBody, EmptyState, Loading, Modal, Form, FormGroup, Input, TextArea } from '@presentation/components'
import { useMatchCommands, useMatchesData } from '@presentation/hooks/useMatch'
import { getSessionUserId } from '@presentation/auth/session-storage'

interface GatheringFormData {
  title: string
  description: string
  when: string
  duration: string
  location: string
}

function isValidDate(value: Date): boolean {
  return !Number.isNaN(value.getTime())
}

function defaultWhenValue(): string {
  const nextHour = new Date(Date.now() + 60 * 60 * 1000)
  return nextHour.toISOString().slice(0, 16)
}

type Gathering = {
  matchId: string
  title: string
  scheduledTime: Date
  durationMinutes: number
  location: string
  participantIds: string[]
  state: 'proposed' | 'confirmed' | 'completed' | 'cancelled'
  description?: string
}

export function MyGatheringsPage() {
  const navigate = useNavigate()
  const { matches, loading, refresh } = useMatchesData()
  const { createMatch } = useMatchCommands()
  const actorId = getSessionUserId()
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  const gatherings = useMemo<Gathering[]>(
    () =>
      matches
        .filter(
          (match) =>
            actorId &&
            (match.organizerId === actorId || match.participantIds.includes(actorId))
        )
        .sort((a, b) => a.scheduledTime.getTime() - b.scheduledTime.getTime()),
    [actorId, matches]
  )

  async function handleCreateGathering(formData: GatheringFormData) {
    if (!actorId) {
      return
    }

    const scheduledTime = new Date(formData.when)
    if (!isValidDate(scheduledTime)) {
      return
    }

    setSaving(true)
    try {
      const createdId = await createMatch({
        organizerId: actorId,
        title: formData.title,
        description: formData.description,
        scheduledTime,
        durationMinutes: Number(formData.duration) || 90,
        location: formData.location,
        participantIds: [actorId],
      })

      if (!createdId) {
        return
      }

      await refresh()
      setCreateModalOpen(false)
      navigate(`/matches/${createdId}`)
    } finally {
      setSaving(false)
    }
  }

  function handleViewGathering(id: string) {
    navigate(`/matches/${id}`)
  }

  if (loading) {
    return <Loading message="Loading gatherings..." />
  }

  if (gatherings.length === 0) {
    return (
      <>
        <EmptyState
          title="No gatherings yet"
          message="Create your first gathering to get started."
          icon="🎯"
          action={
            <Button
              variant="primary"
              onClick={() => setCreateModalOpen(true)}
            >
              + Create Gathering
            </Button>
          }
        />
        <CreateGatheringModal
          open={createModalOpen}
          onClose={() => setCreateModalOpen(false)}
          onSubmit={handleCreateGathering}
          saving={saving}
        />
      </>
    )
  }

  return (
    <div className="panel">
      <div className="section-head">
        <h2>My Gatherings</h2>
        <Button
          variant="primary"
          onClick={() => setCreateModalOpen(true)}
        >
          + New Gathering
        </Button>
      </div>

      <div className="card-grid">
        {gatherings.map((gathering) => (
          <Card key={gathering.matchId}>
            <CardHeader
              title={gathering.title}
              subtitle={`${gathering.participantIds.length} participants`}
            />
            <CardBody>
              <div className="meta">
                <span>📅 {gathering.scheduledTime.toLocaleString()}</span>
                <span className={`state ${gathering.state}`}>
                  {gathering.state}
                </span>
              </div>
              {gathering.description && (
                <p className="subtle">{gathering.description}</p>
              )}
              <p>📍 {gathering.location}</p>
            </CardBody>
            <div className="inline-actions">
              <Button variant="ghost" onClick={() => handleViewGathering(gathering.matchId)}>
                View Details
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <CreateGatheringModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSubmit={handleCreateGathering}
        saving={saving}
      />
    </div>
  )
}

interface CreateGatheringModalProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: GatheringFormData) => Promise<void>
  saving: boolean
}

function CreateGatheringModal({ open, onClose, onSubmit, saving }: CreateGatheringModalProps) {
  const [formData, setFormData] = useState<GatheringFormData>({
    title: '',
    description: '',
    when: defaultWhenValue(),
    duration: '90',
    location: '',
  })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await onSubmit(formData)
    setFormData({
      title: '',
      description: '',
      when: defaultWhenValue(),
      duration: '90',
      location: '',
    })
  }

  return (
    <Modal open={open} title="Create New Gathering" onClose={onClose}>
      <Form onSubmit={handleSubmit}>
        <FormGroup label="Title" required>
          <Input
            type="text"
            placeholder="Gathering title"
            value={formData.title}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, title: e.target.value }))
            }
            required
          />
        </FormGroup>

        <FormGroup label="Description">
          <TextArea
            placeholder="Describe the gathering..."
            value={formData.description}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, description: e.target.value }))
            }
            rows={4}
          />
        </FormGroup>

        <FormGroup label="When" required>
          <Input
            type="datetime-local"
            value={formData.when}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, when: e.target.value }))
            }
            required
          />
        </FormGroup>

        <FormGroup label="Duration (minutes)" required>
          <Input
            type="number"
            min="15"
            step="15"
            value={formData.duration}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, duration: e.target.value }))
            }
            required
          />
        </FormGroup>

        <FormGroup label="Location" required>
          <Input
            type="text"
            placeholder="Where will this gathering happen?"
            value={formData.location}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, location: e.target.value }))
            }
            required
          />
        </FormGroup>

        <div className="inline-actions">
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" loading={saving} disabled={saving}>
            Create Gathering
          </Button>
        </div>
      </Form>
    </Modal>
  )
}
