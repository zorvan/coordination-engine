/**
 * API client tests.
 * 
 * These tests verify the API client functionality.
 * Mocking is used since we don't have a real backend running.
 */

import { describe, it, expect, vi } from 'vitest'
import { post, get } from '@infrastructure/api/client'

/**
 * Mock fetch implementation.
 */
const mockFetch = vi.fn()

// @ts-expect-error - Mock window.fetch
global.fetch = mockFetch

/**
 * Tests for the API client.
 */
describe('APIClient', () => {
  /**
   * Tests POST request success.
   */
  it('should handle successful POST request', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      statusText: 'OK',
      json: async () => ({ matchId: '123', status: 'success' }),
    })

    const response = await post('/matches', {
      organizerId: 'org1',
      title: 'Test Match',
      description: 'Test',
      scheduledTime: new Date(),
      durationMinutes: 60,
      location: 'Online',
      participantIds: ['part1'],
    })

    expect(response.status).toBe('success')
    expect(response.data).toBeDefined()
    expect(response.message).toBe('Operation successful')
  })

  /**
   * Tests POST request error.
   */
  it('should handle POST request error', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      statusText: 'Bad Request',
    })

    const response = await post('/matches', {})

    expect(response.status).toBe('error')
    expect(response.error).toBe('Bad Request')
    expect(response.message).toBe('Error: Bad Request')
  })

  /**
   * Tests GET request success.
   */
  it('should handle successful GET request', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      statusText: 'OK',
      json: async () => ({ matchId: '123', state: 'proposed' }),
    })

    const response = await get('/matches/123')

    expect(response.status).toBe('success')
    expect(response.data).toBeDefined()
  })

  /**
   * Tests network error handling.
   */
  it('should handle network errors', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const response = await post('/matches', {})

    expect(response.status).toBe('error')
    expect(response.message).toContain('Network error')
  })

  /**
   * Tests non-JSON response.
   */
  it('should handle non-JSON response', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      statusText: 'OK',
      json: async () => {
        throw new Error('Not JSON')
      },
    })

    const response = await post('/matches', {})

    expect(response.status).toBe('success')
    expect(response.data).toBeUndefined()
  })
})