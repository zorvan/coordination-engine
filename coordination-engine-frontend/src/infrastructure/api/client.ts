/**
 * HTTP client for API communication.
 * 
 * This module provides a simplified HTTP client for making requests to the
 * coordination engine backend. It handles JSON serialization/deserialization
 * and basic error handling.
 * 
 * Design decisions:
 * - Using fetch API for browser compatibility
 * - Automatic JSON parsing for responses
 * - Consistent error handling
 * - Configurable base URL via environment variables
 */

import { ApiResponse } from './types'

/**
 * API configuration.
 */
const API_CONFIG = {
  /**
   * Base URL for the API.
   * Can be overridden via environment variable.
   */
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000',
  
  /**
   * Default fetch options.
   */
  defaultOptions: {
    headers: {
      'Content-Type': 'application/json',
    },
  },
}

export const API_BASE_URL = API_CONFIG.baseUrl

/**
 * Make a POST request to the API.
 * 
 * @param endpoint - API endpoint path
 * @param body - Request body
 * @returns API response
 */
export async function post<T>(endpoint: string, body?: unknown): Promise<ApiResponse<T>> {
  const url = `${API_CONFIG.baseUrl}${endpoint}`
  
  const options: RequestInit = {
    method: 'POST',
    headers: API_CONFIG.defaultOptions.headers,
    body: body ? JSON.stringify(body) : undefined,
  }
  
  return makeRequest<T>(url, options)
}

/**
 * Make a GET request to the API.
 * 
 * @param endpoint - API endpoint path
 * @returns API response
 */
export async function get<T>(endpoint: string): Promise<ApiResponse<T>> {
  const url = `${API_CONFIG.baseUrl}${endpoint}`
  
  const options: RequestInit = {
    method: 'GET',
    headers: API_CONFIG.defaultOptions.headers,
  }
  
  return makeRequest<T>(url, options)
}

/**
 * Make an API request and parse the response.
 * 
 * @param url - Full URL
 * @param options - Fetch options
 * @returns API response
 */
async function makeRequest<T>(url: string, options: RequestInit): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(url, options)
    
    let data: T | undefined
    let error: string | undefined
    let message = 'Operation successful'
    
    if (response.ok) {
      try {
        const json = await response.json()
        data = json as T
      } catch {
        // Response not JSON, leave data undefined
      }
    } else {
      try {
        const json = await response.json() as { message?: string; error?: string }
        message = json.message || `Error: ${response.statusText}`
        error = json.error || response.statusText
      } catch {
        message = `Error: ${response.statusText}`
        error = response.statusText
      }
      console.error(
        `Failed to load resource: the server responded with a status of ${response.status} (${response.statusText})`,
        { url, method: options.method || 'GET' }
      )
    }
    
    return {
      status: response.ok ? 'success' : 'error',
      message,
      error,
      data,
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error'
    return {
      status: 'error',
      message: `Network error: ${message}`,
      error: message,
    }
  }
}
