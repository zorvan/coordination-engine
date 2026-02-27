const PostgresEventStoreInterface = {
  append: function() {},
  getEventsByAggregate: function() {},
  getAllEvents: function() {},
  getEventsSince: function() {}
};

module.exports = {
  PostgresEventStoreInterface
};