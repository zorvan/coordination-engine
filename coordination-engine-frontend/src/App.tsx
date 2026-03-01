import { AppRoutes } from '@presentation/routes/AppRoutes'
import { useAppAuth } from '@presentation/hooks/useAppAuth'

export default function App() {
  const {
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
  } = useAppAuth()

  return (
    <AppRoutes
      isAuthenticated={isAuthenticated}
      onboardingStatus={onboardingStatus}
      onboardingLoading={onboardingLoading}
      onboardingError={onboardingError}
      onboardingEmail={onboardingEmail}
      onboardingName={onboardingName}
      authError={authError}
      loadingProvider={loadingProvider}
      loginLoadingProvider={loginLoadingProvider}
      onGoogleLogin={handleGoogleLogin}
      onFacebookLogin={handleFacebookLogin}
      onEmailLogin={handleEmailLogin}
      onEmailSignup={handleEmailSignup}
      onOnboardingSubmit={handleOnboardingSubmit}
      onLogout={handleLogout}
    />
  )
}
