const trustValueModule = require('../valuables/trust-value');

const TRUST_FORMULA_VERSION = '1.0';

function computeTrustScore(completedMatches, acceptedMatches) {
  return trustValueModule.computeTrustScore(completedMatches, acceptedMatches);
}

function computeTrustLevel(score) {
  return trustValueModule.computeTrustLevel(score);
}

function getTrustFormulaVersion() {
  return TRUST_FORMULA_VERSION;
}

module.exports = {
  TRUST_FORMULA_VERSION,
  computeTrustScore,
  computeTrustLevel,
  getTrustFormulaVersion,
};