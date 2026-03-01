import { computeTrustLevel as computeTrustLevelFromValue, computeTrustScore as computeTrustScoreFromValue, getTrustLevel as getTrustLevelFromValue } from '../valuables/trust-value';

const TRUST_FORMULA_VERSION = '1.0';

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
  return computeTrustScoreFromValue(completedMatches, acceptedMatches);
}

/**
 * Compute trust level from score
 * 
 * @param {number} score - Trust score between 0 and 1
 * @returns {string} Trust level constant
 */
function computeTrustLevel(score) {
  return computeTrustLevelFromValue(score);
}

/**
 * Alias for computeTrustLevel
 * 
 * @param {number} score - Trust score between 0 and 1
 * @returns {string} Trust level constant
 */
function getTrustLevel(score) {
  return getTrustLevelFromValue(score);
}

function getTrustFormulaVersion() {
  return TRUST_FORMULA_VERSION;
}

export { TRUST_FORMULA_VERSION,
  computeTrustScore,
  computeTrustLevel,
  getTrustLevel,
  getTrustFormulaVersion, };
