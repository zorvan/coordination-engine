/**
 * Projections exports
 * 
 * This module provides read model projections built from event streams
 * 
 * Pattern: Read Model - derived state optimized for querying
 * Pattern: Projection - transform event stream into useful aggregates
 */

const { computeTrustProjection } = require('./trust-projection');

module.exports = {
  computeTrustProjection,
};