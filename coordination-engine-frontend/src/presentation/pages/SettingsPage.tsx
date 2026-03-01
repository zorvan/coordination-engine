/**
 * Settings page component.
 */

import { useState } from 'react'
import { Button, Card, CardHeader, CardBody, Form, FormGroup, Loading } from '@presentation/components'

export function SettingsPage() {
  const [loading] = useState(false)
  const [settings, setSettings] = useState({
    emailNotifications: true,
    pushNotifications: true,
    marketingEmails: false,
    privacyLevel: 'friends',
    theme: 'auto',
    language: 'en',
  })
  const [saved, setSaved] = useState(false)

  function handleToggle(key: keyof typeof settings) {
    setSettings((prev) => {
      const value = prev[key]
      if (typeof value === 'boolean') {
        setSaved(false)
        return { ...prev, [key]: !value }
      }
      return prev
    })
  }

  function handleChange(key: keyof typeof settings, value: string) {
    setSettings((prev) => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  function handleSave() {
    // TODO: Call API to save settings
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  if (loading) {
    return <Loading message="Loading settings..." />
  }

  return (
    <div className="panel">
      <div className="section-head">
        <h2>Settings</h2>
      </div>

      {saved && (
        <div className="alert alert-success">
          Settings saved successfully!
        </div>
      )}

      <Card>
        <CardHeader title="Notifications" subtitle="Manage how you receive updates" />
        <CardBody>
          <Form>
            <div className="setting-item">
              <div>
                <h4>Email Notifications</h4>
                <p className="subtle">Receive gathering updates via email</p>
              </div>
              <input
                type="checkbox"
                checked={settings.emailNotifications}
                onChange={() => handleToggle('emailNotifications')}
              />
            </div>

            <div className="setting-item">
              <div>
                <h4>Push Notifications</h4>
                <p className="subtle">Get instant notifications on your device</p>
              </div>
              <input
                type="checkbox"
                checked={settings.pushNotifications}
                onChange={() => handleToggle('pushNotifications')}
              />
            </div>

            <div className="setting-item">
              <div>
                <h4>Marketing Emails</h4>
                <p className="subtle">Receive updates about new features and offers</p>
              </div>
              <input
                type="checkbox"
                checked={settings.marketingEmails}
                onChange={() => handleToggle('marketingEmails')}
              />
            </div>
          </Form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Privacy & Access" subtitle="Control your data and visibility" />
        <CardBody>
          <Form>
            <FormGroup label="Profile Visibility">
              <select
                className="input"
                value={settings.privacyLevel}
                onChange={(e) => handleChange('privacyLevel', e.target.value)}
              >
                <option value="public">Public</option>
                <option value="friends">Friends Only</option>
                <option value="private">Private</option>
              </select>
            </FormGroup>

            <p className="subtle" style={{ marginTop: '1rem' }}>
              Choose who can see your profile and gatherings.
            </p>
          </Form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Preferences" subtitle="Customize your experience" />
        <CardBody>
          <Form>
            <FormGroup label="Theme">
              <select
                className="input"
                value={settings.theme}
                onChange={(e) => handleChange('theme', e.target.value)}
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto (System Preference)</option>
              </select>
            </FormGroup>

            <FormGroup label="Language">
              <select
                className="input"
                value={settings.language}
                onChange={(e) => handleChange('language', e.target.value)}
              >
                <option value="en">English</option>
                <option value="es">Español</option>
                <option value="fr">Français</option>
                <option value="de">Deutsch</option>
              </select>
            </FormGroup>
          </Form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Danger Zone" subtitle="Irreversible actions" />
        <CardBody>
          <Button variant="ghost" style={{ color: 'var(--color-danger)' }}>
            Delete Account
          </Button>
          <p className="subtle" style={{ marginTop: '0.5rem' }}>
            Permanently delete your account and all associated data.
          </p>
        </CardBody>
      </Card>

      <div className="inline-actions" style={{ marginTop: '2rem' }}>
        <Button variant="ghost">Reset to Defaults</Button>
        <Button variant="primary" onClick={handleSave}>
          Save Settings
        </Button>
      </div>
    </div>
  )
}
