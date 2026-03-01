/**
 * Trust projection computation
 * 
 * This computes trust scores from event store events
 * 
 * Pattern: Projection - derived state from event stream
 * Pattern: Read Model - optimized query from event history
 */

import { computeTrustScore, getTrustLevel } from '../../domain/services/trust-computation';

/**
 * Compute trust score for an actor from event history
 * 
 * Business logic:
 * - Trust score = completed matches / accepted matches
 * - Uses event store to reconstruct state from event history
 * 
 * @param {Object} eventStore - The event store instance
 * @param {string} actorId - Actor identifier
 * @returns {Promise<number>} Trust score between 0 and 1
 */
async function computeTrustProjection(eventStore, actorId) {
  const events = await eventStore.getAllEvents();
  
  const completedMatches = events.filter(
    (e) => e.type === 'MatchCompleted' && e.payload?.completedBy === actorId
  ).length;

  const confirmedMatches = events.filter(
    (e) =>
      e.type === 'MatchConfirmed' &&
      (e.payload?.confirmedBy === actorId ||
        (e.payload?.participants && e.payload.participants.includes(actorId)))
  ).length;

  return computeTrustScore(completedMatches, confirmedMatches);
}

export { computeTrustProjection,
  getTrustLevel, };
