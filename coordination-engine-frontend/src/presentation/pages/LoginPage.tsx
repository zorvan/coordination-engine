import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@presentation/components'

type LoginPageProps = {
  onGoogleLogin: () => Promise<void>
  onFacebookLogin: () => Promise<void>
  onEmailLogin: (email: string, password: string) => Promise<void>
  authError?: string
  loadingProvider?: 'google' | 'facebook' | 'email' | null
}

export function LoginPage({
  onGoogleLogin,
  onFacebookLogin,
  onEmailLogin,
  authError,
  loadingProvider = null,
}: LoginPageProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  function handleEmailLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!email.trim() || !password.trim()) {
      setError('Email and password are required.')
      return
    }

    setError('')
    void onEmailLogin(email.trim(), password)
  }

  return (
    <div className="auth-page">
      <section className="auth-card">
        <div className="auth-head">
          <h1>Sign in</h1>
          <p>Use Google, Facebook, or your email account.</p>
        </div>

        <div className="auth-social">
          <Button
            className="auth-social-btn google"
            onClick={() => void onGoogleLogin()}
            type="button"
            loading={loadingProvider === 'google'}
            disabled={loadingProvider !== null}
          >
            Continue with Google
          </Button>
          <Button
            className="auth-social-btn facebook"
            onClick={() => void onFacebookLogin()}
            type="button"
            loading={loadingProvider === 'facebook'}
            disabled={loadingProvider !== null}
          >
            Continue with Facebook
          </Button>
        </div>

        <div className="auth-divider" role="presentation">
          <span>Email login</span>
        </div>

        <form className="auth-form" onSubmit={handleEmailLogin}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
          />

          {error ? <p className="auth-error">{error}</p> : null}
          {authError ? <p className="auth-error">{authError}</p> : null}

          <Button className="auth-submit" type="submit" loading={loadingProvider === 'email'} disabled={loadingProvider !== null}>
            Sign in with email
          </Button>
        </form>

        <p className="auth-switch">
          New here? <Link to="/signup">Create an account</Link>
        </p>
      </section>
    </div>
  )
}
