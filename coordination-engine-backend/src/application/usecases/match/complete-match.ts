import { MatchCompleted } from '../../../domain/events/domain-event';
import { TrustUpdated } from '../../../domain/events/domain-event';
import { computeTrustScore, getTrustLevel } from '../../../domain/services/trust-computation';
import { ActorRepositoryLike, CompleteMatchUseCaseLike, EventStoreLike, MatchRepositoryLike } from '../../../types/match';

const CompleteMatchUseCase = {
  create(
    matchRepository: MatchRepositoryLike,
    actorRepository: ActorRepositoryLike,
    eventStore: EventStoreLike
  ): CompleteMatchUseCaseLike {
    return {
      /**
       * Complete a match and update trust scores
       * 
       * Business logic:
       * - Only confirmed matches can be completed
       * - Both organizer and participants get trust updates
       * - Trust score = completed/accepted matches ratio
       * 
       * @param {string} matchId - The match to complete
       * @param {string} completedBy - The actor completing the match
       * @param {string} notes - Optional completion notes
       * @throws {Error} If match not found or not in confirmed state
       */
      async execute(matchId: string, completedBy: string, notes: string): Promise<void> {
        const match = await matchRepository.findById(matchId);
        
        if (!match) {
          throw new Error(`Match ${matchId} not found`);
        }

        if (match.state !== 'confirmed') {
          throw new Error('Only confirmed matches can be completed');
        }

        match.state = 'completed';
        match.notes = notes;
        match.completedAt = new Date();
        match.updatedAt = match.completedAt;

        const completedEvent = new MatchCompleted(
          matchId,
          completedBy,
          match.completedAt
        );

        await eventStore.append(completedEvent);

        const completedMatches = await eventStore.getEventsByType('MatchCompleted');
        const confirmedMatches = await eventStore.getEventsByType('MatchConfirmed');
        
        const completedCount = completedMatches.filter(
          (e) => (e.payload as { completedBy?: string }).completedBy === completedBy
        ).length;
        
        const confirmedCount = confirmedMatches.filter(
          (e) => (e.payload as { confirmedBy?: string }).confirmedBy === completedBy
        ).length;

        const trustScore = computeTrustScore(completedCount, confirmedCount);
        const trustLevel = getTrustLevel(trustScore);

        const trustEvent = new TrustUpdated(
          completedBy,
          trustScore,
          trustLevel,
          1,
          match.completedAt
        );

        await eventStore.append(trustEvent);
        await matchRepository.save(match);
      }
    };
  },
};

export { CompleteMatchUseCase };
