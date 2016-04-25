# MSSP JSON Javascript Client

The easiest way for me to make sense of the json schema turned out to be to
build something simple with it. index.js contains my attempt to restructure the
json to be a little easier to work with, and cli.js can be run to prompt a user
to answer random (or specific) questions in the command line, and get some
feedback about the various targets based on the answer. _This format of
answer-question-get-feedback on a per-question basis would not be how an app for
fisheries managers would be structured, but it is useful for debugging_.

## Installation

You'll need a modern version of node.js to run this, let's say 0.12 and up.
There are a lot of instructions online on how to get node running, but my
recommendation would be to install [nvm](https://github.com/creationix/nvm)
so you can easily run multiple versions.

Once node is installed, run the following:

```
cd ./json/client/
npm install
node cli.js
```

![cli.js](https://s3-us-west-2.amazonaws.com/tnc-mssp/Screen+Shot+2016-04-20+at+12.30.21+PM.png)


## Notes and Questions

### Questions about schema

My basic understanding of this workflow is that users answer (all) questions,
and then guidance will be presented to the user as some sort of
report. That report will include a list of Targets that are filtered based on
criteria and caveats. For each target, presumably we'll show all related
caveats, with a byline explaining "because you answered x to question y".

  1. _Is that basic understanding correct?_

  2. _There are many questions where depending on the answer, you may have
     multiple related Targets to show based on the criteria, but there are no
     caveats to show. Is that a bug, or do these targets just represent
     unqualified recommendations for fisheries management measures they should
     look at? Right now my cli.js script assumes they are still relevant to
     show, even without caveats._

  Targets are filtered only based on criteria. 

  Caveats can be thought of in two ways: 

   - (before questions are asked) a caveat indicates that a particular *question* is relevant to a target; 
   - (after questions are answered) the answer indicates whether a particular *note* applies.

  3. _Similarly, there are situations where there is a caveat matches a
     question and answer, but there are no matching criteria. I just assumed in my script
     that the related Target should be shown even without matching any criteria.
     Is that correct? An example of this is Question 49, where caveat 8 matches
     but there are no related criteria._
  4. _I really don't understand the role of `SatisfiedBy` on Questions. Aren't
     all questions asked? Can we just drop Questions that are satisfied by
     others?_

  Questions that are SatisfiedBy others should not get asked-- they're kind of "hidden questions." The reason they
  exist is that (strictly on the Assessment worksheet) there are many targets that can use "any of the above" as an input.
  Technically speaking, the "answer" to a SatisfiedBy question should be the maximum answer value of the questions that
  satisfy it.

  5. _I categorized targets by taking part of `Target.References`. Does that look
     right? It puts them in **Assessment**, **Control Rules**, or **Monitoring**._

  That's right. Targets were supposed to have a 'type' property that was one of those three values, but it looks like I forgot 
  to put that in.

  6. _On that topic, do users choose to answer a questionnaire relating to
     Assessment, Monitoring or Control Rules, or do they answer all questions?_

  I think the first thing the UI should ask is- which one of those categories is of interest, and then proceed to ask the
  questions that have implications on those targets, beginning with criteria questions (except ControlRules don't have any
  criteria questions).  I think in the controlRules case all the questions with controlrules targets should be asked.

  In any case, the UI should remember the answers because some questions apply to multiple target types.

### Data cleaning issues and possible bugs

  1. _There are many questions with only a single valid answer, or even no valid
     answer. I'm not sure what to do about that. Right now I just drop them._

  The answers are auto-detected right now-- basically any answer encountered in the spreadsheet is added as
  a 'valid answer'. The answers are also out of order- added in the order encountered.  Expect this to be fixed in the JSON by
  the time you start "for real."

  2. _Similarly, there are a lot of null and empty string values in the
     Attributes for both `Question` and `Target`. I filtered them out but for
     those questions that have *no* text, I'm not sure how we're supposed to
     even fill them in. For now, I drop them._

  There shouldn't be any questions with "no" attributes, except possibly satisfiedBy questions.  There could be QuestionIDs with no content, 
  I suppose- in which case, yes they should be dropped.  I am fine with moving to UUIDs eventually, but for now I have to refer to questions by
  questionID in order to curate them via a python shell, so we can't do that yet.  Attributes and Notes can have UUIDs right away, since they are not supposed to have publicly visible IDs. In retrospect I could have done that.

  3. _In general, the text for all these things is super vague. There's probably
     not much **we** can do about that though._

  I think an interface for the scientific staff to edit attributes + notes is of early importance.  There is a caution here-- by design, attributes and notes are supposed to be shared across questions so that the staff can edit them in only one place.  But the UI will have to allow users to specify whether their edit applies to only ONE question/target (in which case they are really creating a new attribute and not editing an existing one) or to all instances (which is how the data model is setup).

  4. _Question.answers (for example 63) seem to be in arbitrary order. Is it
     possible to extract them in a better order directly from the spreadsheet,
     or are they just out of order there as well? A simple array#sort doesn't do
     it but there might be a way to make some sort of heuristic function._

  No, no heuristics. The scientific staff need to specify the order manually and exhaustively. THat's just grunt work. Maybe we will be able to do that during the workshop.

  Not coincidentally, I've been writing tools to re-order answers in python. Like I said above, expect that to be fixed by the end of May.

### Schema Changes

I altered the json schema in my "model" represented in index.js to look like them
following.

![schema](http://s3-us-west-2.amazonaws.com/tnc-mssp/Screen+Shot+2016-04-20+at+1.24.47+PM.png)

`client/index.js` has good inline comments, but in summary:

  1. _I dropped the color mappings in my schema and instead stored the score on
     caveat. Color seems like a more presentational aspect we'll want to tweak
     outside the data model._

  Agreed. The colors were there because that's how the spreadsheet authors encoded the scores. 

  2. _I changed some of the attribute names to be more "idiomatic" javascript.
     Mostly a personal thing. Same with the UUIDs, possibly a little more
     durable as we go from one system to another._
  3. _Attributes are really hard to work with. I instead pulled text out into
     `question`, `title`, and `description` fields._
 
  Okay-- although how did you figure out which is which? A title must only apply to a single target, but many attributes apply to many targets.  For instance, "Biophysical/life history" or "1 Catch Limits"

  You did pick up on the "fragility" of the answer reference being to literal text in the JSON. That was by design, because I anticipated editing the `questions.json` directly to re-order answers. In my code currently, I go through the `json` files and create a new attribute for each unique attribute-text string encountered, and map all the questions/targets that mention that text string to that attribute.  Same with notes.  We don't want to end up with 435 identical notes that all read "Will require strong community leadership", because the whole point is for the users to be able to edit them all at once.  For that reason it may be better for me to give Attributes and Notes UUIDs and for us to start using them.

  4. _`Criteria.threshold` is a tough one. In the current JSON the text of
     answers are referenced. This could be really brittle since the answer text
     will likely be changed/reformatted. In my script I instead reference the
     index of the answer in the question. That way if the text changes the logic
     will still work. Well, that is unless the questions are re-ordered. Not a
     great solution. A better solution might be to make answers a first-class
     object and nest thresholds and criteria directly within them. That way
     there's no logic required to keep the data structure consistent, and it
     would be easier to construct an admin interface out of this sort of
     structure anyways. I didn't want to go too far down this road before
     verifying with you (Brandon) that I understand other parts of the system, but I'm thinking it
     would look something like this:_
     ![](http://s3-us-west-2.amazonaws.com/tnc-mssp/Screen+Shot+2016-04-20+at+1.43.37+PM.png)

  This is all correct- The criteria threshold is supposed to be an index, and the index should be determined at read time.  It has to do with the assumptions about where the edits are being made.  I wanted to assume that `questions.json` and `targets.json` would be editable. But in retrospect it's not safe to edit any of the json. Had I realized that I would have formatted them differently (and there's still time!)

  In my codebase, I now have methods to 'reorder answers', which requires re-mapping all the criteria and caveats tables. I think this is essentially inevitable. But it is possible that re-ordering answers will no longer be required by the time you officially pick up the mantle.

     _That then begs the question, maybe Caveat can just be a subclass of Criteria,
     with a score that affects presentation of a note. Something to think about._

  This could be done- with the observation that criteria don't have associated notes, whereas caveats do.
