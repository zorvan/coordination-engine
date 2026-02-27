const RelationalEdge = require('./relational-edge');

/**
 * Relational graph aggregate
 * 
 * Represents a collection of relational edges (soft social constraints)
 * between actors in a gathering context.
 * 
 * Key behaviors:
 * - Track all edges for an actor
 * - Detect loops (mutual exclusion constraints)
 * - Calculate constraint weights for fairness computation
 */
const RelationalGraph = {
  /**
   * Create a new relational graph
   * 
   * @param {string} graphId - Unique graph identifier
   * @param {string} contextId - Context identifier (e.g., gathering ID)
   * @returns {Object} Relational graph aggregate
   */
  create(graphId, contextId) {
    const graph = {
      graphId,
      contextId,
      edges: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    /**
     * Add a relational edge to the graph
     * 
     * @param {Object} edge - Edge entity to add
     * @returns {void}
     */
    graph.addEdge = function(edge) {
      // Check for loops: mutual exclusion constraints
      const existingEdge = this.edges.find(
        (e) => e.sourceId === edge.targetId && e.targetId === edge.sourceId
      );
      
      if (existingEdge) {
        // Check if this would create a mutual exclusion loop
        if (existingEdge.constraintType !== edge.constraintType) {
          throw new Error(
            `Loop detected: ${edge.sourceId} and ${edge.targetId} have conflicting constraints`
          );
        }
      }

      this.edges.push(edge);
      this.updatedAt = new Date();
    };

    /**
     * Get all edges for a specific actor
     * 
     * @param {string} actorId - Actor identifier
     * @returns {Object[]} Array of edges
     */
    graph.getEdgesForActor = function(actorId) {
      return this.edges.filter((e) => e.sourceId === actorId);
    };

    /**
     * Get reciprocal edges (where actor is the target)
     * 
     * @param {string} actorId - Actor identifier
     * @returns {Object[]} Array of edges where actor is target
     */
    graph.getReciprocalEdges = function(actorId) {
      return this.edges.filter((e) => e.targetId === actorId);
    };

    /**
     * Check if a relationship exists
     * 
     * @param {string} sourceId - Source actor ID
     * @param {string} targetId - Target actor ID
     * @returns {boolean} True if relationship exists
     */
    graph.hasEdge = function(sourceId, targetId) {
      return this.edges.some(
        (e) => e.sourceId === sourceId && e.targetId === targetId
      );
    };

    /**
     * Remove a relational edge
     * 
     * @param {string} sourceId - Source actor ID
     * @param {string} targetId - Target actor ID
     * @returns {boolean} True if edge was removed
     */
    graph.removeEdge = function(sourceId, targetId) {
      const index = this.edges.findIndex(
        (e) => e.sourceId === sourceId && e.targetId === targetId
      );
      
      if (index !== -1) {
        this.edges.splice(index, 1);
        this.updatedAt = new Date();
        return true;
      }
      return false;
    };

    /**
     * Check for loops (mutual exclusion constraints)
     * 
     * @returns {boolean} True if any loops detected
     */
    graph.hasLoops = function() {
      for (let i = 0; i < this.edges.length; i++) {
        const edge = this.edges[i];
        const reciprocal = this.edges.find(
          (e) => e.sourceId === edge.targetId && e.targetId === edge.sourceId
        );
        
        if (reciprocal && edge.constraintType !== reciprocal.constraintType) {
          return true;
        }
      }
      return false;
    };

    /**
     * Get constraint weights for an actor
     * 
     * @param {string} actorId - Actor identifier
     * @returns {Object} Weights for positive and negative constraints
     */
    graph.getConstraintWeights = function(actorId) {
      const positiveEdges = this.getEdgesForActor(actorId).filter(
        (e) => e.constraintType === 'positive'
      );
      
      const negativeEdges = this.getEdgesForActor(actorId).filter(
        (e) => e.constraintType === 'negative'
      );

      const positiveWeight = positiveEdges.reduce(
        (sum, e) => sum + e.confidence / 100,
        0
      );
      
      const negativeWeight = negativeEdges.reduce(
        (sum, e) => sum + e.confidence / 100,
        0
      );

      return { positiveWeight, negativeWeight };
    };

    return graph;
  },
};

module.exports = { RelationalGraph };