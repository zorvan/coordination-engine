/**
 * Trust value computation module
 * 
 * Provides trust level calculation from trust scores
 * 
 * Trust levels:
 * - VERY_HIGH: 0.9 - 1.0
 * - HIGH: 0.7 - 0.9
 * - MEDIUM: 0.5 - 0.7
 * - LOW: 0.3 - 0.5
 * - VERY_LOW: 0.0 - 0.3
 */

const TrustValue = {
  VERY_LOW: 'very_low',
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  VERY_HIGH: 'very_high',
};

function createTrustValueObject(score, version, computedAt) {
  const level = computeTrustLevel(score);
  return { score, level, version, computedAt };
}

/**
 * Compute trust level from score
 * 
 * @param {number} score - Trust score between 0 and 1
 * @returns {string} Trust level constant
 */
function computeTrustLevel(score) {
  if (score >= 0.9) return TrustValue.VERY_HIGH;
  if (score >= 0.7) return TrustValue.HIGH;
  if (score >= 0.5) return TrustValue.MEDIUM;
  if (score >= 0.3) return TrustValue.LOW;
  return TrustValue.VERY_LOW;
}

/**
 * Alias for computeTrustLevel
 * 
 * @param {number} score - Trust score between 0 and 1
 * @returns {string} Trust level constant
 */
function getTrustLevel(score) {
  return computeTrustLevel(score);
}

/**
 * Compute trust score from match statistics
 * 
 * Formula: completed_matches / accepted_matches
 * 
 * @param {number} completedMatches - Number of matches completed
 * @param {number} acceptedMatches - Number of matches accepted/confirmed
 * @returns {number} Trust score between 0 and 1
 */
function computeTrustScore(completedMatches, acceptedMatches) {
  if (acceptedMatches === 0) return 0;
  return completedMatches / acceptedMatches;
}

module.exports = {
  TrustValue,
  createTrustValueObject,
  computeTrustLevel,
  getTrustLevel,
  computeTrustScore,
};