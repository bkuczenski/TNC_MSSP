from MSSP.mssp_data_store import MsspDataStore
from MSSP.semantic_elements import SemanticElementSet
from MSSP.mssp_objects import MsspQuestion, MsspTarget
from MSSP.importers import indices
from MSSP.json_exch import read_json
import uuid

import pandas as pd


class JsonImporter(MsspDataStore):

    def __init__(self, file_ref):
        """
        Constructs an MsspDataStore object from a collection of JSON dictionaries.
        :param file_ref: file or directory containing the json data
        :return: an MsspDataStore
        """
        json_in = read_json(file_ref)

        # first thing to do is build the attribute and note lists

        colormap = pd.DataFrame(json_in['colormap'])
        attribute_set = SemanticElementSet.from_json(json_in['attributes'])
        note_set = SemanticElementSet.from_json(json_in['notes'], colormap=colormap)

        question_enum = [None] * (1 + max([i['QuestionID'] for i in json_in['questions']]))
        target_enum = [None] * (1 + max([i['TargetID'] for i in json_in['targets']]))

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

        for t in json_in['targets']:
            # need to preserve IDs because of criteria and caveat maps
            t_index = t['TargetID']
            try:
                target_enum[t_index] = MsspTarget.from_json(t)
            except IndexError:
                print 'Index error at {0}'.format(t_index)
                print t

            # add _attributes to element set and build mapping
            for a in t['Attributes']:
                # a is a text string
                t_a_targets.append(t_index)
                t_a_attrs.append(uuid.UUID(a))

        for q in json_in['questions']:
            # need to preserve IDs because of criteria and caveat maps
            q_index = q['QuestionID']
            question_enum[q_index] = MsspQuestion.from_json(q)

            # add _attributes to element set and build mapping
            for a in q['Attributes']:
                # a is a text string
                q_a_questions.append(q_index)
                q_a_attrs.append(uuid.UUID(a))

        for cri in json_in['criteria']:
            # the threshold is a literal entry from the question's valid_answers-
            # needs to be converted into an index
            q_index = cri['QuestionID']
            t_index = cri['TargetID']
            thresh = indices(question_enum[q_index].valid_answers, lambda k: cri['Threshold'] == k)
            if len(thresh) == 0:
                    print "QuestionID {0}, TargetID {1}, text {2}: no threshold found.".format(
                        q_index, t_index, cri['Threshold'])
                    thresh = [None]

            cri_questions.append(q_index)
            cri_targets.append(t_index)
            cri_thresholds.append(thresh[0])

        for cav in json_in['caveats']:
            # the answer is a literal entry from the question's valid answers-
            # needs to be converted into an index.
            # the color needs to be converted into a colormap RGB.
            q_index = cav['QuestionID']
            t_index = cav['TargetID']

            note_id = uuid.UUID(cav['NoteID'])

            if question_enum[q_index] is None:
                print "Question {0} is none!".format(q_index)
                ans_i = [None]
            else:
                ans_i = indices(question_enum[q_index].valid_answers, lambda k: cav['Answer'] == k)

            if len(ans_i) == 0:
                print "QuestionID {0}, TargetID {1}, valid answer '{2}' unparsed.".format(
                        q_index, t_index, cav['Answer'])
                ans_i = [None]

            cav_questions.append(q_index)
            cav_targets.append(t_index)
            cav_answers.append(ans_i[0])
            cav_notes.append(note_id)

        # create pandas tables
        question_attributes = pd.DataFrame(
            {
                "QuestionID": q_a_questions,
                "AttributeID": q_a_attrs
            }
            ).drop_duplicates()

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

        super(JsonImporter, self).__init__(
            attribute_set, note_set, question_enum, target_enum,
            question_attributes, target_attributes, criteria, caveats,
            colormap)
