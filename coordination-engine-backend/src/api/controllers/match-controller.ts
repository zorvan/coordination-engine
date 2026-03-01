import { Request, Response } from 'express';
import {
  CancelMatchUseCaseLike,
  CompleteMatchUseCaseLike,
  ConfirmMatchUseCaseLike,
  CreateMatchUseCaseLike,
} from '../../types/match';

interface MatchControllerHandlers {
  handleCreateMatch(req: Request, res: Response): Promise<void>;
  handleConfirmMatch(req: Request, res: Response): Promise<void>;
  handleCompleteMatch(req: Request, res: Response): Promise<void>;
  handleCancelMatch(req: Request, res: Response): Promise<void>;
}

const MatchController = {
  create: function(
    createMatchUseCase: CreateMatchUseCaseLike,
    confirmMatchUseCase: ConfirmMatchUseCaseLike,
    completeMatchUseCase: CompleteMatchUseCaseLike,
    cancelMatchUseCase: CancelMatchUseCaseLike
  ): MatchControllerHandlers {
    return {
      async handleCreateMatch(req: Request, res: Response): Promise<void> {
        try {
          const { organizerId, title, description, scheduledTime, durationMinutes, location, participantIds } = req.body;

          const matchId = await createMatchUseCase.execute(
            organizerId,
            title,
            description,
            new Date(scheduledTime),
            durationMinutes,
            location,
            participantIds
          );

          res.status(201).json({
            matchId,
            status: 'match_created',
            message: 'Match has been created successfully'
          });
        } catch (error) {
          res.status(500).json({
            error: 'failed_to_create_match',
            message: error instanceof Error ? error.message : 'Unknown error occurred'
          });
        }
      },

      async handleConfirmMatch(req: Request, res: Response): Promise<void> {
        try {
          const { matchId, actorId } = req.body;
          await confirmMatchUseCase.execute(matchId, actorId);

          res.status(200).json({
            status: 'match_confirmed',
            message: 'Match has been confirmed successfully'
          });
        } catch (error) {
          res.status(500).json({
            error: 'failed_to_confirm_match',
            message: error instanceof Error ? error.message : 'Unknown error occurred'
          });
        }
      },

      async handleCompleteMatch(req: Request, res: Response): Promise<void> {
        try {
          const { matchId, actorId, notes } = req.body;
          await completeMatchUseCase.execute(matchId, actorId, notes);

          res.status(200).json({
            status: 'match_completed',
            message: 'Match has been completed successfully'
          });
        } catch (error) {
          res.status(500).json({
            error: 'failed_to_complete_match',
            message: error instanceof Error ? error.message : 'Unknown error occurred'
          });
        }
      },

      async handleCancelMatch(req: Request, res: Response): Promise<void> {
        try {
          const { matchId, actorId, reason } = req.body;
          await cancelMatchUseCase.execute(matchId, actorId, reason);

          res.status(200).json({
            status: 'match_cancelled',
            message: 'Match has been cancelled successfully'
          });
        } catch (error) {
          res.status(500).json({
            error: 'failed_to_cancel_match',
            message: error instanceof Error ? error.message : 'Unknown error occurred'
          });
        }
      }
    };
  }
};

export { MatchController };
