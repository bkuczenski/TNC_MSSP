"""
mssp_data_store.py

This module contains the core class for emulating the MSSP decision tool.

The constructor transforms a SpreadsheetData object into an MsspEngine object through the use of a
question_map, which is an excel spreadsheet that contains two mappings:

 1. a mapping between questions, consisting of semantic identities that tie different records together;

 2. a mapping from RGB colors to scores, which is used to assign quantitative values to notes.

Once constructed, the MsspEngine object can be used interactively to provide question prompts to a user,
collect answers, and then score the various monitoring, assessment, or control rules options.  At the moment
the scoring and evaluation is target-type-specific.

The MsspEngine can also be used to prototype administrative changes, such as adding a new question, editing
question-target mappings, or reviewing annotation relationships.

An MsspEngine object can be serialized to JSON for future development. A new MsspEngine object can also
be created by de-serializing the JSON.  This allows for interim manual revision of the MSSP content until
an admin interface is constructed.

DATA MODEL

Attributes = ElementSet
Notes = ElementSet

Questions = collection of Attributes and valid answer strings (default to Yes/No)

"""

from collections import namedtuple

from MSSP.utils import convert_reference_to_subject
from MSSP.exceptions import MsspError

searchAttributes = namedtuple('searchAttributes', ['attributes', 'questions', 'targets'])
searchNotes = namedtuple('searchNotes', ['notes', 'questions', 'targets'])

class MsspDataStore(object):
    """
    Engine for reviewing and analyzing MSSP content in its "purified" form.

    Two class methods:
     .from_spreadsheet accepts a SpreadsheetData object
     .from_json accepts a JSON file pointer


    """

    def __init__(self, attribute_set, note_set, question_enum, target_enum,
                 question_attributes, target_attributes, criteria, caveats, colormap):
        """

        :param attribute_set: an ElementSet of attributes
        :param note_set: an ElementSet of notations (scores encoded by RGB)
        :param question_enum: an ordered list of questions with persistent QuestionID
        :param target_enum: an ordered list of targets with persistent TargetID
        :param question_attributes: a DataFrame linking Questions and Attributes
        :param target_attributes: a DataFrame linking Targets and Attributes
        :param criteria: a DataFrame linking QuestionID, TargetID, answer, NoteID, score
        :param caveats: a DataFrame linking QuestionID, TargetID, threshold
        :param colormap: a DataFrame mapping RGB colors to names and scores
        :return:
        """
        self._attributes = attribute_set
        self._notes = note_set
        self._questions = question_enum
        self._targets = target_enum

        self._question_attributes = question_attributes
        self._target_attributes = target_attributes

        self._criteria = criteria
        self._caveats = caveats

        # compute 'satisfies' list from 'satisfied_by'
        [self._set_satisfies(k) for k in range(len(self._questions))]

        self.colormap = colormap  # let the user manipulate the colormap directly

    def _set_satisfies(self, satisfied_by):
        """
        Sets 'satisfies' for questions that appear in another question's 'satisfied_by'

        :param satisfied_by: index into questions enum for satisfied question
        :return: nothing
        """
        sb = self._questions[satisfied_by].satisfied_by
        if len(sb) > 0:
            for q in sb:
                self._questions[q].satisfies.add(satisfied_by)

    def _replace_field_with_answer(self, df, field='Threshold'):
        """

        :param df:
        :param field:
        :return:
        """
        def lookup(rec):
            return self._questions[rec['QuestionID']].valid_answers[rec[field]]

        df['AnswerValue'] = df.apply(lookup, axis=1)
        df.drop(field, axis=1, inplace=True)

    def _make_attr_list(self, mapping, index):
        """
        List of attributes associated with a given record
        :param mapping: self.question_attributes or self.target_attributes
        :param index:
        :return:
        """
        if mapping is self._question_attributes:
            key = 'QuestionID'
        elif mapping is self._target_attributes:
            key = 'TargetID'
        else:
            raise MsspError('Argument to _make_attr_list is not an object-attribute mapping')
        return [self._attributes[k['AttributeID']].text
                for i, k in mapping.iterrows()
                if k[key] == index]

    def _print_object(self, index, mapping):
        """
        Common functions for printing question + target records.
        :param index: the ID of the object
        :param mapping: an input to self._make_attr_list
        :return:
        """
        if mapping is self._question_attributes:
            fieldname = 'QuestionID'
            obj = self._questions[index]
            print('Question ID: %d' % index)
        else:
            fieldname = 'TargetID'
            obj = self._targets[index]
            print('Target ID: %d' % index)

        obj.attributes = [k for k in self._make_attr_list(mapping, index)]
        obj.criteria = None
        obj.caveats = None
        for k in obj.attributes:
            print(k)
        print(obj)
        criteria = self._criteria[self._criteria[fieldname] == index].copy()
        caveats = self._caveats[self._caveats[fieldname] == index].copy()
        if len(criteria) > 0:
            self._replace_field_with_answer(criteria)
            print('Has Criteria:')
            print(criteria)
            obj.criteria = criteria

        if len(caveats) > 0:
            self._replace_field_with_answer(caveats, field='Answer')
            print('Has Caveats:')
            print(caveats)
            obj.caveats = caveats

        return obj

    @staticmethod
    def _search_mapping(attrs, mapping):
        """
        Atomic search- returns records containing an attribute that matches the search term.
        :param attrs:
        :param mapping:
        :return: a set of indices into the specified record list
        """
        return set(mapping[mapping['AttributeID'].isin(attrs)][mapping.columns[1]])

    # user-facing functions begin here
    def question(self, index):
        """
        Print out a question, in terms of its attributes, possible answers, and impacted targets
        :param index: index into the question enum
        :return:
        """
        return self._print_object(index, self._question_attributes)

    def target(self, index):
        """

        :param index:
        :return:
        """
        return self._print_object(index, self._target_attributes)

    def search(self, terms, search_notes=False, match_any=False):
        """
        Find records that contain attributes [or notes] matching the search terms.  'terms' should be a single
        string or a list of strings.  If a list is provided, the search will return entries that match all terms
        (i.e. the intersection of result sets).  This can be changed to 'match_any' to return the union of result
        sets.

        By default, searches on attributes Search notes instead by specifying search_notes=True.

        By default, returns a namedtuple with names 'attributes' [or 'notes'], 'questions', and 'targets', with each
        field containing a list of indices into _attributes or _notes and the record enums.

        :param terms: string or list of strings to search on
        :param search_notes: (bool) search on notes (i.e. "caveats") instead of attributes (default False)
        :param match_any: (bool) match any search term (default False is to match all search terms)
        :return:
        """
        if isinstance(terms, basestring):
            terms = [terms]
        if match_any:
            q_results = set()
            t_results = set()
            a_results = set()
            operation = set.union
        else:
            q_results = set(range(len(self._questions)))
            t_results = set(range(len(self._targets)))
            if search_notes:
                a_results = set(range(len(self._notes)))
            else:
                a_results = set(range(len(self._attributes)))
            operation = set.intersection

        if search_notes:
            rt = searchNotes
            for term in terms:
                notes = self._notes.search(term)
                a_results = operation(a_results, notes)

                n_results = self._caveats[self._caveats['NoteID'].isin(notes)]

                q_results = operation(q_results, set(n_results['QuestionID']))
                t_results = operation(t_results, set(n_results['TargetID']))

        else:
            rt = searchAttributes
            for term in terms:
                attrs = self._attributes.search(term)
                a_results = operation(a_results, attrs)

                q_results = operation(q_results, self._search_mapping(attrs, self._question_attributes))
                t_results = operation(t_results, self._search_mapping(attrs, self._target_attributes))

        return rt(*(sorted(list(k)) for k in (a_results, q_results, t_results)))

    def serialize(self):
        """
        Serializes the MsspEngine object out to a collection of dictionaries.

        The serialization includes the following files:

         - questions.json: an enumeration of questions with spreadsheet refs, explicit _attributes, ordered valid
        answers, and list of satisfied_by keys.

         - targets.json: an enumeration of targets with spreadsheet ref and explicit _attributes

         - criteria.json: a collection of question ID, explicit answer threshold, and target ID

         - caveats.json: a collection of question ID, explicit answer, target ID, note string and note colorname

         - colormap.json: a collection of colorname, RGB value, and score (or scoring mechanism)

        They could conceivably all be placed into a single file, but that would not be useful for human-readability.

        :return: bool
        """

        questions = []
        targets = []
        criteria = []
        caveats = []
        colormap = []

        print "Creating {0} questions...".format(len(self._questions))
        for k in range(len(self._questions)):
            v = self._questions[k]
            attr_list = self._make_attr_list(self._question_attributes, k)
            if len(attr_list) == 0:
                continue
            add = {
                "QuestionID": k,
                "References": [convert_reference_to_subject(i) for i in v.references],
                "ValidAnswers": v.valid_answers,
                "Attributes": attr_list
            }
            if len(v.satisfied_by) > 0:
                add["SatisfiedBy"] = list(v.satisfied_by)
            questions.append(add)

        print "Creating {0} targets...".format(len(self._targets))
        for k in range(len(self._targets)):
            v = self._targets[k]
            attr_list = self._make_attr_list(self._target_attributes, k)
            if len(attr_list) == 0:
                continue
            add = {
                "TargetID": k,
                "Reference": convert_reference_to_subject(v.reference()),
                "Attributes": attr_list
            }
            targets.append(add)

        print "Creating {0} criteria...".format(len(self._criteria))
        for i, k in self._criteria.iterrows():
            threshold = self._questions[k['QuestionID']].valid_answers[k['Threshold']]
            add = {
                "QuestionID": k['QuestionID'],
                "Threshold": threshold,
                "TargetID": k['TargetID']
            }
            criteria.append(add)

        print "Creating {0} caveats...".format(len(self._caveats))
        for i, k in self._caveats.iterrows():
            answer = self._questions[k['QuestionID']].valid_answers[k['Answer']]
            note = self._notes[k['NoteID']]
            color = self.colormap[self.colormap['RGB'] == note.fill_color]['ColorName']
            if len(color) < 1:
                raise MsspError
            add = {
                "QuestionID": k['QuestionID'],
                "Answer": answer,
                "TargetID": k['TargetID'],
                "Color": color.iloc[0],
                "Note": note.text
            }
            caveats.append(add)

        print "Creating colormap..."
        for i, k in self.colormap.iterrows():
            add = {
                "RGB": k['RGB'],
                "Color": k['ColorName'],
                "Score": k['Score']
            }
            colormap.append(add)

        json_out = {
            "colormap": colormap,
            "questions": questions,
            "targets": targets,
            "criteria": criteria,
            "caveats": caveats
        }
        return json_out
