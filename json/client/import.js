// Usage:
// node import.js
// or
// node import.js /path/to/data_dir
// node import.js /path/to/data_dir path/to/output.json

const path = require('path');
const fs = require('fs');
const camelCase = require('camelcase');

const DATA_PATH = process.argv[2] || __dirname;
const OUTPUT_PATH = process.argv[3] || path.join(__dirname, "qdd.json");

const ATTRS = require(path.join(DATA_PATH, "attributes.json"));
const CAVEATS = require(path.join(DATA_PATH, "caveats.json"));
const CRITERIA = require(path.join(DATA_PATH, "criteria.json"));
const COLORMAP = require(path.join(DATA_PATH, "colormap.json"));
const NOTES = require(path.join(DATA_PATH, "notes.json"));
const QUESTIONS = require(path.join(DATA_PATH, "questions.json"));
const TARGETS = require(path.join(DATA_PATH, "targets.json"));

var i = 1;
var existingIds = {};

function idGenerator() {
  return i++;
}

function id(existingId, type) {
  var hash = type + existingId;
  if (existingId !== undefined) {
    if (hash in existingIds) {
      return existingIds[hash];
    } else {
      existingIds[hash] = idGenerator();
      return existingIds[hash];
    }
  } else {
    return idGenerator();
  }
}



let attributesLookup = {};
ATTRS.Elements.forEach((attr) => {
  attributesLookup[attr.AttributeID] = attr.AttributeText;
});

let scoreLookup = {};
COLORMAP.forEach((colormap) => {
  scoreLookup[colormap.ColorName] = colormap.Score;
});

let notesLookup = {};
NOTES.Elements.forEach((note) => {
  notesLookup[note.NoteID] = {
    score: scoreLookup[note.NoteColor],
    title: note.NoteText
  }
});

let targets = TARGETS.map((target) => {
  return {
    id: id(target.TargetID, "target"),
    title: attributesLookup[target.Title] || target.Attributes[0],
    description: target.Attributes.map((attr) => attributesLookup[attr]).join(". "),
    section: camelCase(target.Reference.split(":")[0])
  }
});

let targetById = {};
targets.forEach((target) => targetById[target.id] = target);


let processAnswers = (answers) => {
  return answers.filter((a) => a)
    .map((a) => a.replace(/\d\s*[-]*\s*/, ""))
    .filter((a) => a.length && a.length > 0)
    .map((a) => {
      return {
        id: id(),
        title: a
      }
    });
}

let splitBySection = (items) => {
  return {
    monitoring: items.filter((item) => targetById[item.target].section === "monitoring"),
    assessment: items.filter((item) => targetById[item.target].section === "assessment"),
    controlRules: items.filter((item) => targetById[item.target].section === "controlRules")
  }
}

let questions = QUESTIONS.map((q) => {
  let answers = processAnswers(q.ValidAnswers);
  let criteria = CRITERIA.filter((c) => c.QuestionID === q.QuestionID)
    .map((c) => {
      let index = q.ValidAnswers.indexOf(c.Threshold);
      if (index < 0) {
        throw new Error("Valid answer not found!");
      }
      return {
        id: id(),
        target: id(c.TargetID, "target"),
        answers: answers.slice(index).map((a) => a.id)
      }
    });
  let criteriaBySection = splitBySection(criteria);

  let caveatsForQuestion = CAVEATS.filter((cv) => cv.QuestionID === q.QuestionID)
  let caveats = [];
  if (caveatsForQuestion.length) {
    targets.forEach((t) => {
      // get all notes where question and target match
      let notes = [];
      let caveatsForTarget = caveatsForQuestion.filter(function(cv){
        return id(cv.TargetID, "target") === t.id
      });
      caveatsForTarget.forEach((caveat) => {
        notes = notes.concat(caveat.Answers.filter((a) => "NoteID" in a));
      });
      // de-dupe so that a caveat/note can apply to more than one answer
      let notesById = {};
      let answersByNote = {};
      notes.forEach((n) => {
        if (!(n.NoteID in answersByNote)) {
          answersByNote[n.NoteID] = [];
        }
        if (n.Answer) {
          answersByNote[n.NoteID].push(n.Answer);
        }
      });
      // console.log(answersByNote);
      for (var noteId in answersByNote) {
        caveats.push({
          id: id(),
          title: notesLookup[noteId].title,
          score: notesLookup[noteId].score,
          target: t.id,
          answers: answersByNote[noteId].map((s) => answers.find((a) => a.title === s).id)
        })
      }
    });
  }

  let caveatsBySection = splitBySection(caveats);

  // let caveats = CAVEATS.filter((c) => c.QuestionID === q.QuestionID)
  //   .map((c) => {
  //     return {
  //       target: c.TargetID,
  //
  //     }
  //   });

  if (caveatsBySection['monitoring'].length && criteriaBySection['monitoring'].length) {
    throw new Error("Both criteria and caveats specified for monitoring in question: " + attributesLookup[q.Title]);
  }
  if (caveatsBySection['assessment'].length && criteriaBySection['assessment'].length) {
    throw new Error("Both criteria and caveats specified for assessment in question: " + attributesLookup[q.Title]);
  }
  if (caveatsBySection['controlRules'].length && criteriaBySection['controlRules'].length) {
    throw new Error("Both criteria and caveats specified for controlRules in question: " + attributesLookup[q.Title]);
  }
  var monitoringType = "none";
  if (caveatsBySection['monitoring'].length) {
    monitoringType = "caveats";
  } else if (criteriaBySection['monitoring'].length) {
    monitoringType = "criteria";
  }
  var assessmentType = "none";
  if (caveatsBySection['assessment'].length) {
    assessmentType = "caveats";
  } else if (criteriaBySection['assessment'].length) {
    assessmentType = "criteria";
  }
  var controlRulesType = "none";
  if (caveatsBySection['controlRules'].length) {
    controlRulesType = "caveats";
  } else if (criteriaBySection['controlRules'].length) {
    controlRulesType = "criteria";
  }


  return {
    id: id(q.QuestionID, 'question'),
    title: attributesLookup[q.Title],
    description: q.Attributes.map((attr) => attributesLookup[attr]).join(". "),
    category: attributesLookup[q.Category],
    answers: answers,
    domainLogic: {
      monitoring: {
        type: monitoringType,
        criteria: criteriaBySection['monitoring'],
        caveats: caveatsBySection['monitoring']
      },
      assessment: {
        type: assessmentType,
        criteria: criteriaBySection['assessment'],
        caveats: caveatsBySection['assessment']
      },
      controlRules: {
        type: controlRulesType,
        criteria: criteriaBySection['controlRules'],
        caveats: caveatsBySection['controlRules']
      }
    }
  }
});

let jsonString = JSON.stringify({
  targets: targets,
  questions: questions
}, null, true);

fs.writeFileSync(OUTPUT_PATH, jsonString);
