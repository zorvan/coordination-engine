/**
 * Agent Entity
 * 
 * Represents an AI advisory agent that can:
 * - Analyze match proposals
 * - Generate recommendations
 * - Validate constraints
 */

const AgentType = {
  MATCH_ANALYZER: 'match_analyzer',
  PREFERENCE_SUGGESTER: 'preference_suggester',
  CONFLICT_RESOLVER: 'conflict_resolver',
};

const AgentStatus = {
  IDLE: 'idle',
  ANALYZING: 'analyzing',
  READY: 'ready',
  ERROR: 'error',
};

function createAgent(id, name, type, config = {}) {
  if (!AgentType[type]) {
    throw new Error(`Invalid agent type: ${type}`);
  }

  return {
    id,
    name,
    type,
    config,
    status: AgentStatus.IDLE,
    lastActive: new Date(),
    createdAt: new Date(),
  };
}

function isValidAgentType(type) {
  return !!AgentType[type];
}

module.exports = {
  AgentType,
  AgentStatus,
  createAgent,
  isValidAgentType,
};