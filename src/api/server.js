const PostgresEventStore = require('../infrastructure/persistence/event-store').PostgresEventStore;
const { CreateMatchUseCase } = require('../application/usecases/match/create-match');
const { ConfirmMatchUseCase } = require('../application/usecases/match/confirm-match');
const { CompleteMatchUseCase } = require('../application/usecases/match/complete-match');
const { CancelMatchUseCase } = require('../application/usecases/match/cancel-match');
const { createRoutes } = require('./routes');
const { MatchController } = require('./controllers');

const createServer = function(pool) {
  const eventStore = PostgresEventStore.create(pool);
  
  const createMatchUseCase = CreateMatchUseCase.create(null, eventStore);
  const confirmMatchUseCase = ConfirmMatchUseCase.create(null, eventStore);
  const completeMatchUseCase = CompleteMatchUseCase.create(null, eventStore, null);
  const cancelMatchUseCase = CancelMatchUseCase.create(null, eventStore);
  
  const matchRoutes = createRoutes(createMatchUseCase, confirmMatchUseCase, completeMatchUseCase, cancelMatchUseCase, eventStore);

  return {
    get: function(path, handler) {
      matchRoutes.routes[path] = { method: 'get', handler };
    },
    post: function(path, handler) {
      matchRoutes.routes[path] = { method: 'post', handler };
    }
  };
};

module.exports = { createServer };