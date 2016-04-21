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

  1. Is that basic understanding correct?
  2. There are many questions where depending on the answer, you may have
     multiple related Targets to show based on the criteria, but there are no
     caveats to show. Is that a bug, or do these targets just represent
     unqualified recommendations for fisheries management measures they should
     look at? Right now my cli.js script assumes they are still relevant to
     show, even without caveats.
  3. Similarly, there are situations where there is a caveat matches a
     question and answer, but there are no matching criteria. I just assumed in my script
     that the related Target should be shown even without matching any criteria.
     Is that correct? An example of this is Question 49, where caveat 8 matches
     but there are no related criteria.
  4. I really don't understand the role of `SatisfiedBy` on Questions. Aren't
     all questions asked? Can we just drop Questions that are satisfied by
     others?
  5. I categorized targets by taking part of `Target.References`. Does that look
     right? It puts them in _Assessment_, _Control Rules_, or _Monitoring_.
  6. On that topic, do users choose to answer a questionnaire relating to
     Assessment, Monitoring or Control Rules, or do they answer all questions?


### Data cleaning issues and possible bugs

  1. There are many questions with only a single valid answer, or even no valid
     answer. I'm not sure what to do about that. Right now I just drop them.
  2. Similarly, there are a lot of null and empty string values in the
     Attributes for both `Question` and `Target`. I filtered them out but for
     those questions that have *no* text, I'm not sure how we're supposed to
     even fill them in. For now, I drop them.
  3. In general, the text for all these things is super vague. There's probably
     not much _we_ can do about that though.
  4. Question.answers (for example 63) seem to be in arbitrary order. Is it
     possible to extract them in a better order directly from the spreadsheet,
     or are they just out of order there as well? A simple array#sort doesn't do
     it but there might be a way to make some sort of heuristic function.


### Schema Changes

I altered the json schema in my "model" represented in index.js to look like them
following.

![schema](http://s3-us-west-2.amazonaws.com/tnc-mssp/Screen+Shot+2016-04-20+at+1.24.47+PM.png)

`client/index.js` has good inline comments, but in summary:

  1. I dropped the color mappings in my schema and instead stored the score on
     caveat. Color seems like a more presentational aspect we'll want to tweak
     outside the data model.
  2. I changed some of the attribute names to be more "idiomatic" javascript.
     Mostly a personal thing. Same with the UUIDs, possibly a little more
     durable as we go from one system to another.
  3. Attributes are really hard to work with. I instead pulled text out into
     `question`, `title`, and `description` fields.
  4. `Criteria.threshold` is a tough one. In the current JSON the text of
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
     would look something like this:
     ![](http://s3-us-west-2.amazonaws.com/tnc-mssp/Screen+Shot+2016-04-20+at+1.43.37+PM.png)

     That then begs the question, maybe Caveat can just be a subclass of Criteria,
     with a score that affects presentation of a note. Something to think about.
