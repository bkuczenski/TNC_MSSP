var _ = require('underscore');

// In this script I've replaced the integer ids with globally-unique UUIDs.
var uuid = require('./uuid');

// In this script I'm pulling in all the json files and translating them into
// objects that are a little easier for me to work with, by cleaning out null
// and empty values, using more idiomatic variable names, and restructuring
// attributes into something that can eventually be used in a user-interface.
var questions = require('../2016-03-23/questions.json');
var targets = require('../2016-03-23/targets.json')
var criteria = require('../2016-03-23/criteria.json')
var caveats = require('../2016-03-23/caveats.json')
var colorMap = require('../2016-03-23/colormap.json')

// I found a lot of null and empty string values throughout the attributes. I'm
// running this filter to clean them out
function filterAttributes(attrs) {
  return attrs.filter(function(a) {
    if (a == null) {
      return false;
    } else if (typeof a === 'string') {
      return a.trim().length > 0;
    } else {
      return true
    }
  });
}

// This is the output of this module, a data structure containing lists of all
// questions, targets, criteria, and caveats.
// I dropped the color mappings in favor of adding scores directly to each
// caveat. This will make it easier to theme the final web app.
module.exports = {

  // Users answer Questions to determine what targets are recommended to
  // fisheries managers.
  questions: questions.map(function(record) {
    // clean up null values in the attributes
    var attrs = filterAttributes(record.Attributes)
    // We need a single question to ask the user.
    // Use the attribute that includes a question mark, or if not available
    // use the first attribute
    var questionTitle = _.find(attrs, function(a) {
      return a.indexOf("?") !== -1
    }) || attrs[0] || "";

    // This is the final output object. An example would look like:
    // {
    //   id: '3c21faae-4e60-4bb3-850f-7633c46ba677',
    //   spreadsheetLocation: 'Monitoring:BA',
    //   answers: [ 'No', 'Yes' ],
    //   question: 'Are multiple species targeted, with a portion of species destined towards markets, processors, subsistence, or other components of supply chain?',
    //   description: 'IF YES. Operational characteristics. Expanded Multi-species caveat. ',
    //   _legacyId: 188
    // }
    return {
      // change to a uuid
      id: uuid('question', record.QuestionID),
      // I assume that's what References is?
      spreadsheetLocation: record.References.join(". "),
      // filter out nulls and whitespace
      answers: filterAttributes(record.ValidAnswers),
      // chosen by ? or first attribute
      question: questionTitle,
      // just collapse all this contextual info into a description, excluding
      // the title text
      description: attrs.join(". ").replace(questionTitle, ''),
      // keep the old id around as a pseudo-private var for debugging
      _legacyId: record.QuestionID
    }
  // Filter out questions without attributes or acceptable answers
  }).filter(function(q) { return q.question.length > 0 && q.answers.length > 1 }),

  // Targets describe Assessment, Monitoring, and Control Rules recommended to
  // better manage a fishery. They may be recommended depending upon the answers
  // to Questions.
  // example output:
  // {
  //   id: '8fe14ee1-2fd8-40b4-a52d-d28023511665',
  //   spreadsheetLocation: 'Monitoring:47',
  //   type: 'Monitoring',
  //   title: 'Catch disposal records/sales docket/traceability',
  //   description: 'Across-fleet aggregated catch by species, (possibly) across-fleet aggregated effort;. Sustainability (trend analysis) - e.g. more temporal',
  //   _legacyId: 136
  // }
  targets: targets.map(function(record) {
    record.Attributes = filterAttributes(record.Attributes);
    return {
      id: uuid('target', record.TargetID),
      spreadsheetLocation: record.Reference,
      // this seems to give consistent results for categorizing targets
      type: record.Reference.split(":")[0],
      // the first attribute doesn't make for a great title in all cases, but it
      // will have to do.
      title: record.Attributes[0],
      // don't include title in description
      description: record.Attributes.slice(1).join(". "),
      _legacyId: record.TargetID
    }
  // Filter out anything that doesn't have useful attributes
  }).filter(function(t) { return t.title && t.title.length > 0 }),

  // Here I'm remapping IDs but also changing threshold values to refer to the
  // index value of a question, rather than it's text. This way uses could
  // change/reformat questions and not screw with the logic. It may be better to
  // in the future make answers an object with properties and attach criteria to
  // them to help maintain consistency.
  criteria: criteria.map(function(record) {
    var question = questions.find(function(question) {
      return uuid('question', question.QuestionID) ===
        uuid('question', record.QuestionID);
    });
    return {
      threshold: question.ValidAnswers.indexOf(record.Threshold),
      question: uuid('question', record.QuestionID),
      target: uuid('target', record.TargetID)
    }
  }),

  // Same here, remapping ids and referring to answers by index rather than
  // strings values. I've also copied over the score from the color map files.
  // The colors seem like a presentational detail that could be themed so just
  // tracking the score seems more appropriate.
  caveats: caveats.map(function(record) {
    var question = questions.find(function(question) {
      return uuid('question', question.QuestionID) ===
        uuid('question', record.QuestionID);
    });
    return {
      answer: question.ValidAnswers.indexOf(record.Answer),
      question: uuid('question', record.QuestionID),
      target: uuid('target', record.TargetID),
      score: scoreForColor(record.Color),
      note: record.Note
    }
  }),

  // store.js needs a reference to this.
  uuid: uuid

}

function scoreForColor(colorName) {
  return _.find(colorMap, function(map) {
    return map.ColorName === colorName
  }).Score;
}
