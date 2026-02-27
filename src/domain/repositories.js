const MatchRepositoryInterface = {
  save: function() {},
  getById: function() {},
  getMatchesByActor: function() {},
  getAll: function() {}
};

const EventStoreInterface = {
  append: function() {},
  getEventsByAggregate: function() {},
  getAllEvents: function() {},
  getEventsSince: function() {}
};

const TrustProjectionInterface = {
  computeTrustScore: function() {},
  updateTrustScore: function() {}
};

const RelationalGraphInterface = {
  addEdge: function() {},
  getEdgesForActor: function() {},
  getReciprocalEdges: function() {}
};

const FairnessLedgerInterface = {
  computeFairnessMetrics: function() {},
  getAllFairnessMetrics: function() {},
  rebuildFromEvents: function() {}
};

const TemporalIdentityRepositoryInterface = {
  save: function() {},
  getById: function() {}
};

const GovernanceRepositoryInterface = {
  saveRuleVersion: function() {},
  getCurrentVersion: function() {},
  getAllVersions: function() {}
};

const ActorRepositoryInterface = {
  save: function() {},
  getById: function() {},
  getAll: function() {}
};

module.exports = {
  MatchRepositoryInterface,
  EventStoreInterface,
  TrustProjectionInterface,
  RelationalGraphInterface,
  FairnessLedgerInterface,
  TemporalIdentityRepositoryInterface,
  GovernanceRepositoryInterface,
  ActorRepositoryInterface
};