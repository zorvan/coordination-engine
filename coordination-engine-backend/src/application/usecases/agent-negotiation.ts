/**
 * Agent negotiation use case
 * 
 * This module orchestrates agent negotiation for match coordination
 * 
 * Pattern: Use Case - coordinates domain entities for specific business goals
 */

import { AgentNegotiation } from '../../domain/aggregates/agent-negotiation';
import { AgentType, createAgent } from '../../domain/entities/agent';
import { generateAggregateId } from '../../domain/events/event-utils';

interface AgentRef {
  id: string;
  type: string;
}

interface ProposalModel {
  id: string;
  status: string;
}

interface NegotiationModel {
  assignAgent(agent: AgentRef): void;
  generateProposal(agentId: string, content: string, confidence: number): ProposalModel;
  getProposals(): ProposalModel[];
  getValidatedProposals(): ProposalModel[];
  complete(completedAt?: Date): void;
}

interface AgentRepository {
  findById(id: string): Promise<AgentRef | null>;
}

interface AgentNegotiationRepository {
  save(negotiation: NegotiationModel): Promise<void>;
  findById(id: string): Promise<NegotiationModel | null>;
}

const AgentNegotiationUseCase = {
  /**
   * Create agent negotiation use case
   * 
   * @param {Object} agentRepository - Repository for agent persistence
   * @param {Object} agentNegotiationRepository - Repository for negotiation storage
   * @param {Object} eventStore - Event store for audit trail
   * @returns {Object} Use case with methods
   */
  create(
    agentRepository: AgentRepository,
    agentNegotiationRepository: AgentNegotiationRepository,
    eventStore: unknown
  ) {
    return {
      /**
       * Initialize agent negotiation for a match
       * 
       * @param {string} matchId - Match identifier
       * @param {string} organizerId - Match organizer
       * @returns {Promise<string>} Negotiation ID
       */
      async initiateNegotiation(matchId: string, organizerId: string): Promise<string> {
        const negotiationId = generateAggregateId();
        
        const negotiation = AgentNegotiation.create(
          negotiationId,
          matchId,
          organizerId
        );

        // Assign default agents
        const matchAnalyzer = createAgent(
          generateAggregateId(),
          'Match Analyzer',
          AgentType.MATCH_ANALYZER
        );
        
        const preferenceSuggester = createAgent(
          generateAggregateId(),
          'Preference Suggester',
          AgentType.PREFERENCE_SUGGESTER
        );
        
        negotiation.assignAgent(matchAnalyzer);
        negotiation.assignAgent(preferenceSuggester);

        await agentNegotiationRepository.save(negotiation);

        return negotiationId;
      },

      /**
       * Generate a proposal from an agent
       * 
       * @param {string} negotiationId - Negotiation identifier
       * @param {string} agentId - Agent identifier
       * @param {string} content - Proposal content
       * @param {number} confidence - Confidence score (0-1)
       * @returns {Promise<Object>} Generated proposal
       */
      async generateProposal(
        negotiationId: string,
        agentId: string,
        content: string,
        confidence: number
      ): Promise<ProposalModel> {
        const negotiation = await agentNegotiationRepository.findById(negotiationId);
        
        if (!negotiation) {
          throw new Error(`Negotiation ${negotiationId} not found`);
        }

        const proposal = negotiation.generateProposal(agentId, content, confidence);

        await agentNegotiationRepository.save(negotiation);

        return proposal;
      },

      /**
       * Get all proposals for a negotiation
       * 
       * @param {string} negotiationId - Negotiation identifier
       * @returns {Promise<Object[]>} Array of proposals
       */
      async getProposals(negotiationId: string): Promise<ProposalModel[]> {
        const negotiation = await agentNegotiationRepository.findById(negotiationId);
        
        if (!negotiation) {
          throw new Error(`Negotiation ${negotiationId} not found`);
        }

        return negotiation.getProposals();
      },

      /**
       * Get validated proposals
       * 
       * @param {string} negotiationId - Negotiation identifier
       * @returns {Promise<Object[]>} Array of validated proposals
       */
      async getValidatedProposals(negotiationId: string): Promise<ProposalModel[]> {
        const negotiation = await agentNegotiationRepository.findById(negotiationId);
        
        if (!negotiation) {
          throw new Error(`Negotiation ${negotiationId} not found`);
        }

        return negotiation.getValidatedProposals();
      },

      /**
       * Complete the negotiation
       * 
       * @param {string} negotiationId - Negotiation identifier
       * @returns {Promise<void>}
       */
      async completeNegotiation(negotiationId: string): Promise<void> {
        const negotiation = await agentNegotiationRepository.findById(negotiationId);
        
        if (!negotiation) {
          throw new Error(`Negotiation ${negotiationId} not found`);
        }

        negotiation.complete();
        await agentNegotiationRepository.save(negotiation);
      },

      /**
       * Assign an agent to a negotiation
       * 
       * @param {string} negotiationId - Negotiation identifier
       * @param {string} agentId - Agent identifier
       * @returns {Promise<void>}
       */
      async assignAgent(negotiationId: string, agentId: string): Promise<void> {
        const negotiation = await agentNegotiationRepository.findById(negotiationId);
        
        if (!negotiation) {
          throw new Error(`Negotiation ${negotiationId} not found`);
        }

        const agent = await agentRepository.findById(agentId);
        
        if (!agent) {
          throw new Error(`Agent ${agentId} not found`);
        }

        negotiation.assignAgent(agent);
        await agentNegotiationRepository.save(negotiation);
      },
    };
  },
};

export { AgentNegotiationUseCase };
