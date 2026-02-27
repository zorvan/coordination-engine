/**
 * Application layer use cases
 * 
 * This module contains business use cases that orchestrate domain entities
 * and infrastructure services. Use cases are the primary interface for
 * application logic and depend only on domain abstractions.
 */

const { CreateMatchUseCase } = require('./match/create-match');
const { ConfirmMatchUseCase } = require('./match/confirm-match');
const { CompleteMatchUseCase } = require('./match/complete-match');
const { CancelMatchUseCase } = require('./match/cancel-match');
const { UpdateTrustUseCase } = require('./trust/update-trust');
const { RelationalGraphUseCase } = require('./relational-graph');
const { AgentNegotiationUseCase } = require('./agent-negotiation');

module.exports = {
  CreateMatchUseCase,
  ConfirmMatchUseCase,
  CompleteMatchUseCase,
  CancelMatchUseCase,
  UpdateTrustUseCase,
  RelationalGraphUseCase,
  AgentNegotiationUseCase,
};