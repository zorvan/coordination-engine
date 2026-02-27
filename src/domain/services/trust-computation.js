const trustValueModule = require('../valuables/trust-value');

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
  return trustValueModule.computeTrustScore(completedMatches, acceptedMatches);
}

/**
 * Compute trust level from score
 * 
 * @param {number} score - Trust score between 0 and 1
 * @returns {string} Trust level constant
 */
function computeTrustLevel(score) {
  return trustValueModule.computeTrustLevel(score);
}

/**
 * Alias for computeTrustLevel
 * 
 * @param {number} score - Trust score between 0 and 1
 * @returns {string} Trust level constant
 */
function getTrustLevel(score) {
  return trustValueModule.getTrustLevel(score);
}

function getTrustFormulaVersion() {
  return TRUST_FORMULA_VERSION;
}

module.exports = {
  TRUST_FORMULA_VERSION,
  computeTrustScore,
  computeTrustLevel,
  getTrustLevel,
  getTrustFormulaVersion,
};