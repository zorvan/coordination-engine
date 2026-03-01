import { post } from './client'

export type AuthProvider = 'email' | 'google' | 'facebook'

export interface AuthUser {
  id: string
  email: string
  provider: AuthProvider
  name?: string
}

export interface AuthSession {
  token: string
  user: AuthUser
}

type AuthResponse = {
  status: string
  token: string
  user: AuthUser
}

export async function loginWithEmail(email: string, password: string): Promise<AuthSession> {
  const response = await post<AuthResponse>('/auth/email/login', { email, password })

  if (response.status === 'error') {
    throw new Error(response.message || 'Email login failed')
  }

  const token = response.data?.token
  const user = response.data?.user
  if (!token || !user) {
    throw new Error('Invalid auth response')
  }

  return { token, user }
}

export async function signupWithEmail(
  fullName: string,
  email: string,
  password: string
): Promise<AuthSession> {
  const response = await post<AuthResponse>('/auth/email/signup', { fullName, email, password })

  if (response.status === 'error') {
    throw new Error(response.message || 'Signup failed')
  }

  const token = response.data?.token
  const user = response.data?.user
  if (!token || !user) {
    throw new Error('Invalid auth response')
  }

  return { token, user }
}

type GoogleCredentialResponse = {
  credential?: string
}

type GoogleIdApi = {
  initialize: (config: {
    client_id: string
    callback: (response: GoogleCredentialResponse) => void
    auto_select?: boolean
    cancel_on_tap_outside?: boolean
  }) => void
  prompt: () => void
}

type FacebookApi = {
  init: (params: Record<string, unknown>) => void
  login: (
    callback: (response: { authResponse?: { accessToken?: string } }) => void,
    options?: Record<string, unknown>
  ) => void
  getLoginStatus: (
    callback: (response: { status?: string; authResponse?: { accessToken?: string } }) => void
  ) => void
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`)
    if (existing) {
      resolve()
      return
    }

    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`))
    document.head.appendChild(script)
  })
}

export async function startGoogleLogin(): Promise<AuthSession> {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
  if (!clientId) {
    throw new Error('Google OAuth is not configured (missing VITE_GOOGLE_CLIENT_ID)')
  }

  await loadScript('https://accounts.google.com/gsi/client')

  const googleApi = (window as unknown as { google?: { accounts?: { id?: GoogleIdApi } } }).google?.accounts?.id
  if (!googleApi) {
    throw new Error('Google SDK not available')
  }

  const idToken = await new Promise<string>((resolve, reject) => {
    googleApi.initialize({
      client_id: clientId,
      callback: (response: GoogleCredentialResponse) => {
        if (response.credential) {
          resolve(response.credential)
          return
        }
        reject(new Error('Google did not return an ID token'))
      },
      auto_select: true,
      cancel_on_tap_outside: true,
    })
    googleApi.prompt()
  })

  const response = await post<AuthResponse>('/auth/google/login', { idToken })
  if (response.status === 'error') {
    throw new Error(response.message || 'Google login failed')
  }
  const token = response.data?.token
  const user = response.data?.user
  if (!token || !user) {
    throw new Error('Invalid auth response')
  }
  return { token, user }
}

export async function startFacebookLogin(): Promise<AuthSession> {
  const appId = import.meta.env.VITE_FACEBOOK_APP_ID
  if (!appId) {
    throw new Error('Facebook OAuth is not configured (missing VITE_FACEBOOK_APP_ID)')
  }

  await loadScript('https://connect.facebook.net/en_US/sdk.js')

  const fbApi = (window as unknown as { FB?: FacebookApi }).FB
  if (!fbApi) {
    throw new Error('Facebook SDK not available')
  }

  fbApi.init({
    appId,
    cookie: false,
    xfbml: false,
    version: 'v20.0',
  })

  const accessToken = await new Promise<string>((resolve, reject) => {
    fbApi.getLoginStatus((statusResponse) => {
      const existingToken = statusResponse?.authResponse?.accessToken
      if (statusResponse?.status === 'connected' && existingToken) {
        resolve(existingToken)
        return
      }

      fbApi.login((response) => {
        const token = response?.authResponse?.accessToken
        if (token) {
          resolve(token)
          return
        }
        reject(new Error('Facebook login was cancelled'))
      }, { scope: 'email,public_profile' })
    })
  })

  const response = await post<AuthResponse>('/auth/facebook/login', { accessToken })
  if (response.status === 'error') {
    throw new Error(response.message || 'Facebook login failed')
  }
  const token = response.data?.token
  const user = response.data?.user
  if (!token || !user) {
    throw new Error('Invalid auth response')
  }
  return { token, user }
}
