/**
 * Test file for the application root component.
 *
 * This test verifies that the App component renders correctly.
 */

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../src/App'
import { EventStoreProvider } from '../src/presentation/contexts'
import { InMemoryEventStore } from '../src/infrastructure/persistence/in-memory-event-store'

declare const global: any

describe('App Component', () => {
  beforeAll(() => {
    global.localStorage = {
      removeItem: () => {},
      getItem: () => null,
      setItem: () => {},
    }
  })

  beforeEach(() => {
    sessionStorage.clear()
    // Default fetch stub for tests that trigger onboarding checks.
    // @ts-ignore
    global.fetch = async () => ({
      ok: true,
      json: async () => ({ actor: { onboardingCompletedAt: new Date().toISOString() } }),
    })
  })

  test('renders coordination engine title', async () => {
    sessionStorage.setItem('ce-auth-token', 'dummy')
    sessionStorage.setItem('ce-auth-user', 'email:foo@example.com')

    render(
      <EventStoreProvider eventStore={new InMemoryEventStore()}>
        <MemoryRouter initialEntries={["/"]}>
          <App />
        </MemoryRouter>
      </EventStoreProvider>
    )

    const heading = await screen.findByRole('heading', { name: 'Coordination Engine', level: 1 })
    expect(heading).toBeInTheDocument()
  })

  test('skips onboarding if actor record is already complete', async () => {
    sessionStorage.setItem('ce-auth-token', 'dummy')
    sessionStorage.setItem('ce-auth-user', 'email:foo@example.com')

    const actorResponse = {
      actor: {
        id: 'email:foo@example.com',
        email: 'foo@example.com',
        name: 'Foo Bar',
        onboardingCompletedAt: new Date().toISOString(),
        phone: '123',
        location: 'City',
        bio: 'hi',
      },
    }

    // @ts-ignore
    global.fetch = async () => ({
      ok: true,
      json: async () => actorResponse,
    })

    render(
      <EventStoreProvider eventStore={new InMemoryEventStore()}>
        <MemoryRouter initialEntries={["/"]}>
          <App />
        </MemoryRouter>
      </EventStoreProvider>
    )

    const profileLinks = await screen.findAllByRole('link', { name: 'Profile' })
    expect(profileLinks.length).toBeGreaterThan(0)
  })
})
