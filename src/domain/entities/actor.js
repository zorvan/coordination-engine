const crypto = require('crypto');

const TrustLevel = {
  VERY_LOW: 'very_low',
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  VERY_HIGH: 'very_high',
};

function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function computeTrustLevel(score) {
  if (score >= 0.9) return TrustLevel.VERY_HIGH;
  if (score >= 0.7) return TrustLevel.HIGH;
  if (score >= 0.5) return TrustLevel.MEDIUM;
  if (score >= 0.3) return TrustLevel.LOW;
  return TrustLevel.VERY_LOW;
}

function createActor(id, name, email, avatar, circles = []) {
  if (!isValidEmail(email)) {
    throw new Error('Invalid email address');
  }
  return {
    id,
    name,
    email,
    avatar,
    circles,
    temporalIdentity: null,
    trustScore: 0,
    trustLevel: TrustLevel.VERY_LOW,
    acceptedMatches: 0,
    completedMatches: 0,
    createdAt: new Date(),
    updatedAt: new Date(),
  };
}

module.exports = {
  TrustLevel,
  isValidEmail,
  computeTrustLevel,
  createActor,
};