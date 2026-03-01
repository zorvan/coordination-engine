import { Navigate, Route, Routes } from 'react-router-dom'
import { Loading } from '@presentation/components'
import { LoginPage, OnboardingPage, SignupPage } from '@presentation/pages'
import { AppShell } from '@presentation/layouts/AppShell'
import type { LoadingProvider, OnboardingStatus } from '@presentation/hooks/useAppAuth'

type AppRoutesProps = {
  isAuthenticated: boolean
  onboardingStatus: OnboardingStatus
  onboardingLoading: boolean
  onboardingError: string
  onboardingEmail: string
  onboardingName: string
  authError: string
  loadingProvider: LoadingProvider
  loginLoadingProvider: Exclude<LoadingProvider, 'signup'> | null
  onGoogleLogin: () => Promise<void>
  onFacebookLogin: () => Promise<void>
  onEmailLogin: (email: string, password: string) => Promise<void>
  onEmailSignup: (fullName: string, email: string, password: string) => Promise<void>
  onOnboardingSubmit: (payload: {
    name: string
    phone: string
    location: string
    website: string
    bio: string
  }) => Promise<void>
  onLogout: () => void
}

export function AppRoutes({
  isAuthenticated,
  onboardingStatus,
  onboardingLoading,
  onboardingError,
  onboardingEmail,
  onboardingName,
  authError,
  loadingProvider,
  loginLoadingProvider,
  onGoogleLogin,
  onFacebookLogin,
  onEmailLogin,
  onEmailSignup,
  onOnboardingSubmit,
  onLogout,
}: AppRoutesProps) {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          isAuthenticated ? (
            onboardingStatus === 'required' ? <Navigate to="/onboarding" replace /> : <Navigate to="/" replace />
          ) : (
            <LoginPage
              onGoogleLogin={onGoogleLogin}
              onFacebookLogin={onFacebookLogin}
              onEmailLogin={onEmailLogin}
              authError={authError}
              loadingProvider={loginLoadingProvider}
            />
          )
        }
      />
      <Route
        path="/signup"
        element={
          isAuthenticated ? (
            onboardingStatus === 'required' ? <Navigate to="/onboarding" replace /> : <Navigate to="/" replace />
          ) : (
            <SignupPage
              onEmailSignup={onEmailSignup}
              authError={authError}
              loading={loadingProvider === 'signup'}
            />
          )
        }
      />
      <Route
        path="/onboarding"
        element={
          isAuthenticated ? (
            onboardingStatus === 'unknown' ? (
              <Loading message="Preparing onboarding..." />
            ) : onboardingStatus === 'complete' ? (
              <Navigate to="/" replace />
            ) : (
              <OnboardingPage
                initialEmail={onboardingEmail}
                initialName={onboardingName}
                loading={onboardingLoading}
                error={onboardingError}
                onSubmit={onOnboardingSubmit}
              />
            )
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route
        path="/*"
        element={
          isAuthenticated ? (
            onboardingStatus === 'unknown' ? (
              <Loading message="Loading your account..." />
            ) : onboardingStatus === 'required' ? (
              <Navigate to="/onboarding" replace />
            ) : (
              <AppShell onLogout={onLogout} />
            )
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  )
}
