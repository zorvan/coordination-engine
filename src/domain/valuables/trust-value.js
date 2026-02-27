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

function computeTrustLevel(score) {
  if (score >= 0.9) return TrustValue.VERY_HIGH;
  if (score >= 0.7) return TrustValue.HIGH;
  if (score >= 0.5) return TrustValue.MEDIUM;
  if (score >= 0.3) return TrustValue.LOW;
  return TrustValue.VERY_LOW;
}

function computeTrustScore(completedMatches, acceptedMatches) {
  if (acceptedMatches === 0) return 0;
  return completedMatches / acceptedMatches;
}

module.exports = {
  TrustValue,
  createTrustValueObject,
  computeTrustLevel,
  computeTrustScore,
};