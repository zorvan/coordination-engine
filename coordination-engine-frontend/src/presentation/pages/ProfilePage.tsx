/**
 * User Profile page component.
 */

import { useEffect, useState } from 'react'
import { Button, Card, CardHeader, CardBody, Form, FormGroup, Input, Loading } from '@presentation/components'
import { API_BASE_URL } from '@infrastructure/api/client'

type ProfileModel = {
  name: string
  email: string
  phone: string
  bio: string
  location: string
  website: string
}

type ActorApiModel = {
  id?: string
  name?: string
  email?: string
  phone?: string
  bio?: string
  location?: string
  website?: string
}

const EMPTY_PROFILE: ProfileModel = {
  name: '',
  email: '',
  phone: '',
  bio: '',
  location: '',
  website: '',
}

export function mapActorToProfile(actor: ActorApiModel, fallback: ProfileModel = EMPTY_PROFILE): ProfileModel {
  // accept whatever comes from the server; empty strings should be stored as
  // empty rather than automatically replaced with a previous value.  fallback
  // is used only when the property is completely missing or not a string.
  const pick = (value: unknown, current: string) =>
    typeof value === 'string' ? value : current

  return {
    name: pick(actor.name, fallback.name),
    email: pick(actor.email, fallback.email),
    phone: pick(actor.phone, fallback.phone),
    bio: pick(actor.bio, fallback.bio),
    location: pick(actor.location, fallback.location),
    website: pick(actor.website, fallback.website),
  }
}

export function ProfilePage() {
  const cachedProfile = typeof window !== 'undefined' ? sessionStorage.getItem('ce-profile-cache') : null
  const initialProfile = (() => {
    if (!cachedProfile) {
      return EMPTY_PROFILE
    }
    try {
      return { ...EMPTY_PROFILE, ...(JSON.parse(cachedProfile) as Partial<ProfileModel>) }
    } catch (_err) {
      return EMPTY_PROFILE
    }
  })()

  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<ProfileModel>(initialProfile)
  const userId = typeof window !== 'undefined' ? sessionStorage.getItem('ce-auth-user') : null
  const [editing, setEditing] = useState(false)
  const [formData, setFormData] = useState<ProfileModel>(initialProfile)

  function handleSave() {
    (async () => {
      try {
        if (userId) {
          const normalizedWebsite = formData.website.trim()
          const normalizedFormData = {
            ...formData,
            website: normalizedWebsite,
          }
          // send the entire form data; the backend now treats these as a patch
          const res = await fetch(`${API_BASE_URL}/actors/${encodeURIComponent(userId)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(normalizedFormData),
          })
          if (res.ok) {
            const data = await res.json()
            // if the server returned an actor use it to update state, otherwise
            // fall back to what the user just submitted
            const nextProfile = mapActorToProfile(
              (data && data.actor) as ActorApiModel || normalizedFormData,
              profile
            )
            setProfile(nextProfile)
            setFormData(nextProfile)
            sessionStorage.setItem('ce-profile-cache', JSON.stringify(nextProfile))
          }
        }
      } catch (_err) {
        // keep current profile on save failure
      } finally {
        setEditing(false)
      }
    })()
  }

  function handleCancel() {
    setFormData(profile)
    setEditing(false)
  }

  function handleProfileSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    handleSave()
  }

  useEffect(() => {
    (async () => {
      try {
        if (!userId) {
          setLoading(false)
          return
        }
        const res = await fetch(`${API_BASE_URL}/actors/${encodeURIComponent(userId)}`)
        if (!res.ok) {
          setLoading(false)
          return
        }
        const data = await res.json()
        if (data && data.actor) {
          const nextProfile = mapActorToProfile(data.actor as ActorApiModel, initialProfile)
          setProfile(nextProfile)
          setFormData(nextProfile)
          sessionStorage.setItem('ce-profile-cache', JSON.stringify(nextProfile))
        }
      } catch (_err) {
        // ignore
      } finally {
        setLoading(false)
      }
    })()
  }, [userId])

  const avatarInitials = profile.name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('') || 'U'

  const websiteHref = profile.website
    ? (profile.website.startsWith('http://') || profile.website.startsWith('https://')
      ? profile.website
      : `https://${profile.website}`)
    : '#'

  if (loading) {
    return <Loading message="Loading profile..." />
  }

  return (
    <div className="panel">
      <div className="section-head">
        <h2>My Profile</h2>
        {!editing && (
          <Button variant="ghost" onClick={() => setEditing(true)}>
            Edit
          </Button>
        )}
      </div>

      <Card className="profile-card">
        <CardBody>
          <div className="profile-avatar">
            <div className="avatar-large">{avatarInitials}</div>
          </div>

          {!editing ? (
            <div className="profile-view">
              <div className="profile-item">
                <span className="label">Name</span>
                <span className="value">{profile.name}</span>
              </div>
              <div className="profile-item">
                <span className="label">Email</span>
                <span className="value">{profile.email}</span>
              </div>
              <div className="profile-item">
                <span className="label">Phone</span>
                <span className="value">{profile.phone}</span>
              </div>
              <div className="profile-item">
                <span className="label">Location</span>
                <span className="value">{profile.location}</span>
              </div>
              <div className="profile-item">
                <span className="label">Website</span>
                <span className="value">
                  <a href={websiteHref} target="_blank" rel="noopener noreferrer">
                    {profile.website}
                  </a>
                </span>
              </div>
              <div className="profile-item">
                <span className="label">Bio</span>
                <p className="value">{profile.bio}</p>
              </div>
            </div>
          ) : (
            <Form onSubmit={handleProfileSubmit}>
              <FormGroup label="Name">
                <Input
                  type="text"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, name: e.target.value }))
                  }
                />
              </FormGroup>

              <FormGroup label="Email">
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, email: e.target.value }))
                  }
                />
              </FormGroup>

              <FormGroup label="Phone">
                <Input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, phone: e.target.value }))
                  }
                />
              </FormGroup>

              <FormGroup label="Location">
                <Input
                  type="text"
                  value={formData.location}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, location: e.target.value }))
                  }
                />
              </FormGroup>

              <FormGroup label="Website">
                <Input
                  type="text"
                  value={formData.website}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, website: e.target.value }))
                  }
                />
              </FormGroup>

              <FormGroup label="Bio">
                <textarea
                  className="input"
                  rows={4}
                  value={formData.bio}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, bio: e.target.value }))
                  }
                />
              </FormGroup>

              <div className="inline-actions">
                <Button type="button" variant="ghost" onClick={handleCancel}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary">
                  Save Changes
                </Button>
              </div>
            </Form>
          )}
        </CardBody>
      </Card>

      <Card className="profile-stats">
        <CardHeader title="Statistics" />
        <CardBody>
          <div className="stats-grid">
            <div className="stat">
              <span className="number">24</span>
              <span className="label">Gatherings Created</span>
            </div>
            <div className="stat">
              <span className="number">156</span>
              <span className="label">Participants</span>
            </div>
            <div className="stat">
              <span className="number">92%</span>
              <span className="label">Satisfaction</span>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  )
}
