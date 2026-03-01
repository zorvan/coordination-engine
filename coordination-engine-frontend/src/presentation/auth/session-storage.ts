const AUTH_TOKEN_KEY = 'ce-auth-token'
const AUTH_USER_KEY = 'ce-auth-user'
const AUTH_EMAIL_KEY = 'ce-auth-email'
const AUTH_NAME_KEY = 'ce-auth-name'
const ONBOARDING_COMPLETE_KEY = 'ce-onboarding-complete'
const PROFILE_CACHE_KEY = 'ce-profile-cache'

export function hasSessionToken(): boolean {
  return sessionStorage.getItem(AUTH_TOKEN_KEY) !== null
}

export function getSessionUserId(): string {
  return sessionStorage.getItem(AUTH_USER_KEY) || ''
}

export function getSessionEmail(): string {
  return sessionStorage.getItem(AUTH_EMAIL_KEY) || ''
}

export function getSessionName(): string {
  return sessionStorage.getItem(AUTH_NAME_KEY) || ''
}

export function isOnboardingCompleteFlagSet(): boolean {
  return sessionStorage.getItem(ONBOARDING_COMPLETE_KEY) === 'true'
}

export function setOnboardingCompleteFlag(): void {
  sessionStorage.setItem(ONBOARDING_COMPLETE_KEY, 'true')
}

export function persistSession(payload: {
  token: string
  userId: string
  email?: string
  name?: string
}): void {
  sessionStorage.setItem(AUTH_TOKEN_KEY, payload.token)
  sessionStorage.setItem(AUTH_USER_KEY, payload.userId)

  if (payload.email) {
    sessionStorage.setItem(AUTH_EMAIL_KEY, payload.email)
  }

  if (payload.name) {
    sessionStorage.setItem(AUTH_NAME_KEY, payload.name)
  }
}

export function cacheProfile(payload: {
  name: string
  email: string
  phone: string
  location: string
  website: string
  bio: string
}): void {
  sessionStorage.setItem(PROFILE_CACHE_KEY, JSON.stringify(payload))
}

export function clearSession(): void {
  sessionStorage.removeItem(AUTH_TOKEN_KEY)
  sessionStorage.removeItem(AUTH_USER_KEY)
  sessionStorage.removeItem(AUTH_EMAIL_KEY)
  sessionStorage.removeItem(AUTH_NAME_KEY)
  sessionStorage.removeItem(ONBOARDING_COMPLETE_KEY)
  sessionStorage.removeItem(PROFILE_CACHE_KEY)
}

export function clearLegacyLocalStorageAuth(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(AUTH_USER_KEY)
}
