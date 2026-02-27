const { MatchState, isValidTransition } = require('../valuables/match-state');

const MatchAggregate = {
  /**
   * Create a new match aggregate
   * 
   * @param {string} id - Unique match identifier
   * @param {string} organizerId - Organizing actor ID
   * @param {string} title - Match title
   * @param {string} description - Optional description
   * @param {Date} scheduledTime - When the match is scheduled
   * @param {number} durationMinutes - Duration in minutes
   * @param {string} location - Physical or virtual location
   * @param {string[]} participantIds - Array of participant actor IDs
   * @returns {Object} Match aggregate with state machine
   */
  create(id, organizerId, title, description, scheduledTime, durationMinutes, location, participantIds) {
    return {
      matchId: id,
      state: MatchState.PROPOSED,
      organizerId,
      title,
      description,
      scheduledTime,
      durationMinutes,
      location,
      participantIds,
      createdAt: new Date(),
      updatedAt: new Date(),
      completedAt: null,
      cancelledAt: null,
      notes: null,
      version: 0,

      transitionTo(newState) {
        if (!isValidTransition(this.state, newState)) {
          throw new Error(`Invalid transition from ${this.state} to ${newState}`);
        }
        this.state = newState;
        this.updatedAt = new Date();
        this.version++;
        if (newState === MatchState.COMPLETED) {
          this.completedAt = new Date();
        }
        if (newState === MatchState.CANCELLED) {
          this.cancelledAt = new Date();
        }
      },

      confirm() {
        this.transitionTo(MatchState.CONFIRMED);
      },

      complete(notes) {
        this.transitionTo(MatchState.COMPLETED);
        this.notes = notes;
      },

      cancel(reason) {
        this.transitionTo(MatchState.CANCELLED);
        this.notes = reason;
      },

      isValidTransition(targetState) {
        return isValidTransition(this.state, targetState);
      },
    };
  },
};

module.exports = { MatchAggregate };