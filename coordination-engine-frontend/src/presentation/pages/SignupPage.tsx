import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@presentation/components'

type SignupPageProps = {
  onEmailSignup: (fullName: string, email: string, password: string) => Promise<void>
  authError?: string
  loading?: boolean
}

export function SignupPage({ onEmailSignup, authError, loading = false }: SignupPageProps) {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!fullName.trim() || !email.trim() || !password.trim()) {
      setError('Full name, email and password are required.')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    setError('')
    void onEmailSignup(fullName.trim(), email.trim(), password)
  }

  return (
    <div className="auth-page">
      <section className="auth-card">
        <div className="auth-head">
          <h1>Create account</h1>
          <p>Sign up with your email to start using Coordination Engine.</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="fullName">Full name</label>
          <input
            id="fullName"
            name="fullName"
            type="text"
            autoComplete="name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            placeholder="Your name"
          />

          <label htmlFor="signupEmail">Email</label>
          <input
            id="signupEmail"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />

          <label htmlFor="signupPassword">Password</label>
          <input
            id="signupPassword"
            name="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 8 characters"
          />

          {error ? <p className="auth-error">{error}</p> : null}
          {authError ? <p className="auth-error">{authError}</p> : null}

          <Button className="auth-submit" type="submit" loading={loading} disabled={loading}>
            Create account
          </Button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </section>
    </div>
  )
}
