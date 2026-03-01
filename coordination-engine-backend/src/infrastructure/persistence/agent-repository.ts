/**
 * Agent repository for Phase 4
 * 
 * Stores and manages AI agents
 * 
 * Pattern: Event Sourcing - agent events
 */

import crypto from 'crypto';

interface AgentRecord {
  id: string;
  name: string;
  type: string;
  config: Record<string, unknown>;
  status: string;
  lastActive: Date | null;
  createdAt: Date;
  updatedAt: Date | null;
}

function createAgentRepository(eventStore) {
  return {
    /**
     * Save an agent
     * 
     * @param {Object} agent - Agent entity
     * @returns {Promise<void>}
     */
    async save(agent) {
      const events = await eventStore.getEventsByAggregate(agent.id);
      const createdEvent = events.find((e) => e.type === 'AgentCreated');
      
      if (!createdEvent) {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: agent.id,
          type: 'AgentCreated',
          timestamp: agent.createdAt,
          payload: {
            id: agent.id,
            name: agent.name,
            type: agent.type,
            config: agent.config,
            status: agent.status,
          },
        });
      }

      // Update status if changed
      if (agent.status !== 'idle' || agent.lastActive) {
        await eventStore.append({
          id: crypto.randomUUID(),
          aggregateId: agent.id,
          type: 'AgentStatusUpdated',
          timestamp: agent.lastActive || new Date(),
          payload: {
            id: agent.id,
            status: agent.status,
            lastActive: agent.lastActive,
          },
        });
      }
    },

    /**
     * Find agent by ID
     * 
     * @param {string} id - Agent identifier
     * @returns {Promise<Object|null>} Agent object or null
     */
    async findById(id) {
      const events = await eventStore.getEventsByAggregate(id);
      const createdEvent = events.find((e) => e.type === 'AgentCreated');
      
      if (!createdEvent) {
        return null;
      }

      let agent: AgentRecord = {
        id: createdEvent.payload.id,
        name: createdEvent.payload.name,
        type: createdEvent.payload.type,
        config: createdEvent.payload.config || {},
        status: createdEvent.payload.status || 'idle',
        lastActive: null,
        createdAt: new Date(createdEvent.timestamp),
        updatedAt: null,
      };

      for (const event of events) {
        if (event.type === 'AgentStatusUpdated') {
          agent.status = event.payload.status;
          agent.lastActive = event.payload.lastActive || new Date();
          agent.updatedAt = new Date(event.timestamp);
        }
      }

      return agent;
    },

    /**
     * Find all agents
     * 
     * @returns {Promise<Object[]>} Array of all agent objects
     */
    async findAll() {
      const events = await eventStore.getAllEvents();
      const agentEvents = events.filter((e) => e.type === 'AgentCreated');
      
      return agentEvents.map((event) => ({
        id: event.payload.id,
        name: event.payload.name,
        type: event.payload.type,
        config: event.payload.config || {},
        status: event.payload.status || 'idle',
        lastActive: null,
        createdAt: new Date(event.timestamp),
        updatedAt: null,
      }));
    },

    /**
     * Find agents by type
     * 
     * @param {string} type - Agent type
     * @returns {Promise<Object[]>} Array of agent objects
     */
    async findByType(type) {
      const agents = await this.findAll();
      return agents.filter((a) => a.type === type);
    },
  };
}

export { createAgentRepository };
