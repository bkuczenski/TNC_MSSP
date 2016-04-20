// store.js exposes some useful utilities for debugging the model.

var _ = require('underscore');
var colors = require('colors');

var model = require("../index");

function hasId(id) {
  return function(thing) { return thing.id == id }
}

var Question = function(props, store) {
  var attrs = props;
  _.extend(this, attrs);

  this.criteria = function() {
    return model.criteria.filter(function(criteria) {
      return criteria.question === attrs.id;
    });
  };

  this.caveats = function() {
    return model.caveats.filter(function(caveat) {
      return caveat.question === attrs.id;
    });
  };

  // To answer a question, provide the index (0-based) of your choice
  this.answer = function(index) {
    var answer = this.answers[index];
    var self = this;
    var targetIds = [];
    console.log("You answered: " + answer);
    var caveats = this.caveats().filter(function(caveat) {
      return caveat.answer == index;
    });
    var caveatsById = _.groupBy(caveats, 'target');
    var targetIds = _.keys(caveatsById);
    console.log("Based on your answer, the following targets apply:");
    var allCriteria = this.criteria();
    var targetCriteria = {};
    for (var i = 0; i < allCriteria.length; i++) {
      var criterium = allCriteria[i];
      if (criterium.threshold <= index && (!(criterium.target in targetCriteria) || targetCriteria[criterium.target].threshold < criterium.threshold)) {
        targetCriteria[criterium.target] = criterium;
      }
    }
    targetIds = targetIds.concat(_.keys(targetCriteria));
    var targets = _.uniq(targetIds).map(function(id) { return store.byId(id) })
    targets = _.sortBy(targets, 'type');
    targets.forEach(function(target) {
      console.log("");
      console.log(colors.inverse(target.type + " #" + target._legacyId) + " " + colors.bold(target.title));
      console.log(target.description);
      (caveatsById[target.id] || []).forEach(function(caveat) {
        switch (caveat.score) {
          case -3:
            console.log(colors.red.underline(caveat.note));
            break;
          case -2:
            console.log(colors.red(caveat.note));
            break;
          case -1:
            console.log(colors.yellow(caveat.note));
            break;
          case 0:
            console.log(colors.bold(caveat.note));
            break;
          case 1:
            console.log(colors.magenta(caveat.note));
            break;
          case 2:
            console.log(colors.green(caveat.note));
            break;
          default:
            console.log(colors.bold(caveat.note));
            break;


        }
      });
    });
  };

  return this;
}

module.exports = {
  byId: function(id) {
    return new Question(_.find(model.questions, hasId(id)) || _.find(model.targets, hasId(id)), this);
  },

  byLegacyId: function(klass, id) {
    return this.byId(model.uuid(klass, id));
  },

  randomQuestion: function() {
    return new Question(model.questions[_.random(0, model.questions.length)], this);
  },

  questionDetails: function(question) {
    console.log(question);
  }

}
