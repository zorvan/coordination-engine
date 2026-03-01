/**
 * Trust value computation value object.
 * 
 * Provides trust level calculation from trust scores.
 * 
 * Trust levels:
 * - VERY_HIGH: 0.9 - 1.0
 * - HIGH: 0.7 - 0.9
 * - MEDIUM: 0.5 - 0.7
 * - LOW: 0.3 - 0.5
 * - VERY_LOW: 0.0 - 0.3
 */

/**
 * Trust level constants.
 * 
 * Design decisions:
 * - Using enum-like object for type safety
 * - Clear separation between levels
 */
export const TrustLevel = {
  VERY_LOW: 'very_low',
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  VERY_HIGH: 'very_high',
} as const

/**
 * Create a trust value object with score and level.
 * 
 * @param score - Trust score between 0 and 1
 * @param version - Version number for tracking
 * @param computedAt - Timestamp when trust was computed
 * @returns Trust value object with score, level, version, and timestamp
 */
export function createTrustValueObject(score: number, version: number, computedAt: Date): TrustValueObject {
  const level = computeTrustLevel(score)
  return { score, level, version, computedAt }
}

/**
 * Compute trust level from score.
 * 
 * Business logic:
 * - 0.9-1.0: Very High trust
 * - 0.7-0.9: High trust
 * - 0.5-0.7: Medium trust
 * - 0.3-0.5: Low trust
 * - 0.0-0.3: Very Low trust
 * 
 * @param score - Trust score between 0 and 1
 * @returns Trust level constant
 */
export function computeTrustLevel(score: number): string {
  if (score >= 0.9) return TrustLevel.VERY_HIGH
  if (score >= 0.7) return TrustLevel.HIGH
  if (score >= 0.5) return TrustLevel.MEDIUM
  if (score >= 0.3) return TrustLevel.LOW
  return TrustLevel.VERY_LOW
}

/**
 * Get trust level from score (alias for computeTrustLevel).
 * 
 * @param score - Trust score between 0 and 1
 * @returns Trust level constant
 */
export function getTrustLevel(score: number): string {
  return computeTrustLevel(score)
}

/**
 * Compute trust score from match statistics.
 * 
 * Business formula: completed_matches / accepted_matches
 * 
 * Design decisions:
 * - Returns 0 when no accepted matches (prevents division by zero)
 * - Simple ratio calculation for trustworthiness metric
 * 
 * @param completedMatches - Number of matches completed
 * @param acceptedMatches - Number of matches accepted/confirmed
 * @returns Trust score between 0 and 1
 */
export function computeTrustScore(completedMatches: number, acceptedMatches: number): number {
  if (acceptedMatches === 0) return 0
  return completedMatches / acceptedMatches
}

/**
 * Trust value object type.
 */
export interface TrustValueObject {
  /**
   * Trust score between 0 and 1.
   */
  score: number
  
  /**
   * Computed trust level.
   */
  level: string
  
  /**
   * Version number for tracking changes.
   */
  version: number
  
  /**
   * Timestamp when trust was computed.
   */
  computedAt: Date
}