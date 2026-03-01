import crypto from 'crypto';
import { createProposal, ProposalStatus, validateProposal } from '../entities/agent-proposal';

interface AgentRef {
  id: string;
  type: string;
}

interface ProposalModel {
  id: string;
  agentId: string;
  matchId: string;
  content: string;
  confidence: number;
  status: string;
  createdAt: Date;
  validatedAt: Date | null;
  validationError: string | null;
}

interface AgentNegotiationModel {
  negotiationId: string;
  matchId: string;
  organizerId: string;
  agents: AgentRef[];
  proposals: ProposalModel[];
  status: string;
  createdAt: Date;
  completedAt: Date | null;
  assignAgent(agent: AgentRef): void;
  generateProposal(agentId: string, content: string, confidence: number): ProposalModel;
  getProposals(): ProposalModel[];
  getValidatedProposals(): ProposalModel[];
  complete(completedAt?: Date): void;
  getAgentByType(type: string): AgentRef | null;
  requiresValidation(): boolean;
}

/**
 * Agent Negotiation Aggregate
 * 
 * Manages the negotiation process between AI agents and user validation
 * 
 * Key behaviors:
 * - Agent assignment for different types of analysis
 * - Proposal generation and validation
 * - Conflict resolution
 */

const AgentNegotiation = {
  /**
   * Create a new agent negotiation for a match
   * 
   * @param {string} negotiationId - Unique negotiation identifier
   * @param {string} matchId - Match being negotiated
   * @param {string} organizerId - Match organizer
   * @returns {Object} Agent negotiation aggregate
   */
  create(negotiationId: string, matchId: string, organizerId: string): AgentNegotiationModel {
    const negotiation: AgentNegotiationModel = {
      negotiationId,
      matchId,
      organizerId,
      agents: [],
      proposals: [],
      status: NegotiationStatus.INITIATED,
      createdAt: new Date(),
      completedAt: null,
      assignAgent(agent: AgentRef) {
        if (!this.agents.find((a) => a.id === agent.id)) {
          this.agents.push(agent);
        }
      },
      generateProposal(agentId: string, content: string, confidence: number) {
        const proposal = validateProposal(
          createProposal(
            crypto.randomUUID(),
            agentId,
            this.matchId,
            content,
            confidence
          )
        );
        this.proposals.push(proposal);
        return proposal;
      },
      getProposals() {
        return this.proposals;
      },
      getValidatedProposals() {
        return this.proposals.filter((p) => p.status === ProposalStatus.VALIDATED);
      },
      complete(completedAt: Date = new Date()) {
        this.status = NegotiationStatus.COMPLETED;
        this.completedAt = completedAt;
      },
      getAgentByType(type: string) {
        return this.agents.find((a) => a.type === type) || null;
      },
      requiresValidation() {
        return this.proposals.some((p) => p.status === ProposalStatus.PENDING);
      },
    };

    return negotiation;
  },
};

const NegotiationStatus = {
  INITIATED: 'initiated',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
} as const;

export { AgentNegotiation,
  NegotiationStatus, };
