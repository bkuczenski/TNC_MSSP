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

from MSSP.records import Question, Target
import pandas as pd
from MSSP.utils import *


def is_yes(answer):
    return answer in ('y', 'Y', 'yes', 'YES', 'Yes', 'if yes', 'if Yes', 'if YES', 'IF YES', True)


def is_no(answer):
    return answer in ('n', 'N', 'no', 'NO', 'No', 'if no', 'if No', 'if NO', 'IF NO', False, 'if not', 'if Not')


def is_yes_or_no(answer):
    return is_yes(answer) | is_no(answer)


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
        :param question:
        :param id: the question's index in the q
        :return:
        """
        self.references = []
        self.valid_answers = set(['No', 'Yes'])
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
        self.references.append((question.sel, question.record))

        # handle valid answers
        valid_answers = set(question.valid_answers.keys())

        if useful_answers(valid_answers):
            if self.default_answers:
                # replace default answers with supplied answers
                self.valid_answers = valid_answers
                self.default_answers = False
            else:
                # add supplied answers to existing answers
                self.valid_answers.union(valid_answers)

        # handle satisfied_by
        for ref in question.satisfied_by:
            self.satisfied_by.add(q_dict[ref])  # add index into question enum


class MsspEngine(object):
    """
    Engine for reviewing and analyzing MSSP content in its "purified" form.

    Two class methods:
     .from_spreadsheet accepts a SpreadsheetData object and a QuestionMap file pointer
     .from_json accepts a JSON file pointer


    """

    @staticmethod
    def index_for_synonym(subj, obj, mapping):
        if subj in mapping:
            return mapping[subj]
        if obj in mapping:
            return mapping[obj]
        return None


    @classmethod
    def from_spreadsheet(cls, spreadsheet_data, qmap_file=None):
        """

        :param spreadsheet_data:
        :param qmap_file:
        :return:
        """
        attribute_set = spreadsheet_data.Attributes
        note_set = spreadsheet_data.Notations

        q_a_questions = []
        q_a_attrs = []

        t_a_targets = []
        t_a_attrs = []

        cri_questions = []
        cri_thresholds = []
        cri_targets = []

        cav_questions = []
        cav_targets = []
        cav_scores = []
        cav_notes = []

        # create mapping of dict keys to series
        q_index = 0
        q_dict = dict()

        for k, v in spreadsheet_data.Questions.iteritems():
            if k not in q_dict:
                # if it's not mapped, map it and all its synonyms
                q_dict[k] = q_index
                if len(v.synonyms) > 0:
                    for syn in v.synonyms:
                        q_dict[syn] = q_index
                q_index += 1
            else:
                # already in the dict- nothing to do
                pass

        # create question_enum
        question_enum = []
        for i in range(0,q_index):
            question_enum.append(MsspQuestion())

        # populate question_enum
        for k, v in spreadsheet_data.Questions.iteritems():



        # create target_enum
        target_enum = []
        t_dict = dict()

        for k, v in spreadsheet_data.Targets.iteritems():
            target_enum.append( { 'type': v.selector})
            t_index = len(target_enum)
            t_dict[k] = t_index
            for a in v.attrs:
                t_a_targets.append(t_index)
                t_a_attrs.append(attribute_set.get_index(a))







        return cls(attribute_set, note_set, question_enum, target_enum,
                   question_attributes, target_attributes, criteria, caveats,
                   spreadsheet_data.colormap)


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



