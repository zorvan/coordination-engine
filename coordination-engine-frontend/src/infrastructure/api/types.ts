/**
 * API response types for match endpoints.
 */

/**
 * Match status response.
 */
export interface MatchStatusResponse {
  /**
   * Unique match identifier.
   */
  matchId: string
  
  /**
   * Current match state.
   */
  state: string
  
  /**
   * Success message.
   */
  message: string
}

/**
 * Match creation request.
 */
export interface CreateMatchRequest {
  /**
   * Actor ID creating the match.
   */
  organizerId: string
  
  /**
   * Match title.
   */
  title: string
  
  /**
   * Optional match description.
   */
  description?: string
  
  /**
   * When the match is scheduled.
   */
  scheduledTime: string
  
  /**
   * Duration in minutes.
   */
  durationMinutes: number
  
  /**
   * Physical or virtual location.
   */
  location: string
  
  /**
   * Array of participant actor IDs.
   */
  participantIds: string[]
}

/**
 * Match confirmation request.
 */
export interface ConfirmMatchRequest {
  /**
   * Match ID to confirm.
   */
  matchId: string
  
  /**
   * Actor ID confirming the match.
   */
  actorId: string
}

/**
 * Match completion request.
 */
export interface CompleteMatchRequest {
  /**
   * Match ID to complete.
   */
  matchId: string
  
  /**
   * Actor ID completing the match.
   */
  actorId: string
  
  /**
   * Optional completion notes.
   */
  notes?: string
}

/**
 * Match cancellation request.
 */
export interface CancelMatchRequest {
  /**
   * Match ID to cancel.
   */
  matchId: string
  
  /**
   * Actor ID cancelling the match.
   */
  actorId: string
  
  /**
   * Cancellation reason.
   */
  reason: string
}

/**
 * API response with status.
 */
export interface ApiResponse<T = unknown> {
  /**
   * Operation status.
   */
  status?: string
  
  /**
   * Success message.
   */
  message?: string
  
  /**
   * Error code.
   */
  error?: string
  
  /**
   * Response data.
   */
  data?: T
  
  /**
   * Raw response object.
   */
  [key: string]: unknown
}