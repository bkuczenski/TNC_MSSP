var uuid = require("node-uuid");

var cache = {};

module.exports = function(klass, id) {
  var lookup = klass + id;
  if (!cache[lookup]) {
    cache[lookup] = uuid.v4();
  }
  return cache[lookup];
}
