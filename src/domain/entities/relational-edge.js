const crypto = require('crypto');

/**
 * Relational edge entity
 * 
 * Represents a soft social constraint between actors:
 * - "If X attends, I attend" (positive constraint)
 * - "If X attends, I prefer not" (negative constraint)
 * 
 * These are soft constraints that affect regret scores slightly
 * but are not hard-enforced in V1.
 */
const RelationalEdge = {
  /**
   * Create a new relational edge
   * 
   * @param {string} id - Unique edge identifier
   * @param {string} sourceId - Source actor ID (the one making the constraint)
   * @param {string} targetId - Target actor ID (the one being referenced)
   * @param {string} constraintType - 'positive' or 'negative'
   * @param {number} confidence - Confidence level (0-100)
   * @param {Date} createdAt - When the constraint was added
   * @returns {Object} Relational edge entity
   */
  create(id, sourceId, targetId, constraintType, confidence, createdAt = new Date()) {
    // Validate constraint type
    if (!['positive', 'negative'].includes(constraintType)) {
      throw new Error(`Invalid constraint type: ${constraintType}. Must be 'positive' or 'negative'`);
    }

    // Validate confidence range
    if (confidence < 0 || confidence > 100) {
      throw new Error(`Invalid confidence: ${confidence}. Must be between 0 and 100`);
    }

    return {
      id,
      sourceId,
      targetId,
      constraintType,
      confidence,
      createdAt,
      updatedAt: createdAt,
    };
  },

  /**
   * Create a positive constraint ("If X attends, I attend")
   * 
   * @param {string} sourceId - Source actor ID
   * @param {string} targetId - Target actor ID
   * @param {number} confidence - Confidence level (0-100)
   * @returns {Object} Relational edge with positive constraint
   */
  createPositive(sourceId, targetId, confidence) {
    return this.create(
      crypto.randomUUID(),
      sourceId,
      targetId,
      'positive',
      confidence
    );
  },

  /**
   * Create a negative constraint ("If X attends, I prefer not")
   * 
   * @param {string} sourceId - Source actor ID
   * @param {string} targetId - Target actor ID
   * @param {number} confidence - Confidence level (0-100)
   * @returns {Object} Relational edge with negative constraint
   */
  createNegative(sourceId, targetId, confidence) {
    return this.create(
      crypto.randomUUID(),
      sourceId,
      targetId,
      'negative',
      confidence
    );
  },
};

module.exports = { RelationalEdge };