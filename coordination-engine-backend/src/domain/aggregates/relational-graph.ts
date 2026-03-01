
type ConstraintType = 'positive' | 'negative';

interface RelationalEdgeModel {
  id: string;
  sourceId: string;
  targetId: string;
  constraintType: ConstraintType;
  confidence: number;
  createdAt: Date;
  updatedAt: Date;
}

interface RelationalGraphModel {
  graphId: string;
  contextId: string;
  edges: RelationalEdgeModel[];
  createdAt: Date;
  updatedAt: Date;
  addEdge(edge: RelationalEdgeModel): void;
  getEdgesForActor(actorId: string): RelationalEdgeModel[];
  getReciprocalEdges(actorId: string): RelationalEdgeModel[];
  hasEdge(sourceId: string, targetId: string): boolean;
  removeEdge(sourceId: string, targetId: string): boolean;
  hasLoops(): boolean;
  getConstraintWeights(actorId: string): { positiveWeight: number; negativeWeight: number };
}

interface RelationalGraphFactory {
  create(graphId: string, contextId: string): RelationalGraphModel;
}

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
const RelationalGraph: RelationalGraphFactory = {
  /**
   * Create a new relational graph
   * 
   * @param {string} graphId - Unique graph identifier
   * @param {string} contextId - Context identifier (e.g., gathering ID)
   * @returns {Object} Relational graph aggregate
   */
  create(graphId, contextId) {
    const graph: RelationalGraphModel = {
      graphId,
      contextId,
      edges: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      addEdge(edge: RelationalEdgeModel) {
        const existingEdge = this.edges.find(
          (e) => e.sourceId === edge.targetId && e.targetId === edge.sourceId
        );

        if (existingEdge && existingEdge.constraintType !== edge.constraintType) {
          throw new Error(
            `Loop detected: ${edge.sourceId} and ${edge.targetId} have conflicting constraints`
          );
        }

        this.edges.push(edge);
        this.updatedAt = new Date();
      },
      getEdgesForActor(actorId: string) {
        return this.edges.filter((e) => e.sourceId === actorId);
      },
      getReciprocalEdges(actorId: string) {
        return this.edges.filter((e) => e.targetId === actorId);
      },
      hasEdge(sourceId: string, targetId: string) {
        return this.edges.some((e) => e.sourceId === sourceId && e.targetId === targetId);
      },
      removeEdge(sourceId: string, targetId: string) {
        const index = this.edges.findIndex((e) => e.sourceId === sourceId && e.targetId === targetId);
        if (index !== -1) {
          this.edges.splice(index, 1);
          this.updatedAt = new Date();
          return true;
        }
        return false;
      },
      hasLoops() {
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
      },
      getConstraintWeights(actorId: string) {
        const positiveEdges = this.getEdgesForActor(actorId).filter((e) => e.constraintType === 'positive');
        const negativeEdges = this.getEdgesForActor(actorId).filter((e) => e.constraintType === 'negative');
        const positiveWeight = positiveEdges.reduce((sum, e) => sum + e.confidence / 100, 0);
        const negativeWeight = negativeEdges.reduce((sum, e) => sum + e.confidence / 100, 0);
        return { positiveWeight, negativeWeight };
      },
    };

    return graph;
  },
};

export { RelationalGraph };
