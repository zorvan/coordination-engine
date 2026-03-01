import { useEffect, useState } from 'react'
import { Button } from '@presentation/components'

type OnboardingPayload = {
  name: string
  phone: string
  location: string
  website: string
  bio: string
}

type OnboardingPageProps = {
  initialEmail: string
  initialName?: string
  loading?: boolean
  error?: string
  onSubmit: (payload: OnboardingPayload) => Promise<void>
}

export function OnboardingPage({
  initialEmail,
  initialName = '',
  loading = false,
  error,
  onSubmit,
}: OnboardingPageProps) {
  const [name, setName] = useState(initialName)
  const [phone, setPhone] = useState('')
  const [location, setLocation] = useState('')
  const [website, setWebsite] = useState('')
  const [bio, setBio] = useState('')
  const [formError, setFormError] = useState('')
  const hasKnownName = Boolean(initialName.trim())

  useEffect(() => {
    if (initialName.trim()) {
      setName(initialName.trim())
    }
  }, [initialName])

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const effectiveName = hasKnownName ? initialName.trim() : name.trim()
    if (!effectiveName || !phone.trim() || !location.trim() || !bio.trim()) {
      setFormError('Name, phone, location, and bio are required.')
      return
    }

    setFormError('')
    void onSubmit({
      name: effectiveName,
      phone: phone.trim(),
      location: location.trim(),
      website: website.trim(),
      bio: bio.trim(),
    })
  }

  return (
    <div className="auth-page">
      <section className="auth-card">
        <div className="auth-head">
          <h1>Complete your profile</h1>
          <p>First login setup. This information will be saved to your account.</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {hasKnownName ? (
            <>
              <label htmlFor="onboarding-name">Full name</label>
              <input id="onboarding-name" type="text" value={initialName} disabled />
            </>
          ) : (
            <>
              <label htmlFor="onboarding-name">Full name</label>
              <input
                id="onboarding-name"
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Your full name"
              />
            </>
          )}

          <label htmlFor="onboarding-email">Email</label>
          <input
            id="onboarding-email"
            type="email"
            value={initialEmail}
            disabled
          />

          <label htmlFor="onboarding-phone">Phone</label>
          <input
            id="onboarding-phone"
            type="tel"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            placeholder="+1 555 123 4567"
          />

          <label htmlFor="onboarding-location">Location</label>
          <input
            id="onboarding-location"
            type="text"
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            placeholder="City, Country"
          />

          <label htmlFor="onboarding-website">Website (optional)</label>
          <input
            id="onboarding-website"
            type="url"
            value={website}
            onChange={(event) => setWebsite(event.target.value)}
            placeholder="example.com"
          />

          <label htmlFor="onboarding-bio">Bio</label>
          <textarea
            id="onboarding-bio"
            className="input"
            rows={4}
            value={bio}
            onChange={(event) => setBio(event.target.value)}
            placeholder="Tell people a bit about you"
          />

          {formError ? <p className="auth-error">{formError}</p> : null}
          {error ? <p className="auth-error">{error}</p> : null}

          <Button className="auth-submit" type="submit" loading={loading} disabled={loading}>
            Save and continue
          </Button>
        </form>
      </section>
    </div>
  )
}
