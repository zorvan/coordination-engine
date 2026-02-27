const { AgentType } = require('./agent');
const { validateProposal } = require('./agent-proposal');

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
  create(negotiationId, matchId, organizerId) {
    const negotiation = {
      negotiationId,
      matchId,
      organizerId,
      agents: [],
      proposals: [],
      status: NegotiationStatus.INITIATED,
      createdAt: new Date(),
      completedAt: null,
    };

    /**
     * Assign an agent to this negotiation
     * 
     * @param {Object} agent - Agent entity
     * @returns {void}
     */
    negotiation.assignAgent = function(agent) {
      if (!this.agents.find((a) => a.id === agent.id)) {
        this.agents.push(agent);
      }
    };

    /**
     * Generate a proposal from an agent
     * 
     * @param {string} agentId - Agent identifier
     * @param {string} content - Proposal content
     * @param {number} confidence - Confidence score (0-1)
     * @returns {Object} Generated proposal
     */
    negotiation.generateProposal = function(agentId, content, confidence) {
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
    };

    /**
     * Get all proposals for this negotiation
     * 
     * @returns {Object[]} Array of proposals
     */
    negotiation.getProposals = function() {
      return this.proposals;
    };

    /**
     * Get validated proposals (confidence >= 0.5)
     * 
     * @returns {Object[]} Array of validated proposals
     */
    negotiation.getValidatedProposals = function() {
      return this.proposals.filter(
        (p) => p.status === ProposalStatus.VALIDATED
      );
    };

    /**
     * Mark negotiation as completed
     * 
     * @param {Date} completedAt - Optional completion timestamp
     * @returns {void}
     */
    negotiation.complete = function(completedAt) {
      this.status = NegotiationStatus.COMPLETED;
      this.completedAt = completedAt || new Date();
    };

    /**
     * Get agent by type
     * 
     * @param {string} type - Agent type
     * @returns {Object|null} Agent or null
     */
    negotiation.getAgentByType = function(type) {
      return this.agents.find((a) => a.type === type) || null;
    };

    /**
     * Check if negotiation requires user validation
     * 
     * @returns {boolean} True if proposals need user validation
     */
    negotiation.requiresValidation = function() {
      return this.proposals.some(
        (p) => p.status === ProposalStatus.PENDING
      );
    };

    return negotiation;
  },
};

const NegotiationStatus = {
  INITIATED: 'initiated',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
};

module.exports = {
  AgentNegotiation,
  NegotiationStatus,
};