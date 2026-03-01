import { AgentType, AgentStatus } from './agent';
import crypto from 'crypto';

/**
 * Agent Proposal
 * 
 * Represents a recommendation from an AI agent
 * including validation and confidence scoring
 */

function createProposal(id, agentId, matchId, content, confidence) {
  if (confidence < 0 || confidence > 1) {
    throw new Error('Confidence must be between 0 and 1');
  }

  return {
    id,
    agentId,
    matchId,
    content,
    confidence,
    status: ProposalStatus.PENDING,
    createdAt: new Date(),
    validatedAt: null,
    validationError: null,
  };
}

const ProposalStatus = {
  PENDING: 'pending',
  VALIDATED: 'validated',
  REJECTED: 'rejected',
};

function validateProposal(proposal) {
  if (proposal.confidence < 0.5) {
    proposal.status = ProposalStatus.REJECTED;
    proposal.validationError = 'Confidence too low';
  } else {
    proposal.status = ProposalStatus.VALIDATED;
    proposal.validatedAt = new Date();
  }
  return proposal;
}

export { createProposal,
  ProposalStatus,
  validateProposal, };