from MSSP.mssp_data_store import MsspDataStore
from MSSP.mssp_objects import MsspQuestion, MsspTarget, cast_answer
from MSSP.importers import indices
from MSSP.spreadsheet_data import load_default_set
from MSSP.semantic_elements import SemanticElementSet

import pandas as pd


class XlsImporter(MsspDataStore):
    def __init__(self):
        """

        :return:
        """
        spreadsheet_data = load_default_set()  # TODO: make this flexible

        attribute_set = SemanticElementSet.from_element_set(spreadsheet_data.Attributes)
        note_set = SemanticElementSet.from_element_set(spreadsheet_data.Notations)

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
            my_valid_answers = [cast_answer(ans) for ans in question_enum[q_i].valid_answers]

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
                    print "  valid answers: %s" % my_valid_answers
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
                    print "QuestionID {0}, TargetID {1}, cast answer '{2}' unparsed.".format(
                        q_i, t_i, answer)
                    print "  valid answers: %s" % my_valid_answers
                    cav_answers.append(None)
                cav_notes.append(n_i)

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

        super(XlsImporter, self).__init__(
            attribute_set, note_set, question_enum, target_enum,
            question_attributes, target_attributes, criteria, caveats,
            spreadsheet_data.colormap)
