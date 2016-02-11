"""
mssp_engine.py

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

import pandas as pd
from MSSP.utils import defaultdir, convert_reference_to_subject
from MSSP.exceptions import MsspError


def indices(vec, func):
    """
    matlab-style find, returns indices in list where func is true.
    thanks to http://stackoverflow.com/questions/5957470/
    :param vec:
    :param func: a function that returns a bool
    :return:
    """
    return [i for (i, val) in enumerate(vec) if func(val)]


def is_yes(answer):
    return answer in ('y', 'Y', 'yes', 'YES', 'Yes', 'if yes', 'if Yes', 'if YES', 'IF YES')


def is_no(answer):
    return answer in ('n', 'N', 'no', 'NO', 'No', 'if no', 'if No', 'if NO', 'IF NO', 'if not', 'if Not')


def is_yes_or_no(answer):
    return is_yes(answer) | is_no(answer)


def cast_answer(text):
    if is_yes(text):
        return 'Yes'
    elif is_no(text):
        return 'No'
    else:
        return text


def useful_answers(answer_list):
    """
    Returns true if answer_list contains content-ful answers that differ substantially from the
    'yes/no' default
    :param answer_list: list of discovered answers from spreadsheet
    :return: bool - True indicates answer_list contains answers that are meaningfully different
    from yes/no; False indicates answer_list is either empty or equivalent to yes/no
    """
    if len(answer_list) == 0:
        return False
    if all([is_yes_or_no(k) for k in answer_list]):
        return False
    return True


class MsspQuestion(object):
    """
    An MsspQuestion is an aggregation that represents one or more spreadsheet questions.

    """
    def __init__(self):
        """
        Create an MsspQuestion from an existing
        :return: an empty MsspQuestion
        """
        self.references = []
        self.valid_answers = ['No', 'Yes']
        self.default_answers = True
        self.satisfied_by = set()

    def append(self, question, q_dict):
        """
        Add contents of a Question object to the MsspQuestion.  If Question's valid answers are non-meaningless,
        replace default answers with import answers, or merge with non-default answers.
        :param question: a MSSP.records.Question object
        :param q_dict: a mapping of spreadsheet refs into question enum
        :return: none
        """
        # handle reference
        self.references.append((question.selector, question.record))

        # handle valid answers
        valid_answers = question.valid_answers.keys()

        if useful_answers(valid_answers):
            if self.default_answers:
                # replace default answers with supplied answers
                # note: this will fail for questions that have both "Yes / No" and other valid answers -
                # Y/N will get squashed. so don't do that.
                self.valid_answers = valid_answers
                self.default_answers = False
            else:
                # add supplied answers to existing answers
                for item in valid_answers:
                    if item not in self.valid_answers:
                        self.valid_answers.append(item)

        # handle satisfied_by
        for ref in question.satisfied_by:
            self.satisfied_by.add(q_dict[ref])  # add index into question enum


class MsspTarget(object):
    def __init__(self, target):
        """

        :param target:
        :return:
        """
        self.type = target.selector
        self.record = target.record

    def reference(self):
        return (self.type, self.record)

    def references(self):
        return [self.reference()]


class MsspEngine(object):
    """
    Engine for reviewing and analyzing MSSP content in its "purified" form.

    Two class methods:
     .from_spreadsheet accepts a SpreadsheetData object
     .from_json accepts a JSON file pointer


    """

    def __init__(self, attribute_set, note_set, question_enum, target_enum,
                 question_attributes, target_attributes, criteria, caveats, colormap):
        self.attributes = attribute_set
        self.notes = note_set
        self.questions = question_enum
        self.targets = target_enum

        self.question_attributes = question_attributes
        self.target_attributes = target_attributes

        self.criteria = criteria
        self.caveats = caveats

        self.colormap = colormap

    @classmethod
    def from_spreadsheet(cls, spreadsheet_data):
        """

        :param spreadsheet_data:
        :return:
        """
        attribute_set = spreadsheet_data.Attributes
        note_set = spreadsheet_data.Notations

        t_a_targets = []
        t_a_attrs = []

        q_a_questions = []
        q_a_attrs = []

        cri_questions = []
        cri_thresholds = []
        cri_targets = []

        cav_questions = []
        cav_targets = []
        cav_answers = []
        cav_notes = []

        # create mapping of dict keys to series
        q_index = 0
        q_dict = dict()

        questions = spreadsheet_data.Questions.iterkeys()

        for k in sorted(questions):
            if k not in q_dict:
                # if it's not mapped, map it and all its synonyms
                q_dict[k] = q_index
                v = spreadsheet_data.Questions[k]
                if len(v.synonyms) > 0:
                    for syn in v.synonyms:
                        q_dict[syn] = q_index
                q_index += 1
            else:
                # already in the dict- nothing to do
                pass

        # create target_enum
        target_enum = []
        t_dict = dict()

        targets = spreadsheet_data.Targets.iterkeys()

        for k in sorted(targets):
            t_index = len(target_enum)
            v = spreadsheet_data.Targets[k]
            target_enum.append(MsspTarget(v))
            t_dict[k] = t_index
            for a in v.attrs:
                t_a_targets.append(t_index)
                t_a_attrs.append(attribute_set.get_index(a))

        # create question_enum
        question_enum = []
        for i in range(0, q_index):
            question_enum.append(MsspQuestion())

        # populate question_enum, criteria, caveats
        for k, v in spreadsheet_data.Questions.iteritems():
            q_i = q_dict[k]
            question_enum[q_i].append(v, q_dict)
            my_valid_answers = question_enum[q_i].valid_answers

            for attr in v.attrs:
                q_a_questions.append(q_i)
                q_a_attrs.append(attribute_set.get_index(attr))

            for cross_index, element in v.criteria_mappings:
                # criteria_mappings is (cross-index, element)
                # lookup target index
                t_i = t_dict[(v.selector, cross_index)]
                # lookup threshold
                answer = cast_answer(element.text)  # convert to 'Yes' / 'No' if applicable
                thresh = indices(my_valid_answers, lambda z: answer == z)
                if len(thresh) == 0:
                    print "QuestionID {0}, TargetID {1}, text {2}: no threshold found.".format(
                        q_i, t_i, element.text)
                    thresh = [None]

                cri_questions.append(q_i)
                cri_targets.append(t_i)
                cri_thresholds.append(thresh[0])

            for answer, mapping in v.caveat_mappings:
                # caveat_mappings is (answer, (cross-index, element))
                cross_index, element = mapping
                # lookup target index
                t_i = t_dict[(v.selector, cross_index)]
                # lookup answer sense
                answer = cast_answer(answer)  # convert to 'Yes' / 'No' if applicable
                ans_i = indices(my_valid_answers, lambda z: answer == z)
                n_i = note_set.get_index(element)

                cav_questions.append(q_i)
                cav_targets.append(t_i)
                if len(ans_i) > 0:
                    cav_answers.append(ans_i[0])
                else:
                    print "QuestionID {0}, TargetID {1}, valid answer '{2}' unparsed.".format(
                        q_i, t_i, answer)
                    cav_answers.append(None)
                cav_notes.append(n_i)

        # create pandas tables
        question_attributes = pd.DataFrame(
            {
                "QuestionID": q_a_questions,
                "AttributeID": q_a_attrs
            }
        )

        target_attributes = pd.DataFrame(
            {
                "TargetID": t_a_targets,
                "AttributeID": t_a_attrs
            }
        )

        criteria = pd.DataFrame(
            {
                "QuestionID": cri_questions,
                "Threshold": cri_thresholds,
                "TargetID": cri_targets
            }
        )

        caveats = pd.DataFrame(
            {
                "QuestionID": cav_questions,
                "TargetID": cav_targets,
                "Answer": cav_answers,
                "NoteID": cav_notes
            }
        )

        return cls(attribute_set, note_set, question_enum, target_enum,
                   question_attributes, target_attributes, criteria, caveats,
                   spreadsheet_data.colormap)

    def make_attr_list(self, mapping, index):
        """
        List of attributes associated with a given record
        :param mapping: self.question_attributes or self.target_attributes
        :param index:
        :return:
        """
        if mapping is self.question_attributes:
            key = 'QuestionID'
        elif mapping is self.target_attributes:
            key = 'TargetID'
        else:
            raise MsspError
        return [self.attributes[k['AttributeID']].text
                for i, k in mapping.iterrows()
                if k[key] == index]

    def serialize(self, out=None):
        """
        Serializes the MsspEngine object out to a collection of dictionaries.

        The serialization includes the following files:

         - questions.json: an enumeration of questions with spreadsheet refs, explicit attributes, ordered valid
        answers, and list of satisfied_by keys.

         - targets.json: an enumeration of targets with spreadsheet ref and explicit attributes

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

        print "Creating {0} questions...".format(len(self.questions))
        for k in range(len(self.questions)):
            v = self.questions[k]
            attr_list = self.make_attr_list(self.question_attributes, k)
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

        print "Creating {0} targets...".format(len(self.targets))
        for k in range(len(self.targets)):
            v = self.targets[k]
            attr_list = self.make_attr_list(self.target_attributes, k)
            if len(attr_list) == 0:
                continue
            add = {
                "TargetID": k,
                "Reference": convert_reference_to_subject(v.reference()),
                "Attributes": attr_list
            }
            targets.append(add)

        print "Creating {0} criteria...".format(len(self.criteria))
        for i, k in self.criteria.iterrows():
            threshold = self.questions[k['QuestionID']].valid_answers[k['Threshold']]
            add = {
                "QuestionID": k['QuestionID'],
                "Threshold": threshold,
                "TargetID": k['TargetID']
            }
            criteria.append(add)

        print "Creating {0} caveats...".format(len(self.caveats))
        for i, k in self.caveats.iterrows():
            answer = self.questions[k['QuestionID']].valid_answers[k['Answer']]
            note = self.notes[k['NoteID']]
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

    @staticmethod
    def write_json(json_out, out=None, onefile=False):
        """
        Routine to write json output to file(s)
        :param json_out: the output of serialize()
        :param out: directory name relative to defaultdir to use for writing files.
        :param onefile: (bool) whether to write all content to a single json file (default: false)
        :return:
        """
        import os
        import json

        write_file = 'mssp_engine.json'
        if out is None:
            write_dir = os.path.join(defaultdir, 'JSON_OUT')
        else:
            if os.path.isabs(out):
                write_dir = out
            else:
                write_dir = os.path.join(defaultdir, out)

        if not os.path.exists(write_dir):
            os.makedirs(write_dir)

        if onefile:
            f = open(os.path.join(write_dir, write_file), mode='w')
            f.write(json.dumps(json_out, indent=4))
            f.close()
            print "Output written as {0}.".format(write_file)
        else:
            for i in ('colormap', 'questions', 'targets', 'criteria', 'caveats'):
                f = open(os.path.join(write_dir, i + '.json'), mode='w')
                f.write(json.dumps(json_out[i], indent=4))
                f.close()
            print "Output written to folder {0}.".format(write_dir)
        return True



