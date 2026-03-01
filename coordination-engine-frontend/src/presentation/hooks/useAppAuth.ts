import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { startFacebookLogin, startGoogleLogin, loginWithEmail, signupWithEmail } from '@infrastructure/api/auth-service'
import {
  fetchActorProfile,
  isOnboardingCompleteFromActor,
  updateActorProfile,
} from '@infrastructure/api/actor-service'
import {
  cacheProfile,
  clearLegacyLocalStorageAuth,
  clearSession,
  getSessionEmail,
  getSessionName,
  getSessionUserId,
  hasSessionToken,
  isOnboardingCompleteFlagSet,
  persistSession,
  setOnboardingCompleteFlag,
} from '@presentation/auth/session-storage'

export type LoadingProvider = 'google' | 'facebook' | 'email' | 'signup' | null
export type OnboardingStatus = 'unknown' | 'required' | 'complete'

function decodeOAuthUser(encodedUser: string): { id: string; email?: string } {
  const normalized = encodedUser.replace(/-/g, '+').replace(/_/g, '/')
  const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4)
  const userJson = atob(padded)
  const parsed = JSON.parse(userJson) as { id?: string; email?: string }

  return {
    id: parsed.id || 'oauth-user',
    email: parsed.email,
  }
}

export function useAppAuth() {
  const location = useLocation()

  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => hasSessionToken())
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus>('unknown')
  const [onboardingLoading, setOnboardingLoading] = useState(false)
  const [onboardingError, setOnboardingError] = useState('')
  const [onboardingEmail, setOnboardingEmail] = useState('')
  const [onboardingName, setOnboardingName] = useState('')
  const [authError, setAuthError] = useState('')
  const [loadingProvider, setLoadingProvider] = useState<LoadingProvider>(null)

  const loginLoadingProvider = loadingProvider === 'signup' ? null : loadingProvider

  function persistLogin(token: string, userId: string, email?: string, name?: string) {
    persistSession({ token, userId, email, name })

    if (email) {
      setOnboardingEmail(email)
    }

    if (name) {
      setOnboardingName(name)
    }

    setIsAuthenticated(true)
  }

  async function markOnboardingIfComplete(userId: string) {
    try {
      const actor = await fetchActorProfile(userId)
      if (actor && isOnboardingCompleteFromActor(actor)) {
        setOnboardingCompleteFlag()
      }
    } catch {
      // Ignore profile lookup failures during authentication.
    }
  }

  async function handleGoogleLogin() {
    setAuthError('')
    setLoadingProvider('google')
    try {
      const session = await startGoogleLogin()
      persistLogin(session.token, session.user.id, session.user.email, session.user.name)
      await markOnboardingIfComplete(session.user.id)
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Google login failed')
    } finally {
      setLoadingProvider(null)
    }
  }

  async function handleFacebookLogin() {
    setAuthError('')
    setLoadingProvider('facebook')
    try {
      const session = await startFacebookLogin()
      persistLogin(session.token, session.user.id, session.user.email, session.user.name)
      await markOnboardingIfComplete(session.user.id)
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Facebook login failed')
    } finally {
      setLoadingProvider(null)
    }
  }

  async function handleEmailLogin(email: string, password: string) {
    setAuthError('')
    setLoadingProvider('email')
    try {
      const session = await loginWithEmail(email, password)
      persistLogin(session.token, session.user.id, session.user.email, session.user.name)
      await markOnboardingIfComplete(session.user.id)
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Email login failed')
    } finally {
      setLoadingProvider(null)
    }
  }

  async function handleEmailSignup(fullName: string, email: string, password: string) {
    setAuthError('')
    setLoadingProvider('signup')
    try {
      const session = await signupWithEmail(fullName, email, password)
      persistLogin(session.token, session.user.id, session.user.email, session.user.name || fullName)
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Signup failed')
    } finally {
      setLoadingProvider(null)
    }
  }

  function handleLogout() {
    clearSession()
    setIsAuthenticated(false)
    setOnboardingStatus('unknown')
    setOnboardingError('')
    setOnboardingEmail('')
    setOnboardingName('')
  }

  async function handleOnboardingSubmit(payload: {
    name: string
    phone: string
    location: string
    website: string
    bio: string
  }) {
    setOnboardingError('')
    setOnboardingLoading(true)

    const userId = getSessionUserId()
    if (!userId) {
      setOnboardingError('Session expired. Please login again.')
      setOnboardingLoading(false)
      return
    }

    try {
      const saved = await updateActorProfile(userId, {
        ...payload,
        onboardingCompletedAt: new Date().toISOString(),
      })

      if (!saved) {
        setOnboardingError('Failed to save onboarding data')
        return
      }

      cacheProfile({
        name: payload.name,
        email: onboardingEmail,
        phone: payload.phone,
        location: payload.location,
        website: payload.website,
        bio: payload.bio,
      })
      setOnboardingCompleteFlag()
      setOnboardingStatus('complete')
    } catch {
      setOnboardingError('Failed to save onboarding data')
    } finally {
      setOnboardingLoading(false)
    }
  }

  useEffect(() => {
    clearLegacyLocalStorageAuth()
  }, [])

  useEffect(() => {
    async function checkOnboarding() {
      if (!isAuthenticated) {
        setOnboardingStatus('unknown')
        return
      }

      const userId = getSessionUserId()
      if (!userId) {
        setOnboardingStatus('unknown')
        return
      }

      const emailFromSession = getSessionEmail()
      const nameFromSession = getSessionName()

      if (emailFromSession) {
        setOnboardingEmail(emailFromSession)
      }

      if (nameFromSession) {
        setOnboardingName(nameFromSession)
      }

      try {
        const actor = await fetchActorProfile(userId)

        if (!actor) {
          setOnboardingStatus(isOnboardingCompleteFlagSet() ? 'complete' : 'required')
          return
        }

        const email = typeof actor.email === 'string' ? actor.email : emailFromSession
        const name = typeof actor.name === 'string' ? actor.name : nameFromSession
        const completed = isOnboardingCompleteFromActor(actor)

        setOnboardingEmail(email)
        setOnboardingName(name)

        if (completed) {
          setOnboardingCompleteFlag()
        }

        setOnboardingStatus(completed ? 'complete' : 'required')
      } catch {
        setOnboardingStatus(isOnboardingCompleteFlagSet() ? 'complete' : 'required')
      }
    }

    void checkOnboarding()
  }, [isAuthenticated])

  useEffect(() => {
    async function handleOAuthCallback(): Promise<void> {
      if (location.pathname !== '/login') {
        return
      }

      const params = new URLSearchParams(location.search)
      const token = params.get('token')
      const encodedUser = params.get('user')
      const error = params.get('error')

      if (error) {
        setAuthError(error)
        setLoadingProvider(null)
        return
      }

      if (!token || !encodedUser) {
        return
      }

      try {
        const user = decodeOAuthUser(encodedUser)
        persistLogin(token, user.id, user.email)
        await markOnboardingIfComplete(user.id)
        setLoadingProvider(null)
        setAuthError('')
        window.history.replaceState({}, '', '/')
      } catch {
        setAuthError('Invalid authentication response')
        setLoadingProvider(null)
      }
    }

    void handleOAuthCallback()
  }, [location.pathname, location.search])

  return {
    isAuthenticated,
    onboardingStatus,
    onboardingLoading,
    onboardingError,
    onboardingEmail,
    onboardingName,
    authError,
    loadingProvider,
    loginLoadingProvider,
    handleGoogleLogin,
    handleFacebookLogin,
    handleEmailLogin,
    handleEmailSignup,
    handleOnboardingSubmit,
    handleLogout,
  }
}
