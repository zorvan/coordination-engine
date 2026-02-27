const fairnessLedgerService = require('../domain/services/fairness-ledger');

/**
 * Fairness ledger infrastructure implementation
 * 
 * Computes fairness metrics from event store events
 * 
 * Pattern: Projection - derived state from event history
 */

function createFairnessLedger(eventStore) {
  return {
    /**
     * Compute fairness metrics for a match
     * 
     * @param {string} matchId - Match identifier
     * @returns {Promise<Object>} Fairness metrics
     */
    async computeFairnessMetrics(matchId) {
      const events = await eventStore.getEventsByAggregate(matchId);
      
      let votes = [];
      let totalMembers = 0;
      let votingMembers = 0;
      
      for (const event of events) {
        if (event.type === 'MatchCreated') {
          totalMembers = event.payload.participantIds.length + 1; // +1 for organizer
        } else if (event.type === 'MatchConfirmed' || event.type === 'MatchCompleted' || event.type === 'MatchCancelled') {
          votingMembers++;
        }
      }

      // For simplicity, use a default vote set
      // In production, this would be computed from availability matrix
      votes = ['Strong Yes', 'Yes', 'Prefer Not', 'No'];

      const totalRegret = fairnessLedgerService.computeRegret(votes);
      const enthusiasmScore = fairnessLedgerService.computeEnthusiasm(votes);
      const participationRate = fairnessLedgerService.computeParticipationRate(totalMembers, votingMembers);
      const fairnessScore = fairnessLedgerService.computeFairnessScore(
        totalRegret,
        enthusiasmScore,
        participationRate
      );

      return {
        matchId,
        totalRegret,
        enthusiasmScore,
        participationRate,
        fairnessScore,
        computedAt: new Date(),
      };
    },

    /**
     * Get all fairness metrics for a set of matches
     * 
     * @param {string[]} matchIds - Match identifiers
     * @returns {Promise<Object[]>} Array of fairness metrics
     */
    async getAllFairnessMetrics(matchIds) {
      const metrics = [];
      
      for (const matchId of matchIds) {
        const metric = await this.computeFairnessMetrics(matchId);
        metrics.push(metric);
      }

      return metrics;
    },

    /**
     * Rebuild fairness ledger from event history
     * 
     * @param {Object} eventStore - The event store instance
     * @returns {Promise<void>}
     */
    async rebuildFromEvents() {
      // This would rebuild the fairness ledger from event history
      // For now, it's a placeholder as the ledger is computed on-demand
      return Promise.resolve();
    },
  };
}

module.exports = { createFairnessLedger };