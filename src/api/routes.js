const CreateMatchUseCase = require('../application/usecases/match/create-match').CreateMatchUseCase;

const createRoutes = function(createMatchUseCase, confirmMatchUseCase, completeMatchUseCase, cancelMatchUseCase, eventStore) {
  const router = {
    routes: {},
    post: function(path, handler) {
      this.routes[path] = { method: 'post', handler };
    },
    get: function(path, handler) {
      this.routes[path] = { method: 'get', handler };
    }
  };

  router.post('/matches', function(req, res) {
    createMatchUseCase.execute(
      req.body.organizerId,
      req.body.title,
      req.body.description,
      new Date(req.body.scheduledTime),
      req.body.durationMinutes,
      req.body.location,
      req.body.participantIds
    ).then(function(matchId) {
      res.status(201).json({
        matchId: matchId,
        status: 'match_created',
        message: 'Match has been created successfully'
      });
    }).catch(function(error) {
      res.status(500).json({
        error: 'failed_to_create_match',
        message: error instanceof Error ? error.message : 'Unknown error occurred'
      });
    });
  });

  router.post('/matches/confirm', function(req, res) {
    confirmMatchUseCase.execute(req.body.matchId, req.body.actorId)
      .then(function() {
        res.status(200).json({
          status: 'match_confirmed',
          message: 'Match has been confirmed successfully'
        });
      })
      .catch(function(error) {
        res.status(500).json({
          error: 'failed_to_confirm_match',
          message: error instanceof Error ? error.message : 'Unknown error occurred'
        });
      });
  });

  router.post('/matches/complete', function(req, res) {
    completeMatchUseCase.execute(req.body.matchId, req.body.actorId, req.body.notes)
      .then(function() {
        res.status(200).json({
          status: 'match_completed',
          message: 'Match has been completed successfully'
        });
      })
      .catch(function(error) {
        res.status(500).json({
          error: 'failed_to_complete_match',
          message: error instanceof Error ? error.message : 'Unknown error occurred'
        });
      });
  });

  router.post('/matches/cancel', function(req, res) {
    cancelMatchUseCase.execute(req.body.matchId, req.body.actorId, req.body.reason)
      .then(function() {
        res.status(200).json({
          status: 'match_cancelled',
          message: 'Match has been cancelled successfully'
        });
      })
      .catch(function(error) {
        res.status(500).json({
          error: 'failed_to_cancel_match',
          message: error instanceof Error ? error.message : 'Unknown error occurred'
        });
      });
  });

  router.get('/matches/:matchId', function(req, res) {
    res.status(200).json({
      matchId: req.params.matchId,
      state: 'proposed',
      message: 'Match details retrieved successfully'
    });
  });

  return router;
};

module.exports = { createRoutes };