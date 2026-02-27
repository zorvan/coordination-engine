const MatchState = require('../valuables/match-state').MatchState;

const MatchAggregate = {
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
        if (!this.isValidTransition(newState)) {
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
        return MatchState.isValidTransition(this.state, targetState);
      },
    };
  },
};

module.exports = { MatchAggregate };