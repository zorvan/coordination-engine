/**
 * React contexts for the application.
 * 
 * This module provides global context providers for state management.
 * 
 * Design decisions:
 * - Using React Context API for global state
 * - Simple type definitions with appropriate generic types
 * - Provider components for wrapping app components
 */

import { createContext, useContext, type ReactNode } from 'react'
import type { InMemoryEventStore } from '@infrastructure/persistence/in-memory-event-store'

/**
 * Context for the event store.
 */
export const EventStoreContext = createContext<InMemoryEventStore | undefined>(undefined)

/**
 * Context provider for the event store.
 * 
 * @param props - Component props
 * @param props.children - Child components
 * @param props.eventStore - The event store instance
 */
export function EventStoreProvider({
  children,
  eventStore,
}: {
  children: ReactNode
  eventStore: InMemoryEventStore
}) {
  return <EventStoreContext.Provider value={eventStore}>{children}</EventStoreContext.Provider>
}

/**
 * Hook to access the event store.
 * 
 * @returns The event store instance
 */
export function useEventStore() {
  const context = useContext(EventStoreContext)
  if (!context) {
    throw new Error('useEventStore must be used within an EventStoreProvider')
  }
  return context
}

/**
 * Context for API configuration.
 */
export const ApiConfigContext = createContext<{
  baseUrl: string
} | undefined>(undefined)

/**
 * Context provider for API configuration.
 * 
 * @param props - Component props
 * @param props.children - Child components
 * @param props.config - API configuration
 */
export function ApiConfigProvider({
  children,
  config,
}: {
  children: ReactNode
  config: { baseUrl: string }
}) {
  return <ApiConfigContext.Provider value={config}>{children}</ApiConfigContext.Provider>
}

/**
 * Hook to access API configuration.
 * 
 * @returns API configuration object
 */
export function useApiConfig() {
  const context = useContext(ApiConfigContext)
  if (!context) {
    throw new Error('useApiConfig must be used within an ApiConfigProvider')
  }
  return context
}
