var prompt = require('prompt');
var store = require('./src/store');
var colors = require('colors');

function askQuestion() {
  prompt.start();

  var property = {
    name: 'id',
    message: 'Enter a question id, or press enter to be asked a random quesiton',
    default: 'random'
  };

  prompt.get(property, function(err, result) {
    var question;
    if (result.id == 'random') {
      question = store.randomQuestion();
    } else {
      question = store.byLegacyId('question', result.id);
    }
    if (!question) {
      console.log("Question #"+result.id+" not found.");
      askQuestion();
    } else {
      console.log(colors.bold("#" + question._legacyId + " " + question.question));
      console.log(colors.dim(question.description));
      question.answers.forEach(function(a, i) {
        console.log(i + ") " + a);
      });

      prompt.get("choice", function(err, a) {
        question.answer(a.choice || 0);
        var property = {
          name: 'yesno',
          message: 'Would you like to answer another question?',
          validator: /y[es]*|n[o]?/,
          warning: 'Must respond yes or no',
          default: 'y'
        };
        prompt.get(property, function (err, result) {
          if (result.yesno == 'y' || result.yesno == 'yes') {
            askQuestion();
          } else {
            process.exit();
          }
        });
      });
    }
  });

}

askQuestion();
