/**
 * Domain service for trust computation.
 * 
 * This service provides methods to compute trust scores and levels.
 * It delegates to the TrustValue value object for the actual calculations.
 * 
 * Design decisions:
 * - Service layer abstracts trust computation logic
 * - Consistent interface for use cases to call
 * - Formula version tracking for audit trail
 */

import { computeTrustScore as computeTrustScoreValueObject, getTrustLevel as getTrustLevelValueObject, TrustLevel } from '../valuables/trust-value'

/**
 * Trust formula version for audit and versioning purposes.
 */
export const TRUST_FORMULA_VERSION = '1.0'

/**
 * Compute trust score from match statistics.
 * 
 * Business formula: completed_matches / accepted_matches
 * 
 * @param completedMatches - Number of matches completed
 * @param acceptedMatches - Number of matches accepted/confirmed
 * @returns Trust score between 0 and 1
 */
export function computeTrustScore(completedMatches: number, acceptedMatches: number): number {
  return computeTrustScoreValueObject(completedMatches, acceptedMatches)
}

/**
 * Compute trust level from score.
 * 
 * @param score - Trust score between 0 and 1
 * @returns Trust level constant
 */
export function computeTrustLevel(score: number): string {
  return getTrustLevelValueObject(score)
}

/**
 * Get trust level from score (alias for computeTrustLevel).
 * 
 * @param score - Trust score between 0 and 1
 * @returns Trust level constant
 */
export function getTrustLevel(score: number): string {
  return getTrustLevelValueObject(score)
}

/**
 * Get trust formula version for audit purposes.
 * 
 * @returns Trust formula version string
 */
export function getTrustFormulaVersion(): string {
  return TRUST_FORMULA_VERSION
}

/**
 * Get all trust levels for reference.
 * 
 * @returns Object containing all trust level constants
 */
export function getAllTrustLevels(): typeof TrustLevel {
  return TrustLevel
}